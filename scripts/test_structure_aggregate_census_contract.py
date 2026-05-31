#!/usr/bin/env python3
"""Offline contract test for a bounded Structure aggregate/census window."""

from __future__ import annotations

import copy
import json
import unittest
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
STRUCTURE = "structure"
INVENTORY_ITEM = "inventory_item"

ACCESS_CHECK = "structure.access_check"
DEMOLISH_CHECK = "structure.demolish_check"
VARIANT_CHANGE = "structure.variant_change"
ACTIVATION_TOGGLE = "structure.activation_toggle"
PIN_CODE_CHECK = "structure.pin_code_check"
SEAT_CHECK = "structure.seat_check"

RETURN_VALUE = "ReturnValue"
VARIANT_INDEX = "VariantIndex"
FORCE_SET = "ForceSet"
FORCE = "Force"

FIELD_MASK_TO_FIXTURE_FIELD = {
    "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE": RETURN_VALUE,
    "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX": VARIANT_INDEX,
    "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET": FORCE_SET,
    "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE": FORCE,
}
COPIED_STRUCTURE_FIELDS = frozenset({
    RETURN_VALUE,
    VARIANT_INDEX,
    FORCE_SET,
    FORCE,
})
NON_PIN_STRUCTURE_KINDS = frozenset({
    ACCESS_CHECK,
    DEMOLISH_CHECK,
    VARIANT_CHANGE,
    ACTIVATION_TOGGLE,
    SEAT_CHECK,
})
FORBIDDEN_OUTPUT_TOKENS = (
    "address",
    "base",
    "correlation",
    "exact_timestamp",
    "fname",
    "function_name_index",
    "gobjects",
    "location",
    "outer_name_index",
    "owner",
    "pin",
    "player",
    "pointer",
    "raw_param",
    "resource_handle",
    "sequence",
    "structure_id",
    "timestamp",
    "tribe",
    "ue_pointer",
    "verify",
)
FORBIDDEN_ACTION_TOKENS = (
    "decision",
    "deny",
    "mutate",
    "override",
)


@dataclass(frozen=True)
class CopiedPolicyEvent:
    resource_kind: str
    event_kind: str
    original_called: bool
    bool_values: dict[str, bool]
    int32_values: dict[str, int]


def fixture_events() -> list[CopiedPolicyEvent]:
    """Rows mirror copied GameplayPolicyEvent/Structure scalar fixture shapes."""

    return [
        CopiedPolicyEvent(STRUCTURE, ACCESS_CHECK, True, {RETURN_VALUE: True}, {}),
        CopiedPolicyEvent(STRUCTURE, DEMOLISH_CHECK, True, {RETURN_VALUE: False}, {}),
        CopiedPolicyEvent(STRUCTURE, ACTIVATION_TOGGLE, True, {RETURN_VALUE: True}, {}),
        CopiedPolicyEvent(
            STRUCTURE,
            VARIANT_CHANGE,
            True,
            {FORCE_SET: True, RETURN_VALUE: False},
            {VARIANT_INDEX: 3},
        ),
        CopiedPolicyEvent(
            STRUCTURE,
            VARIANT_CHANGE,
            True,
            {FORCE_SET: False, RETURN_VALUE: True},
            {VARIANT_INDEX: 4},
        ),
        CopiedPolicyEvent(
            STRUCTURE,
            VARIANT_CHANGE,
            True,
            {FORCE_SET: True, RETURN_VALUE: True},
            {VARIANT_INDEX: 99},
        ),
        CopiedPolicyEvent(STRUCTURE, PIN_CODE_CHECK, True, {RETURN_VALUE: True}, {}),
        CopiedPolicyEvent(STRUCTURE, SEAT_CHECK, True, {FORCE: True, RETURN_VALUE: True}, {}),
        CopiedPolicyEvent(
            STRUCTURE,
            VARIANT_CHANGE,
            False,
            {FORCE_SET: True, RETURN_VALUE: True},
            {VARIANT_INDEX: 5},
        ),
        CopiedPolicyEvent(STRUCTURE, ACCESS_CHECK, True, {RETURN_VALUE: False}, {}),
        CopiedPolicyEvent(INVENTORY_ITEM, "inventory.use_check", True, {RETURN_VALUE: True}, {}),
    ]


def gameplay_policy_descriptor_fields() -> dict[str, set[str]]:
    descriptor_path = REPO_ROOT / "docs" / "public_gameplay_events.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    event_kinds = next(
        event["event_kinds"]
        for event in descriptor["promoted_events"]
        if event.get("event_id") == "obelisk.gameplay_policy.v1"
    )
    fields_by_stable_name: dict[str, set[str]] = {}
    for event in event_kinds:
        stable_name = event["stable_name"]
        fields_by_stable_name[stable_name] = {
            FIELD_MASK_TO_FIXTURE_FIELD[field]
            for field in event["field_mask"]
            if field in FIELD_MASK_TO_FIXTURE_FIELD
        }
    return fields_by_stable_name


