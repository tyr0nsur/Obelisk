#!/usr/bin/env python3
"""Build a scoped non-complete v1 release-statement draft from the SDK manifest."""

from __future__ import annotations

import argparse
import json
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
)


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


def build_statement(manifest: dict[str, Any]) -> str:
    post_v1_or_excluded = as_string_list(manifest.get("post_v1_or_excluded_surfaces"))
    completion_blockers = set(as_string_list(manifest.get("v1_sdk_completion_blockers")))
    by_id = surfaces_by_id(manifest)
    lines = [
        "# Scoped non-complete v1 release-statement draft.",
        "# Reviewed against docs/SDK_V1_COMPATIBILITY.md and docs/public_sdk_surfaces.json.",
        "# These rows are bookkeeping only and do not authorize stable/full/production SDK wording.",
    ]
    for surface_id in post_v1_or_excluded:
        if surface_id not in completion_blockers:
            continue
        if surface_id in CANONICAL_V1_REQUIRED_DEPENDENCY_CHAIN:
            raise ValueError(f"scoped builder cannot emit P0 dependency-chain surface: {surface_id}")
        if surface_id in CANONICAL_EXPERIMENTAL_SURFACE_IDS:
            raise ValueError(f"scoped builder cannot emit promoted-experimental surface: {surface_id}")
        surface = by_id.get(surface_id)
        if not surface:
            raise ValueError(f"post_v1_or_excluded surface missing from manifest.surfaces: {surface_id}")
        status = surface.get("status")
        if status not in {"post-v1", "excluded"}:
            raise ValueError(f"{surface_id} has non-scoped status {status!r}")
        lines.append(f"{surface_id}: {status} - {release_statement_detail(surface)}")
    statement = "\n".join(lines) + "\n"
    forbidden_claims = release_statement_forbidden_broad_claims(statement)
    if forbidden_claims:
        raise ValueError(
            "generated scoped release statement contains forbidden broad claim(s): "
            + "; ".join(forbidden_claims[:3])
        )
    return statement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        statement = build_statement(load_manifest(args.manifest))
    except Exception as exc:
        print(f"build_v1_scoped_release_statement_failed:{exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(statement, encoding="utf-8")
    else:
        sys.stdout.write(statement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
