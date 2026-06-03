#!/usr/bin/env python3
"""Smoke-check the player-principal lifecycle planning bundle blocker.

This is an offline guardrail for committed planning-source manifests. It verifies that
candidate lifecycle/principal planning inputs remain internally bound and that the next
blocker is exactly approved_runtime_evidence_missing. It does not accept request packs,
operator receipts, copied logs, or runtime evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "obelisk.player-principal-lifecycle-planning-blocker-smoke.v1"
EXPECTED_BLOCKER = "approved_runtime_evidence_missing"
DEFAULT_ROOT = Path("docs/research/player-identity-planning-sources")
REPORT_NAME = "player-identity-planning-source-manifests-report.json"
LIFECYCLE_NAME = "players-identity-lifecycle-anchor-candidates.json"
POLICY_NAME = "players-identity-principal-invalidation-policy.json"
FIRST_EVIDENCE_NAME = "players-identity-first-evidence.json"
EXPECTED_REPORT_SCHEMA = "obelisk.player-identity-planning-source-manifests-build-report.v1"
EXPECTED_LIFECYCLE_SCHEMA = "obelisk.players-identity-lifecycle-anchor-candidates.v1"
EXPECTED_POLICY_SCHEMA = "obelisk.players-identity-principal-invalidation-policy.v1"
EXPECTED_FIRST_EVIDENCE_SCHEMA = "obelisk.players-identity-first-evidence.v1"
EXPECTED_START_TARGETS = ("ShooterGameMode.HandleNewPlayer",)
EXPECTED_END_TARGETS = ("ShooterGameMode.OnLogout",)
NO_RUNTIME_NON_CLAIM = "no runtime or server operation was performed"
NO_PUBLIC_SDK_NON_CLAIM = "no public SDK, public ABI, release, or v1 completion readiness is claimed"


@dataclass
class LoadedManifest:
    name: str
    path: Path
    payload: dict[str, Any]
    sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"Planning-source manifest directory. Default: {DEFAULT_ROOT}",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_manifest(root: Path, name: str, blockers: list[dict[str, Any]]) -> LoadedManifest | None:
    path = root / name
    if path.is_symlink():
        add(blockers, "planning_manifest_symlinked", name, path=str(path))
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        add(blockers, "planning_manifest_unreadable", name, path=str(path), error=str(exc))
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add(blockers, "planning_manifest_json_invalid", name, path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, "planning_manifest_not_object", name, path=str(path))
        return None
    return LoadedManifest(name=name, path=path, payload=payload, sha256=hashlib.sha256(raw).hexdigest())


def bool_false(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]], label: str) -> None:
    if payload.get(key) is not False:
        add(blockers, f"{label}_{key}_not_false", f"{label}.{key}")


def validate_no_readiness_overclaim(payload: dict[str, Any], blockers: list[dict[str, Any]], label: str) -> None:
    for key in (
        "runtime_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "public_header_allowed",
        "promotion_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "runtime_work_authorized",
        "server_operations_authorized",
    ):
        if key in payload:
            bool_false(payload, key, blockers, label)


def output_entry(report: dict[str, Any], key: str) -> dict[str, Any] | None:
    outputs = report.get("outputs")
    if not isinstance(outputs, dict):
        return None
    entry = outputs.get(key)
    return entry if isinstance(entry, dict) else None


def source_entry(report: dict[str, Any], key: str) -> dict[str, Any] | None:
    sources = report.get("binding_report", {}).get("sources")
    if not isinstance(sources, dict):
        return None
    entry = sources.get(key)
    return entry if isinstance(entry, dict) else None


def validate_report_binding(
    report: LoadedManifest,
    lifecycle: LoadedManifest,
    policy: LoadedManifest,
    first_evidence: LoadedManifest,
    blockers: list[dict[str, Any]],
) -> None:
    expected = {
        "lifecycle_anchor_candidates": lifecycle,
        "principal_invalidation_policy": policy,
        "first_evidence": first_evidence,
    }
    for key, manifest in expected.items():
        for source_kind, entry in (("outputs", output_entry(report.payload, key)), ("sources", source_entry(report.payload, key))):
            if entry is None:
                add(blockers, f"planning_report_{source_kind}_{key}_missing", f"report.{source_kind}.{key}")
                continue
            if entry.get("schema") != manifest.payload.get("schema"):
                add(
                    blockers,
                    f"planning_report_{source_kind}_{key}_schema_mismatch",
                    f"report.{source_kind}.{key}.schema",
                    expected=manifest.payload.get("schema"),
                    actual=entry.get("schema"),
                )
            if entry.get("sha256") != manifest.sha256:
                add(
                    blockers,
                    f"planning_report_{source_kind}_{key}_sha256_mismatch",
                    f"report.{source_kind}.{key}.sha256",
                    expected=manifest.sha256,
                    actual=entry.get("sha256"),
                )


def validate_lifecycle(lifecycle: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if lifecycle.get("schema") != EXPECTED_LIFECYCLE_SCHEMA:
        add(blockers, "lifecycle_schema_mismatch", "lifecycle.schema", expected=EXPECTED_LIFECYCLE_SCHEMA)
    if lifecycle.get("artifact_status") != "candidate_only":
        add(blockers, "lifecycle_artifact_status_not_candidate_only", "lifecycle.artifact_status")
    if lifecycle.get("readiness_classification") != "planning_only":
        add(blockers, "lifecycle_readiness_not_planning_only", "lifecycle.readiness_classification")
    validate_no_readiness_overclaim(lifecycle, blockers, "lifecycle")
    acceptance = lifecycle.get("lifecycle_acceptance")
    if not isinstance(acceptance, dict):
        add(blockers, "lifecycle_acceptance_missing", "lifecycle.lifecycle_acceptance")
        return
    if tuple(acceptance.get("accepted_start_targets", ())) != EXPECTED_START_TARGETS:
        add(blockers, "lifecycle_start_targets_mismatch", "lifecycle.lifecycle_acceptance.accepted_start_targets")
    if tuple(acceptance.get("accepted_end_targets", ())) != EXPECTED_END_TARGETS:
        add(blockers, "lifecycle_end_targets_mismatch", "lifecycle.lifecycle_acceptance.accepted_end_targets")
    if acceptance.get("session_start_accepted") is not True:
        add(blockers, "lifecycle_session_start_not_accepted_for_planning", "lifecycle.lifecycle_acceptance.session_start_accepted")
    if acceptance.get("session_end_accepted") is not True:
        add(blockers, "lifecycle_session_end_not_accepted_for_planning", "lifecycle.lifecycle_acceptance.session_end_accepted")


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if policy.get("schema") != EXPECTED_POLICY_SCHEMA:
        add(blockers, "policy_schema_mismatch", "policy.schema", expected=EXPECTED_POLICY_SCHEMA)
    if policy.get("artifact_status") != "candidate_only":
        add(blockers, "policy_artifact_status_not_candidate_only", "policy.artifact_status")
    if policy.get("readiness_classification") != "planning_only":
        add(blockers, "policy_readiness_not_planning_only", "policy.readiness_classification")
    validate_no_readiness_overclaim(policy, blockers, "policy")

    runtime_evidence = policy.get("runtime_evidence")
    if not isinstance(runtime_evidence, dict):
        add(blockers, "policy_runtime_evidence_missing", "policy.runtime_evidence")
    else:
        if runtime_evidence.get("approved") is not False:
            add(blockers, "policy_runtime_evidence_approved_not_false", "policy.runtime_evidence.approved")
        if runtime_evidence.get("status") != "not_approved":
            add(blockers, "policy_runtime_evidence_status_not_not_approved", "policy.runtime_evidence.status")

    gate = policy.get("promotion_gate")
    if not isinstance(gate, dict):
        add(blockers, "policy_promotion_gate_missing", "policy.promotion_gate")
        return
    validate_no_readiness_overclaim(gate, blockers, "policy_promotion_gate")
    blockers_list = gate.get("blockers")
    if not isinstance(blockers_list, list):
        add(blockers, "policy_promotion_gate_blockers_not_list", "policy.promotion_gate.blockers")
    elif blockers_list != [EXPECTED_BLOCKER, "principal_invalidation_semantics_unresolved", "candidate_only_policy"]:
        add(
            blockers,
            "policy_promotion_gate_blockers_mismatch",
            "policy.promotion_gate.blockers",
            expected=[EXPECTED_BLOCKER, "principal_invalidation_semantics_unresolved", "candidate_only_policy"],
            actual=blockers_list,
        )


def validate_first_evidence(first_evidence: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if first_evidence.get("schema") != EXPECTED_FIRST_EVIDENCE_SCHEMA:
        add(blockers, "first_evidence_schema_mismatch", "first_evidence.schema", expected=EXPECTED_FIRST_EVIDENCE_SCHEMA)
    if first_evidence.get("artifact_status") != "candidate_only":
        add(blockers, "first_evidence_artifact_status_not_candidate_only", "first_evidence.artifact_status")
    if first_evidence.get("readiness_classification") != "planning_only":
        add(blockers, "first_evidence_readiness_not_planning_only", "first_evidence.readiness_classification")
    validate_no_readiness_overclaim(first_evidence, blockers, "first_evidence")


def validate_build_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if report.get("schema") != EXPECTED_REPORT_SCHEMA:
        add(blockers, "planning_report_schema_mismatch", "report.schema", expected=EXPECTED_REPORT_SCHEMA)
    if report.get("accepted_for_planning") is not True:
        add(blockers, "planning_report_not_accepted_for_planning", "report.accepted_for_planning")
    if report.get("planning_only") is not True:
        add(blockers, "planning_report_planning_only_not_true", "report.planning_only")
    if report.get("valid") is not True:
        add(blockers, "planning_report_valid_not_true", "report.valid")
    if report.get("blockers") not in ([], None):
        add(blockers, "planning_report_has_blockers", "report.blockers", actual=report.get("blockers"))
    validate_no_readiness_overclaim(report, blockers, "report")
    non_claims = report.get("non_claims")
    if not isinstance(non_claims, list) or NO_RUNTIME_NON_CLAIM not in non_claims:
        add(blockers, "planning_report_runtime_non_claim_missing", "report.non_claims")
    binding_non_claims = report.get("binding_report", {}).get("non_claims")
    if not isinstance(binding_non_claims, list) or NO_PUBLIC_SDK_NON_CLAIM not in binding_non_claims:
        add(blockers, "planning_report_public_sdk_non_claim_missing", "report.binding_report.non_claims")


def build_report(root: Path, manifests: dict[str, LoadedManifest | None], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    planning_ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "ready": planning_ready,
        "planning_sources_ready": planning_ready,
        "offline_only": True,
        "runtime_evidence_ready": False,
        "approved_runtime_evidence_present": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "runtime_work_authorized": False,
        "server_operations_authorized": False,
        "remaining_blockers": [EXPECTED_BLOCKER],
        "next_blocker": EXPECTED_BLOCKER,
        "root": str(root),
        "manifests": {
            key: (
                {
                    "path": str(manifest.path),
                    "schema": manifest.payload.get("schema"),
                    "sha256": manifest.sha256,
                }
                if manifest is not None
                else None
            )
            for key, manifest in manifests.items()
        },
        "accepted_start_targets": list(EXPECTED_START_TARGETS) if planning_ready else [],
        "accepted_end_targets": list(EXPECTED_END_TARGETS) if planning_ready else [],
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "planning-source smoke only; does not authorize runtime work, server operations, marker/env changes, request approval, or evidence capture",
            "planning-source smoke acceptance is not approved runtime evidence and does not promote public SDK, ABI, identity, lookup, permissions, commands, mutation, return override, or v1 completion",
        ],
    }


def main() -> int:
    args = parse_args()
    root = args.root
    blockers: list[dict[str, Any]] = []
    if root.is_symlink():
        add(blockers, "planning_root_symlinked", "root", path=str(root))
    if not root.is_dir():
        add(blockers, "planning_root_missing", "root", path=str(root))

    manifests = {
        "report": load_manifest(root, REPORT_NAME, blockers),
        "lifecycle_anchor_candidates": load_manifest(root, LIFECYCLE_NAME, blockers),
        "principal_invalidation_policy": load_manifest(root, POLICY_NAME, blockers),
        "first_evidence": load_manifest(root, FIRST_EVIDENCE_NAME, blockers),
    }

    report_manifest = manifests["report"]
    lifecycle_manifest = manifests["lifecycle_anchor_candidates"]
    policy_manifest = manifests["principal_invalidation_policy"]
    first_evidence_manifest = manifests["first_evidence"]

    if report_manifest is not None:
        validate_build_report(report_manifest.payload, blockers)
    if lifecycle_manifest is not None:
        validate_lifecycle(lifecycle_manifest.payload, blockers)
    if policy_manifest is not None:
        validate_policy(policy_manifest.payload, blockers)
    if first_evidence_manifest is not None:
        validate_first_evidence(first_evidence_manifest.payload, blockers)
    if all(manifest is not None for manifest in (report_manifest, lifecycle_manifest, policy_manifest, first_evidence_manifest)):
        validate_report_binding(report_manifest, lifecycle_manifest, policy_manifest, first_evidence_manifest, blockers)

    output = build_report(root, manifests, blockers)
    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    else:
        print(f"player_principal_lifecycle_planning_blocker_smoke=ok next_blocker={EXPECTED_BLOCKER}")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
