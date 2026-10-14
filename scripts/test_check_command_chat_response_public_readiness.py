#!/usr/bin/env python3
"""Tests for check_command_chat_response_public_readiness.py."""

from __future__ import annotations

import hashlib
import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_chat_response_public_readiness.py"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
CERTIFICATE_TEMP_PARENT = REPO_ROOT / "tests" / "core"
CERTIFICATE_TEMP_PREFIX = "CommandChatResponseCert"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_command_chat_response_public_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
READINESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = READINESS
SPEC.loader.exec_module(READINESS)


TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
]


def target_snapshot_payload(target: str) -> dict:
    return {
        "schema": "obelisk.ufunction-chain.snapshot.v1",
        "evidence": {
            "artifact_sha256": "a" * 64,
            "capture_id": "unit-test-command-response",
            "evidence_pack_id": "unit-test-command-response-pack",
            "source": "unit-test",
            "status": "candidate-only",
        },
        "targets": [
            {
                "target": {"name": target.rsplit(".", 1)[1]},
                "property_chain": {
                    "properties": [
                        {"name": "UnitTestProperty", "status": "candidate-only"},
                    ]
                },
            }
        ],
    }


class CheckCommandChatResponsePublicReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_readiness(self, root: Path | None = None) -> dict:
        def target_path(target: str) -> str:
            basename = f"{target.rsplit(':', 1)[1]}.snapshot.json"
            if root is None:
                return f"/offline/{basename}"
            return str(root / "base-snapshots" / basename)

        source_root = str(root) if root is not None else "/offline"
        candidate_root = str(root / "candidate-snapshots") if root is not None else "/offline-candidate"
        return {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "evidence_scope": "second_source_layout_evidence_only",
            "gate_mode": "planning_layout_intake",
            "source_root": source_root,
            "producer": {
                "script": "scripts/compare_reflection_snapshots.py",
                "argv": [
                    "scripts/compare_reflection_snapshots.py",
                    "--base-root",
                    source_root,
                    "--candidate-root",
                    candidate_root,
                    "--target-set",
                    "command-chat-response-route-planning",
                    "--readiness-report",
                    "--json",
                ],
                "output_name": "command-chat-response-route-planning-readiness.json",
            },
            "modules": [
                {
                    "block_reasons": {},
                    "blocked": 0,
                    "comparable": 3,
                    "module": "base-snapshots",
                    "schema": "ufunction",
                    "second_source": {
                        "accepted": 3,
                        "inconclusive": 0,
                        "missing": 0,
                        "rejected": 0,
                    },
                    "target_details": [
                        {
                            "block_reasons": [],
                            "comparable": True,
                            "path": target_path(target),
                            "second_source_status": "accepted",
                            "target": target,
                        }
                        for target in TARGETS
                    ],
                    "targets": 3,
                }
            ],
            "non_claims": [
                "accepted second-source readiness is layout evidence only",
                "does not promote public SDK, Mission SDK, Transfer SDK, Structure SDK, StructureEvents, Inventory SDK, Items SDK, object identity, lookup, mutation, return override, ResourceHandle, or runtime hooks",
            ],
            "not_promoted_surfaces": ["public_sdk", "raw_params", "runtime_hooks"],
            "planning_layout_gate": {
                "blockers": [],
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "ready": True,
                "ready_scope": "planning_only",
                "runtime_ready": False,
            },
            "promotion_gate": {
                "blockers": [{"count": 1, "reason": "planning_layout_intake_not_promotion_gate"}],
                "layout_ready": True,
                "promotion_ready": False,
                "ready": False,
                "ready_scope": "planning_only",
            },
            "second_source_status": "compared",
            "strict_identity_indices": False,
            "target_filters": TARGETS,
            "target_set_guidance": [
                {
                    "classification": "command_chat_response_route_guidance_only_candidate",
                    "next_offline_input": "generate focal snapshots for response-path targets",
                    "non_claim": "does not promote command/chat response path, public reply/send-chat ABI, command router, permissions, player identity, raw FString access, mutation, return override, runtime hooks, or release readiness",
                    "snapshot_prep_checks": [
                        "keep reply API, send-chat API, broadcast/notices, moderation, command router, permission checks, mutation, and return override blocked",
                        "require promoted player identity/principal and permissions/admin before any public response path is considered",
                        "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                        "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                        "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                        "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
                    ],
                    "target_set": "command-chat-response-route-planning",
                    "why_blocked": [
                        "planning_guidance_only",
                        "not_release_readiness_target",
                        "public_response_path_blocked",
                        "player_identity_principal_blocked",
                        "permissions_admin_blocked",
                        "command_router_blocked",
                        "runtime_observation_requires_separate_approval",
                    ],
                }
            ],
            "target_sets": ["command-chat-response-route-planning"],
            "totals": {
                "blocked": 0,
                "comparable": 3,
                "second_source_accepted": 3,
                "second_source_inconclusive": 0,
                "second_source_missing": 0,
                "second_source_rejected": 0,
                "targets": 3,
            },
        }

    def make_surfaces_with_accepted_runtime_evidence(self) -> dict:
        surfaces = self.load_surfaces()
        for surface in surfaces["surfaces"]:
            if surface["id"] == "obelisk.player_identity.v1":
                surface["evidence"]["accepted_runtime_evidence"] = {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "result": "approved runtime principal lifecycle evidence",
                    "next_blocker": "identity_public_contract_gate_missing",
                    "approved_runtime_evidence_binding_required": True,
                    "approved_runtime_evidence_binding": {
                        "schema": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
                        "accepted_for_contract_review": True,
                        "resolved_input": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
                        "next_blocker": "identity_public_contract_gate_missing",
                        "binding_scope": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
                        "non_claim": (
                            "Fixture binding is route metadata only; it does not unlock public "
                            "header, public API/ABI/SDK, downstream P0, runtime readiness, or v1 completion."
                        ),
                        **{key: False for key in READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS},
                    },
                }
                surface["blockers"] = [
                    blocker
                    for blocker in surface["blockers"]
                    if blocker != "No approved runtime principal lifecycle evidence."
                ]
        return surfaces

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def write_surfaces(self, root: Path, surfaces: dict) -> Path:
        path = root / "public_sdk_surfaces.json"
        path.write_text(json.dumps(surfaces), encoding="utf-8")
        return path

    def bind_certificate_artifact(self, root: Path, name: str, payload: dict) -> dict[str, str]:
        path = root / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def repo_artifact_binding(self, path: Path, schema: str) -> dict[str, str]:
        return {
            "path": str(path.relative_to(REPO_ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "schema": schema,
        }

    def identity_contract_review_record(self, surface_hash: str) -> dict:
        record = {
            "schema": READINESS.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
            "artifact_id": READINESS.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
            "surface": READINESS.IDENTITY_SURFACE,
            "active_after_resolved_input": READINESS.PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
            "review_status": "reviewed",
            "accepted_for_contract_review": True,
            "next_blocker": READINESS.PUBLIC_HEADER_ROUTE_BLOCKER,
            "reviewed_surface_record_sha256": surface_hash,
            "resolved_decision_keys": list(
                READINESS.REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS
            ),
        }
        for key in READINESS.REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
            record[key] = False
        record.update(READINESS.REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS)
        return record

    def inline_promotion_certificate(self, surface: dict, surface_id: str) -> dict:
        spec = READINESS.PROMOTION_CERTIFICATE_SPECS[surface_id]
        certificate_key = spec["certificate_key"]
        surface_hash = READINESS.surface_record_sha256(surface, certificate_key)
        evidence = {
            "reviewed_surface_record_sha256": surface_hash,
            "reviewed_artifact_hash": surface_hash,
        }
        if surface_id == READINESS.IDENTITY_SURFACE:
            review = self.identity_contract_review_record(surface_hash)
            runtime_binding_digest = hashlib.sha256(
                b"unit-test-command-response-identity-runtime-binding"
            ).hexdigest()
            evidence.update(
                {
                    "promotion_evidence_kind": (
                        READINESS.PLAYER_IDENTITY_CERTIFICATE_PROMOTION_EVIDENCE_KIND
                    ),
                    "approved_runtime_evidence": {
                        "schema": READINESS.PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": READINESS.IDENTITY_CONTRACT_ROUTE_BLOCKER,
                    },
                    "identity_public_contract_decision_record": review,
                    "identity_public_contract_decision_record_sha256": (
                        READINESS.canonical_json_sha256(review)
                    ),
                    "identity_public_contract_decision_record_runtime_binding": {
                        "schema": (
                            READINESS.PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_SCHEMA
                        ),
                        "policy": READINESS.PLAYER_IDENTITY_DECISION_RUNTIME_BINDING_DIGEST_POLICY,
                        "decision_record_approved_runtime_evidence_binding_sha256": (
                            runtime_binding_digest
                        ),
                        "approved_runtime_evidence_binding_sha256": runtime_binding_digest,
                    },
                }
            )
        return {
            "schema": spec["schema"],
            "surface_id": surface_id,
            "promotion_status": "promoted",
            "v1_dependency_chain": READINESS.DEPENDENCY_CHAIN,
            "v1_dependency_chain_position": spec["chain_position"],
            "required_by_surface": spec["required_by_surface"],
            "required_by_v1_dependency_chain_position": spec["required_by_chain_position"],
            "required_reviewed_artifact_hash": READINESS.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
            "reviewed_artifact_hash_policy": (
                READINESS.REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY
            ),
            "missing_mismatched_or_stale_certificate_counts": False,
            "evidence": evidence,
        }

    def promote_surface_with_certificate(self, root: Path, surfaces: dict, surface_id: str) -> dict:
        surface = next(item for item in surfaces["surfaces"] if item["id"] == surface_id)
        spec = READINESS.PROMOTION_CERTIFICATE_SPECS[surface_id]
        certificate_key = spec["certificate_key"]
        surface["status"] = "promoted"
        evidence = surface.setdefault("evidence", {})
        evidence.pop(certificate_key, None)
        certificate = self.inline_promotion_certificate(surface, surface_id)
        if surface_id == READINESS.PERMISSIONS_SURFACE:
            identity = next(
                item
                for item in surfaces["surfaces"]
                if item["id"] == READINESS.IDENTITY_SURFACE
            )
            identity_evidence = identity.get("evidence")
            identity_binding = (
                identity_evidence.get("player_identity_promotion_certificate")
                if isinstance(identity_evidence, dict)
                else None
            )
            if isinstance(identity_binding, dict):
                input_bindings = {
                    "public_sdk_surfaces": self.repo_artifact_binding(
                        SURFACES,
                        READINESS.SURFACES_SCHEMA,
                    ),
                    "permissions_admin_surface_record_sha256": (
                        READINESS.surface_record_sha256(surface, certificate_key)
                    ),
                    "player_identity_surface_record_sha256": (
                        READINESS.surface_record_sha256(
                            identity,
                            "player_identity_promotion_certificate",
                        )
                    ),
                    "player_identity_promotion_certificate": deepcopy(identity_binding),
                    "permissions_admin_public_contract_decisions": self.repo_artifact_binding(
                        REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json",
                        READINESS.PERMISSIONS_ADMIN_PUBLIC_CONTRACT_DECISIONS_SCHEMA,
                    ),
                    "permissions_admin_query_failclosed_contract": self.repo_artifact_binding(
                        REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json",
                        READINESS.PERMISSIONS_ADMIN_QUERY_FAILCLOSED_CONTRACT_SCHEMA,
                    ),
                    "permissions_admin_public_readiness_report_sha256": "a" * 64,
                    "query_failclosed_contract_report_sha256": "b" * 64,
                }
                certificate["input_bindings"] = input_bindings
                certificate["evidence"]["input_binding_sha256"] = (
                    READINESS.canonical_json_sha256(input_bindings)
                )
        evidence[certificate_key] = self.bind_certificate_artifact(
            root,
            f"{certificate_key}.json",
            certificate,
        )
        if surface_id not in surfaces.get("promoted_surfaces", []):
            surfaces.setdefault("promoted_surfaces", []).append(surface_id)
        return surface

    def rewrite_bound_certificate(
        self,
        surface: dict,
        surface_id: str,
        payload: dict,
    ) -> None:
        certificate_key = READINESS.PROMOTION_CERTIFICATE_SPECS[surface_id]["certificate_key"]
        binding = surface["evidence"][certificate_key]
        path = REPO_ROOT / binding["path"]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    def assert_public_runtime_v1_flags_false(self, report: dict) -> None:
        for key in (
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "public_or_runtime_accounting_allowed",
            "public_readiness_ready",
            "public_header_allowed",
            "promotion_ready",
            "public_sdk_ready",
            "public_abi_ready",
            "runtime_ready",
            "counts_toward_p0_dependency_chain_claim",
            "candidate_capture_counts_toward_public_sdk",
            "candidate_capture_counts_toward_runtime",
            "candidate_capture_counts_toward_v1_completion",
            "candidate_capture_counts_toward_p0_dependency_chain_claim",
            "candidate_capture_public_or_runtime_accounting_allowed",
            "command_support_ready",
            "accepted_runtime_evidence",
            "approved_runtime_evidence",
        ):
            self.assertFalse(report[key], key)
        for key in (
            "complete_sdk_claim_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
            "candidate_capture_progress_contribution",
        ):
            self.assertEqual(0, report[key], key)

    def assert_gap_diagnostic_non_authorizing(self, diagnostic: dict) -> None:
        for key in (
            "diagnostic_only",
            "metadata_only",
            "non_evidence",
            "non_authorizing",
            "route_blocked",
        ):
            self.assertTrue(diagnostic[key], key)
        for key in (
            "reply_send_chat_router_claims_allowed",
            "reply_api_allowed",
            "send_chat_api_allowed",
            "command_support_ready",
            "accepted_runtime_evidence",
            "approved_runtime_evidence",
            "public_header_allowed",
            "public_abi_allowed",
            "runtime_delivery_allowed",
            "public_or_runtime_accounting_allowed",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_p0_dependency_chain_claim",
            "public_readiness_ready",
            "promotion_ready",
            "public_sdk_ready",
            "public_abi_ready",
            "runtime_ready",
            "readiness_ready",
        ):
            self.assertFalse(diagnostic[key], key)
        for key in (
            "complete_sdk_claim_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
        ):
            self.assertEqual(0, diagnostic[key], key)

    def make_decisions(self) -> dict:
        required = [
            {"id": "dependency.promoted_player_identity", "status": "unresolved", "required_behavior": [
                "runtime observation establishes principal identity before command/chat response can consume it",
                "command text cannot establish principal identity",
                "operator config enables surfaces only and cannot establish principal identity",
                "response delivery never creates identity or permission claims",
                "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish principal identity",
                "generic chat routing cannot establish principal identity",
                "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority",
                "commands/replies planning cannot bypass identity promotion",
                "accepted runtime evidence, reviewed identity contract aliases, and player-identity promotion certificate status text cannot replace a matching player-identity promotion certificate with current artifact hash and first chain position",
            ]},
            {"id": "dependency.promoted_permissions_admin", "status": "unresolved", "required_behavior": [
                "permissions/admin must be promoted before any reply, send-chat, broadcast, or moderation delivery is public",
                "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish permissions or admin authority",
                "generic chat routing cannot establish permissions or admin authority",
                "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority",
                "commands/replies planning cannot bypass permissions/admin promotion",
                "runtime-owned permissions/admin allow for the same runtime-owned principal tuple is required before any reply, send-chat, broadcast, moderation, or router response path is public",
                "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot unlock reply, send-chat, broadcast, moderation, or router response delivery before permissions/admin promotion",
                "permissions/admin shortcut aliases, command planning records, and response bridge records cannot stand in for the promoted permissions/admin certificate or the upstream player-identity promotion certificate",
            ]},
            {
                "id": "abi.copied_response_payload",
                "status": "unresolved",
                "required_fields_or_equivalent": [
                    "response_handle",
                    "plugin_owner_token",
                ],
                "required_behavior": [
                    "missing or zero plugin_owner_token fails closed",
                ],
            },
            {"id": "abi.capability_and_owner_token", "status": "unresolved", "required_behavior": [
                "captured post-init debug CallProcessEvent tables do not authorize response delivery",
                "minimal ChatMessageEvent registration does not authorize response delivery",
                "generic chat routing does not authorize response delivery",
                "raw ProcessEvent callbacks do not authorize response delivery",
                "static thunk orientation does not authorize response delivery",
            ]},
            {"id": "lifecycle.owner_scoped_unregister_and_drain", "status": "unresolved", "required_behavior": [
                "owner unregister cancels pending responses for that plugin owner",
                "plugin init failure cleans up registered response handles before dlclose",
                "plugin unload waits for in-flight response callbacks or fails closed without dlclose",
                "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
                "response callbacks cannot outlive copied payload storage",
                "server shutdown does not call into unmapped plugin code",
            ]},
            {"id": "privacy.redaction_and_targeting", "status": "unresolved", "required_behavior": [
                "principal tuple source must be runtime-owned player identity observation before any directed response target is public",
                "principal_handle, principal_generation, and principal_scope_flags must appear together before response targeting can consume player identity",
                "plugin-supplied principal tuple fails closed",
                "command-supplied principal tuple fails closed",
                "operator-supplied principal tuple fails closed",
                "missing principal provenance fails closed",
                "server process epoch mismatch fails closed",
                "permission allow cannot be consumed without policy provenance",
                "runtime-owned principal tuple must be paired with runtime-owned permission provenance before reply/send-chat/router planning can become public",
                "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
                "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
                "sender identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "directed recipient identity remains redacted and does not expose player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
                "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
            ]},
            {"id": "abuse.rate_limit_and_audit", "status": "unresolved", "required_behavior": [
                "response attempts are rate-limited per plugin owner token",
                "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
                "burst exhaustion drops or rejects the response, never bypasses permission checks",
                "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
                "malformed UTF-8 or oversize messages fail closed",
                "audit records are sanitized and do not expose raw UE internals",
                "operator controls can disable response delivery without disabling passive chat intake",
            ]},
            {"id": "separation.no_commands_router_or_moderation", "status": "unresolved", "required_exclusions": [
                "command router",
                "command registration API",
                "commands/replies shortcut before identity and permissions/admin",
                "public response path through ChatMessageEvent",
                "public response path through generic chat routing",
                "public response path through raw ProcessEvent",
                "public response path through static thunk orientation",
                "reply/send-chat/broadcast/moderation through legacy CallProcessEvent",
                "reply/send-chat/router claims before promotion",
                "moderation API",
            ], "v1_sequence_gate": [
                "minimal ChatMessageEvent remains passive input and cannot route replies/send-chat/broadcast/moderation",
                "generic chat routing cannot bypass promoted identity and permissions/admin",
                "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority",
                "raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot bypass identity and permissions/admin",
                "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot bypass promoted identity and permissions/admin",
            ]},
            {
                "id": "evidence.layout_runtime_sdk_coverage",
                "status": "unresolved",
                "not_sufficient": [
                    "static thunk orientation",
                    "candidate vtable slots",
                    "minimal ChatMessageEvent callback registration",
                    "passive ChatMessageEvent parsing",
                    "generic chat routing",
                    "commands/replies planning status",
                    "legacy CallProcessEvent debug gate",
                    "raw ProcessEvent callbacks",
                    "activation preconditions met are not sufficient",
                    "beta notice sent is not sufficient",
                    "copied response intent planning is not sufficient",
                    "identity_public_contract_gate_missing route blocker is not sufficient",
                    "local routing or chat seeds are not sufficient",
                    "next-action runner/planner artifacts are not sufficient",
                    "no-users/passive runtime is not sufficient",
                    "notice artifacts are not sufficient",
                    "package-shape artifacts are not sufficient",
                    "passive evidence is not sufficient",
                    "passive monitor ticks/output and passive player summaries/snapshots are not sufficient",
                    "public reachability is not sufficient",
                    "request checks are not sufficient",
                    "response bridge planning is not sufficient",
                    "runtime status artifacts are not sufficient",
                    "side-lane evidence is not sufficient",
                    "status artifacts are not sufficient",
                ],
            },
            {"id": "evidence.response_target_set_snapshot_second_source", "status": "unresolved", "required_targets": TARGETS, "not_sufficient": [
                "static thunk orientation",
                "minimal ChatMessageEvent callback registration",
                "generic chat routing",
                "raw ProcessEvent callbacks",
                "legacy CallProcessEvent debug gate",
                "activation preconditions met are not sufficient",
                "beta notice sent is not sufficient",
                "copied response intent planning is not sufficient",
                "identity_public_contract_gate_missing route blocker is not sufficient",
                "local routing or chat seeds are not sufficient",
                "next-action runner/planner artifacts are not sufficient",
                "no-users/passive runtime is not sufficient",
                "notice artifacts are not sufficient",
                "package-shape artifacts are not sufficient",
                "passive evidence is not sufficient",
                "passive monitor ticks/output and passive player summaries/snapshots are not sufficient",
                "public reachability is not sufficient",
                "request checks are not sufficient",
                "response bridge planning is not sufficient",
                "runtime status artifacts are not sufficient",
                "side-lane evidence is not sufficient",
                "status artifacts are not sufficient",
            ]},
        ]
        return {
            "schema": "obelisk.command-chat-response-public-contract-decisions.v1",
            "surface": "obelisk.command_chat_response_path.v1",
            "status": "blocked",
            "accounting_lock": {
                "dependency_chain_locked": True,
                "current_route_blocker": "approved_runtime_evidence_missing",
                "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "non_claim": (
                    "command/chat response readiness reports may be accepted for planning only; "
                    "they do not count while player identity remains blocked"
                ),
            },
            "public_header_allowed": False,
            "public_header": "include/obelisk/ObeliskApi.h",
            "public_header_symbols_now": [],
            "legacy_call_process_event_public_response_allowed": False,
            "minimal_chat_message_event_public_response_allowed": False,
            "generic_chat_routing_public_response_allowed": False,
            "raw_process_event_public_response_allowed": False,
            "static_thunk_orientation_public_response_allowed": False,
            "commands_replies_shortcut_public_response_allowed": False,
            "runtime_owned_principal_permissions_gate": {
                "planning_only": True,
                "runtime_owned_principal_required": True,
                "runtime_owned_permission_allow_required": True,
                "same_principal_tuple_required": True,
                "permission_policy_provenance_required": True,
                "reply_send_chat_router_claims_allowed": False,
                "public_abi_allowed": False,
                "runtime_delivery_allowed": False,
                "required_runtime_owned_inputs": [
                    "principal_handle",
                    "principal_generation",
                    "principal_scope_flags",
                    "server_process_epoch",
                    "permission_decision",
                    "permission_policy_epoch",
                    "policy_source_id",
                    "policy_source_generation",
                    "authority_kind",
                    "authority_generation",
                ],
                "forbidden_authority_sources": [
                    "activation preconditions",
                    "beta notice send",
                    "copied response intent planning",
                    "identity_public_contract_gate_missing alias",
                    "local chat seed",
                    "local routing seed",
                    "next-action artifact",
                    "no-users passive runtime",
                    "notice artifact",
                    "package-shape artifact",
                    "passive evidence",
                    "passive monitor output",
                    "post-runtime planning metadata",
                    "plugin input",
                    "command text",
                    "operator config",
                    "public reachability",
                    "request check",
                    "response bridge",
                    "reply request",
                    "send-chat request",
                    "chat/RCON/broadcast/send source alias",
                    "router metadata",
                    "runtime status artifact",
                    "side-lane evidence",
                    "status artifact",
                    "status metadata",
                    "passive ChatMessageEvent",
                    "raw ProcessEvent",
                    "legacy CallProcessEvent",
                    "static thunk orientation",
                ],
            },
            "post_permissions_next_step": deepcopy(READINESS.POST_PERMISSIONS_NEXT_STEP),
            "post_permissions_abi_evidence_guardrail": deepcopy(
                READINESS.POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL
            ),
            "forbidden_public_contract": [
                "public CallProcessEvent response path",
                "public minimal ChatMessageEvent response path",
                "public generic chat routing response path",
                "public raw ProcessEvent response path",
                "raw ProcessEvent or legacy CallProcessEvent fallback",
                "public static thunk orientation response path",
                "public commands/replies response shortcut before promoted identity and permissions/admin",
                "activation preconditions, beta notice sends, public reachability, request checks, and identity_public_contract_gate_missing aliases cannot be used as command/chat response unlocks",
                "reply API",
                "send-chat API",
                "reply/send-chat/router claims before promotion",
                "broadcast/notices API",
                "moderation API",
                "raw UE pointers",
                "raw ProcessEvent params",
                "raw FString storage",
                "UObject pointers",
                "UFunction pointers",
                "FName/GObjects indices",
                "direct native-call wrappers",
                "principal or permission claims from command text",
                "principal or permission claims from operator config",
                "player lookup",
                "mutation",
                "return override",
            ],
            "required_before_public_header": required,
        }

    def write_inputs(
        self,
        root: Path,
        readiness: dict | None = None,
        decisions: dict | None = None,
        *,
        temp_header: bool = False,
    ) -> tuple[Path, Path, Path]:
        snapshot_root = root / "base-snapshots"
        candidate_root = root / "candidate-snapshots"
        snapshot_root.mkdir(parents=True, exist_ok=True)
        candidate_root.mkdir(parents=True, exist_ok=True)
        for target in TARGETS:
            (snapshot_root / f"{target.rsplit(':', 1)[1]}.snapshot.json").write_text(
                json.dumps(target_snapshot_payload(target.rsplit(":", 1)[1])),
                encoding="utf-8",
            )
        readiness_path = root / "command-chat-response-route-planning-readiness.json"
        decisions_path = root / "command_chat_response_public_contract_decisions.json"
        effective_readiness = deepcopy(readiness) if readiness is not None else self.make_readiness(root)
        if effective_readiness.get("source_root") in (None, "/offline"):
            effective_readiness["source_root"] = str(root)
        effective_readiness.setdefault(
            "producer",
            {
                "script": "scripts/compare_reflection_snapshots.py",
                "argv": [
                    "scripts/compare_reflection_snapshots.py",
                    "--base-root",
                    effective_readiness["source_root"],
                    "--candidate-root",
                    str(candidate_root),
                    "--target-set",
                    "command-chat-response-route-planning",
                    "--readiness-report",
                    "--json",
                ],
                "output_name": "command-chat-response-route-planning-readiness.json",
            },
        )
        producer = effective_readiness.get("producer")
        if isinstance(producer, dict) and isinstance(producer.get("argv"), list):
            producer["argv"] = [
                effective_readiness["source_root"] if item == "/offline" else str(candidate_root) if item == "/offline-candidate" else item
                for item in producer["argv"]
            ]
        readiness_path.write_text(json.dumps(effective_readiness), encoding="utf-8")
        decisions_path.write_text(json.dumps(decisions if decisions is not None else self.make_decisions()), encoding="utf-8")
        if temp_header:
            public_header_path = root / "ObeliskApi.h"
            public_header_path.write_text("/* minimal public header without response-path ABI */\n", encoding="utf-8")
        else:
            public_header_path = READINESS.DEFAULT_PUBLIC_HEADER
        return readiness_path, decisions_path, public_header_path

    def test_accepts_planning_layout_second_source_but_not_public_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir))
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
            )

        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["runtime_ready"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
            report["blocked_behind_surfaces"],
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            [item["certificate_schema"] for item in report["future_public_abi"]["requires"]],
        )
        self.assertIn(
            "approved_runtime_principal_lifecycle_evidence",
            report["future_public_abi"]["requires"][0]["required_artifact"],
        )
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertEqual(READINESS.POST_PERMISSIONS_NEXT_STEP, report["post_permissions_next_step"])
        self.assertIn("runtime status reports", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertIn("post-runtime planning metadata", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertIn("generated certificate/build-report artifacts", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertIn("reviewed-template artifacts", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertIn("beta-notice artifacts", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertIn(
            "chat/RCON/broadcast/send-source alias artifacts",
            report["post_permissions_next_step"]["non_evidence_artifacts"],
        )
        self.assertIn("package-shape/support-tier artifacts", report["post_permissions_next_step"]["non_evidence_artifacts"])
        self.assertFalse(report["post_permissions_next_step"]["public_readiness_ready"])
        self.assertFalse(report["post_permissions_next_step"]["counts_toward_v1_completion"])
        self.assertEqual(
            READINESS.POST_PERMISSIONS_ABI_EVIDENCE_GUARDRAIL,
            report["post_permissions_abi_evidence_guardrail"],
        )
        self.assertIn(
            "response/send/broadcast readiness aliases cannot count without valid upstream promotion certificates",
            report["post_permissions_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "post-runtime planning metadata and chat/RCON/broadcast/send-source aliases cannot count without valid upstream promotion certificates",
            report["post_permissions_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "generated certificate reports; reviewed templates; package shape; beta notices stay blocked substitutes",
            report["post_permissions_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn(
            "runtime status and status artifacts stay blocked substitutes",
            report["post_permissions_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertFalse(report["post_permissions_abi_evidence_guardrail"]["certificate_metadata_counts_as_promotion"])
        self.assertFalse(report["post_permissions_abi_evidence_guardrail"]["response_send_broadcast_aliases_count_as_promotion"])
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertEqual(
            "obelisk.command-chat-response-post-identity-permissions-gap-diagnostic.v1",
            diagnostic["schema"],
        )
        self.assertEqual("blocked_waiting_for_upstream_identity_permissions", diagnostic["state"])
        self.assertEqual(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
            diagnostic["upstream_missing_surfaces"],
        )
        self.assertFalse(diagnostic["upstream_promotions_satisfied"])
        self.assertIn(
            "command_response_promotion_certificate",
            diagnostic["missing_after_valid_upstream_promotions"],
        )
        self.assertIn(
            "command_principal_authz_response_bridge_proof",
            diagnostic["missing_after_valid_upstream_promotions"],
        )
        self.assertIn(
            "command_principal_authz_response_bridge_proof",
            report["post_permissions_next_step"]["required_evidence"],
        )
        self.assertIn(
            "command/principal/authz/response bridge proof must be valid and hash-current; bridge reports, package shape, beta, status, and source aliases cannot replace it",
            report["post_permissions_abi_evidence_guardrail"]["required_fail_closed_guardrails"],
        )
        self.assertIn("approved_runtime_placeholders", diagnostic["non_authorizing_inputs"])
        self.assertIn("static_thunk_orientation", diagnostic["non_authorizing_inputs"])
        self.assertIn("response_intent_planning", diagnostic["non_authorizing_inputs"])
        self.assertIn("route_samples", diagnostic["non_authorizing_inputs"])
        self.assertIn("package_shape_installs", diagnostic["non_authorizing_inputs"])
        self.assert_gap_diagnostic_non_authorizing(diagnostic)
        self.assertEqual("candidate_only_non_counting", report["candidate_capture_classification"])
        self.assertEqual(
            "candidate_only_non_counting",
            report["candidate_capture_guardrail"]["classification"],
        )
        self.assertEqual(
            "approved_runtime_evidence_missing",
            report["candidate_capture_guardrail"]["requires_player_principal_runtime_blocker"],
        )
        self.assertIn("beta capture plans", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("approved runtime placeholders", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn(
            "chat/RCON/broadcast/send source alias probes",
            report["candidate_capture_guardrail"]["capture_inputs"],
        )
        self.assertIn("command candidates", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("package-shape installs", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("passive logs", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("post-runtime planning metadata", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("response bridge candidates", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("response intent planning artifacts", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("route samples", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertIn("static thunk orientation records", report["candidate_capture_guardrail"]["capture_inputs"])
        self.assertFalse(report["candidate_capture_guardrail"]["counts_toward_public_sdk"])
        self.assertFalse(report["candidate_capture_guardrail"]["approved_runtime_evidence"])
        self.assertFalse(report["candidate_capture_guardrail"]["command_support_ready"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertEqual([], report["blockers"])
        self.assertEqual(sorted(TARGETS), report["target_filters"])

    def test_rejects_missing_post_permissions_next_step_metadata(self) -> None:
        decisions = self.make_decisions()
        decisions.pop("post_permissions_next_step")
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("post_permissions_next_step_mismatch", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_missing_post_permissions_abi_evidence_guardrail(self) -> None:
        decisions = self.make_decisions()
        decisions.pop("post_permissions_abi_evidence_guardrail")
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("post_permissions_abi_evidence_guardrail_mismatch", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_post_permissions_next_step_credit_drift(self) -> None:
        decisions = self.make_decisions()
        decisions["post_permissions_next_step"]["counts_toward_v1_completion"] = True
        decisions["post_permissions_next_step"]["public_readiness_ready"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("post_permissions_next_step_mismatch", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_identity_contract_route_blocker_before_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                SURFACES,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_accepts_identity_contract_route_blocker_after_runtime_evidence_without_unlocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions = self.make_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, self.make_surfaces_with_accepted_runtime_evidence())
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
            report["blocked_behind_surfaces"],
        )
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
                "obelisk.command-chat-response-path-promotion-certificate.v1",
            ],
            [item["certificate_schema"] for item in report["future_public_abi"]["requires"]],
        )
        self.assertFalse(report["identity_public_contract_gate_missing_unlock_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_send_chat_api_allowed"])
        self.assertFalse(report["public_broadcast_api_allowed"])
        self.assertFalse(report["candidate_capture_guardrail"]["approved_runtime_evidence"])
        self.assertFalse(report["candidate_capture_guardrail"]["command_support_ready"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_accepts_post_runtime_identity_parent_lock_with_persisted_runtime_decision_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, self.make_surfaces_with_accepted_runtime_evidence())
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual(
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
            report["blocked_behind_surfaces"],
        )
        self.assertFalse(report["identity_public_contract_gate_missing_unlock_allowed"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(report["public_send_chat_api_allowed"])
        self.assertFalse(report["public_broadcast_api_allowed"])
        self.assertEqual(
            "identity_public_contract_gate_missing",
            report["candidate_capture_guardrail"]["current_route_blocker"],
        )
        self.assertFalse(report["candidate_capture_guardrail"]["approved_runtime_evidence"])
        self.assertFalse(report["candidate_capture_guardrail"]["command_support_ready"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_post_runtime_identity_parent_lock_rejects_accounting_unlock_overclaim(self) -> None:
        decisions = self.make_decisions()
        decisions["accounting_lock"]["counts_toward_runtime"] = True
        decisions["accounting_lock"]["public_or_runtime_accounting_allowed"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, self.make_surfaces_with_accepted_runtime_evidence())
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("accounting_lock_counts_toward_runtime_not_false", report["blockers"])
        self.assertIn(
            "accounting_lock_public_or_runtime_accounting_allowed_not_false",
            report["blockers"],
        )
        self.assertNotIn(
            "accounting_lock_route_blocker_stale_after_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertNotIn(
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_runtime_evidence_context_without_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions = self.make_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity["evidence"].pop("accepted_runtime_evidence", None)
            identity["evidence"]["accepted_runtime_evidence_context"] = {
                "status": "accepted",
                "next_blocker": "identity_public_contract_gate_missing",
            }
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_bare_accepted_runtime_evidence_without_canonical_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions = self.make_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            accepted = identity["evidence"]["accepted_runtime_evidence"]
            accepted.pop("approved_runtime_evidence_binding_required", None)
            accepted.pop("approved_runtime_evidence_binding", None)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn(
            "player_identity_accepted_runtime_evidence_binding_required_missing",
            report["blockers"],
        )
        self.assertIn(
            "player_identity_accepted_runtime_evidence_binding_missing_or_not_object",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_runtime_evidence_alias_sources_as_parent_transition(self) -> None:
        alias_sources = (
            "approved_runtime_placeholder",
            "approved_runtime_evidence_placeholder",
            "passive_status",
            "beta_capture_pack",
            "package_shape",
            "package_shape_install",
            "route_sample",
            "response_intent_planning",
            "runtime_principal_lifecycle_start_end_evidence",
            "public_readiness",
            "static_thunk_orientation",
        )
        for source in alias_sources:
            with self.subTest(source=source):
                surfaces = self.make_surfaces_with_accepted_runtime_evidence()
                identity = next(
                    surface
                    for surface in surfaces["surfaces"]
                    if surface["id"] == "obelisk.player_identity.v1"
                )
                identity["evidence"]["accepted_runtime_evidence"]["source"] = source
                blockers: list[dict] = []

                self.assertFalse(READINESS.player_identity_has_approved_runtime_evidence(identity))
                READINESS.validate_player_identity_accepted_runtime_evidence(
                    identity,
                    blockers,
                    label="$.surfaces.player_identity",
                )
                self.assertIn(
                    "player_identity_accepted_runtime_evidence_non_authorizing_context",
                    [blocker["reason"] for blocker in blockers],
                )

    def test_rejects_command_candidate_capture_route_blocker_bypass_without_player_principal_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions = self.make_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            surfaces = self.load_surfaces()
            response_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.command_chat_response_path.v1"
            )
            response_surface.setdefault("evidence", {})["command_response_candidate_capture"] = {
                "status": "accepted",
                "current_route_blocker": "identity_public_contract_gate_missing",
                "claim": "command response candidate unlocks public reply ABI",
            }
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_identity_promotion_without_permissions_admin_promotion(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_dependency_not_promoted", report["blockers"])
        self.assertNotIn("player_identity_evidence_not_approved", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_permissions_admin_promotion_before_player_identity(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_promoted_before_player_identity", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn(
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_permissions_admin_certificate_without_current_identity_binding(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            permissions = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.permissions_admin.v1",
            )
            certificate_key = "permissions_admin_promotion_certificate"
            certificate_path = REPO_ROOT / permissions["evidence"][certificate_key]["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["input_bindings"]["player_identity_promotion_certificate"]["sha256"] = "0" * 64
            self.rewrite_bound_certificate(
                permissions,
                "obelisk.permissions_admin.v1",
                certificate,
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn(
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            report["blockers"],
        )
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertFalse(diagnostic["upstream_promotions_satisfied"])
        self.assertIn("obelisk.permissions_admin.v1", diagnostic["upstream_missing_surfaces"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_player_identity_certificate_without_current_review_evidence(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            identity = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.player_identity.v1",
            )
            certificate_key = "player_identity_promotion_certificate"
            certificate_path = REPO_ROOT / identity["evidence"][certificate_key]["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["evidence"].pop(
                "identity_public_contract_decision_record_runtime_binding",
                None,
            )
            self.rewrite_bound_certificate(
                identity,
                "obelisk.player_identity.v1",
                certificate,
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn(
            "player_identity_promotion_certificate_identity_contract_runtime_binding_missing",
            report["blockers"],
        )
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertFalse(diagnostic["upstream_promotions_satisfied"])
        self.assertIn("obelisk.player_identity.v1", diagnostic["upstream_missing_surfaces"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_permissions_admin_certificate_with_stale_input_binding_digest(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            permissions = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.permissions_admin.v1",
            )
            certificate_key = "permissions_admin_promotion_certificate"
            certificate_path = REPO_ROOT / permissions["evidence"][certificate_key]["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["input_bindings"]["permissions_admin_surface_record_sha256"] = "0" * 64
            self.rewrite_bound_certificate(
                permissions,
                "obelisk.permissions_admin.v1",
                certificate,
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn(
            "permissions_admin_promotion_certificate_permissions_surface_record_sha256_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_input_binding_sha256_mismatch",
            report["blockers"],
        )
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertFalse(diagnostic["upstream_promotions_satisfied"])
        self.assertIn("obelisk.permissions_admin.v1", diagnostic["upstream_missing_surfaces"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_permissions_admin_certificate_shortcuts_without_accounting_credit(self) -> None:
        cases = (
            "builder_report",
            "inline_certificate",
            "schema_only",
            "path_only",
            "sha_only",
            "identity_certificate",
            "binding_extra_status",
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory(
                    dir=CERTIFICATE_TEMP_PARENT,
                    prefix=CERTIFICATE_TEMP_PREFIX,
                ) as temp_dir:
                    root = Path(temp_dir)
                    surfaces = self.load_surfaces()
                    identity = self.promote_surface_with_certificate(
                        root,
                        surfaces,
                        "obelisk.player_identity.v1",
                    )
                    permissions = next(
                        item
                        for item in surfaces["surfaces"]
                        if item["id"] == "obelisk.permissions_admin.v1"
                    )
                    permissions["status"] = "promoted"
                    permissions_evidence = permissions.setdefault("evidence", {})
                    certificate_key = "permissions_admin_promotion_certificate"
                    permissions_evidence.pop(certificate_key, None)
                    expected_reason = "permissions_admin_promotion_certificate_inline_certificate_not_hash_bound"

                    if case == "builder_report":
                        builder_payload = self.inline_promotion_certificate(
                            permissions,
                            "obelisk.permissions_admin.v1",
                        )
                        builder_payload["certificate_builder_report"] = {
                            "schema": "obelisk.permissions-admin-promotion-certificate-builder-report.v1",
                            "generated_certificate_sha256": "a" * 64,
                            "counts_toward_public_sdk": False,
                            "counts_toward_runtime": False,
                            "counts_toward_v1_completion": False,
                        }
                        permissions_evidence[certificate_key] = self.bind_certificate_artifact(
                            root,
                            "permissions_admin_promotion_certificate_builder_report.json",
                            builder_payload,
                        )
                        expected_reason = "permissions_admin_promotion_certificate_builder_report_not_certificate"
                    elif case == "inline_certificate":
                        permissions_evidence[certificate_key] = self.inline_promotion_certificate(
                            permissions,
                            "obelisk.permissions_admin.v1",
                        )
                    elif case == "schema_only":
                        permissions_evidence[certificate_key] = {
                            "schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                        }
                    elif case == "path_only":
                        certificate = self.inline_promotion_certificate(
                            permissions,
                            "obelisk.permissions_admin.v1",
                        )
                        binding = self.bind_certificate_artifact(
                            root,
                            "permissions_admin_promotion_certificate_path_only.json",
                            certificate,
                        )
                        permissions_evidence[certificate_key] = {"path": binding["path"]}
                        expected_reason = "permissions_admin_promotion_certificate_sha256_invalid"
                    elif case == "sha_only":
                        permissions_evidence[certificate_key] = {"sha256": "a" * 64}
                        expected_reason = "permissions_admin_promotion_certificate_path_invalid"
                    elif case == "identity_certificate":
                        permissions_evidence[certificate_key] = deepcopy(
                            identity["evidence"]["player_identity_promotion_certificate"]
                        )
                        expected_reason = "permissions_admin_promotion_certificate_schema_mismatch"
                    elif case == "binding_extra_status":
                        certificate = self.inline_promotion_certificate(
                            permissions,
                            "obelisk.permissions_admin.v1",
                        )
                        binding = self.bind_certificate_artifact(
                            root,
                            "permissions_admin_promotion_certificate_binding_extra_status.json",
                            certificate,
                        )
                        binding["status"] = "promoted"
                        permissions_evidence[certificate_key] = binding
                        expected_reason = "permissions_admin_promotion_certificate_binding_keys_mismatch"

                    readiness_path, decisions_path, public_header_path = self.write_inputs(root)
                    surfaces_path = self.write_surfaces(root, surfaces)
                    report = READINESS.build_report(
                        root,
                        readiness_path,
                        decisions_path,
                        public_header_path,
                        surfaces_path,
                    )

                self.assertFalse(report["valid"])
                self.assertFalse(report["accepted_for_planning"])
                self.assertIn(expected_reason, report["blockers"])
                self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
                self.assert_public_runtime_v1_flags_false(report)
                diagnostic = report["post_identity_permissions_gap_diagnostic"]
                self.assertFalse(diagnostic["upstream_promotions_satisfied"])
                self.assertIn("obelisk.permissions_admin.v1", diagnostic["upstream_missing_surfaces"])
                self.assert_gap_diagnostic_non_authorizing(diagnostic)

    def test_rejects_inline_promotion_certificate_without_hash_bound_artifact(self) -> None:
        surfaces = self.load_surfaces()
        identity = next(
            item for item in surfaces["surfaces"] if item["id"] == "obelisk.player_identity.v1"
        )
        identity["status"] = "promoted"
        identity.setdefault("evidence", {})["player_identity_promotion_certificate"] = (
            self.inline_promotion_certificate(identity, "obelisk.player_identity.v1")
        )

        blockers: list[dict[str, object]] = []
        READINESS.validate_surfaces(surfaces, blockers)

        reasons = [item["reason"] for item in blockers]
        self.assertIn(
            "player_identity_promotion_certificate_inline_certificate_not_hash_bound",
            reasons,
        )
        self.assertIn("player_identity_evidence_not_approved", reasons)

    def test_rejects_hash_bound_permissions_admin_certificate_payload_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            permissions = self.promote_surface_with_certificate(
                root,
                surfaces,
                "obelisk.permissions_admin.v1",
            )
            certificate_key = "permissions_admin_promotion_certificate"
            certificate_path = REPO_ROOT / permissions["evidence"][certificate_key]["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["identity_public_contract_gate_missing_allows_send_chat"] = True
            certificate["commands_replies_shortcut_public_response_allowed"] = True
            certificate["public_readiness_ready"] = True
            certificate["evidence"]["runtimeWindowReady"] = True
            certificate["evidence"]["beta_window_status"] = {"status": "ready"}
            certificate["evidence"]["CallProcessEventResponseShortcutAllowed"] = True
            certificate["evidence"]["notice_status_artifact"] = {"status": "sent"}
            self.rewrite_bound_certificate(
                permissions,
                "obelisk.permissions_admin.v1",
                certificate,
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_public_surface_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_route_or_runtime_readiness_alias_missing_upstream_certificates",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_payload_non_evidence_artifact_credit_overclaim",
            report["blockers"],
        )
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertFalse(diagnostic["upstream_promotions_satisfied"])
        self.assertIn("obelisk.permissions_admin.v1", diagnostic["upstream_missing_surfaces"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_response_terminal_certificate_binding_as_non_counting_metadata(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            response = next(
                item
                for item in surfaces["surfaces"]
                if item["id"] == "obelisk.command_chat_response_path.v1"
            )
            response.setdefault("evidence", {})["command_response_promotion_certificate"] = (
                self.bind_certificate_artifact(
                    root,
                    "command-response-terminal-certificate.json",
                    {
                        "schema": READINESS.COMMAND_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": READINESS.SURFACE,
                        "promotion_status": "promoted",
                        "public_readiness_ready": True,
                        "evidence": {
                            "runtimeWindowReady": True,
                            "package_shape_artifact": {
                                "artifact_class": "package_shape",
                                "status": "ready",
                            },
                        },
                    },
                )
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn(
            "command_response_promotion_certificate_terminal_artifact_non_counting",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_payload_public_surface_overclaim",
            report["blockers"],
        )
        self.assertIn(
            "command_response_promotion_certificate_payload_non_evidence_artifact_credit_overclaim",
            report["blockers"],
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_accepts_promoted_identity_and_permissions_without_unlocking_response_path(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=CERTIFICATE_TEMP_PARENT,
            prefix=CERTIFICATE_TEMP_PREFIX,
        ) as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            self.promote_surface_with_certificate(root, surfaces, "obelisk.player_identity.v1")
            self.promote_surface_with_certificate(root, surfaces, "obelisk.permissions_admin.v1")
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertTrue(report["valid"])
        self.assertEqual([], report["blockers"])
        diagnostic = report["post_identity_permissions_gap_diagnostic"]
        self.assertEqual("upstream_promoted_but_response_path_still_blocked", diagnostic["state"])
        self.assertEqual([], diagnostic["upstream_missing_surfaces"])
        self.assertTrue(diagnostic["upstream_promotions_satisfied"])
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
            ],
            [
                item["required_certificate_schema"]
                for item in diagnostic["upstream_dependencies"]
            ],
        )
        self.assertTrue(
            all(
                item["valid_hash_bound_promotion_certificate_present"]
                for item in diagnostic["upstream_dependencies"]
            )
        )
        self.assertIn(
            "isolated_runtime_delivery_evidence",
            diagnostic["missing_after_valid_upstream_promotions"],
        )
        self.assertIn(
            "second_source_or_independently_reviewed_response_target_evidence",
            diagnostic["missing_after_valid_upstream_promotions"],
        )
        self.assert_gap_diagnostic_non_authorizing(diagnostic)
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_player_identity_runtime_evidence_alias_that_skips_identity_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decisions = self.make_decisions()
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            surfaces = self.make_surfaces_with_accepted_runtime_evidence()
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity["evidence"]["accepted_runtime_evidence"]["acceptedRuntimeEvidenceReady"] = True
            identity["evidence"]["accepted_runtime_evidence"]["claim"] = (
                "accepted runtime evidence unlocks public ABI"
            )
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
                current_route_blocker="identity_public_contract_gate_missing",
            )

        self.assertFalse(report["valid"])
        self.assertIn(
            "player_identity_accepted_runtime_evidence_alias_skips_identity_public_contract_gate",
            report["blockers"],
        )
        self.assertFalse(report["counts_toward_public_sdk"])

    def test_rejects_stale_runtime_route_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, self.make_surfaces_with_accepted_runtime_evidence())
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn(
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_accounting_lock_identity_route_before_runtime_evidence(self) -> None:
        decisions = self.make_decisions()
        decisions["accounting_lock"] = {
            "dependency_chain_locked": True,
            "current_route_blocker": "identity_public_contract_gate_missing",
            "remaining_route_blockers": ["identity_public_contract_gate_missing"],
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "public_or_runtime_accounting_allowed": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, decisions=decisions)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                SURFACES,
            )

        self.assertFalse(report["valid"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_remaining_route_blocker_out_of_order", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_release_or_v1_readiness_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            decisions["release_note"] = "v1 SDK completion is ready and release readiness is public."
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_broad_release_sdk_wording_overclaim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "release_notes": [
                    "complete SDK is ready",
                    "full SDK is available",
                    "production SDK is supported",
                    "stable SDK is enabled",
                    "v1.0 stable is public",
                ],
                "aliases": {
                    "completeSdkReady": True,
                    "full-sdk-ready": True,
                    "production sdk ready": True,
                    "stableSdkReady": True,
                    "releaseReadinessReady": True,
                    "v1.0-stable-ready": True,
                },
            },
            blockers,
        )

        reasons = [item["reason"] for item in blockers]
        self.assertEqual(5, reasons.count("positive_public_surface_claim"))
        self.assertEqual(6, reasons.count("public_surface_overclaim"))

    def test_rejects_final_authz_response_path_shortcut_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "finalGateReady": True,
                    "authzReady": True,
                    "responsePathComplete": True,
                },
                "split_claims": [
                    {"field": "finalGateReady", "status": "ready"},
                    {"field": "authzReady", "value": True},
                    {"field": "responsePathComplete", "state": "complete"},
                ],
                "notes": [
                    "final gate ready now",
                    "authz ready now",
                    "response path complete now",
                    "response path remains blocked until predecessor certificates",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.finalGateReady",
            "$.aliases.authzReady",
            "$.aliases.responsePathComplete",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
            self.assertIn(
                (
                    "route_or_runtime_readiness_alias_missing_upstream_certificates",
                    f"$.notes[{index}]",
                ),
                paths,
            )
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_rejects_public_abi_identity_lookup_handle_wording(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "notes": [
                    "public ABI exposes player lookup handles before ResourceHandle promotion",
                    "public ABI does not expose player lookup handles before ResourceHandle promotion",
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_abi_identity_lookup_handle_claim", "$.notes[0]"), paths)
        self.assertNotIn(("public_abi_identity_lookup_handle_claim", "$.notes[1]"), paths)

    def test_rejects_nested_route_and_accounting_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "secondary_report": {
                    "routeReady": True,
                    "public-route-ready": True,
                    "counts_toward_public_sdk": True,
                    "counts_toward_runtime": True,
                    "counts_toward_v1_completion": True,
                    "public_or_runtime_accounting_allowed": True,
                    "stableClaimAllowed": True,
                    "v1_completion_ready": True,
                    "promotedSurfaceCount": 1,
                    "promoted_surfaces_count": "1/4",
                    "surfacePromotionCount": 1,
                    "promotedSurfaceTotal": 1,
                    "promoted_surfaces_total": "1/4",
                    "surfacePromotionTotal": 1,
                    "promotedSurfaceCountZero": "0/4",
                    "promotedSurfaceTotalZero": "0/4",
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.routeReady"),
                ("public_surface_overclaim", "$.secondary_report.public-route-ready"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_public_sdk"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_runtime"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_v1_completion"),
                ("public_surface_overclaim", "$.secondary_report.public_or_runtime_accounting_allowed"),
                ("public_surface_overclaim", "$.secondary_report.stableClaimAllowed"),
                ("public_surface_overclaim", "$.secondary_report.v1_completion_ready"),
                ("public_surface_overclaim", "$.secondary_report.promotedSurfaceCount"),
                ("public_surface_overclaim", "$.secondary_report.promoted_surfaces_count"),
                ("public_surface_overclaim", "$.secondary_report.surfacePromotionCount"),
                ("public_surface_overclaim", "$.secondary_report.promotedSurfaceTotal"),
                ("public_surface_overclaim", "$.secondary_report.promoted_surfaces_total"),
                ("public_surface_overclaim", "$.secondary_report.surfacePromotionTotal"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_collect_surface_overclaims_rejects_split_key_value_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "claims": [
                    {"key": "publicResponsePathReady", "value": True},
                    {"field": "public-reply-abi-ready", "state": "ready"},
                    {"name": "routeGateUnlocked", "enabled": "yes"},
                    {"key": "publicResponsePathReady", "value": False},
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_surface_overclaim", "$.claims[0]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[1]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[2]"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.claims[3]"), paths)

    def test_rejects_non_evidence_artifact_metadata_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "metadata": {
                    "package": {"artifact_class": "package_shape", "status": "ready"},
                    "beta": {"source_kind": "beta_notice", "counts_toward_runtime": True},
                    "passive": {"kind": "passive_monitor", "progress": "1/4"},
                    "no_users": {"artifact_type": "no-users status", "state": "supported"},
                    "diagnostic": {"report_kind": "diagnostic candidate", "readiness": "accepted"},
                    "post_runtime": {"artifact_kind": "post_runtime_planning_metadata", "status": "ready"},
                    "source_alias": {"source": "chat/RCON/broadcast/send-source alias", "status": "ready"},
                    "non_evidence_artifacts": [
                        {"artifact_class": "passive_monitor", "status": False}
                    ],
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.metadata.package.status",
            "$.metadata.beta.counts_toward_runtime",
            "$.metadata.passive.progress",
            "$.metadata.no_users.state",
            "$.metadata.diagnostic.readiness",
            "$.metadata.post_runtime.status",
            "$.metadata.source_alias.status",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertNotIn(
            ("non_evidence_artifact_credit_overclaim", "$.metadata.non_evidence_artifacts[0].status"),
            paths,
        )

    def test_rejects_planning_layout_and_route_accepted_reply_send_chat_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "planningLayoutPublicReplyOrSendChatAbiReady": True,
                    "routeAcceptedAsPublicReplyAbi": True,
                    "routeAcceptedAsPublicReplyAbiReady": True,
                    "routeAccepted": True,
                    "publicRuntimeReadinessReady": True,
                    "planning_layout_accepted": True,
                    "staticThunkOrientationReady": True,
                    "static_thunk_orientation_promoted": True,
                    "responseIntentReady": True,
                    "response_intent_promoted": True,
                },
                "claims": [
                    {"field": "planning-layout-public-send-chat-abi-ready", "state": "ready"},
                    {"name": "routeAcceptedForPublicReplyOrSendChatAbi", "enabled": "yes"},
                    {"name": "routeAcceptedForPublicRuntimeReadiness", "enabled": "yes"},
                    "planning_layout_public_reply_or_send_chat_abi_ready",
                    "route accepted as public send-chat ABI ready",
                    "route accepted remains blocked",
                    "static thunk orientation ready for promotion",
                    "response intent promoted",
                ],
                "non_claims": [
                    "route accepted as public runtime readiness",
                    "route accepted remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_surface_overclaim", "$.aliases.planningLayoutPublicReplyOrSendChatAbiReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.routeAcceptedAsPublicReplyAbi"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.routeAcceptedAsPublicReplyAbiReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.routeAccepted"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.publicRuntimeReadinessReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.planning_layout_accepted"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.staticThunkOrientationReady"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.staticThunkOrientationReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.static_thunk_orientation_promoted"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.static_thunk_orientation_promoted"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.responseIntentReady"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.responseIntentReady"), paths)
        self.assertIn(("public_surface_overclaim", "$.aliases.response_intent_promoted"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.aliases.response_intent_promoted"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[0]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[1]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[2]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[3]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[4]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[4]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[5]"), paths)
        self.assertNotIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[5]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[6]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[6]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[7]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[7]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.non_claims[0]"), paths)
        self.assertNotIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.non_claims[1]"), paths)
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
            ],
            certificate_detail["required_certificate_schemas"],
        )

    def test_rejects_static_thunk_and_response_intent_planning_is_ready_wording(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "claims": [
                    "static thunk orientation is ready",
                    "response intent planning is ready",
                    "static thunk orientation remains blocked",
                    "response intent planning remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for index in (0, 1):
            self.assertIn(("non_evidence_artifact_credit_overclaim", f"$.claims[{index}]"), paths)
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        for index in (2, 3):
            self.assertNotIn(("non_evidence_artifact_credit_overclaim", f"$.claims[{index}]"), paths)
            self.assertNotIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)

    def test_rejects_nested_runtime_readiness_alias_values(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "publicRuntimeReady": {"state": {"ready": True}},
                    "runtimeReadinessAccepted": {"status": {"verified": "yes"}},
                    "identityPublicContractGateMissingAllowsSendChat": {
                        "review": {"ready": True}
                    },
                },
                "claims": [
                    {
                        "field": "public_runtime_readiness_accepted",
                        "value": {"nested": {"status": "ready"}},
                    }
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.publicRuntimeReady",
            "$.aliases.runtimeReadinessAccepted",
            "$.aliases.identityPublicContractGateMissingAllowsSendChat",
            "$.claims[0]",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        self.assertIn(
            ("public_surface_overclaim", "$.aliases.identityPublicContractGateMissingAllowsSendChat"),
            paths,
        )

    def test_rejects_response_send_broadcast_aliases_and_certificate_metadata_without_upstream_certificates(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "publicResponseSendBroadcastReady": True,
                    "routeAcceptedAsPublicSendChatAbiReady": True,
                    "identityPublicContractGateMissingAllowsBroadcast": True,
                },
                "metadata": {
                    "fake_player_identity_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "evidence": {"reviewed_artifact_hash": "a" * 64},
                    },
                    "fake_permissions_admin_certificate": {
                        "certificate_schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                        "status": "promoted",
                        "counts_toward_public_sdk": True,
                    },
                },
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.publicResponseSendBroadcastReady",
            "$.aliases.routeAcceptedAsPublicSendChatAbiReady",
            "$.aliases.identityPublicContractGateMissingAllowsBroadcast",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        for label in (
            "$.metadata.fake_player_identity_certificate",
            "$.metadata.fake_permissions_admin_certificate",
        ):
            self.assertIn(
                ("promotion_certificate_metadata_missing_required_upstream_certificates", label),
                paths,
            )
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "promotion_certificate_metadata_missing_required_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
            ],
            certificate_detail["required_upstream_certificate_schemas"],
        )

    def test_rejects_plain_inline_and_unbound_upstream_promotion_certificate_metadata(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "metadata": {
                    "plain_player_identity_promotion_certificate": (
                        READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
                    ),
                    "plain_permissions_admin_promotion_certificate": (
                        READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA
                    ),
                    "inline_player_identity_promotion_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": "obelisk.player_identity.v1",
                    },
                    "inline_permissions_admin_promotion_certificate": {
                        "certificate_schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                    },
                    "unbound_player_identity_promotion_certificate": {
                        "path": "docs/fake-player-identity-certificate.json",
                    },
                    "unbound_permissions_admin_promotion_certificate": {
                        "sha256": "b" * 64,
                    },
                    "hash_bound_player_identity_promotion_certificate": {
                        "path": "docs/hash-bound-player-identity-certificate.json",
                        "sha256": "a" * 64,
                    },
                    "required_identity_promotion_certificate": {
                        "schema": READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "promotion_status": "promoted",
                    },
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.metadata.plain_player_identity_promotion_certificate",
            "$.metadata.plain_permissions_admin_promotion_certificate",
            "$.metadata.inline_player_identity_promotion_certificate",
            "$.metadata.inline_permissions_admin_promotion_certificate",
            "$.metadata.unbound_player_identity_promotion_certificate",
            "$.metadata.unbound_permissions_admin_promotion_certificate",
        ):
            self.assertIn(
                ("promotion_certificate_metadata_missing_required_upstream_certificates", label),
                paths,
            )
        self.assertNotIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.metadata.hash_bound_player_identity_promotion_certificate",
            ),
            paths,
        )
        self.assertNotIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.metadata.required_identity_promotion_certificate",
            ),
            paths,
        )

    def test_rejects_response_surface_placeholder_upstream_promotion_certificate_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            response_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.command_chat_response_path.v1"
            )
            response_surface.setdefault("evidence", {})[
                "player_identity_promotion_certificate"
            ] = READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
            response_surface["evidence"]["permissions_admin_promotion_certificate"] = {
                "path": "docs/fake-permissions-admin-certificate.json",
            }
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        self.assertIn(
            "promotion_certificate_metadata_missing_required_upstream_certificates",
            report["blockers"],
        )
        paths = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        self.assertIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.surfaces.command_chat_response_path.evidence.player_identity_promotion_certificate",
            ),
            paths,
        )
        self.assertIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.surfaces.command_chat_response_path.evidence.permissions_admin_promotion_certificate",
            ),
            paths,
        )

    def test_rejects_direct_runtime_evidence_on_response_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            response_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.command_chat_response_path.v1"
            )
            response_surface.setdefault("evidence", {})["approved_runtime_evidence"] = {
                "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                "result": "approved runtime principal lifecycle evidence",
                "next_blocker": "identity_public_contract_gate_missing",
            }
            response_surface["evidence"]["identity_public_contract_decision_record"] = {
                "schema": "obelisk.player-identity-public-contract-decision-record.v1",
                "review_status": "reviewed",
            }
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        paths = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        self.assertIn(
            (
                "direct_identity_or_runtime_evidence_substitute",
                "$.surfaces.command_chat_response_path.evidence.approved_runtime_evidence",
            ),
            paths,
        )
        self.assertIn(
            (
                "direct_identity_or_runtime_evidence_substitute",
                "$.surfaces.command_chat_response_path.evidence.identity_public_contract_decision_record",
            ),
            paths,
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_upstream_surface_placeholder_promotion_certificate_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = self.load_surfaces()
            identity_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            permissions_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.permissions_admin.v1"
            )
            identity_surface.setdefault("evidence", {})[
                "player_identity_promotion_certificate"
            ] = READINESS.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
            permissions_surface.setdefault("evidence", {})[
                "permissions_admin_promotion_certificate"
            ] = {
                "schema": READINESS.PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
                "promotion_status": "promoted",
            }
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = self.write_surfaces(root, surfaces)
            report = READINESS.build_report(
                root,
                readiness_path,
                decisions_path,
                public_header_path,
                surfaces_path,
            )

        self.assertFalse(report["valid"])
        paths = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        self.assertIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.surfaces.player_identity.evidence.player_identity_promotion_certificate",
            ),
            paths,
        )
        self.assertIn(
            (
                "promotion_certificate_metadata_missing_required_upstream_certificates",
                "$.surfaces.permissions_admin.evidence.permissions_admin_promotion_certificate",
            ),
            paths,
        )
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_broad_accept_promote_and_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "commandResponseAccepted": True,
                    "commandResponsePromoted": {"status": "ready"},
                    "commandsRepliesAccepted": True,
                    "sendChatPromoted": "ready",
                    "routePromoted": True,
                    "publicRuntimeReadinessPromoted": True,
                    "v1CompletionProgressContribution": "25%",
                    "p0DependencyChainProgressContribution": 1,
                    "progress": "1/2",
                    "progressReady": True,
                    "readinessProgress": "1/4",
                    "readinessReady": True,
                    "runtimeEvidenceReady": True,
                },
                "split_claims": [
                    {"field": "commandResponseAccepted", "status": "accepted"},
                    {"name": "sendChatPromoted", "value": {"state": "ready"}},
                    {"key": "v1CompletionProgress", "value": "10%"},
                    {"field": "commandsRepliesAccepted", "status": "blocked"},
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.commandResponseAccepted",
            "$.aliases.commandResponsePromoted",
            "$.aliases.commandsRepliesAccepted",
            "$.aliases.sendChatPromoted",
            "$.aliases.routePromoted",
            "$.aliases.publicRuntimeReadinessPromoted",
            "$.aliases.v1CompletionProgressContribution",
            "$.aliases.p0DependencyChainProgressContribution",
            "$.aliases.progress",
            "$.aliases.progressReady",
            "$.aliases.readinessProgress",
            "$.aliases.readinessReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.aliases.runtimeEvidenceReady"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[3]"), paths)

    def test_rejects_unlocked_public_abi_reply_send_chat_claim_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "publicAbiUnlocked": True,
                    "publicReplyAbiUnlocked": True,
                    "replyUnlocked": True,
                    "sendChatApiUnlocked": True,
                },
                "claims": [
                    "public_abi_unlocked",
                    "reply_abi_unlocked",
                    "send_chat_api_unlocked",
                    "publicReplyOrSendChatAbiUnlocked",
                    "send_chat_api_unlocked remains blocked",
                ],
            },
            blockers,
        )

        self.assertEqual(4, [item["reason"] for item in blockers].count("public_surface_overclaim"))
        self.assertEqual(4, [item["reason"] for item in blockers].count("positive_public_surface_claim"))
        self.assertNotIn(("positive_public_surface_claim", "$.claims[4]"), [(item["reason"], item["label"]) for item in blockers])

    def test_rejects_activation_notice_reachability_request_and_identity_gate_unlock_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "activationPreconditionsMet": True,
                    "betaNoticeSent": True,
                    "discordSent": True,
                    "publicReachabilityReady": True,
                    "requestCheckReady": True,
                    "requestPackReady": True,
                    "identityPublicContractGateMissingAllowsSendChat": True,
                },
                "claims": [
                    {"field": "identity_public_contract_gate_missing_allows_broadcast", "state": "ready"},
                    "activation preconditions met make send-chat API ready",
                    "beta notice sent makes replies ready",
                    "public reachability is reachable so broadcast API is enabled",
                    "request checks passed make command replies public",
                    "identity_public_contract_gate_missing unlocks chat/send/broadcast APIs",
                    "identity_public_contract_gate_missing remains blocked until permissions/admin promotion",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.activationPreconditionsMet",
            "$.aliases.betaNoticeSent",
            "$.aliases.discordSent",
            "$.aliases.publicReachabilityReady",
            "$.aliases.requestCheckReady",
            "$.aliases.requestPackReady",
            "$.aliases.identityPublicContractGateMissingAllowsSendChat",
            "$.claims[0]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(1, 6):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[5]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[6]"), paths)
        self.assertNotIn(
            ("route_or_runtime_readiness_alias_missing_upstream_certificates", "$.claims[6]"),
            paths,
        )

    def test_rejects_response_bridge_passive_seed_and_copied_intent_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "responseBridgeReady": True,
                    "commandPrincipalAuthzResponseBridgeReady": True,
                    "passiveEvidenceReady": True,
                    "passiveChatEvidenceReady": True,
                    "copiedResponseIntentPlanningReady": True,
                    "copiedResponseIntentReady": True,
                    "localRoutingSeedReady": True,
                    "localChatSeedReady": True,
                    "chatSeedReady": True,
                },
                "split_claims": [
                    {"name": "responseBridgeReady", "isReady": True},
                    {"claim": "passiveEvidenceReady", "result": "accepted"},
                    {"field": "copiedResponseIntentPlanningReady", "outcome": "promoted"},
                    {"key": "localRoutingSeedReady", "verdict": "ready"},
                    {"name": "responseBridgeReady", "isReady": False},
                ],
                "claims": [
                    "response bridge planning is ready",
                    "copied response intent planning is accepted for public runtime readiness",
                    "passive evidence is sufficient for reply/send-chat ABI",
                    "local routing seed unlocks command response path",
                    "local chat seeds are ready for public send-chat API",
                    "response bridge planning remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.responseBridgeReady",
            "$.aliases.commandPrincipalAuthzResponseBridgeReady",
            "$.aliases.passiveEvidenceReady",
            "$.aliases.passiveChatEvidenceReady",
            "$.aliases.copiedResponseIntentPlanningReady",
            "$.aliases.copiedResponseIntentReady",
            "$.aliases.localRoutingSeedReady",
            "$.aliases.localChatSeedReady",
            "$.aliases.chatSeedReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[4]"), paths)
        for index in range(5):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[5]"), paths)

    def test_rejects_notice_route_snapshot_and_bundle_positive_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "notice_bundle": {"status": "delivered"},
                "notices_package": {"state": "complete"},
                "route_snapshot": {"result": "accepted"},
                "route_bundle": {"status": "ready"},
                "route_snapshot_bundle": {"outcome": "sent"},
                "claims": [
                    {"field": "notice_bundle", "delivered": True},
                    {"name": "route_snapshot_bundle", "complete": True},
                    "notice bundle delivered makes command/chat response ready",
                    "route snapshot bundle complete unlocks public runtime readiness",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.notice_bundle",
            "$.notices_package",
            "$.route_snapshot",
            "$.route_bundle",
            "$.route_snapshot_bundle",
            "$.claims[0]",
            "$.claims[1]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[3]"), paths)

    def test_rejects_next_action_passive_notice_and_status_artifacts_as_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "next_action_runner_output": {"progress": "1/4"},
                "passive_monitor_tick": {"evidence_status": "accepted"},
                "passive_player_summary": {"readiness": "ready"},
                "notice_status_artifact": {"status": "sent"},
                "route_status_report": {"readiness": {"state": "verified"}},
                "source_marker_pair": {
                    "source_marker": "next_action_runner_output",
                    "status": "accepted",
                },
                "split_claims": [
                    {"field": "next_action_runner_output", "status": "ready"},
                    {"name": "passive_monitor_snapshot", "progress": "1/3"},
                    {"claim": "notice_status_artifact", "result": "accepted"},
                    {"key": "route_status_report", "value": "blocked"},
                ],
                "claims": [
                    "next-action planner output is accepted as command response evidence",
                    "passive monitor snapshot counts as progress",
                    "notice status artifact makes readiness ready",
                    "route status report is progress credit",
                    "next-action planner output remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.next_action_runner_output.progress",
            "$.passive_monitor_tick",
            "$.passive_player_summary",
            "$.notice_status_artifact",
            "$.route_status_report",
            "$.source_marker_pair.status",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.claims[0]",
            "$.claims[1]",
            "$.claims[2]",
            "$.claims[3]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertNotIn(("non_evidence_artifact_credit_overclaim", "$.split_claims[3]"), paths)
        self.assertNotIn(("non_evidence_artifact_credit_overclaim", "$.claims[4]"), paths)

    def test_rejects_beta_plan_passive_log_and_command_candidate_positive_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "beta_capture_plan": {"progress": "1/2"},
                "passive_runtime_log": {"status": "accepted"},
                "command_response_candidate": {"readiness": "ready"},
                "debug_capture": {
                    "claim": "command_response_candidate",
                    "status": "accepted",
                },
                "claims": [
                    "beta capture plan makes command/chat response ready",
                    "passive log accepted counts toward SDK/P0 progress",
                    "command response candidate capture unlocks public reply ABI",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.beta_capture_plan.progress"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.passive_runtime_log.status"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.command_response_candidate.readiness"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.debug_capture"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[1]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)

    def test_non_evidence_artifact_inventory_strings_are_not_credit_but_structured_credit_is_rejected(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "non_evidence_artifacts": [
                    "next-action runner/planner artifacts",
                    "runtime status reports",
                    "package-shape/support-tier artifacts",
                    {"artifact_kind": "status_report", "status": "ready"},
                    {"artifact": "notice_status_artifact", "readiness": "ready"},
                    {"artifact_class": "package_shape", "counts_toward_public_sdk": True},
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.non_evidence_artifacts[0]",
            "$.non_evidence_artifacts[1]",
            "$.non_evidence_artifacts[2]",
        ):
            self.assertNotIn(("positive_public_surface_claim", label), paths)
        for label in (
            "$.non_evidence_artifacts[3]",
            "$.non_evidence_artifacts[4]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(
            ("non_evidence_artifact_credit_overclaim", "$.non_evidence_artifacts[5].counts_toward_public_sdk"),
            paths,
        )
        self.assertIn(
            ("public_surface_overclaim", "$.non_evidence_artifacts[5].counts_toward_public_sdk"),
            paths,
        )

    def test_rejects_nested_router_abi_and_runtime_authorization_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "secondary_report": {
                    "acceptedRuntimeEvidenceReady": True,
                    "broadcastReady": True,
                    "commandRouteReady": True,
                    "commandRouterAllowed": True,
                    "commandsUnlocked": True,
                    "moderationReady": True,
                    "operatorApprovalGranted": True,
                    "publicAbiAllowed": True,
                    "publicBridgeAbiAllowed": True,
                    "publicCommandRouterAllowed": True,
                    "publicResponseAbiAllowed": True,
                    "replyPathReady": True,
                    "responseHeaderAllowed": True,
                    "replySendChatRouterClaimsAllowed": True,
                    "runtimeWorkAuthorized": True,
                    "serverOperationsAuthorized": True,
                    "sendChatReady": True,
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.acceptedRuntimeEvidenceReady"),
                ("public_surface_overclaim", "$.secondary_report.broadcastReady"),
                ("public_surface_overclaim", "$.secondary_report.commandRouteReady"),
                ("public_surface_overclaim", "$.secondary_report.commandRouterAllowed"),
                ("public_surface_overclaim", "$.secondary_report.commandsUnlocked"),
                ("public_surface_overclaim", "$.secondary_report.moderationReady"),
                ("public_surface_overclaim", "$.secondary_report.operatorApprovalGranted"),
                ("public_surface_overclaim", "$.secondary_report.publicAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicBridgeAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicCommandRouterAllowed"),
                ("public_surface_overclaim", "$.secondary_report.publicResponseAbiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.replyPathReady"),
                (
                    "route_or_runtime_readiness_alias_missing_upstream_certificates",
                    "$.secondary_report.replyPathReady",
                ),
                ("public_surface_overclaim", "$.secondary_report.responseHeaderAllowed"),
                ("public_surface_overclaim", "$.secondary_report.replySendChatRouterClaimsAllowed"),
                ("public_surface_overclaim", "$.secondary_report.runtimeWorkAuthorized"),
                ("public_surface_overclaim", "$.secondary_report.serverOperationsAuthorized"),
                ("public_surface_overclaim", "$.secondary_report.sendChatReady"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_downstream_identity_permission_capability_and_route_gate_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "secondary_report": {
                    "adminAuthorityReady": True,
                    "identityPublicContractReviewed": True,
                    "permissionHeaderAllowed": True,
                    "permissionsQueryReady": True,
                    "playerIdentityPromotionCertificateReady": True,
                    "publicCapabilityAdvertised": True,
                    "publicContractReady": True,
                    "routeGateUnlocked": True,
                },
                "claims": [
                    "accepted runtime evidence is accepted",
                    "identity public contract is reviewed",
                    "permission header allowed",
                    "permissions query ready",
                    "public ABI is ready",
                    "public capability is advertised",
                    "route gate opened for command response",
                    "ready route gate",
                ],
            },
            blockers,
        )

        reasons = [item["reason"] for item in blockers]
        self.assertEqual(8, reasons.count("public_surface_overclaim"))
        self.assertEqual(8, reasons.count("positive_public_surface_claim"))

    def test_rejects_reviewed_identity_contract_and_runtime_evidence_key_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "reviewedIdentityPublicContract": True,
                    "reviewedIdentityPublicContractReady": True,
                    "reviewedPlayerIdentityPublicContractReady": True,
                    "identityPublicContractGatePassed": True,
                    "identityPublicContractGateResolved": True,
                    "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin": True,
                    "playerIdentityEvidenceAccepted": True,
                    "identityContractReviewComplete": True,
                },
                "split_claims": [
                    {"field": "reviewedIdentityPublicContractReady", "state": "reviewed"},
                    {"claim": "identityPublicContractGatePassed", "value": "passed"},
                    {"name": "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin", "enabled": "yes"},
                ],
                "notes": [
                    "reviewed identity public contract unlocks command response",
                    "identity public contract gate passed so public response path ready",
                    "player identity runtime evidence unlocks permissions/admin",
                    "accepted runtime evidence remains normalized only to identity_public_contract_gate_missing",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.aliases.playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin",
            "$.aliases.playerIdentityEvidenceAccepted",
            "$.aliases.identityContractReviewComplete",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.notes[0]",
            "$.notes[1]",
        ):
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_default_root_is_repo_local_and_provenance_bound(self) -> None:
        self.assertTrue(READINESS.DEFAULT_ROOT.is_relative_to(REPO_ROOT))
        self.assertNotIn("/servidor/ark", str(READINESS.DEFAULT_ROOT))

        result = self.run_checker("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(str(READINESS.DEFAULT_ROOT.resolve()), report["readiness_root"])
        self.assertEqual([], report["blockers"])

    def test_rejects_readiness_without_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir))
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness.pop("source_root")
            readiness.pop("producer")
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_provenance_missing", report["blockers"])
        self.assertIn("readiness_producer_missing", report["blockers"])

    def test_default_root_readiness_still_requires_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness.pop("source_root")
            readiness.pop("producer")
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

            old_default_root = READINESS.DEFAULT_ROOT
            try:
                READINESS.DEFAULT_ROOT = root
                report = READINESS.build_report(
                    root,
                    readiness_path,
                    decisions_path,
                    public_header_path,
                    SURFACES,
                )
            finally:
                READINESS.DEFAULT_ROOT = old_default_root

        self.assertFalse(report["valid"])
        self.assertIn("readiness_provenance_missing", report["blockers"])
        self.assertIn("readiness_producer_missing", report["blockers"])

    def test_rejects_readiness_source_root_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stale_root = root / "stale-root"
            stale_root.mkdir()
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            readiness["source_root"] = str(stale_root)
            readiness["producer"]["argv"] = [
                str(stale_root) if item == str(root) else item
                for item in readiness["producer"]["argv"]
            ]
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_source_root_mismatch", report["blockers"])

    def test_rejects_accepted_second_source_without_candidate_root_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            argv = readiness["producer"]["argv"]
            candidate_index = argv.index("--candidate-root")
            del argv[candidate_index : candidate_index + 2]
            readiness_path.write_text(json.dumps(readiness), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_producer_argv_candidate_root_missing", report["blockers"])

    def test_rejects_placeholder_target_snapshot_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            first_snapshot = root / "base-snapshots" / "ShooterPlayerController.ClientChatMessage.snapshot.json"
            first_snapshot.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-chain.snapshot.v1",
                        "status": "fixture-placeholder",
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("target_snapshot_placeholder", report["blockers"])
        self.assertIn("target_snapshot_evidence_missing", report["blockers"])
        self.assertIn("target_snapshot_targets_invalid", report["blockers"])

    def test_rejects_readiness_not_bound_to_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()
            readiness_path, decisions_path, public_header_path = self.write_inputs(stale_root)
            result = self.run_checker(
                "--root",
                str(expected_root),
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("readiness_path_not_bound_to_root", report["blockers"])
        self.assertIn("target_detail_path_root_mismatch", report["blockers"])

    def test_rejects_readiness_public_runtime_and_promotion_overclaims(self) -> None:
        readiness = self.make_readiness()
        readiness["planning_layout_gate"]["promotion_ready"] = True
        readiness["promotion_gate"]["ready"] = True
        readiness["target_set_guidance"][0]["reply_api"] = True
        readiness["target_set_guidance"][0]["public_readiness_ready"] = True
        readiness["target_set_guidance"][0]["public_response_path_allowed"] = True
        readiness["target_set_guidance"][0]["public_reply_or_send_chat_abi_allowed"] = True
        readiness["target_set_guidance"][0]["reply_api_allowed"] = True
        readiness["target_set_guidance"][0]["send_chat_api_allowed"] = True
        readiness["target_set_guidance"][0]["runtime_delivery_allowed"] = True
        readiness["target_set_guidance"][0]["required_behavior"] = ["reply API is public and ready"]
        readiness["claim"] = "reply API is public and ready"
        readiness["generic_chat_claim"] = "generic chat routing is public and ready"
        readiness["send_chat_claim"] = "send-chat is available"
        readiness["router_claim"] = "router is supported"
        readiness["live_claim"] = "command response path is live"
        readiness["endpoint_claim"] = "reply endpoint is live"
        readiness["operational_claim"] = "send chat API is operational"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("ready_mismatch", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_mixed_negation_does_not_hide_positive_send_chat_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {"note": "reply API remains blocked but send-chat API is operational"},
            blockers,
        )

        self.assertEqual(["positive_public_surface_claim"], [item["reason"] for item in blockers])

    def test_negative_reply_suffix_is_not_positive_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims({"note": "reply API ready remains blocked"}, blockers)

        self.assertEqual([], blockers)

    def test_blocker_container_does_not_hide_positive_response_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "blockers": [
                    "command response path is ready",
                    "reply API ready remains blocked",
                ],
                "promotion_requires": [
                    "reply API must be promoted before release",
                ],
            },
            blockers,
        )

        self.assertEqual(
            [("positive_public_surface_claim", "$.blockers[0]")],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_nested_runtime_and_supported_router_claims_are_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "nested_report": {
                    "structured_evidence": [
                        {"runtime_claim": "runtime delivery is ready"},
                        {"router_claim": "command router is supported"},
                    ],
                },
            },
            blockers,
        )

        self.assertEqual(
            ["positive_public_surface_claim", "positive_public_surface_claim"],
            [item["reason"] for item in blockers],
        )
        self.assertEqual(
            [
                "$.nested_report.structured_evidence[0].runtime_claim",
                "$.nested_report.structured_evidence[1].router_claim",
            ],
            [item["label"] for item in blockers],
        )

    def test_rejects_nested_moderation_broadcast_aliases_and_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "nested_report": {
                    "publicBroadcastApiAllowed": True,
                    "publicNoticeAbiAllowed": True,
                    "moderationApiAllowed": True,
                    "claims": [
                        "broadcast/notices API is ready",
                        "moderation authority is supported",
                    ],
                },
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.nested_report.publicBroadcastApiAllowed"),
                ("public_surface_overclaim", "$.nested_report.publicNoticeAbiAllowed"),
                ("public_surface_overclaim", "$.nested_report.moderationApiAllowed"),
                ("positive_public_surface_claim", "$.nested_report.claims[0]"),
                ("positive_public_surface_claim", "$.nested_report.claims[1]"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_runtime_evidence_route_raw_p0_and_live_ops_bypass_claims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "acceptedRuntimeEvidenceOnly": True,
                    "routeBlockerBypassed": True,
                    "rawFStringShortcutReady": True,
                    "callProcessEventShortcutAllowed": True,
                    "p0ProgressReady": True,
                    "sdkP0ProgressReady": True,
                    "liveOpsAuthorized": True,
                    "liveOpsApprovalGranted": True,
                },
                "claims": [
                    "accepted runtime evidence alone is enough",
                    "route blocker bypasses are enabled",
                    "raw FString shortcut is ready",
                    "CallProcessEvent shortcuts are available",
                    "SDK/P0 progress is complete",
                    "live-ops approval is granted",
                    "route blocker bypass remains blocked",
                ],
                "non_claims": [
                    "accepted-runtime-evidence-only is enough",
                    "live-ops authorization remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.acceptedRuntimeEvidenceOnly",
            "$.aliases.routeBlockerBypassed",
            "$.aliases.rawFStringShortcutReady",
            "$.aliases.callProcessEventShortcutAllowed",
            "$.aliases.p0ProgressReady",
            "$.aliases.sdkP0ProgressReady",
            "$.aliases.liveOpsAuthorized",
            "$.aliases.liveOpsApprovalGranted",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for index in range(6):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[6]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.non_claims[0]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.non_claims[1]"), paths)

    def test_rejects_identity_public_contract_review_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "identity_public_contract_decision_record_reviewed": True,
                    "identity_public_contract_decision_record_hash_current": True,
                    "identity_public_contract_decision_record_contract_review_only": True,
                    "reviewed_hash_current_contract_review_only": True,
                },
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.identity_public_contract_decision_record_reviewed",
            "$.aliases.identity_public_contract_decision_record_hash_current",
            "$.aliases.identity_public_contract_decision_record_contract_review_only",
            "$.aliases.reviewed_hash_current_contract_review_only",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)

    def test_rejects_scoped_release_statement_route_credit_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "scopedReleaseStatementReady": True,
                    "scoped_release_statement_counts_toward_complete_sdk_claim": True,
                    "scoped_release_statement_outcomes_satisfy_completion": True,
                },
                "split_claims": [
                    {"claim": "scoped_release_statement_ready", "value": "ready"},
                ],
                "notes": [
                    "scoped release statement unlocks v1 completion",
                    "scoped release statement counts toward public SDK",
                    "scoped release statements cannot unlock command response",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.scopedReleaseStatementReady",
            "$.aliases.scoped_release_statement_counts_toward_complete_sdk_claim",
            "$.aliases.scoped_release_statement_outcomes_satisfy_completion",
            "$.split_claims[0]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes[1]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[2]"), paths)

    def test_terminal_route_package_status_support_aliases_need_upstream_certificates(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "aliases": {
                    "terminalCertificateReady": True,
                    "packageShapeEvidenceReady": True,
                    "responseStatusReportAccepted": True,
                    "routeClearedForPublicSendChatAbi": True,
                    "bridgeReady": True,
                    "supportTierReportReady": True,
                    "scopedStatementReady": True,
                },
                "split_claims": [
                    {"field": "terminal_certificate_metadata", "status": "accepted"},
                    {"field": "route_cleared", "value": "ready"},
                    {"field": "scoped_statement_counts_toward_completion", "value": True},
                ],
                "notes": [
                    "terminal certificate metadata is accepted",
                    "package shape evidence is ready",
                    "response status report accepted means route cleared",
                    "bridge-ready support tier report is supported",
                    "scoped statement counts toward complete SDK claim",
                    "terminal certificate remains blocked until upstream certificates",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.terminalCertificateReady",
            "$.aliases.packageShapeEvidenceReady",
            "$.aliases.responseStatusReportAccepted",
            "$.aliases.routeClearedForPublicSendChatAbi",
            "$.aliases.bridgeReady",
            "$.aliases.supportTierReportReady",
            "$.aliases.scopedStatementReady",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.notes[0]",
            "$.notes[1]",
            "$.notes[2]",
            "$.notes[3]",
            "$.notes[4]",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        self.assertNotIn(
            (
                "route_or_runtime_readiness_alias_missing_upstream_certificates",
                "$.notes[5]",
            ),
            paths,
        )

    def test_rejects_package_shape_runtime_simulation_and_planning_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "acceptedRuntimeSimulationReady": True,
                "accepted_runtime_simulation": {"status": "accepted"},
                "activation_precondition_report": {"status": "ready"},
                "beta_notice_action_report": {"status": "accepted"},
                "bridge_report": {"progress": "1/4", "status": "ready"},
                "notice_action_report": {"status": "accepted"},
                "precondition_artifact": {"progress": "1/3"},
                "support_tier_report": {"status": "supported"},
                "supportTierReadinessReady": True,
                "supportTierPackageReady": True,
                "support_tier_package_shape": {"status": "supported"},
                "packageShapeAccepted": True,
                "public_contract_record_package": {"status": "accepted"},
                "request_pack_public_contract_record": {"status": "accepted"},
                "commandPlanningReady": True,
                "command_planning_package": {"status": "ready"},
                "command_response_planning_package": {"status": "ready"},
                "copied_intent_package_shape": {"status": "ready"},
                "route_snapshot": {"status": "accepted"},
                "source_marker": "public_sdk_ready",
                "source_status": "supported",
                "source_marker_pair": {
                    "source_marker": "generic_command_planning_package",
                    "status": "accepted",
                },
                "source_marker_list_pair": {
                    "source_markers": ["route_snapshot"],
                    "source_state": "ready",
                },
                "source_provenance_route_snapshot": {
                    "source_provenance": "route_snapshot",
                    "status": "accepted",
                },
                "source_provenance_accepted_runtime": {
                    "source_provenance": "accepted_runtime_evidence_only",
                    "source_status": "ready",
                },
                "source_provenance_reviewed_contract_metadata": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
                "aliases": [
                    {"field": "bridge_report", "status": "ready"},
                    {"field": "support_tier_report", "status": "supported"},
                    {"field": "activation_precondition_report", "status": "ready"},
                    {"field": "notice_action_report", "status": "accepted"},
                    {"field": "support_tier_package_shape", "status": "supported"},
                    {"field": "accepted_runtime_simulation", "status": "accepted"},
                    {"field": "command_planning_package", "status": "ready"},
                    {"field": "route_snapshot", "status": "accepted"},
                ],
                "notes": [
                    "bridge report is ready",
                    "activation precondition report is ready",
                    "beta notice action report is accepted",
                    "support tier report is supported",
                    "support tier package shape is supported",
                    "accepted runtime simulation is accepted",
                    "package shape unlocks command response",
                    "command planning is ready",
                    "route snapshot is accepted",
                    "support tier package shape remains blocked",
                    "command planning remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.acceptedRuntimeSimulationReady",
            "$.accepted_runtime_simulation",
            "$.activation_precondition_report",
            "$.beta_notice_action_report",
            "$.bridge_report",
            "$.notice_action_report",
            "$.precondition_artifact.progress",
            "$.support_tier_report",
            "$.supportTierReadinessReady",
            "$.supportTierPackageReady",
            "$.support_tier_package_shape",
            "$.packageShapeAccepted",
            "$.public_contract_record_package",
            "$.request_pack_public_contract_record",
            "$.commandPlanningReady",
            "$.command_planning_package",
            "$.command_response_planning_package",
            "$.copied_intent_package_shape",
            "$.route_snapshot",
            "$.source_marker",
            "$.source_status",
            "$.source_marker_pair",
            "$.source_marker_pair.status",
            "$.source_marker_list_pair",
            "$.source_marker_list_pair.source_state",
            "$.source_provenance_route_snapshot",
            "$.source_provenance_route_snapshot.status",
            "$.source_provenance_accepted_runtime",
            "$.source_provenance_accepted_runtime.source_status",
            "$.source_provenance_reviewed_contract_metadata.state",
            "$.aliases[0]",
            "$.aliases[1]",
            "$.aliases[2]",
            "$.aliases[3]",
            "$.aliases[4]",
            "$.aliases[5]",
            "$.aliases[6]",
            "$.aliases[7]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for index in range(9):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[9]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[10]"), paths)

    def test_rejects_route_samples_approved_runtime_placeholders_and_package_shape_installs(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "route_sample": {"status": "ready"},
                "routeSampleAccepted": True,
                "approved_runtime_placeholder": {"status": "ready"},
                "approvedRuntimePlaceholderReady": True,
                "approved_runtime_evidence_placeholder": {"source_status": "approved"},
                "package_shape_install": {"status": "complete"},
                "installed_sdk_package_shape": {"readiness": "verified"},
                "source_provenance_route_sample": {
                    "source_provenance": "route_sample",
                    "source_status": "ready",
                },
                "source_provenance_placeholder": {
                    "source_provenance": "approved_runtime_placeholder",
                    "source_status": "ready",
                },
                "split_claims": [
                    {"field": "route_sample", "status": "accepted"},
                    {"field": "approvedRuntimePlaceholderReady", "state": "ready"},
                    {"field": "packageShapeInstallComplete", "status": "complete"},
                ],
                "claims": [
                    "route sample is ready",
                    "approved runtime placeholder is ready",
                    "package-shape install is complete",
                    "route sample remains blocked",
                    "approved runtime placeholder remains blocked",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.route_sample",
            "$.routeSampleAccepted",
            "$.approved_runtime_placeholder",
            "$.approvedRuntimePlaceholderReady",
            "$.approved_runtime_evidence_placeholder",
            "$.package_shape_install",
            "$.installed_sdk_package_shape",
            "$.source_provenance_route_sample",
            "$.source_provenance_route_sample.source_status",
            "$.source_provenance_placeholder.source_status",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.route_sample",
            "$.route_sample.status",
            "$.routeSampleAccepted",
            "$.approved_runtime_placeholder",
            "$.approved_runtime_placeholder.status",
            "$.approvedRuntimePlaceholderReady",
            "$.approved_runtime_evidence_placeholder",
            "$.approved_runtime_evidence_placeholder.source_status",
            "$.package_shape_install",
            "$.package_shape_install.status",
            "$.installed_sdk_package_shape",
            "$.installed_sdk_package_shape.readiness",
            "$.source_provenance_route_sample.source_status",
            "$.source_provenance_placeholder.source_status",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.claims[0]",
            "$.claims[1]",
            "$.claims[2]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[3]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[4]"), paths)

    def test_rejects_downstream_route_shortcut_status_and_source_ready_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "sourceReady": True,
                "source_status_ready": True,
                "chatSourceReady": True,
                "rconSourceReady": True,
                "broadcastSourceReady": True,
                "sendSourceReady": True,
                "sendSourceStatusReady": True,
                "identity_public_contract_gate_missing": {
                    "source_ready": True,
                    "ready": True,
                    "status": "ready",
                },
                "response_bridge_candidate": {
                    "status": "ready",
                    "counts_toward_public_sdk": True,
                    "p0_dependency_chain_progress_contribution": 1,
                },
                "public_reachability_status": {"source_ready": True, "status": "reachable"},
                "rcon_status": {"source_ready": True, "status": "ready"},
                "broadcast_status": {"ready": True, "status": "enabled"},
                "send_status": {"source_ready": True, "status": "ready"},
                "source_kind_status_probe": {"source_kind": "rcon", "status": "ready"},
                "source_kind_chat_ready_probe": {"source_kind": "chat", "ready": True},
                "reply_channel_status_probe": {"reply_channel": "rcon", "status": "ready"},
                "send_channel_ready_probe": {"send_channel": "server_console", "is_ready": True},
                "status_metadata_probe": {"channel": "broadcast", "status": "sent"},
                "delivery_source_metadata": {"transport": "send_chat", "source_status": "delivered"},
                "transport_result_probe": {"transport": "broadcast", "result": "delivered"},
                "package_support_plugin": {
                    "plugin_hub_support_ready": True,
                    "support_tier_ready": True,
                },
                "split_claims": [
                    {"field": "identity_public_contract_gate_missing", "source_ready": True},
                    {"field": "public_reachability", "ready": True},
                    {"field": "rcon_route", "status": "ready"},
                    {"field": "broadcast_status", "status": "enabled"},
                    {"field": "send_source", "status": "ready"},
                    {"field": "sendSourceStatusReady", "source_status": "sent"},
                    {"field": "package_shape_support", "source_ready": True},
                    {"field": "plugin_hub_package_shape", "ready": True},
                ],
                "claims": [
                    "Plugin Hub stable SDK is public",
                    "command response candidate counts toward SDK/P0 progress",
                    "send source is ready",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.sourceReady",
            "$.source_status_ready",
            "$.chatSourceReady",
            "$.rconSourceReady",
            "$.broadcastSourceReady",
            "$.sendSourceReady",
            "$.sendSourceStatusReady",
            "$.identity_public_contract_gate_missing",
            "$.response_bridge_candidate.counts_toward_public_sdk",
            "$.response_bridge_candidate.p0_dependency_chain_progress_contribution",
            "$.public_reachability_status",
            "$.rcon_status",
            "$.broadcast_status",
            "$.send_status",
            "$.source_kind_status_probe",
            "$.source_kind_status_probe.status",
            "$.source_kind_chat_ready_probe",
            "$.source_kind_chat_ready_probe.ready",
            "$.reply_channel_status_probe",
            "$.reply_channel_status_probe.status",
            "$.send_channel_ready_probe",
            "$.send_channel_ready_probe.is_ready",
            "$.status_metadata_probe.status",
            "$.delivery_source_metadata.source_status",
            "$.transport_result_probe",
            "$.transport_result_probe.result",
            "$.split_claims[5]",
            "$.package_support_plugin.plugin_hub_support_ready",
            "$.package_support_plugin.support_tier_ready",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
            "$.split_claims[4]",
            "$.split_claims[6]",
            "$.split_claims[7]",
        ):
            with self.subTest(label=label):
                self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.public_reachability_status.source_ready",
            "$.response_bridge_candidate",
            "$.response_bridge_candidate.status",
            "$.response_bridge_candidate.counts_toward_public_sdk",
            "$.response_bridge_candidate.p0_dependency_chain_progress_contribution",
            "$.rcon_status.source_ready",
            "$.source_kind_status_probe.status",
            "$.source_kind_chat_ready_probe.ready",
            "$.reply_channel_status_probe.status",
            "$.send_channel_ready_probe.is_ready",
            "$.status_metadata_probe",
            "$.status_metadata_probe.status",
            "$.delivery_source_metadata.source_status",
            "$.transport_result_probe.result",
            "$.split_claims[6]",
        ):
            with self.subTest(label=label):
                self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertIn(("non_evidence_artifact_credit_overclaim", "$.claims[1]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[2]"), paths)

    def test_rejects_multi_surface_beta_capture_pack_and_plan_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_surface_overclaims(
            {
                "multiSurfaceBetaCapturePackReady": True,
                "multi_surface_beta_capture_plan": {
                    "status": "accepted",
                    "counts_toward_public_sdk": True,
                    "p0_dependency_chain_progress_contribution": 1,
                },
                "source_provenance_pack": {
                    "source_provenance": "multi_surface_beta_capture_pack",
                    "source_status": "ready",
                },
                "claims": [
                    "multi-surface beta capture pack accepted as public SDK evidence",
                    "multi-surface beta capture plan remains candidate-only and non-counting",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.multiSurfaceBetaCapturePackReady",
            "$.multi_surface_beta_capture_plan",
            "$.multi_surface_beta_capture_plan.counts_toward_public_sdk",
            "$.multi_surface_beta_capture_plan.p0_dependency_chain_progress_contribution",
            "$.source_provenance_pack.source_status",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.multiSurfaceBetaCapturePackReady",
            "$.multi_surface_beta_capture_plan",
            "$.multi_surface_beta_capture_plan.status",
            "$.multi_surface_beta_capture_plan.counts_toward_public_sdk",
            "$.multi_surface_beta_capture_plan.p0_dependency_chain_progress_contribution",
            "$.source_provenance_pack.source_status",
            "$.claims[0]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(("positive_public_surface_claim", "$.claims[0]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[1]"), paths)
        certificate_detail = next(
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        )
        self.assertEqual(
            [
                "obelisk.player-identity-promotion-certificate.v1",
                "obelisk.permissions-admin-promotion-certificate.v1",
            ],
            certificate_detail["required_certificate_schemas"],
        )

    def test_rejects_beta_capture_pack_as_player_identity_runtime_evidence(self) -> None:
        surfaces = self.make_surfaces_with_accepted_runtime_evidence()
        identity = next(
            surface
            for surface in surfaces["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        identity["evidence"]["accepted_runtime_evidence"]["source"] = "multi_surface_beta_capture_pack"
        decisions = self.make_decisions()
        decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
        decisions["accounting_lock"]["remaining_route_blockers"] = [
            "identity_public_contract_gate_missing"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                root,
                decisions=decisions,
            )
            surfaces_path = self.write_surfaces(root, surfaces)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("player_identity_accepted_runtime_evidence_non_authorizing_context", report["blockers"])
        self.assert_public_runtime_v1_flags_false(report)

    def test_rejects_decision_public_header_overclaims(self) -> None:
        decisions = self.make_decisions()
        decisions["status"] = "promoted"
        decisions["public_header_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterCommandChatResponse"]
        decisions["required_before_public_header"][0]["status"] = "resolved"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("status_mismatch", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("required_before_public_header_item_not_unresolved", report["blockers"])

    def test_rejects_response_path_symbols_in_public_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            public_header_path.write_text(
                "typedef struct ObeliskCommandChatResponse ObeliskCommandChatResponse;\n"
                "typedef struct ObeliskChatRouter ObeliskChatRouter;\n"
                "typedef struct ObeliskModeration ObeliskModeration;\n"
                "typedef struct ObeliskRawFStringResponse ObeliskRawFStringResponse;\n"
                "void RegisterCommandChatResponse(void);\n"
                "void RegisterChatRouter(void);\n"
                "void ModerateChat(void);\n"
                "void RawProcessEventCommandResponse(void);\n"
                "void CallProcessEventShortcut(void);\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH 0x80000000u\n"
                "#define OBELISK_API_CAPABILITY_CHAT_REPLY 0x40000000u\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_REPLY 0x20000000u\n"
                "#define OBELISK_API_CAPABILITY_COMMANDS_REPLIES 0x10000000u\n"
                "#define OBELISK_COMMAND_REPLY_ABI_VERSION 1\n"
                "#define OBELISK_CHAT_REPLY_ABI_VERSION 1\n"
                "#define OBELISK_COMMANDS_REPLIES_ABI_VERSION 1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_forbidden_symbols_present", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_forbidden_symbols_present")
        self.assertIn("ObeliskCommandChatResponse", detail["symbols"])
        self.assertIn("ObeliskChatRouter", detail["symbols"])
        self.assertIn("ObeliskModeration", detail["symbols"])
        self.assertIn("ObeliskRawFStringResponse", detail["symbols"])
        self.assertIn("RegisterCommandChatResponse", detail["symbols"])
        self.assertIn("RegisterChatRouter", detail["symbols"])
        self.assertIn("ModerateChat", detail["symbols"])
        self.assertIn("RawProcessEventCommandResponse", detail["symbols"])
        self.assertIn("CallProcessEventShortcut", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_CHAT_REPLY", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_REPLY", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMANDS_REPLIES", detail["symbols"])
        self.assertIn("OBELISK_COMMAND_REPLY_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_CHAT_REPLY_ABI_VERSION", detail["symbols"])
        self.assertIn("OBELISK_COMMANDS_REPLIES_ABI_VERSION", detail["symbols"])

    def test_public_header_scan_ignores_comments_and_identifier_supersets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            public_header_path.write_text(
                "/* ObeliskCommandChatResponse and RegisterCommandChatResponse stay blocked. */\n"
                "// OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH remains absent.\n"
                "typedef struct MyObeliskCommandChatResponseSuffix MyObeliskCommandChatResponseSuffix;\n"
                "void RegisterCommandChatResponseForTestsOnly(void);\n"
                "#define OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH_EXTRA 1\n",
                encoding="utf-8",
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertNotIn("public_header_forbidden_symbols_present", report["blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_public_header_not_canonical_repo_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root, temp_header=True)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_decision_public_header_path_mismatch(self) -> None:
        decisions = self.make_decisions()
        decisions["public_header"] = "include/obelisk/OtherApi.h"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_public_header_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_explicit_surface_claim_fields(self) -> None:
        for field in (
            "send_chat_api",
            "command_router",
            "chat_routing",
            "generic_chat_routing_public_response_allowed",
            "player_identity_ready",
            "permissions_ready",
            "public_header_ready",
            "public_reply_abi_allowed",
            "public_send_chat_abi_allowed",
            "reply_allowed",
            "send_chat_allowed",
        ):
            with self.subTest(field=field):
                readiness = self.make_readiness()
                readiness[field] = True
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
                    result = self.run_checker(
                        "--readiness",
                        str(readiness_path),
                        "--decisions",
                        str(decisions_path),
                        "--public-header",
                        str(public_header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn("public_surface_overclaim", report["blockers"])

    def test_rejects_non_matching_target_set_and_missing_second_source(self) -> None:
        readiness = deepcopy(self.make_readiness())
        readiness["target_sets"] = ["chat-intake"]
        readiness["totals"]["second_source_missing"] = 1
        readiness["modules"][0]["target_details"][0]["second_source_status"] = "missing"
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("target_sets_mismatch", report["blockers"])
        self.assertIn("second_source_missing_mismatch", report["blockers"])
        self.assertIn("second_source_status_mismatch", report["blockers"])

    def test_rejects_missing_response_redaction_guidance(self) -> None:
        cases = (
            "ClientChatMessage.Chat",
            "raw FString storage/data",
            "sender identity remains redacted",
            "directed recipient identity remains redacted",
            "future targeting must use only a promoted copied principal handle/generation",
        )
        for phrase in cases:
            with self.subTest(phrase=phrase):
                readiness = self.make_readiness()
                readiness["target_set_guidance"][0]["snapshot_prep_checks"] = [
                    check
                    for check in readiness["target_set_guidance"][0]["snapshot_prep_checks"]
                    if phrase not in check
                ]
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), readiness=readiness)
                    result = self.run_checker(
                        "--readiness",
                        str(readiness_path),
                        "--decisions",
                        str(decisions_path),
                        "--public-header",
                        str(public_header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn("target_set_guidance_missing_redaction_checks", report["blockers"])

    def test_rejects_missing_privacy_decision_behavior(self) -> None:
        decisions = self.make_decisions()
        privacy = next(item for item in decisions["required_before_public_header"] if item["id"] == "privacy.redaction_and_targeting")
        privacy["required_behavior"] = [
            item
            for item in privacy["required_behavior"]
            if not item.startswith("raw FString storage/data")
            and not item.startswith("principal tuple source must be runtime-owned")
            and item != "plugin-supplied principal tuple fails closed"
            and item != "permission allow cannot be consumed without policy provenance"
            and item != (
                "runtime-owned principal tuple must be paired with runtime-owned permission provenance "
                "before reply/send-chat/router planning can become public"
            )
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("privacy_redaction_behavior_missing", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "privacy_redaction_behavior_missing"
        )
        self.assertIn(
            "principal tuple source must be runtime-owned player identity observation before any directed response target is public",
            detail["missing"],
        )
        self.assertIn("plugin-supplied principal tuple fails closed", detail["missing"])
        self.assertIn("permission allow cannot be consumed without policy provenance", detail["missing"])
        self.assertIn(
            "runtime-owned principal tuple must be paired with runtime-owned permission provenance before reply/send-chat/router planning can become public",
            detail["missing"],
        )

    def test_rejects_missing_runtime_owned_principal_permissions_gate(self) -> None:
        decisions = self.make_decisions()
        gate = decisions["runtime_owned_principal_permissions_gate"]
        gate["runtime_owned_permission_allow_required"] = False
        gate["reply_send_chat_router_claims_allowed"] = True
        gate["required_runtime_owned_inputs"] = [
            item for item in gate["required_runtime_owned_inputs"] if item != "permission_decision"
        ]
        gate["forbidden_authority_sources"] = [
            item for item in gate["forbidden_authority_sources"] if item != "router metadata"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("runtime_owned_principal_permissions_gate_required_true_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_required_false_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_inputs_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_forbidden_sources_missing", report["blockers"])

    def test_rejects_missing_response_lifecycle_and_abuse_guards(self) -> None:
        decisions = self.make_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item != "raw ProcessEvent or legacy CallProcessEvent fallback"
        ]
        lifecycle = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "lifecycle.owner_scoped_unregister_and_drain"
        )
        lifecycle["required_behavior"] = [
            item
            for item in lifecycle["required_behavior"]
            if item
            not in {
                "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
            }
        ]
        abuse = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "abuse.rate_limit_and_audit"
        )
        abuse["required_behavior"] = [
            item
            for item in abuse["required_behavior"]
            if item
            not in {
                "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
                "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_unregister_behavior_missing", report["blockers"])
        self.assertIn("abuse_rate_limit_audit_behavior_missing", report["blockers"])

    def test_rejects_missing_not_sufficient_shortcut_evidence(self) -> None:
        decisions = self.make_decisions()
        evidence = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "evidence.layout_runtime_sdk_coverage"
        )
        evidence["not_sufficient"] = [
            "candidate vtable slots",
            "raw ProcessEvent callbacks",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence_not_sufficient_missing_required", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "evidence_not_sufficient_missing_required"
        )
        self.assertIn("passive ChatMessageEvent parsing", detail["missing"])
        self.assertIn("minimal ChatMessageEvent callback registration", detail["missing"])
        self.assertIn("generic chat routing", detail["missing"])
        self.assertIn("static thunk orientation", detail["missing"])
        self.assertIn("legacy CallProcessEvent debug gate", detail["missing"])
        self.assertIn("next-action runner/planner artifacts are not sufficient", detail["missing"])
        self.assertIn("passive monitor ticks/output and passive player summaries/snapshots are not sufficient", detail["missing"])
        self.assertIn("notice artifacts are not sufficient", detail["missing"])
        self.assertIn("status artifacts are not sufficient", detail["missing"])

    def test_rejects_missing_generic_chat_routing_separation(self) -> None:
        decisions = self.make_decisions()
        decisions["generic_chat_routing_public_response_allowed"] = True
        decisions["forbidden_public_contract"] = [
            item for item in decisions["forbidden_public_contract"] if item != "public generic chat routing response path"
        ]
        capability = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "abi.capability_and_owner_token"
        )
        capability["required_behavior"] = [
            item for item in capability["required_behavior"] if item != "generic chat routing does not authorize response delivery"
        ]
        separation = next(
            item for item in decisions["required_before_public_header"] if item["id"] == "separation.no_commands_router_or_moderation"
        )
        separation["v1_sequence_gate"] = [
            item for item in separation["v1_sequence_gate"] if item != "generic chat routing cannot bypass promoted identity and permissions/admin"
        ]
        separation["required_exclusions"] = [
            item for item in separation["required_exclusions"] if item != "public response path through generic chat routing"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("generic_chat_routing_public_response_allowed_not_false", report["blockers"])
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("capability_behavior_missing", report["blockers"])
        self.assertIn("separation_sequence_gate_missing", report["blockers"])
        self.assertIn("separation_exclusion_missing", report["blockers"])

    def test_rejects_missing_generic_chat_routing_identity_permission_dependency(self) -> None:
        decisions = self.make_decisions()
        identity = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        permissions = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_permissions_admin"
        )
        identity["required_behavior"] = [
            item
            for item in identity["required_behavior"]
            if item != "generic chat routing cannot establish principal identity"
        ]
        permissions["required_behavior"] = [
            item
            for item in permissions["required_behavior"]
            if item != "generic chat routing cannot establish permissions or admin authority"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("identity_dependency_behavior_missing", report["blockers"])
        self.assertIn("permissions_dependency_behavior_missing", report["blockers"])
        detail_behaviors = {
            item["behavior"]
            for item in report["blocker_details"]
            if item["reason"] in {"identity_dependency_behavior_missing", "permissions_dependency_behavior_missing"}
        }
        self.assertIn("generic chat routing cannot establish principal identity", detail_behaviors)
        self.assertIn("generic chat routing cannot establish permissions or admin authority", detail_behaviors)

    def test_rejects_missing_chat_intake_is_not_authority_guardrails(self) -> None:
        decisions = self.make_decisions()
        identity = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        permissions = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "dependency.promoted_permissions_admin"
        )
        separation = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "separation.no_commands_router_or_moderation"
        )
        identity["required_behavior"] = [
            item
            for item in identity["required_behavior"]
            if item != "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish principal identity or roadmap priority"
        ]
        permissions["required_behavior"] = [
            item
            for item in permissions["required_behavior"]
            if item != "chat intake, send mode, passive parsing, command text, and chat snapshots cannot establish permissions, targeting, command authority, moderation authority, or roadmap priority"
        ]
        separation["v1_sequence_gate"] = [
            item
            for item in separation["v1_sequence_gate"]
            if item != "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("identity_dependency_behavior_missing", report["blockers"])
        self.assertIn("permissions_dependency_behavior_missing", report["blockers"])
        self.assertIn("separation_sequence_gate_missing", report["blockers"])

    def test_rejects_response_target_shortcut_evidence_gap(self) -> None:
        decisions = self.make_decisions()
        evidence = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "evidence.response_target_set_snapshot_second_source"
        )
        evidence["not_sufficient"] = [
            item
            for item in evidence["not_sufficient"]
            if item not in {"generic chat routing", "static thunk orientation"}
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_target_not_sufficient_missing", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "response_target_not_sufficient_missing"
        )
        self.assertIn("generic chat routing", detail["missing"])
        self.assertIn("static thunk orientation", detail["missing"])

    def test_rejects_missing_call_process_event_and_native_wrapper_forbidden_contracts(self) -> None:
        decisions = self.make_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item
            not in {
                "public CallProcessEvent response path",
                "direct native-call wrappers",
                "broadcast/notices API",
                "moderation API",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_path, decisions_path, public_header_path = self.write_inputs(
                Path(temp_dir),
                decisions=decisions,
            )
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])

    def test_rejects_surface_manifest_response_path_overclaim(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        response = next(item for item in surfaces["surfaces"] if item["id"] == "obelisk.command_chat_response_path.v1")
        response["status"] = "promoted"
        response["public_abi"] = True
        response["adds_obelisk_api"] = True
        response["public_contract"] = ["ObeliskCommandChatResponse"]
        response["depends_on"] = ["obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("status_mismatch", report["blockers"])
        self.assertIn("public_abi_not_false", report["blockers"])
        self.assertIn("adds_obelisk_api_not_false", report["blockers"])
        self.assertIn("command_chat_response_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("command_chat_response_surface_dependencies_mismatch", report["blockers"])

    def test_rejects_response_path_planning_evidence_promoted_in_surfaces(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        response = next(item for item in surfaces["surfaces"] if item["id"] == "obelisk.command_chat_response_path.v1")
        response["status"] = "promoted"
        surfaces["promoted_surfaces"].append("obelisk.command_chat_response_path.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_planning_evidence_treated_as_promoted", report["blockers"])
        self.assertIn("command_chat_response_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_rejects_response_path_dependency_order_drift(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        response = next(item for item in surfaces["surfaces"] if item["id"] == "obelisk.command_chat_response_path.v1")
        response["depends_on"] = ["obelisk.permissions_admin.v1", "obelisk.player_identity.v1"]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("command_chat_response_surface_dependencies_mismatch", report["blockers"])

    def test_rejects_dependency_sequence_required_chain_and_blocker_drift(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        surfaces["v1_dependency_sequence"] = [
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.commands_replies.v1",
        ]
        surfaces["v1_required_dependency_chain"] = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
        ]
        surfaces["v1_sdk_completion_blockers"] = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("v1_dependency_sequence_mismatch", report["blockers"])
        self.assertIn("dependency_chain_surface_missing_from_required_chain", report["blockers"])
        self.assertIn("dependency_chain_surface_missing_from_blockers", report["blockers"])

    def test_rejects_manifest_only_upstream_dependency_promotion(self) -> None:
        cases = (
            ("obelisk.player_identity.v1", "player_identity_evidence_not_approved"),
            ("obelisk.permissions_admin.v1", "permissions_admin_evidence_not_approved"),
            ("obelisk.command_chat_response_path.v1", "command_chat_response_evidence_not_approved"),
        )
        for surface_id, blocker in cases:
            with self.subTest(surface_id=surface_id):
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                for surface in surfaces["surfaces"]:
                    if surface["id"] == surface_id:
                        surface["status"] = "promoted"
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    readiness_path, decisions_path, public_header_path = self.write_inputs(root)
                    surfaces_path = root / "public_sdk_surfaces.json"
                    surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
                    result = self.run_checker(
                        "--readiness",
                        str(readiness_path),
                        "--decisions",
                        str(decisions_path),
                        "--public-header",
                        str(public_header_path),
                        "--surfaces",
                        str(surfaces_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn(blocker, report["blockers"])

    def test_rejects_promoted_surfaces_manifest_only_upstream_dependencies(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        surfaces["promoted_surfaces"].extend(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("permissions_admin_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("command_chat_response_manifest_promotion_without_evidence", report["blockers"])

    def test_rejects_promoted_experimental_upstream_dependency_statuses(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        for surface in surfaces["surfaces"]:
            if surface["id"] in {
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            }:
                surface["status"] = "promoted-experimental-only"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_path, decisions_path, public_header_path = self.write_inputs(root)
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")
            result = self.run_checker(
                "--readiness",
                str(readiness_path),
                "--decisions",
                str(decisions_path),
                "--public-header",
                str(public_header_path),
                "--surfaces",
                str(surfaces_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_overclaim_scan_rejects_source_zero_start_end_transfer_and_rcon_aliases(self) -> None:
        blockers: list[dict] = []
        payload = {
            "source_overclaim_total_flag_count": 0,
            "status": "ready",
            "start_end_only_evidence": {"status": "ready"},
            "transfer_baccept_candidate": {"status": "ready"},
            "rcon_command_candidate": {"status": "ready"},
        }

        READINESS.collect_surface_overclaims(payload, blockers, "$.unit")
        reasons = [blocker["reason"] for blocker in blockers]

        self.assertIn("source_overclaim_zero_status_alias_overclaim", reasons)
        self.assertIn("non_evidence_artifact_credit_overclaim", reasons)
        self.assertIn("public_surface_overclaim", reasons)


if __name__ == "__main__":
    unittest.main()
