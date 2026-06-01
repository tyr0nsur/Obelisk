#!/usr/bin/env python3
"""Tests for the v1 complete-SDK release claim checker."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"
PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
SCOPED_RELEASE_STATEMENT_TEMPLATE = (
    REPO_ROOT / "release" / "v1" / "public-sdk" / "scoped-release-statement-template.md"
)
EXPERIMENTAL_EXCLUSION_DETAILS = {
    "obelisk.gameplay_policy_event.v1": "GameplayPolicyEvent is not included in v1.",
    "obelisk.chat_message.v1": "ChatMessageEvent is not included in v1.",
    "obelisk.chat.local_routing.v1": "chat routing is not included in v1.",
    "obelisk.inventory_item_copied_signals.v1": "inventory copied signals are not included in v1.",
}


def complete_excluded_manifest() -> tuple[dict, str]:
    manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
    manifest["v1_completion_required"] = True
    manifest["stable_release_contract"]["claim_allowed"] = True
    manifest["experimental_surfaces"] = []
    manifest["planning_surfaces"] = []
    release_lines = [
        "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
    ]
    for surface in manifest["surfaces"]:
        if surface["status"] == "promoted-experimental-only":
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            detail = EXPERIMENTAL_EXCLUSION_DETAILS.get(surface["id"], "experimental seed is not included in v1.")
            release_lines.append(f"{surface['id']}: excluded - {detail}")
        if surface["id"] in manifest["v1_sdk_completion_blockers"]:
            surface["status"] = "excluded"
            surface["public_contract"] = []
            if not isinstance(surface.get("v1_decision_contract"), dict):
                exclusions = surface.get("exclusions") if isinstance(surface.get("exclusions"), list) else []
                audit_units = surface.get("audit_units") if isinstance(surface.get("audit_units"), list) else []
                named_exclusions = [
                    str(item)
                    for item in [*exclusions, *audit_units]
                    if isinstance(item, str)
                ]
                required_text = (
                    f"no {', '.join(named_exclusions)} API is included in v1"
                    if named_exclusions
                    else f"no public API for {surface['id']} is included in v1"
                )
                surface["v1_decision_contract"] = {
                    "exclusion_requires": [
                        f"the v1 release statement names {surface['id']} as excluded",
                        f"the v1 release statement states that {required_text}",
                    ]
                }
            if surface["id"] not in manifest["post_v1_or_excluded_surfaces"]:
                manifest["post_v1_or_excluded_surfaces"].append(surface["id"])
            contract = surface.get("v1_decision_contract")
            detail_parts = ["no public API for this surface is included in v1"]
            if isinstance(contract, dict):
                for requirement in contract.get("exclusion_requires", []):
                    marker = "the v1 release statement states that "
                    if isinstance(requirement, str) and requirement.lower().startswith(marker):
                        detail_parts.append(requirement[len(marker) :])
            release_lines.append(f"{surface['id']}: excluded - {'; '.join(detail_parts)}")
    return manifest, "\n".join(release_lines) + "\n"


class PublicSdkV1CompletionCheckTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["python3", str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_inventory_copied_signals_contract_decision_manifest_is_required(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        surface_id = "obelisk.inventory_item_copied_signals.v1"
        filename = "inventory_item_copied_signals_public_contract_decisions.json"
        self.assertEqual(module.REQUIRED_PUBLIC_CONTRACT_DECISION_MANIFESTS[surface_id], filename)
        bridge_surface_id = "obelisk.command_principal_authz_response_bridge.v1"
        bridge_filename = "command_principal_authz_response_bridge_decisions.json"
        self.assertEqual(module.REQUIRED_ROUTE_GUARDRAIL_DECISION_MANIFESTS[bridge_surface_id], bridge_filename)
        lifecycle_surface_id = "obelisk.command_copied_response_intent_lifecycle.planning.v1"
        lifecycle_filename = "command_copied_response_intent_lifecycle_planning_decisions.json"
        self.assertEqual(
            module.REQUIRED_PLANNING_GUARDRAIL_DECISION_MANIFESTS[lifecycle_surface_id],
            lifecycle_filename,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_dir = Path(temp_dir) / "docs"
            decisions_dir.mkdir()
            original_default = module.DEFAULT_CONTRACT_DECISIONS_DIR
            module.DEFAULT_CONTRACT_DECISIONS_DIR = decisions_dir
            try:
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertEqual(missing[surface_id], filename)
                self.assertEqual(missing[bridge_surface_id], bridge_filename)
                self.assertEqual(missing[lifecycle_surface_id], lifecycle_filename)

                (decisions_dir / filename).write_text(
                    json.dumps(
                        {
                            "surface": surface_id,
                            "decision": "copied_signal_only",
                            "public_header_allowed": True,
                            "blocked_public_contract": {
                                "standalone_inventory_sdk_allowed": False,
                                "standalone_items_sdk_allowed": False,
                                "forbidden_terms": [
                                    "lookup",
                                    "mutation",
                                    "return override",
                                ],
                            },
                            "v1_completion_contract": {
                                "claim_effect": "does_not_complete_v1_sdk",
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(surface_id, missing)
                self.assertIn(lifecycle_surface_id, missing)
                self.assertIn(bridge_surface_id, missing)

                (decisions_dir / lifecycle_filename).write_text(
                    json.dumps(
                        {
                            "surface": lifecycle_surface_id,
                            "status": "blocked",
                            "public_header_allowed": False,
                            "public_header_symbols_now": [],
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(lifecycle_surface_id, missing)
                self.assertIn(bridge_surface_id, missing)

                (decisions_dir / bridge_filename).write_text(
                    json.dumps(
                        {
                            "surface": bridge_surface_id,
                            "status": "blocked",
                            "public_header_allowed": False,
                            "public_header_symbols_now": [],
                        }
                    ),
                    encoding="utf-8",
                )
                missing = module.missing_required_contract_decision_manifests(decisions_dir)
                self.assertNotIn(bridge_surface_id, missing)
            finally:
                module.DEFAULT_CONTRACT_DECISIONS_DIR = original_default

    def test_current_manifest_fails_closed_for_v1_completion(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.public-sdk-v1-completion-check.v1")
        self.assertFalse(payload["ready"])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("v1_completion_required_false", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})
        self.assertNotIn("required_public_contract_decision_manifest_missing", payload["blockers"])
        self.assertEqual(payload["missing_required_public_contract_decision_manifests"], {})
        self.assertNotIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["unresolved_completion_blockers"])
        self.assertIn("obelisk.gameplay_policy_event.v1", payload["unresolved_experimental_surfaces"])
        inventory_stability = payload["inventory_copied_signals_stability"]
        self.assertEqual(
            inventory_stability["schema"],
            "obelisk.inventory-item-copied-signals-stability-check.v1",
        )
        self.assertTrue(inventory_stability["ready"])
        self.assertEqual(inventory_stability["allowed_signal_count"], 5)
        self.assertEqual(inventory_stability["resource_kind_contract"], "category-only metadata")
        self.assertFalse(inventory_stability["public_sdk_ready"])
        self.assertFalse(inventory_stability["v1_completion_ready"])
        self.assertNotIn("inventory_copied_signals_stability_invalid", payload["blockers"])
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blocker_total"], 12)
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_total"], 4)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        self.assertNotIn(
            "obelisk.permissions_admin.v1",
            progress["completion_blockers_with_post_v1_or_excluded_outcome"],
        )
        self.assertIn(
            "bookkeeping only",
            progress["completion_blockers_with_post_v1_or_excluded_outcome_note"],
        )
        self.assertEqual(
            progress["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
            progress["completion_blockers_with_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            progress["completion_blockers_with_release_statement_post_v1_or_excluded_outcome"],
            [],
        )
        self.assertEqual(
            progress["completion_blockers_with_release_statement_post_v1_or_excluded_outcome_count"],
            0,
        )
        self.assertIn("obelisk.player_identity.v1", progress["completion_blockers_without_manifest_outcome"])
        self.assertEqual(progress["completion_blockers_without_manifest_outcome_count"], 6)
        self.assertGreaterEqual(progress["unresolved_completion_blocker_count"], 6)
        self.assertFalse(progress["stable_claim_allowed"])
        self.assertIn("status accounting", progress["outcome_accounting_note"])
        self.assertIn("never contribute percentage", progress["outcome_accounting_note"])
        self.assertIn("accounting only", progress["non_claim"])
        self.assertIn("core-first release readiness", " ".join(payload["non_claims"]))
        self.assertEqual(progress["manifest_outcome_missing_count"], 6)
        self.assertEqual(progress["release_statement_outcome_missing_count"], 6)
        self.assertEqual(progress["dependency_chain_remaining_count"], 4)
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["total"], 12)
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
                "obelisk.structure_census.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
            ],
        )

        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["release_statement_outcome_missing"],
            [
                "obelisk.inventory_items_mutation.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.player_services_economy_mobility.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.gameplay_tick_callbacks.v1",
            ],
        )
        blocker_rows = payload["v1_sdk_blocker_outcomes"]
        self.assertEqual(len(blocker_rows), 12)
        self.assertTrue(all(row["unresolved_for_complete_sdk_claim"] for row in blocker_rows))
        self.assertTrue(all("non_claim" in row for row in blocker_rows))
        self.assertEqual(blocker_rows[0]["surface"], "obelisk.player_identity.v1")
        self.assertIsNone(blocker_rows[0]["manifest_outcome"])
        self.assertIn("priority dependency-chain blocker", blocker_rows[0]["next_action"])
        self.assertEqual(blocker_rows[1]["surface"], "obelisk.permissions_admin.v1")
        self.assertIsNone(blocker_rows[1]["manifest_outcome"])
        self.assertIsNone(blocker_rows[1]["release_statement_outcome"])
        self.assertFalse(blocker_rows[1]["release_statement_contract_satisfied"])
        sections = payload["v1_sdk_report_sections"]
        self.assertEqual(
            set(sections),
            {
                "no_live_progress",
                "release_statement_bookkeeping",
                "promoted_demand_gaps",
                "runtime_required_blockers",
                "next_v1_work",
            },
        )
        self.assertFalse(sections["no_live_progress"]["live_server_required_for_this_report"])
        self.assertFalse(sections["no_live_progress"]["stable_claim_allowed"])
        self.assertIn("no-live inventory/package-shape progress", sections["no_live_progress"]["non_claim"])
        self.assertEqual(
            sections["release_statement_bookkeeping"]["manifest_post_v1_or_excluded_outcomes"],
            progress["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            sections["release_statement_bookkeeping"]["release_statement_post_v1_or_excluded_outcomes"],
            [],
        )
        self.assertEqual(
            sections["release_statement_bookkeeping"]["missing_blocker_outcomes"],
            payload["release_statement_missing_blocker_outcomes"],
        )
        self.assertIn("bookkeeping alone never approves", sections["release_statement_bookkeeping"]["non_claim"])
        self.assertEqual(
            sections["promoted_demand_gaps"]["minimum_promoted_demand_family_gaps"],
            payload["minimum_promoted_demand_family_gaps"],
        )
        self.assertFalse(
            sections["promoted_demand_gaps"]["all_minimum_demand_families_promoted_or_equivalent"]
        )
        self.assertTrue(sections["promoted_demand_gaps"]["claim_blocker_active"])
        self.assertIn(
            "Excluded/post-v1 outcomes do not satisfy",
            sections["promoted_demand_gaps"]["non_claim"],
        )
        self.assertEqual(
            sections["runtime_required_blockers"]["manifest_outcome_missing"],
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
        )
        self.assertEqual(
            sections["runtime_required_blockers"]["dependency_chain_remaining"],
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertIn(
            "v1_sdk_completion_blockers_unresolved",
            sections["runtime_required_blockers"]["blocker_codes"],
        )
        self.assertEqual(
            sections["next_v1_work"]["critical_path"],
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertEqual(
            sections["next_v1_work"]["product_decision_required"],
            payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing"],
        )
        self.assertEqual(
            sections["next_v1_work"]["release_statement_bookkeeping_required"],
            payload["release_statement_missing_blocker_outcomes"],
        )
        self.assertIn(
            "approved copied runtime principal lifecycle evidence",
            sections["next_v1_work"]["recommended_next_action"],
        )
        self.assertIn("prioritizes work only", sections["next_v1_work"]["non_claim"])

    def test_inventory_copied_signal_stability_checker_is_required(self) -> None:
        result = self.run_checker(
            "--inventory-copied-signals-stability",
            "/tmp/obelisk-missing-inventory-copied-signals-checker.py",
            "--json",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("inventory_copied_signals_stability_output_invalid", payload["blockers"])
        self.assertEqual(
            payload["inventory_copied_signals_stability"]["path"],
            "/tmp/obelisk-missing-inventory-copied-signals-checker.py",
        )
        self.assertEqual(payload["inventory_copied_signals_stability"]["exit_code"], 2)

    def test_missing_p0_dependency_chain_blocker_reports_specific_mismatch(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        p0_chain = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        manifest["v1_dependency_sequence"] = list(p0_chain)
        manifest["v1_required_dependency_chain"] = list(p0_chain)
        manifest["v1_sdk_completion_blockers"] = [
            surface_id
            for surface_id in manifest["v1_sdk_completion_blockers"]
            if surface_id != "obelisk.command_chat_response_path.v1"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertIn(
            "v1_required_dependency_chain_missing_from_completion_blockers",
            payload["blockers"],
        )
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertEqual(
            payload["missing_v1_required_dependency_chain_completion_blockers"],
            ["obelisk.command_chat_response_path.v1"],
        )
        self.assertEqual(payload["v1_required_dependency_chain"], p0_chain)
        self.assertEqual(payload["v1_dependency_sequence"], p0_chain)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_total"], 4)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["dependency_chain_remaining_count"], 4)
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["v1_sdk_report_sections"]["next_v1_work"]["critical_path"],
        )
        self.assertIn(
            "obelisk.command_chat_response_path.v1",
            payload["unpromoted_required_dependency_chain"],
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])

    def test_missing_canonical_non_p0_completion_blocker_still_counts_in_accounting(self) -> None:
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        omitted = "obelisk.operator_ingress_storage.v1"
        manifest["v1_sdk_completion_blockers"] = [
            surface_id
            for surface_id in manifest["v1_sdk_completion_blockers"]
            if surface_id != omitted
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertIn(omitted, payload["missing_canonical_completion_blockers"])
        self.assertEqual(payload["v1_sdk_progress"]["completion_blocker_total"], 12)
        self.assertIn(omitted, [row["surface"] for row in payload["v1_sdk_blocker_outcomes"]])

    def test_human_output_names_actionable_v1_blocker_details(self) -> None:
        result = self.run_checker(check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("The stable v1 SDK claim remains disabled", result.stdout)
        self.assertIn("12-blocker outcome accounting: 6 need manifest outcomes; 6 need release-statement outcomes", result.stdout)
        self.assertIn("High-demand v1 completion blockers are still unresolved", result.stdout)
        self.assertIn("obelisk.player_identity.v1", result.stdout)
        self.assertIn("Experimental copied-data seeds still need an explicit v1 outcome", result.stdout)
        self.assertIn("obelisk.chat_message.v1", result.stdout)
        self.assertIn("Use --json for the full machine-readable report.", result.stdout)

    def test_completion_gate_rejects_route_gate_public_or_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'checks': [{\n"
                "        'name': 'command_chat_response_public_readiness',\n"
                "        'public_or_runtime_claims': ['reply_api_allowed'],\n"
                "        'runtime_delivery_allowed': True,\n"
                "        'notes': ['reply API is public and ready']\n"
                "    }, {\n"
                "        'name': 'commands_replies_public_readiness',\n"
                "        'non_claim': 'reply API is not public, not ready, and must remain blocked'\n"
                "    }],\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_public_or_runtime_claims", payload["blockers"])
        route_gate = payload["command_permission_route_gate"]
        self.assertIn(
            "checks[0].public_or_runtime_claims:reply_api_allowed",
            route_gate["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].runtime_delivery_allowed",
            route_gate["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].notes[0]:positive_text_claim",
            route_gate["public_or_runtime_claims"],
        )
        self.assertNotIn(
            "checks[1].non_claim:positive_text_claim",
            route_gate["public_or_runtime_claims"],
        )
        self.assertFalse(payload["stable_claim_allowed"])

    def test_completion_gate_rejects_route_gate_schema_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'wrong-schema',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_schema_mismatch", payload["blockers"])

    def test_route_gate_claim_scanner_rejects_public_command_reply_aliases(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        claims = module.command_permission_route_gate_public_or_runtime_claims(
            {
                "schema": "obelisk.command-permission-route-gate-check.v1",
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "checks": [
                    {
                        "name": "commands_replies_public_readiness",
                        "public_command_router_allowed": True,
                        "public_reply_or_send_chat_abi_allowed": True,
                        "public_reply_api": True,
                        "public_send_chat_api": True,
                        "public_reply_abi_allowed": True,
                        "public_send_chat_abi_allowed": "ready",
                        "public-reply-api": True,
                        "publicSendChatApi": True,
                        "reply_send_chat_router_claims_allowed": True,
                        "public_abi_allowed": "ready",
                        "permissions_admin_ready": True,
                        "permissions_ready": True,
                        "permission_ready": True,
                        "reply_allowed": 1,
                        "send_chat_allowed": "true",
                        "notes": [
                            "send-chat ABI is public and ready",
                            "command routing is public and ready",
                            "permissions/admin is public and ready",
                            "replies API is public and ready",
                            "command response path is live",
                            "reply endpoint is live",
                            "send chat API is operational",
                        ],
                    }
                ],
            }
        )

        self.assertIn("checks[0].public_command_router_allowed", claims)
        self.assertIn("checks[0].public_reply_or_send_chat_abi_allowed", claims)
        self.assertIn("checks[0].public_reply_api", claims)
        self.assertIn("checks[0].public_send_chat_api", claims)
        self.assertIn("checks[0].public_reply_abi_allowed", claims)
        self.assertIn("checks[0].public_send_chat_abi_allowed", claims)
        self.assertIn("checks[0].public-reply-api", claims)
        self.assertIn("checks[0].publicSendChatApi", claims)
        self.assertIn("checks[0].reply_send_chat_router_claims_allowed", claims)
        self.assertIn("checks[0].public_abi_allowed", claims)
        self.assertIn("checks[0].permissions_admin_ready", claims)
        self.assertIn("checks[0].permissions_ready", claims)
        self.assertIn("checks[0].permission_ready", claims)
        self.assertIn("checks[0].reply_allowed", claims)
        self.assertIn("checks[0].send_chat_allowed", claims)
        self.assertIn("checks[0].notes[0]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[1]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[2]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[3]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[4]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[5]:positive_text_claim", claims)
        self.assertIn("checks[0].notes[6]:positive_text_claim", claims)

    def test_completion_gate_rejects_route_gate_alias_claims_without_claims_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            route_gate_path = Path(temp_dir) / "fake_route_gate.py"
            route_gate_path.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'schema': 'obelisk.command-permission-route-gate-check.v1',\n"
                "    'valid': True,\n"
                "    'accepted_for_planning': True,\n"
                "    'planning_only': True,\n"
                "    'promotion_ready': False,\n"
                "    'public_sdk_ready': False,\n"
                "    'public_abi_ready': False,\n"
                "    'runtime_ready': False,\n"
                "    'public_header_allowed': False,\n"
                "    'checks': [{\n"
                "        'name': 'commands_replies_public_readiness',\n"
                "        'public_command_router_allowed': True,\n"
                "        'public_reply_or_send_chat_abi_allowed': True,\n"
                "        'public_reply_api': 'ready',\n"
                "        'public_send_chat_api': 'ready',\n"
                "        'reply_allowed': 1,\n"
                "        'send_chat_allowed': 'true'\n"
                "    }],\n"
                "    'blockers': []\n"
                "} ))\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--command-permission-route-gate",
                str(route_gate_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("command_permission_route_gate_public_or_runtime_claims", payload["blockers"])
        claims = payload["command_permission_route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].public_command_router_allowed", claims)
        self.assertIn("checks[0].public_reply_or_send_chat_abi_allowed", claims)
        self.assertFalse(payload["stable_claim_allowed"])

    def test_blocked_contract_decisions_detect_untracked_public_header_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskPlayerIdentity {\n"
                "    uint32_t abi_version;\n"
                "    uint64_t principal_handle;\n"
                "} ObeliskPlayerIdentity;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterPlayerIdentityWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "player_identity_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-identity-public-contract-decisions.v1",
                        "surface": "obelisk.player_identity.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.player_identity.v1")
        self.assertIn("ObeliskPlayerIdentity", drift["undeclared_symbols"])
        self.assertIn("RegisterPlayerIdentityWithOwnerTokenHandle", drift["undeclared_symbols"])
        self.assertIn("principal_handle", drift["undeclared_symbols"])

    def test_blocked_permissions_contract_detects_public_reason_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef uint64_t ObeliskPermissionReasonFlags;\n"
                "#define OBELISK_PERMISSION_REASON_DENY 1\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t reason_flags;\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "permissions_admin_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.permissions-admin-public-contract-decisions.v1",
                        "surface": "obelisk.permissions_admin.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(
            item
            for item in payload["blocked_public_contract_header_symbols"].values()
            if item["surface"] == "obelisk.permissions_admin.v1"
        )
        self.assertIn("ObeliskPermissionReasonFlags", drift["undeclared_symbols"])
        self.assertIn("OBELISK_PERMISSION_REASON_DENY", drift["undeclared_symbols"])
        self.assertIn("reason_flags", drift["undeclared_symbols"])

    def test_blocked_contract_symbol_drift_ignores_existing_chat_message_rc_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskChatMessageEvent { uint32_t abi_version; } ObeliskChatMessageEvent;\n"
                "typedef void (*ObeliskChatMessageEventCallback)(const ObeliskChatMessageEvent* event, void* user_data);\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterChatMessageEventWithOwnerTokenHandle)(uint64_t ownerToken, ObeliskChatMessageEventCallback callback, void* userData);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_chat_response_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})

    def test_blocked_commands_replies_contract_detects_command_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskCommandPayload { uint32_t abi_version; } ObeliskCommandPayload;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterCommandWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "commands_replies_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.commands-replies-public-contract-decisions.v1",
                        "surface": "obelisk.commands_replies.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.commands_replies.v1")
        self.assertIn("ObeliskCommandPayload", drift["undeclared_symbols"])
        self.assertIn("RegisterCommandWithOwnerTokenHandle", drift["undeclared_symbols"])

    def test_route_guardrail_contract_detects_forbidden_token_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE 0x80000000u\n"
                "typedef struct ObeliskCommandPrincipalAuthzResponseBridge { unsigned abi_version; } ObeliskCommandPrincipalAuthzResponseBridge;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_principal_authz_response_bridge_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-principal-authz-response-bridge-decisions.v1",
                        "surface": "obelisk.command_principal_authz_response_bridge.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": [],
                        "public_header_forbidden_tokens": [
                            "OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE",
                            "ObeliskCommandPrincipalAuthzResponseBridge",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift = next(iter(payload["blocked_public_contract_header_symbols"].values()))
        self.assertEqual(drift["surface"], "obelisk.command_principal_authz_response_bridge.v1")
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE", drift["undeclared_symbols"])
        self.assertIn("ObeliskCommandPrincipalAuthzResponseBridge", drift["undeclared_symbols"])

    def test_blocked_contract_symbols_are_not_reported_when_contract_lists_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterCommandResponseWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            (decisions_dir / "command_chat_response_public_contract_decisions.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
                        "surface": "obelisk.command_chat_response_path.v1",
                        "status": "blocked",
                        "public_header_allowed": False,
                        "public_header": str(header_path),
                        "public_header_symbols_now": ["RegisterCommandResponseWithOwnerTokenHandle"],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertNotIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        self.assertEqual(payload["blocked_public_contract_header_symbols"], {})

    def test_manifest_blocked_side_lane_contracts_detect_public_header_symbols(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            header_path = temp_path / "ObeliskApi.h"
            decisions_dir = temp_path / "docs"
            manifest_path = temp_path / "public_sdk_surfaces.json"
            release_statement_path = temp_path / "RELEASE_STATEMENT.md"
            decisions_dir.mkdir()
            header_path.write_text(
                "#pragma once\n"
                "#include <stdint.h>\n"
                "typedef struct ObeliskStructureCensus { uint32_t abi_version; } ObeliskStructureCensus;\n"
                "typedef struct ObeliskDinoSdk { uint32_t abi_version; } ObeliskDinoSdk;\n"
                "typedef struct ObeliskInventoryMutation { uint32_t abi_version; } ObeliskInventoryMutation;\n"
                "typedef struct ObeliskObjectIdentity { uint32_t abi_version; } ObeliskObjectIdentity;\n"
                "typedef struct ObeliskEconomyApi { uint32_t abi_version; } ObeliskEconomyApi;\n"
                "typedef struct ObeliskRCONIngress { uint32_t abi_version; } ObeliskRCONIngress;\n"
                "typedef struct ObeliskPluginWatchdog { uint32_t abi_version; } ObeliskPluginWatchdog;\n"
                "typedef struct ObeliskGameplayTickCallback { uint32_t abi_version; } ObeliskGameplayTickCallback;\n"
                "typedef struct ObeliskApi {\n"
                "    uint64_t (*RegisterStructureCensusWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterMissionWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*GiveItemWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterResourceHandleWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterEconomyWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterOperatorReloadWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterPluginWatchdogWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "    uint64_t (*RegisterGameplayTickWithOwnerTokenHandle)(uint64_t ownerToken);\n"
                "} ObeliskApi;\n",
                encoding="utf-8",
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")

            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--public-header",
                str(header_path),
                "--contract-decisions-dir",
                str(decisions_dir),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked_public_contract_header_symbols_detected", payload["blockers"])
        drift_by_surface = {
            drift["surface"]: drift["undeclared_symbols"]
            for drift in payload["blocked_public_contract_header_symbols"].values()
        }
        self.assertIn("ObeliskStructureCensus", drift_by_surface["obelisk.structure_census.v1"])
        self.assertIn("RegisterMissionWithOwnerTokenHandle", drift_by_surface["obelisk.mission_transfer_dino_tribe.v1"])
        self.assertIn("GiveItemWithOwnerTokenHandle", drift_by_surface["obelisk.inventory_items_mutation.v1"])
        self.assertIn("ObeliskObjectIdentity", drift_by_surface["obelisk.object_identity_resource_handle.v1"])
        self.assertIn(
            "RegisterResourceHandleWithOwnerTokenHandle",
            drift_by_surface["obelisk.object_identity_resource_handle.v1"],
        )
        self.assertIn("RegisterEconomyWithOwnerTokenHandle", drift_by_surface["obelisk.player_services_economy_mobility.v1"])
        self.assertIn("ObeliskRCONIngress", drift_by_surface["obelisk.operator_ingress_storage.v1"])
        self.assertIn("ObeliskPluginWatchdog", drift_by_surface["obelisk.lifecycle_ops_recovery.v1"])
        self.assertIn("RegisterGameplayTickWithOwnerTokenHandle", drift_by_surface["obelisk.gameplay_tick_callbacks.v1"])

    def test_current_manifest_reports_exact_unresolved_v1_surface_groups(self) -> None:
        result = self.run_checker("--json", check=False)
        payload = json.loads(result.stdout)
        manifest = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
        surfaces = {surface["id"]: surface for surface in manifest["surfaces"]}
        gameplay = surfaces["obelisk.mission_transfer_dino_tribe.v1"]

        self.assertEqual(
            payload["unresolved_completion_blockers"],
            [
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
                "obelisk.structure_census.v1",
            ],
        )
        self.assertEqual(
            [leaf["id"] for leaf in gameplay["leaf_decision_units"]],
            ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
        )
        self.assertTrue(gameplay["v1_decision_contract"]["leaf_split_reviewed"])
        self.assertEqual({leaf["status"] for leaf in gameplay["leaf_decision_units"]}, {"planning"})
        self.assertEqual(
            payload["unresolved_experimental_surfaces"],
            [
                "obelisk.chat.local_routing.v1",
                "obelisk.chat_message.v1",
                "obelisk.gameplay_policy_event.v1",
                "obelisk.inventory_item_copied_signals.v1",
            ],
        )
        self.assertEqual(
            payload["release_statement_missing_blocker_outcomes"],
            [
                "obelisk.gameplay_tick_callbacks.v1",
                "obelisk.inventory_items_mutation.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.player_services_economy_mobility.v1",
            ],
        )
        self.assertEqual(payload["promoted_surfaces_with_unresolved_dependencies"], {})
        self.assertEqual(payload["promoted_surfaces_without_evidence"], [])
        self.assertEqual(payload["promoted_blockers_without_evidence"], [])

    def test_scoped_release_statement_template_passes_statement_scope_only(self) -> None:
        result = self.run_checker(
            "--release-statement",
            str(SCOPED_RELEASE_STATEMENT_TEMPLATE),
            "--validate-release-statement-scope",
            "--json",
        )
        payload = json.loads(result.stdout)

        self.assertFalse(payload["ready"])
        self.assertTrue(payload["scoped_release_statement"]["ready"])
        self.assertFalse(payload["scoped_release_statement"]["stable_v1_sdk_claim_allowed"])
        self.assertEqual(
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
            [
                "obelisk.gameplay_tick_callbacks.v1",
                "obelisk.inventory_items_mutation.v1",
                "obelisk.lifecycle_ops_recovery.v1",
                "obelisk.object_identity_resource_handle.v1",
                "obelisk.operator_ingress_storage.v1",
                "obelisk.player_services_economy_mobility.v1",
            ],
        )
        self.assertEqual(
            payload["v1_sdk_progress"]["completion_blockers_with_release_statement_post_v1_or_excluded_outcome"],
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_post_v1_or_excluded_outcome"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "release_statement_post_v1_or_excluded_outcomes"
            ],
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "manifest_post_v1_or_excluded_outcomes"
            ],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "missing_blocker_outcomes"
            ],
            [],
        )
        self.assertFalse(payload["v1_sdk_report_sections"]["no_live_progress"]["stable_claim_allowed"])
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["manifest_outcome_missing_count"], 6)
        self.assertEqual(payload["v1_sdk_blocker_outcome_summary"]["release_statement_outcome_missing_count"], 0)
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        for surface in (
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ):
            with self.subTest(surface=surface):
                self.assertIsNone(outcome_by_surface[surface]["release_statement_outcome"])
                self.assertEqual(
                    outcome_by_surface[surface]["next_action"],
                    "priority dependency-chain blocker: promote with evidence; excluded/post-v1 cannot satisfy complete SDK",
                )
        self.assertFalse(
            outcome_by_surface["obelisk.permissions_admin.v1"][
                "release_statement_contract_satisfied"
            ]
        )
        self.assertIsNone(outcome_by_surface["obelisk.player_identity.v1"]["manifest_outcome"])
        self.assertFalse(
            outcome_by_surface["obelisk.player_identity.v1"][
                "release_statement_contract_satisfied"
            ]
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertNotIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], [])
        self.assertIn("stable_release_contract_claim_not_allowed", payload["blockers"])
        self.assertIn("top_level_planning_surfaces_unresolved_for_v1_claim", payload["blockers"])

        full_gate = self.run_checker(
            "--release-statement",
            str(SCOPED_RELEASE_STATEMENT_TEMPLATE),
            "--json",
            check=False,
        )
        full_payload = json.loads(full_gate.stdout)
        self.assertEqual(full_gate.returncode, 1)
        self.assertFalse(full_payload["ready"])
        self.assertIn("v1_completion_required_false", full_payload["blockers"])

    def test_scoped_release_statement_scope_rejects_broad_v1_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "Inventory SDK is ready in v1.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )

    def test_scoped_release_statement_scope_rejects_v1_stable_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "This is a v1.0 stable release.\n"
                + "This statement authorizes v1 stable wording.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["scoped_release_statement"]["ready"])
        self.assertIn(
            "release_statement_forbidden_broad_claims",
            payload["scoped_release_statement"]["blocking_report_blockers"],
        )
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        self.assertIn("This is a v1.0 stable release.", forbidden_claims)
        self.assertIn("This statement authorizes v1 stable wording.", forbidden_claims)

    def test_scoped_release_statement_scope_allows_negated_v1_stable_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            statement_path = Path(temp_dir) / "SCOPED_RELEASE_STATEMENT.md"
            statement_path.write_text(
                SCOPED_RELEASE_STATEMENT_TEMPLATE.read_text(encoding="utf-8")
                + "v1 stable remains blocked until the full gate passes.\n",
                encoding="utf-8",
            )

            result = self.run_checker(
                "--release-statement",
                str(statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["scoped_release_statement"]["ready"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], [])
        self.assertIn("v1_completion_required_false", payload["blockers"])

    def test_complete_claim_rejects_all_excluded_blockers_as_scoped_only(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )
            scoped_result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--validate-release-statement-scope",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertTrue(payload["stable_release_contract_claim_allowed"])
        self.assertEqual(payload["installed_sdk_package_shape_guardrail_drift"], [])
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertIn("p0_dependency_chain_outcomes_scoped_non_complete_only", payload["blockers"])
        self.assertEqual(
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(payload["p0_dependency_chain_scoped_non_complete_outcome_count"], 4)
        self.assertEqual(
            payload["minimum_promoted_demand_family_gaps"],
            payload["minimum_promoted_demand_families"],
        )
        self.assertFalse(payload["v1_sdk_progress"]["stable_claim_allowed"])
        self.assertTrue(payload["v1_sdk_progress"]["stable_release_contract_claim_allowed"])
        self.assertEqual(payload["v1_sdk_progress"]["completion_blockers_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_outcome_count"], 4)
        self.assertEqual(
            payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_outcomes"],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertIn(
            "do not increase p0_chain_promoted_count",
            payload["v1_sdk_progress"]["p0_chain_scoped_non_complete_note"],
        )
        self.assertEqual(payload["v1_sdk_progress"]["complete_sdk_claim_progress_percent"], 0)
        outcome_by_surface = {row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]}
        identity_outcome = outcome_by_surface["obelisk.player_identity.v1"]
        self.assertTrue(identity_outcome["is_p0_dependency_chain"])
        self.assertTrue(identity_outcome["scoped_non_complete_outcome_only"])
        self.assertFalse(identity_outcome["counts_toward_complete_sdk_claim"])
        self.assertTrue(identity_outcome["unresolved_for_complete_sdk_claim"])
        self.assertIn("scoped non-complete outcome only", identity_outcome["next_action"])
        self.assertEqual(
            payload["v1_sdk_blocker_outcome_summary"]["p0_scoped_non_complete_outcomes"],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["release_statement_bookkeeping"][
                "p0_scoped_non_complete_outcomes"
            ],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        self.assertEqual(
            payload["v1_sdk_report_sections"]["runtime_required_blockers"][
                "p0_scoped_non_complete_outcomes"
            ],
            payload["p0_dependency_chain_scoped_non_complete_outcomes"],
        )
        scoped_payload = json.loads(scoped_result.stdout)
        self.assertFalse(scoped_payload["ready"])
        self.assertTrue(scoped_payload["scoped_release_statement"]["ready"])
        self.assertFalse(scoped_payload["scoped_release_statement"]["stable_v1_sdk_claim_allowed"])
        self.assertIn(
            "complete_sdk_claim_requires_promoted_demand_families",
            scoped_payload["scoped_release_statement"]["allowed_remaining_blockers"],
        )
        self.assertIn(
            "p0_dependency_chain_outcomes_scoped_non_complete_only",
            scoped_payload["scoped_release_statement"]["allowed_remaining_blockers"],
        )
        self.assertEqual(scoped_payload["scoped_release_statement"]["blocking_report_blockers"], [])

    def test_minimum_promoted_demand_family_accepts_explicit_promoted_equivalent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.inventory_items_mutation_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertNotIn(blocker_id, gaps)
        self.assertEqual(satisfied_by[blocker_id], equivalent_id)

    def test_minimum_promoted_demand_family_rejects_p0_equivalent(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.player_identity.v1"
        equivalent_id = "obelisk.player_identity_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "v1_completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_minimum_promoted_demand_family_ignores_completion_equivalent_alias(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        blocker_id = "obelisk.inventory_items_mutation.v1"
        equivalent_id = "obelisk.inventory_items_mutation_alias_equivalent.v1"
        surfaces_by_id = {
            surface_id: {"id": surface_id, "status": "promoted"}
            for surface_id in module.CANONICAL_COMPLETE_SDK_MINIMUM_PROMOTED_DEMAND_FAMILIES
        }
        surfaces_by_id[blocker_id] = {"id": blocker_id, "status": "excluded"}
        surfaces_by_id[equivalent_id] = {
            "id": equivalent_id,
            "status": "promoted",
            "completion_equivalent_for": [blocker_id],
            "evidence": {"tests": ["tests/sdk_consumer"]},
        }
        stable_contract = {
            "promoted_demand_family_equivalents": {
                blocker_id: equivalent_id,
            }
        }

        gaps, satisfied_by = module.complete_sdk_minimum_promoted_demand_family_gaps(
            surfaces_by_id,
            stable_contract,
        )

        self.assertFalse(module.surface_declares_completion_equivalent(surfaces_by_id[equivalent_id], blocker_id))
        self.assertIn(blocker_id, gaps)
        self.assertNotIn(blocker_id, satisfied_by)

    def test_empty_or_truncated_manifest_fails_closed(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical_surface_id_missing", payload["blockers"])
        self.assertIn("canonical_v1_completion_blocker_missing", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_surfaces"])
        self.assertIn("obelisk.player_identity.v1", payload["missing_canonical_completion_blockers"])

    def test_stable_release_contract_must_keep_canonical_claim_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["stable_release_contract"]["claim_requires"] = [
            item
            for item in manifest["stable_release_contract"]["claim_requires"]
            if "promoted-experimental-only" not in item
        ]
        manifest["stable_release_contract"]["not_sufficient"] = [
            item
            for item in manifest["stable_release_contract"]["not_sufficient"]
            if item != "Foundation/Plugin Hub seed package shape"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stable_release_contract_claim_requires_incomplete", payload["blockers"])
        self.assertIn("stable_release_contract_not_sufficient_incomplete", payload["blockers"])
        self.assertEqual(
            payload["stable_release_contract_missing_claim_requires"],
            ["no promoted-experimental-only surface remains unresolved"],
        )
        self.assertEqual(
            payload["stable_release_contract_missing_not_sufficient"],
            ["Foundation/Plugin Hub seed package shape"],
        )

    def test_stable_release_contract_rejects_ambiguous_demand_family_equivalent_text(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        canonical = (
            "non-P0 minimum promoted demand families are promoted or satisfied by explicit "
            "v1_completion_equivalent_for records before complete/full/production SDK wording; "
            "no demand-family equivalent or legacy completion alias may satisfy a P0 dependency-chain surface"
        )
        legacy = (
            "minimum promoted demand families are promoted or satisfied by explicit completion "
            "equivalents before complete/full/production SDK wording"
        )
        manifest["stable_release_contract"]["claim_requires"] = [
            legacy if item == canonical else item
            for item in manifest["stable_release_contract"]["claim_requires"]
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            release_statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            release_statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(release_statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stable_release_contract_claim_requires_incomplete", payload["blockers"])
        self.assertIn(canonical, payload["stable_release_contract_missing_claim_requires"])

    def test_installed_sdk_package_shape_must_remain_non_claim_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["installed_sdk_package_shape"]["status"] = "plugin-hub-seed-ready"
        manifest["installed_sdk_package_shape"]["not_sufficient_for"] = [
            item
            for item in manifest["installed_sdk_package_shape"]["not_sufficient_for"]
            if item != "Plugin Hub seed/package publication"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("installed_sdk_package_shape_guardrail_incomplete", payload["blockers"])
        self.assertIn("status", payload["installed_sdk_package_shape_guardrail_drift"])
        self.assertIn(
            "not_sufficient_for:Plugin Hub seed/package publication",
            payload["installed_sdk_package_shape_guardrail_drift"],
        )

    def test_installed_sdk_package_shape_canonical_files_are_required(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["installed_sdk_package_shape"]["installed_files"].append(
            "lib/cmake/Obelisk/PluginHubTargets.cmake"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("installed_sdk_package_shape_guardrail_incomplete", payload["blockers"])
        self.assertIn("installed_files", payload["installed_sdk_package_shape_guardrail_drift"])

    def test_release_statement_must_name_non_promoted_blockers(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_negated_or_global_outcome_wording(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1 is intentionally not described here as excluded.\n"
                "Other items may be post-v1.\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_blocker_outcomes"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_ambiguous_outcome_punctuation(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.player_identity.v1: excluded -",
            "obelisk.player_identity.v1: excluded? actually included -",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])
        self.assertIn("obelisk.player_identity.v1", payload["release_statement_missing_blocker_outcomes"])

    def test_release_statement_rejects_negated_contract_substring_in_surface_record(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - it is false that no player identity API is included in v1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_not_the_case_negation(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - it is not the case that "
                "no player identity API is included in v1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_contradictory_exception_after_required_text(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "planning_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded - no player identity API is included in v1; "
                "except player identity is included in v1 for admins.\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_release_statement_rejects_complete_sdk_claim_after_excluded_blocker_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = "\n".join(
            (
                line + "; Inventory SDK is a complete SDK for v1 plugin authors."
                if line.startswith("obelisk.inventory_items_mutation.v1: excluded -")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.inventory_items_mutation.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_rejects_available_support_claim_after_post_v1_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface["status"] = "post-v1"
                break
        release_statement = "\n".join(
            (
                line.replace("obelisk.commands_replies.v1: excluded -", "obelisk.commands_replies.v1: post-v1 -")
                + "; command router support is available in v1."
                if line.startswith("obelisk.commands_replies.v1: excluded -")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn("obelisk.commands_replies.v1", payload["release_statement_missing_exclusion_contracts"])

    def test_release_statement_rejects_global_complete_sdk_claim_for_excluded_blocker(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += "Release summary: Inventory SDK is a complete SDK for v1 plugin authors.\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.inventory_items_mutation.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_rejects_ready_claims_for_inventory_items_and_plugin_hub(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Inventory SDK is ready in v1.\n"
            "Items SDK is ready in v1.\n"
            "Plugin Hub completion is ready for v1.\n"
            "Plugin Hub is complete for v1 plugin authors.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Inventory SDK is ready in v1.",
            "Items SDK is ready in v1.",
            "Plugin Hub completion is ready for v1.",
            "Plugin Hub is complete for v1 plugin authors.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_allows_negated_inventory_items_and_plugin_hub_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Inventory SDK is not ready in v1.\n"
            "Items SDK is not ready in v1.\n"
            "Plugin Hub completion remains blocked for v1.\n"
            "Plugin Hub is not complete for v1 plugin authors.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_allows_plugin_hub_post_sdk_deferred_wording(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Plugin Hub post-SDK-complete planning remains parked.\n"
            "Plugin Hub seed/package publication remains post-SDK.\n"
            "Plugin Hub work resumes after SDK completion.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_plugin_hub_publication_and_scope_overclaims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Plugin Hub is included in v1.\n"
            "Plugin Hub API is public.\n"
            "Plugin Hub package is published for v1.\n"
            "Plugin Hub publication is in release scope.\n"
            "Stable SDK includes Plugin Hub.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Plugin Hub is included in v1.",
            "Plugin Hub API is public.",
            "Plugin Hub package is published for v1.",
            "Plugin Hub publication is in release scope.",
            "Stable SDK includes Plugin Hub.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_rejects_identity_permissions_command_mission_buff_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Player identity SDK is ready in v1.\n"
            "Permissions/admin SDK is supported in v1.\n"
            "Command response API is available in v1.\n"
            "Commands/replies API is included in v1.\n"
            "Mission SDK is ready in v1.\n"
            "Buff SDK is supported in v1.\n"
            "Buff/status SDK is included in v1.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Player identity SDK is ready in v1.",
            "Permissions/admin SDK is supported in v1.",
            "Command response API is available in v1.",
            "Commands/replies API is included in v1.",
            "Mission SDK is ready in v1.",
            "Buff SDK is supported in v1.",
            "Buff/status SDK is included in v1.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_allows_negated_identity_permissions_command_mission_buff_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Player identity SDK is not ready in v1.\n"
            "Permissions/admin SDK remains blocked in v1.\n"
            "Command response API is not available in v1.\n"
            "Commands/replies API is not included in v1.\n"
            "Mission SDK is not ready in v1.\n"
            "Buff SDK is not supported in v1.\n"
            "Buff/status SDK is not included in v1.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_non_promotional_evidence_as_v1_claim_basis(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Candidate evidence proves a complete SDK for v1 plugin authors.\n"
            "Static orientation readiness makes the public SDK ready.\n"
            "Consume-only planning evidence validates v1.0 stable.\n"
            "Foundation package shape support is production-ready SDK support.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Candidate evidence proves a complete SDK for v1 plugin authors.",
            "Static orientation readiness makes the public SDK ready.",
            "Consume-only planning evidence validates v1.0 stable.",
            "Foundation package shape support is production-ready SDK support.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)

    def test_release_statement_rejects_without_prefixed_affirmative_claims(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Without promotion, Inventory SDK is ready in v1.\n"
            "Without promoted dependencies, command router support is available in v1.\n"
            "Without evidence, Candidate evidence proves a complete SDK for v1 plugin authors.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_broad_claims", payload["blockers"])
        forbidden_claims = "\n".join(payload["release_statement_forbidden_broad_claims"])
        for term in (
            "Without promotion, Inventory SDK is ready in v1.",
            "Without evidence, Candidate evidence proves a complete SDK for v1 plugin authors.",
        ):
            with self.subTest(term=term):
                self.assertIn(term, forbidden_claims)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.commands_replies.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_allows_negated_non_promotional_evidence_boundaries(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "Candidate evidence does not prove a complete SDK for v1 plugin authors.\n"
            "Static orientation readiness is not public SDK readiness.\n"
            "Consume-only planning evidence does not validate v1.0 stable.\n"
            "Foundation package shape support is not production-ready SDK support.\n"
            "Without promoted demand families, no complete SDK claim is allowed.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_forbidden_broad_claims", payload["blockers"])
        self.assertEqual(payload["release_statement_forbidden_broad_claims"], [])

    def test_release_statement_rejects_blocked_claim_inside_other_surface_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1.",
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1; chat replies are included in v1.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn("obelisk.commands_replies.v1", payload["release_statement_missing_exclusion_contracts"])

    def test_release_statement_rejects_side_lane_claim_inside_other_surface_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.inventory_item_copied_signals.v1: excluded - inventory copied signals are not included in v1.",
            "obelisk.inventory_item_copied_signals.v1: excluded - inventory copied signals are not included in v1; Mission SDK is included in v1.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertIn(
            "obelisk.mission_transfer_dino_tribe.v1",
            payload["release_statement_missing_exclusion_contracts"],
        )

    def test_release_statement_rejects_duplicate_or_mixed_surface_records(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement += (
            "obelisk.player_identity.v1: post-v1 - contradictory duplicate record for the same surface.\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_duplicate_or_mixed_surface_records", payload["blockers"])
        self.assertEqual(payload["release_statement_duplicate_or_mixed_records"], ["obelisk.player_identity.v1"])

    def test_release_statement_accepts_exact_outcome_with_no_explanatory_text(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.player_identity.v1: excluded - no public API for this surface is included in v1; "
            "no player identity/principal, player lookup, cross-instance identity, session lifecycle, "
            "permissions/admin, commands/replies, economy/mobility, mutation, return override, "
            "ResourceHandle, UE pointer, raw params, or UObject identity API is included in v1\n",
            "obelisk.player_identity.v1: excluded - no player identity/principal, player lookup, "
            "cross-instance identity, session lifecycle, permissions/admin, commands/replies, "
            "economy/mobility, mutation, return override, ResourceHandle, UE pointer, raw params, "
            "or UObject identity API is included in v1\n",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertNotIn("release_statement_missing_non_promoted_blocker_outcomes", payload["blockers"])

    def test_release_statement_must_satisfy_surface_exclusion_contract(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.player_identity.v1"],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "excluded",
                    "public_contract": [],
                    "v1_decision_contract": {
                        "exclusion_requires": [
                            "the v1 release statement names obelisk.player_identity.v1 as excluded",
                            "the v1 release statement states that no player identity API is included in v1",
                        ]
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(
                "Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.\n"
                "obelisk.player_identity.v1: excluded\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.player_identity.v1"])

    def test_non_promoted_public_contract_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.commands_replies.v1"],
            "post_v1_or_excluded_surfaces": ["obelisk.commands_replies.v1"],
            "surfaces": [
                {
                    "id": "obelisk.commands_replies.v1",
                    "status": "post-v1",
                    "public_contract": ["RegisterCommand"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_contract"], ["obelisk.commands_replies.v1"])

    def test_non_promoted_public_abi_blocks_claim_even_with_promoted_dependencies(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            }:
                surface["status"] = "promoted"
                surface["public_contract"] = [f"{surface['id']}.placeholder"]
                surface["evidence"] = {
                    "surface_id": surface["id"],
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/abi/player_identity_placeholder"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/player_identity_placeholder"],
                    "terms": [
                        "obelisk.core-dump-evidence-pack.v1",
                        "obelisk.reflection-inventory-pack.v1",
                        "ServerListPlayers",
                        "ServerKickPlayer",
                    ],
                }
            if surface["id"] == "obelisk.command_chat_response_path.v1":
                surface["public_abi"] = True
        manifest["promoted_surfaces"].extend(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"]
        )
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id
            not in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("non_promoted_surface_has_public_abi", payload["blockers"])
        self.assertEqual(
            payload["non_promoted_with_public_abi"],
            ["obelisk.command_chat_response_path.v1"],
        )

    def test_status_experimental_surface_omitted_from_top_level_list_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": [],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": [],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.chat_message.v1",
                    "status": "promoted-experimental-only",
                    "public_contract": ["RegisterChatCallback"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("experimental_surface_list_mismatch", payload["blockers"])
        self.assertIn("promoted_experimental_surfaces_unresolved", payload["blockers"])
        self.assertEqual(payload["experimental_list_mismatches"], ["obelisk.chat_message.v1"])
        self.assertEqual(payload["unresolved_experimental_surfaces"], ["obelisk.chat_message.v1"])

    def test_experimental_surface_exclusion_requires_release_statement_outcome(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = "\n".join(
            line for line in release_statement.splitlines() if "obelisk.chat_message.v1" not in line
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_experimental_surface_exclusion_requires_specific_surface_terms(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        release_statement = release_statement.replace(
            "obelisk.chat_message.v1: excluded - ChatMessageEvent is not included in v1.",
            "obelisk.chat_message.v1: excluded - later.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_completion_blocker_status_must_match_required_release_outcome(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "post-v1"
                break
        manifest["post_v1_or_excluded_surfaces"].append("obelisk.structure_census.v1")
        release_statement = release_statement.replace(
            "obelisk.structure_census.v1: excluded -",
            "obelisk.structure_census.v1: post-v1 -",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_exclusion_contract", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_exclusion_contracts"], ["obelisk.structure_census.v1"])

    def test_docs_only_promotion_evidence_blocks_claim(self) -> None:
        manifest = {
            "schema": "obelisk.public-sdk-surfaces.v1",
            "sdk_version": "v1.0",
            "v1_completion_required": True,
            "stable_release_contract": {"claim_allowed": True},
            "promoted_surfaces": ["obelisk.player_identity.v1"],
            "experimental_surfaces": [],
            "v1_sdk_completion_blockers": ["obelisk.player_identity.v1"],
            "post_v1_or_excluded_surfaces": [],
            "surfaces": [
                {
                    "id": "obelisk.player_identity.v1",
                    "status": "promoted",
                    "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
                    "evidence": {"docs": ["TODO-only-doc.md"]},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_fake_promotion_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["TODO-not-a-real-test"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_generic_existing_directory_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_absolute_external_evidence_path_blocks_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["/tmp"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_existing_generic_script_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {"tests": ["scripts/check_release_readiness.sh"]}
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_plugin_hub_package_shape_evidence_does_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPluginHubFoundation",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_plugin_hub_foundation",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPluginHubFoundationTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_plugin_hub_foundation_plugin.c"
            core_test.write_text("// Plugin Hub package shape placeholder\n", encoding="utf-8")
            sdk_test.write_text("// Plugin Hub package shape consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.plugin-hub-foundation-package-shape.v1"],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_core_first_and_copied_seed_terms_do_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "runtime/core-first RC readiness",
                            "GameplayPolicyEvent, ChatMessageEvent, and inventory item copied-signal seeds",
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_player_identity_requires_runtime_privacy_abi_and_sdk_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"]["obelisk.player_identity.v1"],
            [
                "accepted login/logout lifecycle ordering and principal invalidation semantics",
                "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                "approved runtime principal lifecycle evidence",
                "principal privacy, invalidation, and cross-instance semantics",
            ],
        )

    def test_candidate_only_player_identity_preflight_test_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_report_does_not_promote_completion_blocker(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["docs/research/2026-05-31-player-identity-static-target-orientation.json"],
                    "sdk_consumer_tests": [
                        "docs/research/2026-05-31-player-identity-static-target-orientation.json"
                    ],
                    "schemas": [
                        "obelisk.player-identity-static-orientation-check.v1",
                        "obelisk.player-identity-static-admin-thunks-check.v1",
                        "obelisk.static-candidate-orientation-contract.v1",
                    ],
                    "terms": [
                        "obelisk.core-dump-evidence-pack.v1",
                        "obelisk.reflection-inventory-pack.v1",
                        "ServerListPlayers",
                        "ServerKickPlayer",
                    ],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_named_tests_do_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityStaticOrientation",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_static_orientation",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityAdminThunksTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_admin_thunks_plugin.c"
            core_test.write_text("// candidate-only player identity admin thunks test\n", encoding="utf-8")
            sdk_test.write_text("// candidate-only player identity admin thunks consumer\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_static_orientation_schema_does_not_promote_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI test placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": [
                            "obelisk.player-identity-static-orientation-check.v1",
                            "obelisk.player-identity-static-admin-thunks-check.v1",
                            "obelisk.static-candidate-orientation-contract.v1",
                        ],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_lifecycle_anchor_and_principal_policy_schemas_do_not_promote_player_identity(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as sdk_dir,
        ):
            core_test = Path(core_dir) / "PlayerIdentityPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "player_identity_promotion_plugin.c"
            core_test.write_text("// promoted player identity ABI test placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted player identity consumer placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "runtime_ready": True,
                        "schemas": [
                            "obelisk.players-identity-lifecycle-anchor-candidates.v1",
                            "obelisk.players-identity-principal-invalidation-policy.v1",
                        ],
                        "blockers": ["approved_runtime_evidence_missing"],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                        ],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id != "obelisk.player_identity.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            header_path = Path(core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.player_identity.v1"])

    def test_principal_invalidation_policy_schema_does_not_promote_permissions_readiness(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PlayerIdentityPromotion",
            ) as identity_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="player_identity_promotion",
            ) as identity_sdk_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as permissions_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as permissions_sdk_dir,
        ):
            identity_core_test = Path(identity_core_dir) / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = Path(identity_sdk_dir) / "player_identity_promotion_plugin.c"
            permissions_core_test = Path(permissions_core_dir) / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = Path(permissions_sdk_dir) / "permissions_admin_promotion_plugin.c"
            for path in (identity_core_test, identity_sdk_test, permissions_core_test, permissions_sdk_test):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")

            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPermissionsAdminQuery"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.players-identity-principal-invalidation-policy.v1"],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
            manifest["promoted_surfaces"].extend(
                ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"]
            )
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            ]
            manifest_path = Path(identity_core_dir) / "public_sdk_surfaces.json"
            header_path = Path(identity_core_dir) / "ObeliskApi.h"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            header_path.write_text("#pragma once\n", encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--public-header",
                str(header_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.permissions_admin.v1"])

    def test_promoted_completion_blocker_requires_valid_abi_and_sdk_consumer_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterStructureCensusCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                    "sdk_consumer_tests": ["TODO-missing-sdk-consumer-test"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.structure_census.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.structure_census.v1"])

    def test_promoted_completion_blocker_rejects_core_test_as_sdk_consumer_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.structure_census.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterStructureCensusCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.structure_census.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                    "sdk_consumer_tests": ["tests/core/StructureAggregateCensusTests.cpp"],
                }
                break
        manifest["promoted_surfaces"].append("obelisk.structure_census.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_blockers_without_evidence"], ["obelisk.structure_census.v1"])

    def test_descriptor_catalog_contract_does_not_promote_module_completion_blockers(self) -> None:
        cases = (
            (
                "obelisk.inventory_items_mutation.v1",
                "tests/core/InventoryPolicyEventDispatcherTests.cpp",
                "ObeliskApi.DescribeResourceKind",
            ),
            (
                "obelisk.structure_census.v1",
                "tests/core/StructureEventDispatcherTests.cpp",
                "ObeliskApi.DescribeGameplayPolicyEventKind",
            ),
            (
                "obelisk.mission_transfer_dino_tribe.v1",
                "tests/core/MissionCopiedBoolEventDispatcherTests.cpp",
                "ObeliskResourceKindDescriptor",
            ),
        )
        for surface_id, abi_test, descriptor_contract in cases:
            with self.subTest(surface=surface_id):
                manifest, _ = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["status"] = "promoted"
                        surface["public_contract"] = [descriptor_contract]
                        surface["evidence"] = {
                            "surface_id": surface_id,
                            "promotion_status": "promoted",
                            "public_sdk_ready": True,
                            "abi_tests": [abi_test],
                            "sdk_consumer_tests": [
                                "tests/sdk_installed_consumer/descriptor_catalog_plugin.cpp"
                            ],
                        }
                        break
                manifest["promoted_surfaces"].append(surface_id)
                manifest["post_v1_or_excluded_surfaces"] = [
                    item for item in manifest["post_v1_or_excluded_surfaces"] if item != surface_id
                ]
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
                self.assertIn(surface_id, payload["promoted_blockers_without_evidence"])

    def test_item_return_only_readiness_does_not_promote_inventory_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="InventoryItemMutationPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="inventory_item_mutation_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "InventoryItemMutationPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "inventory_item_mutation_plugin.c"
            abi_test.write_text("// promoted inventory item mutation ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// promoted inventory item mutation SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.inventory_items_mutation.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterInventoryItemMutationCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.inventory_items_mutation.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                        "schemas": ["obelisk.item-return-only-policy-slice.v1"],
                        "release_readiness_target_sets": ["item-return-only-policy-slice"],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                item for item in manifest["post_v1_or_excluded_surfaces"] if item != "obelisk.inventory_items_mutation.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn("obelisk.inventory_items_mutation.v1", payload["promoted_blockers_without_evidence"])

    def test_copied_signal_and_descriptor_paths_do_not_promote_inventory_completion_blocker(self) -> None:
        cases = (
            "InventoryPolicyEventDispatcher",
            "InventoryItemReturnEventDispatcher",
            "InventoryDescriptorCatalog",
        )
        for case_name in cases:
            with self.subTest(case=case_name):
                with (
                    tempfile.TemporaryDirectory(
                        dir=REPO_ROOT / "tests" / "core",
                        prefix=case_name,
                    ) as core_dir,
                    tempfile.TemporaryDirectory(
                        dir=REPO_ROOT / "tests" / "sdk_consumer",
                        prefix=case_name,
                    ) as sdk_dir,
                ):
                    abi_test = Path(core_dir) / f"{case_name}Tests.cpp"
                    sdk_test = Path(sdk_dir) / f"{case_name}Plugin.c"
                    abi_test.write_text(
                        "// copied signal or descriptor evidence placeholder\n",
                        encoding="utf-8",
                    )
                    sdk_test.write_text(
                        "// copied signal or descriptor SDK consumer placeholder\n",
                        encoding="utf-8",
                    )
                    manifest, _ = complete_excluded_manifest()
                    for surface in manifest["surfaces"]:
                        if surface["id"] == "obelisk.inventory_items_mutation.v1":
                            surface["status"] = "promoted"
                            surface["public_contract"] = [
                                "ObeliskApi.RegisterInventoryItemMutationCallback"
                            ]
                            surface["evidence"] = {
                                "surface_id": "obelisk.inventory_items_mutation.v1",
                                "promotion_status": "promoted",
                                "public_sdk_ready": True,
                                "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                                "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                            }
                            break
                    manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
                    manifest["post_v1_or_excluded_surfaces"] = [
                        item
                        for item in manifest["post_v1_or_excluded_surfaces"]
                        if item != "obelisk.inventory_items_mutation.v1"
                    ]
                    manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
                self.assertIn(
                    "obelisk.inventory_items_mutation.v1",
                    payload["promoted_blockers_without_evidence"],
                )

    def test_descriptor_catalog_path_does_not_promote_inventory_completion_blocker(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="InventoryMutationPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="inventory_descriptor_catalog_promotion",
            ) as sdk_dir,
        ):
            abi_test = Path(core_dir) / "InventoryMutationPromotionTests.cpp"
            sdk_test = Path(sdk_dir) / "inventory_descriptor_catalog_plugin.c"
            abi_test.write_text("// promoted inventory mutation ABI placeholder\n", encoding="utf-8")
            sdk_test.write_text("// inventory descriptor catalog SDK placeholder\n", encoding="utf-8")
            manifest, _ = complete_excluded_manifest()
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.inventory_items_mutation.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterInventoryItemMutationCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.inventory_items_mutation.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(sdk_test.relative_to(REPO_ROOT))],
                    }
                    break
            manifest["promoted_surfaces"].append("obelisk.inventory_items_mutation.v1")
            manifest["post_v1_or_excluded_surfaces"] = [
                item for item in manifest["post_v1_or_excluded_surfaces"] if item != "obelisk.inventory_items_mutation.v1"
            ]
            manifest_path = Path(core_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn("obelisk.inventory_items_mutation.v1", payload["promoted_blockers_without_evidence"])

    def test_duplicate_surface_id_blocks_v1_claim(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        duplicate = {
            "id": "obelisk.player_identity.v1",
            "status": "planning",
            "public_contract": ["ObeliskApi.RegisterPlayerIdentityCallback"],
        }
        for index, surface in enumerate(manifest["surfaces"]):
            if surface["id"] == "obelisk.player_identity.v1":
                manifest["surfaces"].insert(index, duplicate)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate_surface_id", payload["blockers"])
        self.assertEqual(payload["duplicate_surface_ids"], ["obelisk.player_identity.v1"])

    def test_duplicate_v1_completion_blocker_blocks_progress_accounting(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["v1_sdk_completion_blockers"].append("obelisk.player_identity.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate_v1_sdk_completion_blocker", payload["blockers"])
        self.assertEqual(payload["duplicate_v1_sdk_completion_blockers"], ["obelisk.player_identity.v1"])
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blocker_total"], 12)
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)

    def test_promoted_experimental_surface_requires_structured_surface_specific_evidence(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.chat_message.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterChatEventWithOwnerTokenHandle"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        manifest["promoted_surfaces"].append("obelisk.chat_message.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertEqual(payload["promoted_surfaces_without_evidence"], ["obelisk.chat_message.v1"])

    def test_promoted_experimental_surface_still_requires_release_statement_record(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.chat_message.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterChatEventWithOwnerTokenHandle"]
                surface["evidence"] = {
                    "surface_id": "obelisk.chat_message.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["tests/core/ChatEventDispatcherTests.cpp"],
                    "sdk_consumer_tests": ["tests/sdk_consumer/CAbiPlugin.c"],
                }
                break
        if "obelisk.chat_message.v1" not in manifest["promoted_surfaces"]:
            manifest["promoted_surfaces"].append("obelisk.chat_message.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.chat_message.v1"
        ]
        release_statement = "\n".join(
            line for line in release_statement.splitlines() if "obelisk.chat_message.v1" not in line
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_missing_experimental_outcomes", payload["blockers"])
        self.assertEqual(payload["release_statement_missing_experimental_outcomes"], ["obelisk.chat_message.v1"])

    def test_release_statement_parser_accepts_promoted_surface_record(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        record = module.release_statement_surface_record(
            "obelisk.chat_message.v1: promoted - reviewed ABI and SDK evidence.\n",
            "obelisk.chat_message.v1",
            "promoted",
        )

        self.assertEqual(record, "obelisk.chat_message.v1: promoted - reviewed ABI and SDK evidence.")

    def test_new_planning_surface_blocks_v1_claim_until_outcome_is_named(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["surfaces"].append(
            {
                "id": "obelisk.future_unmapped_surface.v1",
                "status": "planning",
                "public_contract": [],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertEqual(payload["unresolved_planning_surfaces"], ["obelisk.future_unmapped_surface.v1"])

    def test_top_level_planning_surfaces_block_v1_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("top_level_planning_surfaces_unresolved_for_v1_claim", payload["blockers"])
        self.assertIn("planning_surface_list_mismatch", payload["blockers"])
        self.assertEqual(payload["top_level_planning_surfaces"], ["obelisk.player_identity.v1"])

    def test_post_v1_or_excluded_surface_list_must_match_surface_statuses(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["post_v1_or_excluded_surfaces"].remove("obelisk.commands_replies.v1")
        manifest["post_v1_or_excluded_surfaces"].append("obelisk.descriptors.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("post_v1_or_excluded_surface_list_mismatch", payload["blockers"])
        self.assertEqual(
            payload["post_v1_or_excluded_list_mismatches"],
            ["obelisk.commands_replies.v1", "obelisk.descriptors.v1"],
        )

    def test_debug_only_surface_cannot_be_promoted(self) -> None:
        manifest, _ = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.debug_raw_process_event.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterRawProcessEvent"]
                surface["evidence"] = {"tests": ["tests/sdk_consumer"]}
                break
        manifest["promoted_surfaces"].append("obelisk.debug_raw_process_event.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("debug_only_surface_promoted", payload["blockers"])
        self.assertEqual(payload["debug_only_promoted_surfaces"], ["obelisk.debug_raw_process_event.v1"])

    def test_non_promoted_completion_blocker_requires_exclusion_contract(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.commands_replies.v1":
                surface.pop("v1_decision_contract", None)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("completion_blocker_exclusion_contract_missing", payload["blockers"])
        self.assertEqual(payload["missing_completion_blocker_exclusion_contracts"], ["obelisk.commands_replies.v1"])

    def test_public_abi_dependency_chain_blocks_until_identity_dependencies_promoted(self) -> None:
        cases = {
            "obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"],
            "obelisk.command_chat_response_path.v1": [
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
            "obelisk.commands_replies.v1": [
                "obelisk.command_chat_response_path.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
            ],
        }
        for surface_id, expected_dependencies in cases.items():
            with self.subTest(surface=surface_id):
                manifest, release_statement = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["public_abi"] = True
                        break
                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    statement_path.write_text(release_statement, encoding="utf-8")
                    result = self.run_checker(
                        "--manifest",
                        str(manifest_path),
                        "--release-statement",
                        str(statement_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("promoted_surface_dependency_unresolved", payload["blockers"])
                self.assertEqual(
                    payload["promoted_surfaces_with_unresolved_dependencies"],
                    {surface_id: expected_dependencies},
                )

    def test_dependency_declarations_block_permissions_and_commands_sequence_drift(self) -> None:
        cases = {
            "obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"],
            "obelisk.commands_replies.v1": ["obelisk.command_chat_response_path.v1"],
            "obelisk.player_services_economy_mobility.v1": [
                "obelisk.command_chat_response_path.v1",
            ],
        }
        for surface_id, removed_dependencies in cases.items():
            with self.subTest(surface=surface_id):
                manifest, release_statement = complete_excluded_manifest()
                for surface in manifest["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["depends_on"] = [
                            dependency
                            for dependency in surface.get("depends_on", [])
                            if dependency not in removed_dependencies
                        ]
                        break

                with tempfile.TemporaryDirectory() as temp_dir:
                    manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
                    statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    statement_path.write_text(release_statement, encoding="utf-8")
                    result = self.run_checker(
                        "--manifest",
                        str(manifest_path),
                        "--release-statement",
                        str(statement_path),
                        "--json",
                        check=False,
                    )

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertIn("required_surface_dependency_declaration_missing", payload["blockers"])
                self.assertEqual(
                    payload["surfaces_missing_required_dependency_declarations"],
                    {surface_id: removed_dependencies},
                )

    def test_v1_dependency_sequence_blocks_reordering_before_completion_claim(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        manifest["v1_dependency_sequence"] = [
            "obelisk.permissions_admin.v1",
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        manifest["v1_sdk_completion_blockers"] = [
            "obelisk.permissions_admin.v1",
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
            *[
                surface_id
                for surface_id in manifest["v1_sdk_completion_blockers"]
                if surface_id
                not in {
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                    "obelisk.commands_replies.v1",
                }
            ],
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("v1_dependency_sequence_mismatch", payload["blockers"])
        self.assertEqual(
            payload["v1_dependency_sequence_expected"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(
            payload["v1_dependency_sequence_mismatches"],
            ["v1_dependency_sequence", "v1_sdk_completion_blockers"],
        )

    def test_permissions_admin_public_cache_api_contract_blocks_until_player_identity_promoted(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "planning"
                surface["public_contract"] = []
            if surface["id"] == "obelisk.permissions_admin.v1":
                surface["public_abi"] = True
                surface["public_contract"] = [
                    "ObeliskApi.CheckPermissionWithCopiedPrincipal",
                    "ObeliskApi.CheckPermissionCachedWithCopiedPrincipal",
                    "ObeliskPermissionCacheEntry",
                    "ObeliskPermissionsAdminContractV1",
                ]
                surface["public_permission_cache_contract"] = "policy_epoch_generation_scope_keyed"
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_with_unresolved_dependencies"],
            {"obelisk.permissions_admin.v1": ["obelisk.player_identity.v1"]},
        )
        self.assertIn("non_promoted_surface_has_public_abi", payload["blockers"])
        self.assertEqual(payload["non_promoted_with_public_abi"], ["obelisk.permissions_admin.v1"])
        self.assertIn("non_promoted_surface_has_public_contract", payload["blockers"])
        self.assertIn("obelisk.permissions_admin.v1", payload["non_promoted_with_public_contract"])

    def test_promoted_permissions_admin_requires_semantic_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            identity_abi_test = core_path / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = sdk_path / "player_identity_promotion_plugin.c"
            permissions_abi_test = core_path / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = sdk_path / "permissions_admin_promotion_plugin.c"
            identity_abi_test.write_text("// promoted player identity ABI placeholder\n", encoding="utf-8")
            identity_sdk_test.write_text("// promoted player identity SDK placeholder\n", encoding="utf-8")
            permissions_abi_test.write_text("// promoted permissions admin ABI placeholder\n", encoding="utf-8")
            permissions_sdk_test.write_text("// promoted permissions admin SDK placeholder\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": ["nominal permissions/admin ABI and SDK consumer tests"],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"
            manifest_path = core_path / "public_sdk_surfaces.json"
            statement_path = core_path / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"],
            {
                "obelisk.permissions_admin.v1": [
                    "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                    "promoted copied principal semantics",
                    "query-only fail-closed permission checks over copied principals",
                    "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                ]
            },
        )

    def test_promoted_command_response_requires_semantic_evidence_terms(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="CommandChatResponsePromotion",
            ) as core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="command_chat_response_promotion",
            ) as sdk_dir,
        ):
            core_path = Path(core_dir)
            sdk_path = Path(sdk_dir)
            identity_abi_test = core_path / "PlayerIdentityPromotionTests.cpp"
            identity_sdk_test = sdk_path / "player_identity_promotion_plugin.c"
            permissions_abi_test = core_path / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = sdk_path / "permissions_admin_promotion_plugin.c"
            response_abi_test = core_path / "CommandChatResponsePromotionTests.cpp"
            response_sdk_test = sdk_path / "command_chat_response_promotion_plugin.c"
            for path in (
                identity_abi_test,
                identity_sdk_test,
                permissions_abi_test,
                permissions_sdk_test,
                response_abi_test,
                response_sdk_test,
            ):
                path.write_text("// synthetic promotion evidence fixture\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            }
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(identity_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(identity_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "obelisk.core-dump-evidence-pack.v1",
                            "obelisk.reflection-inventory-pack.v1",
                            "ServerListPlayers",
                            "ServerKickPlayer",
                            "approved runtime principal lifecycle evidence",
                            "accepted login/logout lifecycle ordering and principal invalidation semantics",
                            "principal privacy, invalidation, and cross-instance semantics",
                            "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
                        ],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
                if surface["id"] == "obelisk.command_chat_response_path.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterCommandChatResponsePath"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.command_chat_response_path.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(response_abi_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(response_sdk_test.relative_to(REPO_ROOT))],
                        "terms": ["nominal command/chat response ABI and SDK consumer tests"],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"
            manifest_path = core_path / "public_sdk_surfaces.json"
            statement_path = core_path / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertNotIn("promoted_surface_dependency_unresolved", payload["blockers"])
        self.assertIn("promoted_surface_required_evidence_terms_missing", payload["blockers"])
        self.assertEqual(
            payload["promoted_surfaces_missing_required_evidence_terms"],
            {
                "obelisk.command_chat_response_path.v1": [
                    "copied append-only response ABI with capability gates and owner-scoped cleanup",
                    "no raw UE pointer, raw ProcessEvent parameter, or raw FString response API",
                    "privacy, redaction, rate-limit, abuse, audit, and cross-instance routing semantics for command/chat responses",
                    "promoted permission/authority checks for directed responses",
                    "promoted player identity/principal semantics",
                ]
            },
        )

    def test_commands_replies_requires_response_path_semantic_evidence_terms(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("check_public_sdk_v1_completion", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        missing_terms = module.surface_missing_required_promotion_evidence(
            {
                "id": "obelisk.commands_replies.v1",
                "status": "promoted",
                "evidence": {
                    "terms": [
                        "promoted player identity/principal semantics",
                        "promoted permission/authority model",
                        "nominal command router ABI and SDK consumer tests",
                    ],
                },
            }
        )

        self.assertEqual(
            missing_terms,
            [
                "obelisk.command_chat_response_path.v1 dependency resolved through its own future promotion gate for replies/send-chat",
                "command lifecycle, abuse, rate-limit, and moderation boundaries",
                "copied append-only command/reply ABI with capability gates, owner-scoped cleanup, and SDK consumer tests",
            ],
        )

    def test_dependency_chain_accounting_keeps_invalid_promoted_identity_visible(self) -> None:
        manifest, release_statement = complete_excluded_manifest()
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "promoted"
                surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                surface["evidence"] = {
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                }
                break
        if "obelisk.player_identity.v1" not in manifest["promoted_surfaces"]:
            manifest["promoted_surfaces"].append("obelisk.player_identity.v1")
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        release_statement = "\n".join(
            (
                "obelisk.player_identity.v1: promoted - reviewed ABI and SDK evidence."
                if line.startswith("obelisk.player_identity.v1:")
                else line
            )
            for line in release_statement.splitlines()
        ) + "\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            statement_path = Path(temp_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_surface_evidence_missing", payload["blockers"])
        self.assertIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_blocker_outcome_summary"]["dependency_chain_remaining"],
        )
        self.assertEqual(
            payload["unpromoted_required_dependency_chain"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(payload["v1_sdk_progress"]["completion_blockers_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["p0_chain_promoted_count"], 0)
        self.assertEqual(payload["v1_sdk_progress"]["complete_sdk_claim_progress_percent"], 0)
        self.assertNotIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_progress"]["completion_blockers_with_promoted_outcome"],
        )
        self.assertIn(
            "obelisk.player_identity.v1",
            payload["v1_sdk_progress"]["completion_blockers_with_manifest_promoted_status"],
        )
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        self.assertTrue(
            outcome_by_surface["obelisk.player_identity.v1"]["unresolved_for_complete_sdk_claim"]
        )

    def test_p0_progress_does_not_count_surface_when_promoted_dependency_lacks_evidence(self) -> None:
        with (
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "core",
                prefix="PermissionsAdminPromotion",
            ) as permissions_core_dir,
            tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "tests" / "sdk_consumer",
                prefix="permissions_admin_promotion",
            ) as permissions_sdk_dir,
        ):
            permissions_core_test = Path(permissions_core_dir) / "PermissionsAdminPromotionTests.cpp"
            permissions_sdk_test = Path(permissions_sdk_dir) / "permissions_admin_promotion_plugin.c"
            permissions_core_test.write_text("// promoted permissions admin ABI placeholder\n", encoding="utf-8")
            permissions_sdk_test.write_text("// promoted permissions admin SDK placeholder\n", encoding="utf-8")

            manifest, release_statement = complete_excluded_manifest()
            promoted_ids = {"obelisk.player_identity.v1", "obelisk.permissions_admin.v1"}
            for surface in manifest["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.RegisterPlayerIdentityCallback"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                        "sdk_consumer_tests": ["scripts/test_check_player_identity_first_evidence_readiness.py"],
                    }
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskApi.CheckPermissionWithCopiedPrincipal"]
                    surface["evidence"] = {
                        "surface_id": "obelisk.permissions_admin.v1",
                        "promotion_status": "promoted",
                        "public_sdk_ready": True,
                        "abi_tests": [str(permissions_core_test.relative_to(REPO_ROOT))],
                        "sdk_consumer_tests": [str(permissions_sdk_test.relative_to(REPO_ROOT))],
                        "terms": [
                            "query-only fail-closed permission checks over copied principals",
                            "stale principal, scope mismatch, missing generation, missing owner token, unknown authority source, and missing policy provenance fail closed",
                            "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
                            "promoted copied principal semantics",
                        ],
                    }
            for surface_id in promoted_ids:
                if surface_id not in manifest["promoted_surfaces"]:
                    manifest["promoted_surfaces"].append(surface_id)
            manifest["post_v1_or_excluded_surfaces"] = [
                surface_id
                for surface_id in manifest["post_v1_or_excluded_surfaces"]
                if surface_id not in promoted_ids
            ]
            release_statement = "\n".join(
                (
                    f"{surface_id}: promoted - reviewed ABI and SDK evidence."
                    if surface_id in promoted_ids
                    else line
                )
                for line in release_statement.splitlines()
                for surface_id in [line.split(":", 1)[0]]
            ) + "\n"

            manifest_path = Path(permissions_core_dir) / "public_sdk_surfaces.json"
            statement_path = Path(permissions_core_dir) / "RELEASE_STATEMENT.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            statement_path.write_text(release_statement, encoding="utf-8")
            result = self.run_checker(
                "--manifest",
                str(manifest_path),
                "--release-statement",
                str(statement_path),
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        progress = payload["v1_sdk_progress"]
        self.assertEqual(progress["completion_blockers_promoted_count"], 0)
        self.assertEqual(progress["p0_chain_promoted_count"], 0)
        self.assertEqual(progress["complete_sdk_claim_progress_percent"], 0)
        outcome_by_surface = {
            row["surface"]: row for row in payload["v1_sdk_blocker_outcomes"]
        }
        self.assertFalse(outcome_by_surface["obelisk.player_identity.v1"]["promotion_evidence_satisfied"])
        self.assertFalse(outcome_by_surface["obelisk.permissions_admin.v1"]["dependency_claims_satisfied"])
        self.assertFalse(outcome_by_surface["obelisk.permissions_admin.v1"]["counts_toward_complete_sdk_claim"])

    def test_planning_completion_blocker_requires_exclusion_contract(self) -> None:
        manifest, _ = complete_excluded_manifest()
        manifest["v1_completion_required"] = False
        manifest["stable_release_contract"]["claim_allowed"] = False
        manifest["planning_surfaces"] = ["obelisk.player_identity.v1"]
        manifest["post_v1_or_excluded_surfaces"] = [
            surface_id
            for surface_id in manifest["post_v1_or_excluded_surfaces"]
            if surface_id != "obelisk.player_identity.v1"
        ]
        for surface in manifest["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["status"] = "planning"
                surface.pop("v1_decision_contract", None)
                break
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("completion_blocker_exclusion_contract_missing", payload["blockers"])
        self.assertIn("v1_sdk_completion_blockers_unresolved", payload["blockers"])
        self.assertIn("complete_sdk_claim_requires_promoted_demand_families", payload["blockers"])
        self.assertEqual(payload["missing_completion_blocker_exclusion_contracts"], ["obelisk.player_identity.v1"])
        self.assertEqual(payload["unresolved_completion_blockers"], ["obelisk.player_identity.v1"])

    def test_release_statement_required_for_v1_completion_claim(self) -> None:
        manifest, _ = complete_excluded_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "public_sdk_surfaces.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest_path), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_required_for_v1_completion", payload["blockers"])


if __name__ == "__main__":
    unittest.main()