def add_capped_histogram_value(histogram: dict[str, int], value: int, cap: int) -> None:
    key = str(value)
    if key in histogram:
        histogram[key] += 1
        return
    if len([existing for existing in histogram if existing != "__other__"]) < cap:
        histogram[key] = 1
        return
    histogram["__other__"] = histogram.get("__other__", 0) + 1


def aggregate_structure_window(
    events: list[CopiedPolicyEvent],
    *,
    window_event_limit: int,
    variant_bucket_limit: int,
) -> dict[str, Any]:
    counters: dict[str, Any] = {
        "matched_total": 0,
        "original_called_total": 0,
        "original_blocked_total": 0,
        "rejected_total_by_reason": Counter(),
        "copied_field_present_total": Counter(),
        "bool_true_total": Counter(),
        "bool_false_total": Counter(),
        "int32_present_total": Counter(),
    }
    variant_index_histogram: dict[str, int] = {}

    for event in events[:window_event_limit]:
        if event.resource_kind != STRUCTURE or event.event_kind not in NON_PIN_STRUCTURE_KINDS:
            counters["rejected_total_by_reason"]["excluded_sensitive_or_non_structure"] += 1
            continue

        counters["matched_total"] += 1
        if not event.original_called:
            counters["original_blocked_total"] += 1
            continue
        counters["original_called_total"] += 1

        for field, value in event.bool_values.items():
            if field not in COPIED_STRUCTURE_FIELDS:
                counters["rejected_total_by_reason"]["unexpected_copied_field"] += 1
                continue
            counters["copied_field_present_total"][field] += 1
            if value:
                counters["bool_true_total"][field] += 1
            else:
                counters["bool_false_total"][field] += 1

        for field, value in event.int32_values.items():
            if field != VARIANT_INDEX:
                counters["rejected_total_by_reason"]["unexpected_copied_field"] += 1
                continue
            counters["copied_field_present_total"][field] += 1
            counters["int32_present_total"][field] += 1
            add_capped_histogram_value(variant_index_histogram, value, variant_bucket_limit)

    return {
        "window_event_limit": window_event_limit,
        "variant_bucket_limit": variant_bucket_limit,
        "counters": {key: dict(value) if isinstance(value, Counter) else value for key, value in counters.items()},
        "histograms": {
            "VariantIndex": variant_index_histogram,
        },
    }


def flattened_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        strings: list[str] = []
        for key, child in value.items():
            strings.append(str(key))
            strings.extend(flattened_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(flattened_strings(child))
        return strings
    if isinstance(value, str):
        return [value]
    return []


class StructureAggregateCensusContractTests(unittest.TestCase):
    def test_fixture_rows_match_existing_copied_gameplay_policy_fields(self) -> None:
        descriptor_fields = gameplay_policy_descriptor_fields()

        for event in fixture_events():
            if event.resource_kind != STRUCTURE:
                continue
            copied_fields = set(event.bool_values) | set(event.int32_values)
            self.assertLessEqual(copied_fields, descriptor_fields[event.event_kind])

        self.assertEqual(descriptor_fields[PIN_CODE_CHECK], {RETURN_VALUE})

    def test_bounded_window_counts_and_capped_variant_histogram(self) -> None:
        events = fixture_events()
        original_events = copy.deepcopy(events)

        aggregate = aggregate_structure_window(
            events,
            window_event_limit=9,
            variant_bucket_limit=2,
        )

        self.assertEqual(events, original_events)
        self.assertEqual(aggregate["window_event_limit"], 9)
        self.assertEqual(aggregate["variant_bucket_limit"], 2)
        self.assertEqual(
            aggregate["counters"],
            {
                "matched_total": 8,
                "original_called_total": 7,
                "original_blocked_total": 1,
                "rejected_total_by_reason": {"excluded_sensitive_or_non_structure": 1},
                "copied_field_present_total": {
                    RETURN_VALUE: 7,
                    FORCE_SET: 3,
                    VARIANT_INDEX: 3,
                    FORCE: 1,
                },
                "bool_true_total": {
                    RETURN_VALUE: 5,
                    FORCE_SET: 2,
                    FORCE: 1,
                },
                "bool_false_total": {
                    RETURN_VALUE: 2,
                    FORCE_SET: 1,
                },
                "int32_present_total": {
                    VARIANT_INDEX: 3,
                },
            },
        )
        self.assertEqual(aggregate["histograms"], {"VariantIndex": {"3": 1, "4": 1, "__other__": 1}})
        self.assertNotIn("99", aggregate["histograms"]["VariantIndex"])

    def test_output_excludes_pin_identity_correlation_and_action_fields(self) -> None:
        aggregate = aggregate_structure_window(
            fixture_events(),
            window_event_limit=9,
            variant_bucket_limit=2,
        )
        flattened = "\n".join(flattened_strings(aggregate)).casefold()

        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, flattened)
        for token in FORBIDDEN_ACTION_TOKENS:
            self.assertNotIn(token, flattened)

        self.assertNotIn(PIN_CODE_CHECK, flattened)
        self.assertNotIn("5", aggregate["histograms"]["VariantIndex"])


if __name__ == "__main__":
    unittest.main()
