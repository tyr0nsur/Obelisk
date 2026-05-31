"""Shared fail-closed contract for static orientation clues.

This module intentionally models navigation evidence only. It must not be
registered as an offline artifact gate or promotion source.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


SCHEMA = "obelisk.static-candidate-orientation-contract.v1"
CONTRACT_KIND = "candidate_static_orientation"
STATUS = "candidate_blocked"
GATE_MODE = "consume"

FORBIDDEN_PROMOTION_RE = re.compile(
    r"\b(?:accepted|callback|identity_resolved|mutation|promoted|"
    r"resource_handle|return_override|runtime_observed)\b",
    re.IGNORECASE,
)

REQUIRED_NON_CLAIM_PHRASE_GROUPS = (
    ("does not replace core evidence", "does not replace a non-protected complete core evidence"),
    ("does not promote public identity",),
    ("does not promote permissions", "permissions"),
    ("does not promote commands", "commands"),
    ("does not promote mutation", "mutation"),
    ("does not promote return override", "return override"),
)


def build_contract(
    *,
    topic: str,
    binary_sha256: str | None,
    target_set: str,
    expected_targets: Iterable[str],
    address_convention: str,
    subjects: list[dict[str, Any]],
    non_claims: list[str],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "contract_kind": CONTRACT_KIND,
        "status": STATUS,
        "gate_mode": GATE_MODE,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "scope": {
            "topic": topic,
            "binary_sha256": binary_sha256,
            "target_set": target_set,
            "address_convention": address_convention,
            "expected_targets": sorted(expected_targets),
        },
        "subjects": subjects,
        "non_claims": non_claims,
        "blockers": blockers,
    }


def _string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def validate_contract(contract: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []

    def add(reason: str, **details: Any) -> None:
        blockers.append({"reason": reason, **details})

    if contract.get("schema") != SCHEMA:
        add("static_orientation_contract_schema_invalid", value=contract.get("schema"))
    if contract.get("contract_kind") != CONTRACT_KIND:
        add("static_orientation_contract_kind_invalid", value=contract.get("contract_kind"))
    if contract.get("status") != STATUS:
        add("static_orientation_contract_status_invalid", value=contract.get("status"))
    if contract.get("gate_mode") != GATE_MODE:
        add("static_orientation_contract_gate_mode_invalid", value=contract.get("gate_mode"))

    for key in ("not_artifact_gate",):
        if contract.get(key) is not True:
            add("static_orientation_contract_boolean_invalid", field=key, value=contract.get(key))
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if contract.get(key) is not False:
            add("static_orientation_contract_readiness_overclaim", field=key, value=contract.get(key))

    scope = contract.get("scope")
    expected_targets: set[str] = set()
    if not isinstance(scope, dict):
        add("static_orientation_contract_scope_missing")
    else:
        for key in ("topic", "binary_sha256", "target_set", "address_convention"):
            if not isinstance(scope.get(key), str) or not scope[key]:
                add("static_orientation_contract_scope_field_invalid", field=key, value=scope.get(key))
        raw_expected = scope.get("expected_targets")
        if not isinstance(raw_expected, list) or not all(isinstance(item, str) for item in raw_expected):
            add("static_orientation_contract_expected_targets_invalid")
        else:
            expected_targets = set(raw_expected)

    subjects = contract.get("subjects")
    observed_targets: set[str] = set()
    if not isinstance(subjects, list) or not subjects:
        add("static_orientation_contract_subjects_missing")
    else:
        for subject in subjects:
            if not isinstance(subject, dict):
                add("static_orientation_contract_subject_not_object")
                continue
            target = subject.get("target")
            if isinstance(target, str):
                observed_targets.add(target)
            else:
                add("static_orientation_contract_subject_target_invalid", value=target)
            if subject.get("status") != "candidate_only":
                add(
                    "static_orientation_contract_subject_status_not_candidate_only",
                    target=target,
                    value=subject.get("status"),
                )
            if not isinstance(subject.get("kind"), str) or not subject["kind"]:
                add("static_orientation_contract_subject_kind_invalid", target=target, value=subject.get("kind"))
            for text in _string_values(subject):
                if FORBIDDEN_PROMOTION_RE.search(text):
                    add("static_orientation_contract_subject_contains_promotion_token", target=target)
                    break

    if expected_targets and observed_targets != expected_targets:
        add(
            "static_orientation_contract_target_coverage_mismatch",
            missing=sorted(expected_targets - observed_targets),
            unexpected=sorted(observed_targets - expected_targets),
        )

    non_claims = contract.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) for item in non_claims):
        add("static_orientation_contract_non_claims_invalid")
    else:
        joined = " ".join(non_claims).lower()
        for phrases in REQUIRED_NON_CLAIM_PHRASE_GROUPS:
            if not any(phrase in joined for phrase in phrases):
                add("static_orientation_contract_required_non_claim_missing", phrase=phrases[0])

    contract_blockers = contract.get("blockers")
    if not isinstance(contract_blockers, list) or not all(isinstance(item, str) for item in contract_blockers):
        add("static_orientation_contract_blockers_invalid")
    elif not contract_blockers:
        add("static_orientation_contract_blockers_empty")

    return blockers
