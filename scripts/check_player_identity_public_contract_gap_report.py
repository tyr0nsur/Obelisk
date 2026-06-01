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


SCHEMA = "obelisk.player-identity-public-contract-gap-report.v1"
DECISIONS_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PRIVATE_CANDIDATE_SCHEMA = "obelisk.player-identity-private-candidate-contract.v1"
SURFACE = "obelisk.player_identity.v1"
PRIMARY_OFFLINE_GAP = "privacy.identifier_redaction"

READINESS_FALSE_KEYS = {
    "accepted_for_contract_review",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_contract_allowed",
    "public_abi_ready",
    "v1_completion_evidence",
}
EMPTY_PUBLIC_LIST_KEYS = {
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_callback_abi_now",
}
HEADER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
}
HEADER_SYMBOL_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net_?id|player_?data_?id",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"redact(?:ed|ion)?|excludes?|without|until|missing|blocked|blocker|"
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
    "resource_handle": re.compile(r"ResourceHandle|resource[_ -]?handle", re.IGNORECASE),
    "lookup": re.compile(r"\blookup\b|lookup_", re.IGNORECASE),
    "persistence": re.compile(r"\bpersist(?:ent|ed|ence|s|ing)?(?:\b|[_ -])", re.IGNORECASE),
    "mutation": re.compile(r"\bmutat(?:e|ion|ing|able)(?:\b|[_ -])", re.IGNORECASE),
    "return_override": re.compile(r"return[_ -]?override", re.IGNORECASE),
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
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


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
        if key in READINESS_FALSE_KEYS and item is not False:
            add(blockers, "readiness_flag_not_false", path, input=label, value=item)


def validate_empty_public_lists(value: Any, blockers: list[dict[str, Any]], label: str) -> None:
    for key in sorted(EMPTY_PUBLIC_LIST_KEYS):
        if key in value and value.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", input=label, value=value.get(key))


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


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if decisions.get("schema") != DECISIONS_SCHEMA:
        add(blockers, "decisions_schema_mismatch", "$.schema", value=decisions.get("schema"))
    if decisions.get("surface") != SURFACE:
        add(blockers, "decisions_surface_mismatch", "$.surface", value=decisions.get("surface"))
    if decisions.get("status") != "blocked":
        add(blockers, "decisions_status_not_blocked", "$.status", value=decisions.get("status"))
    if decisions.get("public_header_allowed") is not False:
        add(blockers, "decisions_public_header_allowed_not_false", "$.public_header_allowed")
    validate_empty_public_lists(decisions, blockers, "decisions")
    validate_false_flags(decisions, blockers, "decisions")


def validate_surfaces(surfaces: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if surfaces.get("schema") != SURFACES_SCHEMA:
        add(blockers, "surfaces_schema_mismatch", "$.schema", value=surfaces.get("schema"))
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
    prefix = normalized[max(0, match_start - 32) : match_start]
    whole = normalized
    return bool(NEGATIVE_CONTEXT_RE.search(prefix) or NEGATIVE_CONTEXT_RE.search(whole))


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
                exposures.append({"path": path, "term": term, "value": item})
                break
    return exposures


def validate_private_candidate(candidate: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
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


def build_report(
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
    decisions: dict[str, Any],
    surface: dict[str, Any],
    header_scan: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "surface": SURFACE,
        "status": "blocked",
        "guardrail_passed": not blockers,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "primary_offline_gap": PRIMARY_OFFLINE_GAP,
        "runtime_evidence_missing": True,
        "inputs": {
            "decisions": str(args.decisions),
            "surfaces": str(args.surfaces),
            "private_candidate_contract": str(args.private_candidate_contract),
            "public_header": str(args.public_header),
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
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "offline gap report does not require approved runtime evidence",
            "blocked player identity state does not add public header symbols, capability bits, callbacks, lookup, persistence, mutation, return override, or v1 SDK readiness",
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
    header_scan = scan_public_header(args.public_header, blockers)

    report = build_report(args, blockers, decisions, surface, header_scan, candidate)
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
