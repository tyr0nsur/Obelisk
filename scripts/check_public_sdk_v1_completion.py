#!/usr/bin/env python3
"""Fail-closed checker for the Obelisk v1.0 complete-SDK claim."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
CANONICAL_SURFACE_IDS = {
    "obelisk.arkapi_compatibility.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.chat_message.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
    "obelisk.debug_raw_process_event.v1",
    "obelisk.descriptors.v1",
    "obelisk.gameplay_policy_event.v1",
    "obelisk.gameplay_tick_callbacks.v1",
    "obelisk.inventory_item_copied_signals.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_config_logging.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.player_identity.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.process_local_timers.v1",
    "obelisk.structure_census.v1",
}
CANONICAL_V1_COMPLETION_BLOCKERS = {
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.commands_replies.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.structure_census.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.gameplay_tick_callbacks.v1",
}
CANONICAL_EXPERIMENTAL_SURFACE_IDS = {
    "obelisk.gameplay_policy_event.v1",
    "obelisk.chat_message.v1",
    "obelisk.chat.local_routing.v1",
    "obelisk.inventory_item_copied_signals.v1",
}
CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT = {
    "obelisk.gameplay_policy_event.v1": ("GameplayPolicyEvent", "not included in v1"),
    "obelisk.chat_message.v1": ("ChatMessageEvent", "not included in v1"),
    "obelisk.chat.local_routing.v1": ("chat routing", "not included in v1"),
    "obelisk.inventory_item_copied_signals.v1": ("inventory copied signals", "not included in v1"),
}
STRICT_PROMOTION_EVIDENCE_SURFACE_IDS = CANONICAL_V1_COMPLETION_BLOCKERS | CANONICAL_EXPERIMENTAL_SURFACE_IDS
PROMOTION_EVIDENCE_REQUIRED_TERMS = {
    "obelisk.player_identity.v1": (
        "obelisk.core-dump-evidence-pack.v1",
        "obelisk.reflection-inventory-pack.v1",
        "ServerListPlayers",
        "ServerKickPlayer",
    ),
}
REQUIRED_PROMOTED_SURFACE_DEPENDENCIES = {
    "obelisk.permissions_admin.v1": (
        "obelisk.player_identity.v1",
    ),
    "obelisk.command_chat_response_path.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
    ),
    "obelisk.commands_replies.v1": (
        "obelisk.player_identity.v1",
        "obelisk.permissions_admin.v1",
        "obelisk.command_chat_response_path.v1",
    ),
}
PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS = {
    "blockers",
    "candidate",
    "missing",
    "non_claim",
    "non_claims",
    "planning",
    "requires",
    "todo",
    "todos",
    "unresolved",
}
PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT = re.compile(
    r"\b(?:blocked|candidate(?:-only)?|insufficient|missing|needs?|no|not|planning|requires?|todo|unresolved|without)\b",
    re.IGNORECASE,
)
STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS = (
    "candidate",
    "planning",
    "orientation",
    "preflight",
    "readiness",
    "consume-only",
    "consume_only",
    "evidence-only",
    "evidence_only",
)
STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS = {
    "contract_kind",
    "schema",
    "schemas",
    "status",
}
STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS = re.compile(
    r"(?:candidate|planning|static[-_ ]?orientation|orientation|preflight|readiness|consume[-_ ]?only|evidence[-_ ]?only)",
    re.IGNORECASE,
)
CANONICAL_DEBUG_ONLY_SURFACE_IDS = {
    "obelisk.debug_raw_process_event.v1",
}
ALLOWED_GENERIC_EVIDENCE_DIRS = {
    "tests/sdk_consumer",
    "tests/sdk_installed_consumer",
}
PROMOTION_EVIDENCE_ALLOWED_PREFIXES = (
    "tests/abi/",
    "tests/core/",
    "tests/sdk_consumer/",
    "tests/sdk_installed_consumer/",
    "scripts/test_",
)
GENERIC_SCRIPT_EVIDENCE_DENYLIST = {
    "scripts/check_release_readiness.sh",
    "scripts/check_public_sdk_v1_completion.py",
}
AFFIRMATIVE_RELEASE_CLAIM_PATTERNS = (
    r"\b(?:complete|full|production|stable)\s+(?:[a-z0-9_/+-]+\s+){0,5}(?:sdk|api|support)\b",
    r"\b(?:sdk|api|surface|capability|support)\s+"
    r"(?:is|are|remains?|stays?)\s+"
    r"(?:complete|full|production|stable|available|supported|included|shipped)\b",
)
CLAUSE_START_PATTERN = re.compile(r"[.;\n]|(?:\s+-\s+)")


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
    return release_statement_surface_record(text, surface_id, status) is not None


def release_statement_surface_records(text: str, surface_id: str, status: str | None = None) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"^\s*{re.escape(surface_id)}\s*:\s*(?P<status>promoted|excluded|post-v1)(?:\s+-\s*(?P<details>.+)|\s*)$",
        re.IGNORECASE,
    )
    records: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if not match:
            continue
        found_status = match.group("status").lower()
        if status is None or found_status == status.lower():
            records.append((found_status, line.strip()))
    return records


def release_statement_surface_record(text: str, surface_id: str, status: str) -> str | None:
    records = release_statement_surface_records(text, surface_id, status)
    if len(records) != 1:
        return None
    return records[0][1]


def release_statement_duplicate_or_mixed_records(text: str, surface_id: str) -> bool:
    records = release_statement_surface_records(text, surface_id)
    if len(records) > 1:
        return True
    return False


def required_release_statement_text(requirement: str) -> str | None:
    lowered = requirement.lower()
    marker = "the v1 release statement states that "
    if lowered.startswith(marker):
        return requirement[len(marker) :]
    if lowered.startswith("the v1 release statement names "):
        return None
    if "v1_completion_required changes only" in lowered:
        return None
    return requirement


def required_release_statement_outcomes(surface: dict[str, Any]) -> set[str]:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        status = surface.get("status")
        return {status} if status in {"excluded", "post-v1"} else set()
    required = as_string_list(contract.get("exclusion_requires"))
    outcomes: set[str] = set()
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return outcomes
    prefix = f"the v1 release statement names {surface_id} as "
    for requirement in required:
        lowered = requirement.lower()
        if not lowered.startswith(prefix.lower()):
            continue
        suffix = lowered[len(prefix) :]
        if "post-v1" in suffix:
            outcomes.add("post-v1")
        if "excluded" in suffix:
            outcomes.add("excluded")
    if outcomes:
        return outcomes
    status = surface.get("status")
    return {status} if status in {"excluded", "post-v1"} else set()


def text_has_affirmative_release_claim(text: str) -> bool:
    lowered = text.lower()
    for pattern in AFFIRMATIVE_RELEASE_CLAIM_PATTERNS:
        for match in re.finditer(pattern, lowered):
            prefix = lowered[: match.start()]
            clause_start = 0
            for boundary in CLAUSE_START_PATTERN.finditer(prefix):
                clause_start = boundary.end()
            claim_prefix = lowered[clause_start : match.start()]
            if re.search(r"\b(?:no|not|never|without|excluded|post-v1|post v1)\b", claim_prefix):
                continue
            return True
    return False


def release_statement_record_has_contradiction(record: str) -> bool:
    lowered = record.lower()
    if re.search(
        r"\b(?:not true that|false that|it is not the case that|not the case that|"
        r"actually included|included despite|contradict)\b",
        lowered,
    ):
        return True
    if re.search(
        r"\b(?:except|other than|unless|but|however)\b[^.;\n]*"
        r"\b(?:included|available|supported|shipped)\b",
        lowered,
    ):
        return True
    return text_has_affirmative_release_claim(record)


def surface_exclusion_claim_terms(surface: dict[str, Any]) -> set[str]:
    terms = set(as_string_list(surface.get("exclusions")))
    terms.update(as_string_list(surface.get("audit_units")))
    if isinstance(surface.get("public_name"), str):
        terms.add(surface["public_name"])
    contract = surface.get("v1_decision_contract")
    if isinstance(contract, dict):
        for requirement in as_string_list(contract.get("exclusion_requires")):
            required_text = required_release_statement_text(requirement)
            if required_text is None:
                continue
            body = re.sub(r"^\s*no\s+", "", required_text, flags=re.IGNORECASE)
            body = re.sub(r"\s+(?:api\s+)?is included in v1\s*$", "", body, flags=re.IGNORECASE)
            for term in re.split(r"\s*,\s*|\s+\bor\b\s+|\s+\band\b\s+", body):
                term = term.strip(" .")
                if len(term) >= 4:
                    terms.add(term)
    return {term.lower() for term in terms if term}


def release_statement_has_surface_claim_contradiction(text: str, surface: dict[str, Any]) -> bool:
    terms = surface_exclusion_claim_terms(surface)
    if not terms:
        return False
    for line in text.splitlines():
        if re.match(r"^\s*obelisk\.[a-z0-9_.-]+\.v1\s*:", line, re.IGNORECASE):
            continue
        lowered = line.lower()
        if any(term in lowered for term in terms) and text_has_affirmative_release_claim(line):
            return True
    return False


def release_statement_satisfies_exclusion_contract(text: str, surface: dict[str, Any]) -> bool:
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        return False
    required = as_string_list(contract.get("exclusion_requires"))
    if not required:
        return False
    surface_id = surface.get("id")
    status = surface.get("status")
    if not isinstance(surface_id, str) or status not in {"excluded", "post-v1"}:
        return False
    expected = "post-v1" if status == "post-v1" else "excluded"
    record = release_statement_surface_record(text, surface_id, expected)
    if record is None:
        return False
    lowered = record.lower()
    if release_statement_record_has_contradiction(record):
        return False
    if release_statement_has_surface_claim_contradiction(text, surface):
        return False
    required_text = [item for item in (required_release_statement_text(item) for item in required) if item]
    return all(item.lower() in lowered for item in required_text)


def release_statement_satisfies_experimental_outcome(text: str, surface_id: str, status: str) -> bool:
    record = release_statement_surface_record(text, surface_id, status)
    if record is None or release_statement_record_has_contradiction(record):
        return False
    if status == "promoted":
        return True
    required_terms = CANONICAL_EXPERIMENTAL_RELEASE_STATEMENT_TEXT.get(surface_id, ())
    lowered = record.lower()
    return all(term.lower() in lowered for term in required_terms)


def repo_relative_evidence_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            return None
    else:
        path = REPO_ROOT / path
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except (OSError, ValueError):
        return None


def evidence_path_is_specific(raw_path: str, surface_id: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    relative_text = relative.as_posix()
    if surface_id in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS and relative_text.startswith("scripts/test_"):
        return False
    if relative_text in GENERIC_SCRIPT_EVIDENCE_DENYLIST:
        return False
    if not relative_text.startswith(PROMOTION_EVIDENCE_ALLOWED_PREFIXES):
        return False
    surface_tokens = [
        token
        for token in surface_id.removeprefix("obelisk.").removesuffix(".v1").replace(".", "_").split("_")
        if token
    ]
    lowered = relative_text.lower()
    return any(token.lower() in lowered for token in surface_tokens)


def evidence_path_has_non_promotional_marker(raw_path: str) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    normalized_parts = [
        part.lower().replace("-", "_")
        for part in relative.with_suffix("").parts
    ]
    for part in normalized_parts:
        for marker in STRICT_PROMOTION_EVIDENCE_PATH_DENY_MARKERS:
            if marker.replace("-", "_") in part:
                return True
    return False


def evidence_path_exists(raw_path: str, *, allow_generic_dirs: bool) -> bool:
    relative = repo_relative_evidence_path(raw_path)
    if relative is None:
        return False
    path = REPO_ROOT / relative
    if not path.exists():
        return False
    if path.is_dir():
        return allow_generic_dirs and relative.as_posix() in ALLOWED_GENERIC_EVIDENCE_DIRS
    return path.is_file()


def evidence_has_non_promotional_schema_marker(
    value: Any,
    *,
    parent_key: str | None = None,
) -> bool:
    normalized_key = parent_key.lower().replace("-", "_") if isinstance(parent_key, str) else None
    if normalized_key in STRICT_PROMOTION_EVIDENCE_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
        if STRICT_PROMOTION_EVIDENCE_SCHEMA_DENY_MARKERS.search(text):
            return True
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_has_non_promotional_schema_marker(item, parent_key=next_key):
                return True
    if isinstance(value, list):
        return any(
            evidence_has_non_promotional_schema_marker(item, parent_key=parent_key)
            for item in value
        )
    return False


def surface_has_promotion_evidence(surface: dict[str, Any]) -> bool:
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        return False
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        return False
    allow_generic_dirs = surface_id not in STRICT_PROMOTION_EVIDENCE_SURFACE_IDS
    if not allow_generic_dirs:
        if evidence.get("surface_id") != surface_id:
            return False
        if evidence.get("promotion_status") != "promoted":
            return False
        if evidence.get("public_sdk_ready") is not True:
            return False
        if evidence_has_non_promotional_schema_marker(evidence):
            return False
        if not isinstance(evidence.get("abi_tests"), list) or not evidence["abi_tests"]:
            return False
        if not isinstance(evidence.get("sdk_consumer_tests"), list) or not evidence["sdk_consumer_tests"]:
            return False
    def evidence_value_valid(value: Any, *, evidence_key: str | None = None) -> bool:
        def item_valid(item: str) -> bool:
            relative = repo_relative_evidence_path(item)
            if relative is None:
                return False
            relative_text = relative.as_posix()
            if not allow_generic_dirs and evidence_key in {"sdk_consumer_tests", "installed_sdk_consumer_tests"}:
                if not (
                    relative_text == "tests/sdk_consumer"
                    or relative_text.startswith("tests/sdk_consumer/")
                    or relative_text == "tests/sdk_installed_consumer"
                    or relative_text.startswith("tests/sdk_installed_consumer/")
                ):
                    return False
            if not allow_generic_dirs and evidence_key == "abi_tests":
                if not (relative_text.startswith("tests/abi/") or relative_text.startswith("tests/core/")):
                    return False
            if not allow_generic_dirs and evidence_path_has_non_promotional_marker(item):
                return False
            return evidence_path_exists(item, allow_generic_dirs=allow_generic_dirs) and (
                allow_generic_dirs or evidence_path_is_specific(item, surface_id)
            )

        if isinstance(value, list) and value:
            return all(isinstance(item, str) and item_valid(item) for item in value)
        return isinstance(value, str) and item_valid(value)

    if not allow_generic_dirs and not (
        evidence_value_valid(evidence.get("abi_tests"), evidence_key="abi_tests")
        and evidence_value_valid(evidence.get("sdk_consumer_tests"), evidence_key="sdk_consumer_tests")
    ):
        return False

    machine_keys = (
        "abi_tests",
        "sdk_consumer_tests",
        "installed_sdk_consumer_tests",
        "tests",
        "install_gate",
    )
    for key in machine_keys:
        if evidence_value_valid(evidence.get(key), evidence_key=key):
            return True
    return False


def promotion_evidence_key_is_negative_context(parent_key: str | None) -> bool:
    if parent_key is None:
        return False
    normalized = parent_key.lower().replace("-", "_")
    return any(marker in normalized for marker in PROMOTION_EVIDENCE_NEGATIVE_CONTEXT_KEYS)


def evidence_value_contains_positive_term(
    value: Any,
    term: str,
    *,
    parent_key: str | None = None,
) -> bool:
    if promotion_evidence_key_is_negative_context(parent_key):
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            next_key = key if isinstance(key, str) else None
            if evidence_value_contains_positive_term(item, term, parent_key=next_key):
                return True
        return False
    if isinstance(value, list):
        return any(
            evidence_value_contains_positive_term(item, term, parent_key=parent_key) for item in value
        )
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
    else:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
    if term.lower() not in text.lower():
        return False
    return PROMOTION_EVIDENCE_NEGATIVE_TERM_CONTEXT.search(text) is None


def surface_missing_required_promotion_evidence(surface: dict[str, Any]) -> list[str]:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str) or surface.get("status") != "promoted":
        return []
    required_terms = PROMOTION_EVIDENCE_REQUIRED_TERMS.get(surface_id, ())
    if not required_terms:
        return []
    evidence = surface.get("evidence", {})
    return [term for term in required_terms if not evidence_value_contains_positive_term(evidence, term)]


def unresolved_promoted_surface_dependencies(
    surface: dict[str, Any],
    surfaces_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    if surface.get("status") != "promoted":
        return []
    unresolved: list[str] = []
    dependency_ids = as_string_list(surface.get("depends_on"))
    surface_id = surface.get("id")
    if isinstance(surface_id, str):
        for required_dependency_id in REQUIRED_PROMOTED_SURFACE_DEPENDENCIES.get(surface_id, ()):
            if required_dependency_id not in dependency_ids:
                dependency_ids.append(required_dependency_id)
    for dependency_id in dependency_ids:
        dependency = surfaces_by_id.get(dependency_id)
        if not isinstance(dependency, dict) or dependency.get("status") != "promoted":
            unresolved.append(dependency_id)
    return unresolved


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
    seen_surface_ids: set[str] = set()
    duplicate_surface_ids: list[str] = []
    for surface in surface_rows:
        if not isinstance(surface, dict) or not isinstance(surface.get("id"), str):
            continue
        surface_id = surface["id"]
        if surface_id in seen_surface_ids:
            duplicate_surface_ids.append(surface_id)
        seen_surface_ids.add(surface_id)
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
    planning_surfaces = set(as_string_list(manifest.get("planning_surfaces")))
    status_experimental_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "promoted-experimental-only"
    }
    status_planning_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") == "planning"
    }
    completion_blockers = as_string_list(manifest.get("v1_sdk_completion_blockers"))
    completion_blocker_set = set(completion_blockers)
    post_v1_or_excluded = set(as_string_list(manifest.get("post_v1_or_excluded_surfaces")))
    status_post_v1_or_excluded_surfaces = {
        surface_id
        for surface_id, surface in surfaces_by_id.items()
        if surface.get("status") in {"post-v1", "excluded"}
    }
    debug_only_surfaces = set(as_string_list(manifest.get("debug_only_surfaces")))
    canonical_debug_only_present = CANONICAL_DEBUG_ONLY_SURFACE_IDS & set(surfaces_by_id)

    unresolved_experimental: list[str] = []
    unresolved_completion_blockers: list[str] = []
    unresolved_planning_surfaces: list[str] = []
    missing_surfaces: list[str] = []
    missing_canonical_surfaces = sorted(CANONICAL_SURFACE_IDS - set(surfaces_by_id))
    missing_canonical_completion_blockers = sorted(CANONICAL_V1_COMPLETION_BLOCKERS - completion_blocker_set)
    promoted_without_contract: list[str] = []
    promoted_without_evidence: list[str] = []
    non_promoted_with_contract: list[str] = []
    promoted_list_mismatches: list[str] = []
    experimental_list_mismatches: list[str] = []
    planning_list_mismatches: list[str] = []
    post_v1_or_excluded_list_mismatches: list[str] = []
    release_statement_missing_blockers: list[str] = []
    release_statement_missing_contracts: list[str] = []
    release_statement_missing_experimental_outcomes: list[str] = []
    release_statement_duplicate_records: list[str] = []
    missing_completion_blocker_exclusion_contracts: list[str] = []
    debug_only_promoted: list[str] = []
    promoted_dependency_failures: dict[str, list[str]] = {}
    promoted_missing_required_evidence_terms: dict[str, list[str]] = {}

    if stable_claim_allowed and manifest.get("v1_completion_required") is True and release_statement_text is None:
        blockers.append("release_statement_required_for_v1_completion")

    if not canonical_debug_only_present.issubset(debug_only_surfaces):
        blockers.append("debug_only_surface_list_missing_canonical_ids")

    if experimental_surfaces != status_experimental_surfaces:
        experimental_list_mismatches = sorted(experimental_surfaces ^ status_experimental_surfaces)
    if planning_surfaces != status_planning_surfaces:
        planning_list_mismatches = sorted(planning_surfaces ^ status_planning_surfaces)
    if post_v1_or_excluded != status_post_v1_or_excluded_surfaces:
        post_v1_or_excluded_list_mismatches = sorted(
            post_v1_or_excluded ^ status_post_v1_or_excluded_surfaces
        )

    experimental_outcome_surface_ids = (
        experimental_surfaces
        | status_experimental_surfaces
        | (CANONICAL_EXPERIMENTAL_SURFACE_IDS & set(surfaces_by_id))
    )
    for surface_id in sorted(experimental_outcome_surface_ids):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
            unresolved_experimental.append(surface_id)
            continue
        status = surface.get("status")
        if status == "promoted":
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if release_statement_text is None:
                release_statement_missing_experimental_outcomes.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_satisfies_experimental_outcome(release_statement_text, surface_id, status):
                release_statement_missing_experimental_outcomes.append(surface_id)
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
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
                release_statement_missing_blockers.append(surface_id)
            continue
        if status in {"post-v1", "excluded"} and surface_id in post_v1_or_excluded:
            if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
                contract = surface.get("v1_decision_contract")
                if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                    missing_completion_blocker_exclusion_contracts.append(surface_id)
                    continue
                allowed_outcomes = required_release_statement_outcomes(surface)
                if status not in allowed_outcomes:
                    release_statement_missing_contracts.append(surface_id)
                    continue
            if release_statement_text is None:
                release_statement_missing_blockers.append(surface_id)
            elif release_statement_duplicate_or_mixed_records(release_statement_text, surface_id):
                release_statement_duplicate_records.append(surface_id)
            elif not release_statement_names_outcome(release_statement_text, surface_id, status):
                release_statement_missing_blockers.append(surface_id)
            elif not release_statement_satisfies_exclusion_contract(release_statement_text, surface):
                release_statement_missing_contracts.append(surface_id)
            continue
        if surface_id in CANONICAL_V1_COMPLETION_BLOCKERS:
            contract = surface.get("v1_decision_contract")
            if not isinstance(contract, dict) or not as_string_list(contract.get("exclusion_requires")):
                missing_completion_blocker_exclusion_contracts.append(surface_id)
        unresolved_completion_blockers.append(surface_id)

    for surface_id, surface in surfaces_by_id.items():
        status = surface.get("status")
        contract = surface.get("public_contract")
        contract_items = contract if isinstance(contract, list) else []
        if surface_id in debug_only_surfaces or surface_id in CANONICAL_DEBUG_ONLY_SURFACE_IDS:
            if status == "promoted" or surface_id in promoted_surfaces:
                debug_only_promoted.append(surface_id)
        if status == "promoted":
            if surface_id not in promoted_surfaces:
                promoted_list_mismatches.append(surface_id)
            if not contract_items:
                promoted_without_contract.append(surface_id)
            if not surface_has_promotion_evidence(surface):
                promoted_without_evidence.append(surface_id)
            missing_required_terms = surface_missing_required_promotion_evidence(surface)
            if missing_required_terms:
                promoted_missing_required_evidence_terms[surface_id] = missing_required_terms
            unresolved_dependencies = unresolved_promoted_surface_dependencies(surface, surfaces_by_id)
            if unresolved_dependencies:
                promoted_dependency_failures[surface_id] = unresolved_dependencies
        elif status == "planning":
            unresolved_planning_surfaces.append(surface_id)
        elif status != "promoted-experimental-only" and contract_items:
            non_promoted_with_contract.append(surface_id)

    for surface_id in sorted(promoted_surfaces):
        surface = surfaces_by_id.get(surface_id)
        if not surface:
            missing_surfaces.append(surface_id)
        elif surface.get("status") != "promoted":
            promoted_list_mismatches.append(surface_id)

    missing_surfaces.extend(missing_canonical_surfaces)
    unresolved_completion_blockers.extend(missing_canonical_completion_blockers)

    if missing_surfaces:
        blockers.append("surface_id_missing")
    if duplicate_surface_ids:
        blockers.append("duplicate_surface_id")
    if missing_canonical_surfaces:
        blockers.append("canonical_surface_id_missing")
    if missing_canonical_completion_blockers:
        blockers.append("canonical_v1_completion_blocker_missing")
    if unresolved_experimental:
        blockers.append("promoted_experimental_surfaces_unresolved")
    if unresolved_completion_blockers:
        blockers.append("v1_sdk_completion_blockers_unresolved")
    if unresolved_planning_surfaces:
        blockers.append("planning_surfaces_unresolved_for_v1_claim")
    if planning_surfaces:
        blockers.append("top_level_planning_surfaces_unresolved_for_v1_claim")
    if missing_completion_blocker_exclusion_contracts:
        blockers.append("completion_blocker_exclusion_contract_missing")
    if debug_only_promoted:
        blockers.append("debug_only_surface_promoted")
    if promoted_without_contract:
        blockers.append("promoted_surface_public_contract_missing")
    if promoted_without_evidence:
        blockers.append("promoted_surface_evidence_missing")
    if promoted_missing_required_evidence_terms:
        blockers.append("promoted_surface_required_evidence_terms_missing")
    if promoted_dependency_failures:
        blockers.append("promoted_surface_dependency_unresolved")
    if non_promoted_with_contract:
        blockers.append("non_promoted_surface_has_public_contract")
    if promoted_list_mismatches:
        blockers.append("promoted_surface_list_mismatch")
    if experimental_list_mismatches:
        blockers.append("experimental_surface_list_mismatch")
    if planning_list_mismatches:
        blockers.append("planning_surface_list_mismatch")
    if post_v1_or_excluded_list_mismatches:
        blockers.append("post_v1_or_excluded_surface_list_mismatch")
    if release_statement_missing_blockers:
        blockers.append("release_statement_missing_non_promoted_blocker_outcomes")
    if release_statement_missing_contracts:
        blockers.append("release_statement_missing_exclusion_contract")
    if release_statement_missing_experimental_outcomes:
        blockers.append("release_statement_missing_experimental_outcomes")
    if release_statement_duplicate_records:
        blockers.append("release_statement_duplicate_or_mixed_surface_records")
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
        "unresolved_planning_surfaces": sorted(set(unresolved_planning_surfaces)),
        "top_level_planning_surfaces": sorted(planning_surfaces),
        "planning_list_mismatches": planning_list_mismatches,
        "post_v1_or_excluded_list_mismatches": post_v1_or_excluded_list_mismatches,
        "debug_only_promoted_surfaces": sorted(set(debug_only_promoted)),
        "missing_completion_blocker_exclusion_contracts": sorted(
            set(missing_completion_blocker_exclusion_contracts)
        ),
        "missing_surfaces": sorted(set(missing_surfaces)),
        "duplicate_surface_ids": sorted(set(duplicate_surface_ids)),
        "promoted_without_public_contract": sorted(set(promoted_without_contract)),
        "missing_canonical_surfaces": missing_canonical_surfaces,
        "missing_canonical_completion_blockers": missing_canonical_completion_blockers,
        "promoted_surfaces_without_evidence": sorted(set(promoted_without_evidence)),
        "promoted_surfaces_missing_required_evidence_terms": {
            surface_id: sorted(set(terms))
            for surface_id, terms in sorted(promoted_missing_required_evidence_terms.items())
        },
        "promoted_surfaces_with_unresolved_dependencies": {
            surface_id: sorted(set(dependencies))
            for surface_id, dependencies in sorted(promoted_dependency_failures.items())
        },
        "promoted_blockers_without_evidence": sorted(set(promoted_without_evidence) & completion_blocker_set),
        "non_promoted_with_public_contract": sorted(set(non_promoted_with_contract)),
        "promoted_list_mismatches": sorted(set(promoted_list_mismatches)),
        "experimental_list_mismatches": sorted(set(experimental_list_mismatches)),
        "release_statement_missing_blocker_outcomes": sorted(set(release_statement_missing_blockers)),
        "release_statement_missing_exclusion_contracts": sorted(set(release_statement_missing_contracts)),
        "release_statement_missing_experimental_outcomes": sorted(set(release_statement_missing_experimental_outcomes)),
        "release_statement_duplicate_or_mixed_records": sorted(set(release_statement_duplicate_records)),
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
