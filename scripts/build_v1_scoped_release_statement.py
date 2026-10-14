#!/usr/bin/env python3
"""Build a scoped non-complete v1 release-statement draft from the SDK manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from check_public_sdk_v1_completion import (
    CANONICAL_EXPERIMENTAL_SURFACE_IDS,
    CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN,
    DEFAULT_MANIFEST,
    as_string_list,
    release_statement_forbidden_broad_claims,
    required_release_statement_text,
    required_release_statement_outcomes,
    scoped_release_statement_required_outcome_records,
)
import protected_paths


SCOPED_RELEASE_STATEMENT_BLOCKER = "release_statement_missing_non_promoted_blocker_outcomes"
SCOPED_RELEASE_STATEMENT_SCHEMA = "obelisk.scoped-release-statement-outcomes.v1"
SCOPED_RELEASE_STATEMENT_NON_CLAIM = (
    "Scoped post-v1/excluded outcome rows are bookkeeping only; they do not "
    "authorize stable/full/production SDK wording."
)
P0_DEPENDENCY_CHAIN_FIRST_BLOCKER = CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN[0]
APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER = "approved_runtime_evidence_missing"
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE = (
    "approved_runtime_principal_lifecycle_evidence_bundle"
)
SCOPED_DETAIL_FORBIDDEN_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("promoted", re.compile(r"\bpromoted\b", re.IGNORECASE)),
    ("stable", re.compile(r"\bstable\b", re.IGNORECASE)),
    ("production", re.compile(r"\bproduction\b|\bprod(?:uction)?[-_ ]+ready\b", re.IGNORECASE)),
    ("full-sdk", re.compile(r"\bfull[-_ ]+(?:sdk|api)\b", re.IGNORECASE)),
    ("complete", re.compile(r"(?<!non[- ])\bcomplete(?:d|s|ly)?\b", re.IGNORECASE)),
    (
        "support-tier",
        re.compile(r"\bsupport[-_ ]+tier\b|\brelease[-_ ]supported\b", re.IGNORECASE),
    ),
    (
        "v1-ready",
        re.compile(
            r"\bv1(?:\.0)?[-_ ]?ready\b|\bready\s+(?:for|in)\s+v1(?:\.0)?\b",
            re.IGNORECASE,
        ),
    ),
    ("plugin-hub", re.compile(r"\bPlugin[-_ ]+Hub\b|\bpluginhub\b", re.IGNORECASE)),
    (
        "package-shape",
        re.compile(
            r"\bpackage[-_ ]+shape\b|\bCMake[-_ ]+package\b|"
            r"\binstalled[-_ ]+SDK[-_ ]+package\b",
            re.IGNORECASE,
        ),
    ),
    (
        "public-module",
        re.compile(
            r"\bpublic[-_ ]+module\b|\bmodule[-_ ]+(?:availab(?:le|ility)|ready|readiness)\b|"
            r"\bproduction[-_ ]+module\b",
            re.IGNORECASE,
        ),
    ),
    ("public-package", re.compile(r"\bpublic[-_ ]+package\b|\brelease[-_ ]+package\b", re.IGNORECASE)),
    (
        "public-sdk-readiness",
        re.compile(r"\bpublic[-_ ]+SDK[-_ ]+(?:availab(?:le|ility)|ready|readiness)\b", re.IGNORECASE),
    ),
    (
        "active-monitor",
        re.compile(
            r"\bactive[-_ ]+(?:passive[-_ ]+)?monitor\b|"
            r"\bpassive[-_ ]+monitor[-_ ]+session\b",
            re.IGNORECASE,
        ),
    ),
    (
        "discord-beta-bridge",
        re.compile(
            r"\bDiscord[-_ ]+beta[-_ ]+bridge\b|\bdiscord[-_ ]+beta[-_ ]+bot\b",
            re.IGNORECASE,
        ),
    ),
    (
        "active-notice",
        re.compile(
            r"\bactive[-_ ]+notice\b|\bactive[-_ ]+beta[-_ ]+notice\b",
            re.IGNORECASE,
        ),
    ),
    (
        "beta-pack",
        re.compile(
            r"\bbeta[-_ ]+(?:capture[-_ ]+)?pack\b|\bmulti[-_ ]+surface[-_ ]+beta\b",
            re.IGNORECASE,
        ),
    ),
    (
        "side-lane-candidate",
        re.compile(
            r"\bside[-_ ]+lane\b|\bcandidate[-_ ]+(?:surface|queue|pack)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "scoped-release-statement",
        re.compile(
            r"\bscoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?release[-_ ]+statement[-_ ]+"
            r"(?:ready|readiness|satisfies|counts?)\b",
            re.IGNORECASE,
        ),
    ),
)
SCOPED_RELEASE_STATEMENT_PUBLIC_NON_CLAIM_FLAGS = {
    "active_notice_accepted": False,
    "active_notice_counts_toward_complete_sdk_claim": False,
    "active_notice_counts_toward_p0_dependency_chain": False,
    "active_notice_counts_toward_sdk": False,
    "active_notice_ready": False,
    "active_notice_sent": False,
    "active_notice_updated": False,
    "approved_runtime_evidence_missing_cleared": False,
    "approved_runtime_evidence_missing_resolved": False,
    "blocker_cleared": False,
    "blocker_resolved": False,
    "current_route_blocker_cleared": False,
    "current_route_blocker_resolved": False,
    "remaining_route_blockers_cleared": False,
    "remaining_route_blockers_resolved": False,
    "route_blocker_cleared": False,
    "route_blocker_resolved": False,
    "route_lock_cleared": False,
    "route_lock_resolved": False,
    "route_ready": False,
    "sdk_route_blocker_cleared": False,
    "sdk_route_blocker_resolved": False,
    "side_lane_promoted": False,
    "structure_build_policy_ready": False,
    "plugin_hub_publication_allowed": False,
    "plugin_hub_readiness_claim_allowed": False,
    "support_tier_activation_allowed": False,
    "support_tier_claim_allowed": False,
    "public_module_availability_claim_allowed": False,
    "public_module_sdk_coverage_claim_allowed": False,
    "public_package_availability_claim_allowed": False,
    "package_shape_readiness_claim_allowed": False,
    "installed_sdk_package_shape_claim_allowed": False,
    "scoped_release_statement_readiness_claim_allowed": False,
    "scoped_release_statement_v1_completion_claim_allowed": False,
    "scoped_release_statement_public_sdk_readiness_claim_allowed": False,
}
SCOPED_RELEASE_STATEMENT_ZERO_PROGRESS_FLAGS = {
    "required_outcome_bookkeeping_only": True,
    "required_outcome_counts_as_progress": False,
    "required_outcome_progress_contribution": 0,
    "required_outcomes_listed_counts_toward_completion": False,
    "required_outcomes_listed_completion_progress_contribution": 0,
    "required_outcomes_listed_claim_count": 0,
    "required_outcomes_listed_completion_count": 0,
    "non_p0_bookkeeping_counts_toward_completion": False,
    "non_p0_bookkeeping_progress_contribution": 0,
    "scoped_outcome_claim_count": 0,
    "scoped_release_statement_claim_count": 0,
    "scoped_release_statement_completion_count": 0,
    "scoped_release_statement_promoted_count": 0,
    "active_notice_progress_contribution": 0,
    "side_lane_progress_contribution": 0,
    "side_lane_promoted_count": 0,
    "structure_build_policy_progress_contribution": 0,
}


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")
    return payload


def surfaces_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        raise ValueError("manifest.surfaces must be a list")
    result: dict[str, dict[str, Any]] = {}
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("id")
        if isinstance(surface_id, str):
            result[surface_id] = surface
    return result


def scoped_detail_forbidden_claims(detail: str) -> list[str]:
    return [
        name
        for name, pattern in SCOPED_DETAIL_FORBIDDEN_CLAIM_PATTERNS
        if pattern.search(detail)
    ]


def release_statement_detail(surface: dict[str, Any]) -> str:
    contract = surface.get("v1_decision_contract")
    required: list[str] = []
    if isinstance(contract, dict):
        for requirement in as_string_list(contract.get("exclusion_requires")):
            detail = required_release_statement_text(requirement)
            if detail:
                if "\n" in detail or "\r" in detail:
                    raise ValueError("release-statement detail must be a single line")
                required.append(detail.rstrip("."))
    if not required:
        required.append("scoped non-complete release bookkeeping only; no public API is included in v1")
    return "; ".join(required)


def scoped_release_statement_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    post_v1_or_excluded = as_string_list(manifest.get("post_v1_or_excluded_surfaces"))
    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    completion_blocker_set = set(completion_blockers)
    by_id = surfaces_by_id(manifest)
    seen_post_v1_or_excluded: set[str] = set()
    for surface_id in post_v1_or_excluded:
        if surface_id in seen_post_v1_or_excluded and surface_id in completion_blocker_set:
            raise ValueError(f"scoped builder cannot emit duplicate surface row: {surface_id}")
        seen_post_v1_or_excluded.add(surface_id)
        if surface_id not in completion_blocker_set:
            continue
        if surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
            raise ValueError(f"scoped builder cannot emit P0 dependency-chain surface: {surface_id}")
        if surface_id in CANONICAL_EXPERIMENTAL_SURFACE_IDS:
            raise ValueError(f"scoped builder cannot emit promoted-experimental surface: {surface_id}")
    required_records = scoped_release_statement_required_outcome_records(
        completion_blockers,
        by_id,
        set(post_v1_or_excluded),
    )
    rows: list[dict[str, Any]] = []
    for required_record in required_records:
        surface_id = required_record["surface"]
        surface = by_id.get(surface_id)
        if not surface:
            raise ValueError(f"post_v1_or_excluded surface missing from manifest.surfaces: {surface_id}")
        status = required_record["outcome"]
        if status not in {"post-v1", "excluded"}:
            raise ValueError(f"{surface_id} has non-scoped status {status!r}")
        allowed_outcomes = required_release_statement_outcomes(surface)
        if status not in allowed_outcomes:
            raise ValueError(
                f"{surface_id} scoped release-statement status {status!r} is not allowed "
                f"by exclusion contract outcomes {sorted(allowed_outcomes)!r}"
            )
        detail = release_statement_detail(surface)
        forbidden_detail_claims = scoped_detail_forbidden_claims(detail)
        if forbidden_detail_claims:
            raise ValueError(
                f"{surface_id} scoped release-statement detail contains forbidden scoped claim token(s): "
                + ", ".join(forbidden_detail_claims)
            )
        line = f"{surface_id}: {status} - {detail}"
        rows.append(
            {
                "surface": surface_id,
                "outcome": status,
                "detail": detail,
                "line": line,
                "blocker": SCOPED_RELEASE_STATEMENT_BLOCKER,
                "approved_runtime_evidence": False,
                "stable_claim_allowed": False,
                "stable_sdk_claim_allowed": False,
                "complete_sdk_claim_allowed": False,
                "complete_sdk_ready": False,
                "v1_completion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "scoped_release_statement_counts_toward_complete_sdk_claim": False,
                "scoped_release_statement_claim_progress_contribution": 0,
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "counts_toward_complete_sdk_claim": False,
                "counts_toward_p0_dependency_chain": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "p0_dependency_chain_progress_contribution": 0,
                "p0_dependency_chain_first_blocker": P0_DEPENDENCY_CHAIN_FIRST_BLOCKER,
                "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
                "remaining_route_blockers": [APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER],
                "next_required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
                "missing_required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
                "approved_runtime_evidence_accepted": False,
                "approved_runtime_principal_lifecycle_evidence_bundle_accepted": False,
                "evidence_bundle_accepted": False,
                "v1_completion_contribution": 0,
                "passive_activity_triage_counts_toward_release": False,
                "observer_event_triage_counts_toward_release": False,
                "passive_snapshot_counts_toward_public_sdk": False,
                "non_claim": SCOPED_RELEASE_STATEMENT_NON_CLAIM,
                **SCOPED_RELEASE_STATEMENT_PUBLIC_NON_CLAIM_FLAGS,
                **SCOPED_RELEASE_STATEMENT_ZERO_PROGRESS_FLAGS,
            }
        )
    return rows


def current_p0_dependency_chain_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    by_id = surfaces_by_id(manifest)
    manifest_promoted_count = 0
    first_blocker = P0_DEPENDENCY_CHAIN_FIRST_BLOCKER
    for surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
        surface = by_id.get(surface_id)
        if not surface:
            raise ValueError(f"P0 dependency-chain surface missing from manifest.surfaces: {surface_id}")
        if surface.get("status") == "promoted":
            manifest_promoted_count += 1
            continue
        first_blocker = surface_id
        break
    required_count = len(CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN)
    return {
        "p0_dependency_chain_current_promoted_count": 0,
        "p0_dependency_chain_manifest_promoted_status_count": manifest_promoted_count,
        "p0_dependency_chain_required_count": required_count,
        "p0_dependency_chain_current_progress_ratio": f"0/{required_count}",
        "p0_dependency_chain_first_blocker": first_blocker,
        "p0_dependency_chain_blocked": True,
        "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "remaining_route_blockers": [APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER],
        "next_required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
        "missing_required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
        "approved_runtime_evidence_accepted": False,
        "approved_runtime_principal_lifecycle_evidence_bundle_accepted": False,
        "evidence_bundle_accepted": False,
    }


def build_statement(manifest: dict[str, Any]) -> str:
    rows = scoped_release_statement_rows(manifest)
    completion_blocker_count = len(as_string_list(manifest.get("v1_sdk_completion_blockers")))
    p0_summary = current_p0_dependency_chain_summary(manifest)
    lines = [
        "# Scoped non-complete v1 release-statement draft.",
        "# Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
        f"# Generated for blocker: {SCOPED_RELEASE_STATEMENT_BLOCKER}.",
        f"# Scoped outcome rows: {len(rows)}; non-claim bookkeeping only.",
        f"# Required scoped non-promoted blocker outcomes listed: {len(rows)}/{len(rows)}.",
        f"# Completion progress from this statement: 0/{completion_blocker_count}; "
        f"P0 dependency-chain progress remains {p0_summary['p0_dependency_chain_current_progress_ratio']} "
        f"with {p0_summary['p0_dependency_chain_first_blocker']} blocked first.",
        f"# Current route blocker remains {APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER}; "
        f"next required artifact is {APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE}.",
        "# Scope is exact: P0, promoted, experimental, and non-blocker rows are intentionally absent.",
        "# These rows are bookkeeping only and do not authorize stable/full/production SDK wording.",
        "# No Plugin Hub readiness/publication, support-tier activation, public module availability, or package-shape/public package readiness is authorized.",
        "# Passive snapshots, passive activity triage, and observer-event triage do not count toward this statement, release readiness, or public SDK readiness.",
        "# Post-reboot passive monitor context and confirmed beta notices are operator context only; they do not count toward this statement, SDK/P0 progress, release readiness, runtime readiness, or public SDK readiness.",
        "# Offline hardening, reviewed decision records, generated certificate reports, beta packs, package-shape metadata, and public/debug boundary fixes are bookkeeping-only context with 0 SDK/P0 contribution.",
    ]
    lines.extend(row["line"] for row in rows)
    statement = "\n".join(lines) + "\n"
    forbidden_claims = release_statement_forbidden_broad_claims(statement)
    if forbidden_claims:
        raise ValueError(
            "generated scoped release statement contains forbidden broad claim(s): "
            + "; ".join(forbidden_claims[:3])
        )
    return statement


def build_outcome_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = scoped_release_statement_rows(manifest)
    statement = build_statement(manifest)
    completion_blocker_count = len(as_string_list(manifest.get("v1_sdk_completion_blockers")))
    p0_summary = current_p0_dependency_chain_summary(manifest)
    return {
        "schema": SCOPED_RELEASE_STATEMENT_SCHEMA,
        "blocker": SCOPED_RELEASE_STATEMENT_BLOCKER,
        "outcome_count": len(rows),
        "required_outcome_count": len(rows),
        "required_outcomes_listed": len(rows),
        "required_outcome_surfaces": [row["surface"] for row in rows],
        "outcomes": rows,
        "statement": statement,
        "completion_progress_count": 0,
        "completion_progress_total": completion_blocker_count,
        "completion_progress_ratio": f"0/{completion_blocker_count}",
        "stable_claim_allowed": False,
        "stable_sdk_claim_allowed": False,
        "complete_sdk_claim_allowed": False,
        "complete_sdk_ready": False,
        "v1_completion_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "scoped_release_statement_counts_toward_complete_sdk_claim": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_v1_completion": False,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "v1_completion_contribution": 0,
        "approved_runtime_evidence": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "passive_activity_triage_counts_toward_release": False,
        "observer_event_triage_counts_toward_release": False,
        "passive_snapshot_counts_toward_public_sdk": False,
        "non_claim": SCOPED_RELEASE_STATEMENT_NON_CLAIM,
        **p0_summary,
        **SCOPED_RELEASE_STATEMENT_PUBLIC_NON_CLAIM_FLAGS,
        **SCOPED_RELEASE_STATEMENT_ZERO_PROGRESS_FLAGS,
    }


def write_statement(path: Path, statement: str) -> None:
    output_path = protected_paths.reject_protected_output_path(
        path,
        "scoped release statement output",
    )
    output_path.write_text(statement, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit structured non-claim outcome rows to stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = load_manifest(args.manifest)
        payload = build_outcome_payload(manifest) if args.json_output else None
        statement = payload["statement"] if payload is not None else build_statement(manifest)
    except Exception as exc:
        print(f"build_v1_scoped_release_statement_failed:{exc}", file=sys.stderr)
        return 2
    if args.output:
        try:
            write_statement(args.output, statement)
        except SystemExit as exc:
            print(f"build_v1_scoped_release_statement_failed:{exc}", file=sys.stderr)
            return 2
    else:
        if payload is None:
            sys.stdout.write(statement)
    if payload is not None:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
