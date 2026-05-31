#!/usr/bin/env python3
"""Fail-closed checker for the Obelisk v1.0 complete-SDK claim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that public_sdk_surfaces.json allows a complete v1 SDK claim."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to docs/public_sdk_surfaces.json.",
    )
    parser.add_argument(
        "--release-statement",
        type=Path,
        help="Reviewed v1 SDK release statement that names excluded/post-v1 blockers.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the full readiness report as JSON.")
    return parser.parse_args()


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"manifest_load_failed:{exc}"]
    if not isinstance(payload, dict):
        return None, ["manifest_not_object"]
    return payload, []


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def load_release_statement(path: Path | None) -> tuple[str | None, list[str]]:
    if path is None:
        return None, []
    try:
        return path.read_text(encoding="utf-8"), []
    except OSError as exc:
        return None, [f"release_statement_load_failed:{exc}"]


def release_statement_names_outcome(text: str, surface_id: str, status: str) -> bool:
    lowered = text.lower()
    if surface_id.lower() not in lowered:
        return False
    expected = "post-v1" if status == "post-v1" else "excluded"
    return expected in lowered


def build_report(manifest_path: Path, release_statement_path: Path | None = None) -> dict[str, Any]:
    manifest, blockers = load_manifest(manifest_path)
    release_statement_text, release_statement_blockers = load_release_statement(release_statement_path)
    blockers.extend(release_statement_blockers)
    if manifest is None:
        return {
            "schema": "obelisk.public-sdk-v1-completion-check.v1",
            "status": "blocked",
            "ready": False,
            "manifest": str(manifest_path),
            "release_statement": str(release_statement_path) if release_statement_path else None,
            "blockers": blockers,
        }

    surfaces = manifest.get("surfaces")
    surface_rows = surfaces if isinstance(surfaces, list) else []
    surfaces_by_id = {
        surface.get("id"): surface
        for surface in surface_rows
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        blockers.append("schema_mismatch")
    if manifest.get("sdk_version") != "v1.0":
        blockers.append("sdk_version_not_v1")

    stable_contract = manifest.get("stable_release_contract")
    if not isinstance(stable_contract, dict):
        blockers.append("stable_release_contract_missing")
        stable_claim_allowed = False
    else:
        stable_claim_allowed = stable_contract.get("claim_allowed") is True
        if not stable_claim_allowed:
            blockers.append("stable_release_contract_claim_not_allowed")

    if manifest.get("v1_completion_required") is not True:
        blockers.append("v1_completion_required_false")

    promoted_surfaces = set(as_string_list(manifest.get("promoted_surfaces")))
    experimental_surfaces = set(as_string_list(manifest.get("experimental_surfaces")))
    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    post_v1_or_excluded = set(as_string_list(manifest.get("post_v1_or_excluded_surfaces")))

    unresolved_experimental: list[str] = []
    unresolved_completion_blockers: list[str] = []
    missing_surfaces: list[str] = []
    promoted_without_contract: list[str] = []
    promoted_blockers_without_evidence: list[str] = []
    non_promoted_with_contract: list[str] = []
    promoted_list_mismatches: list[str] = []
    release_statement_missing_blockers: list[str] = []

    for surface_id in sorted(experimental_surfaces):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_experimental.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            continue
        unresolved_experimental.append(surface_id)

    for surface_id in completion_blockers:
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_completion_blockers.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if not surface.get("evidence"):
                promoted_blockers_without_evidence.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
                release_statement_missing_blockers.append(surface_id)
            continue
        unresolved_completion_blockers.append(surface_id)

    for surface_id, surface in surfaces_by_id.items():
        status = surface.get("status")
        contract = surface.get("public_contract")
        contract_items = contract if isinstance(contract, list) else []
        if status == "promoted":
            if surface_id not in promoted_surfaces:
                promoted_list_mismatches.append(surface_id)
            if not contract_items:
                promoted_without_contract.append(surface_id)
        elif status != "promoted-experimental-only" and contract_items:
            non_promoted_with_contract.append(surface_id)

    for surface_id in sorted(promoted_surfaces):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
        elif surface.get("status") != "promoted":
            promoted_list_mismatches.append(surface_id)

    if missing_surfaces:
        blockers.append("surface_id_missing")
    if unresolved_experimental:
        blockers.append("promoted_experimental_surfaces_unresolved")
    if unresolved_completion_blockers:
        blockers.append("v1_sdk_completion_blockers_unresolved")
    if promoted_without_contract:
        blockers.append("promoted_surface_public_contract_missing")
    if promoted_blockers_without_evidence:
        blockers.append("promoted_blocker_evidence_missing")
    if non_promoted_with_contract:
        blockers.append("non_promoted_surface_has_public_contract")
    if promoted_list_mismatches:
        blockers.append("promoted_surface_list_mismatch")
    if release_statement_missing_blockers:
        blockers.append("release_statement_missing_non_promoted_blocker_outcomes")
    if release_statement_text is not None:
        if "docs/sdk_v1_compatibility.md" not in release_statement_text.lower():
            blockers.append("release_statement_missing_sdk_compatibility_reference")
        if "docs/public_sdk_surfaces.json" not in release_statement_text.lower():
            blockers.append("release_statement_missing_public_sdk_surfaces_reference")

    return {
        "schema": "obelisk.public-sdk-v1-completion-check.v1",
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "manifest": str(manifest_path),
        "release_statement": str(release_statement_path) if release_statement_path else None,
        "sdk_version": manifest.get("sdk_version"),
        "v1_completion_required": manifest.get("v1_completion_required"),
        "stable_claim_allowed": stable_claim_allowed,
        "blockers": blockers,
        "unresolved_experimental_surfaces": sorted(set(unresolved_experimental)),
        "unresolved_completion_blockers": sorted(set(unresolved_completion_blockers)),
        "missing_surfaces": sorted(set(missing_surfaces)),
        "promoted_without_public_contract": sorted(set(promoted_without_contract)),
        "promoted_blockers_without_evidence": sorted(set(promoted_blockers_without_evidence)),
        "non_promoted_with_public_contract": sorted(set(non_promoted_with_contract)),
        "promoted_list_mismatches": sorted(set(promoted_list_mismatches)),
        "release_statement_missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
        "non_claims": [
            "core-first release readiness, install layout, and package-shape checks do not satisfy this v1 SDK completion gate",
            "post-v1 or excluded surfaces must be named in the manifest and release statement before a stable v1 SDK claim",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.manifest, args.release_statement)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["ready"]:
        print("Public SDK v1 completion gate passed.")
    else:
        print("Public SDK v1 completion gate blocked:")
        for blocker in report["blockers"]:
            print(f"- {blocker}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
