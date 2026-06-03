#!/usr/bin/env python3
"""Validate the candidate-only player identity owner-token SDK consumer contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_public_abi_preflight_candidate as public_abi_preflight


SCHEMA = "obelisk.player-identity-owner-token-sdk-consumer-contract.v1"
REPORT_SCHEMA = "obelisk.player-identity-owner-token-sdk-consumer-contract-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_MANIFEST = Path(
    "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json"
)
DEFAULT_PUBLIC_ABI_PREFLIGHT = Path(
    "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json"
)
DEFAULT_PUBLIC_HEADER = Path("include/obelisk/ObeliskApi.h")
PUBLIC_ABI_PREFLIGHT_INPUT = "abi.public_pod_contract.public_abi_preflight_candidate"

REQUIRED_BEFORE_PROMOTION = {
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
    "runtime.lifecycle_evidence",
    "v1_completion",
}
REQUIRED_DOES_NOT_RESOLVE = {
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
    "runtime.lifecycle_evidence",
    "public_sdk",
    "v1_completion",
}
REQUIRED_ABI_LAYOUT_CHECKS = {
    "front-loaded abi_version and struct_size in promoted POD structs",
    "fixed-size POD only; no UE pointers, raw ProcessEvent params, FString, STL, references, or exceptions",
    "append-only after promotion; no inserting or retyping existing fields",
    "struct_size and capability checked before accessing appended fields",
    "layout tests assert size, alignment, offsets, reserved-zero, and prefix compatibility or rejection",
    "descriptor and event payload match the accepted private candidate until a replacement candidate is reviewed",
    "public header changes remain forbidden until the promotion gate opens",
}
REQUIRED_SDK_CONSUMER_CHECKS = {
    "installed SDK consumer compiles against the promoted header",
    "C and C++ consumers check abi_version, struct_size, capability bit, non-null function pointers, and nonzero plugin_owner_token before registration",
    "missing capability, short struct_size, null function pointer, or zero owner token fails closed without registration",
    "consumer treats callback payload storage as callback-local and never retains borrowed pointers",
    "consumer treats principal handles and registration handles as process-local and non-persistent",
    "consumer can unregister by owner token and registration handle",
    "consumer tests prove no dependency on private runtime headers or runtime C++ types",
}
REQUIRED_OWNER_CLEANUP_CHECKS = {
    "nonzero plugin_owner_token required",
    "opaque uint64 registration handle returned on success",
    "owner-scoped unregister requires the same plugin_owner_token",
    "plugin init failure removes registrations before dlclose",
    "plugin unload removes registrations and drains in-flight callbacks before dlclose",
    "self-unregister from the callback is safe",
    "callback exceptions do not cross the C ABI",
    "cleanup failure retains unload state for retry instead of pretending dlclose completed",
}
REQUIRED_DOWNSTREAM_CHECKS = {
    "no downstream surface may consume player identity until obelisk.player_identity.v1 has separate promotion evidence",
    "permissions/admin and command response keep independent fail-closed gates",
    "public principal does not authorize lookup, persistence, mutation, return override, send-chat identity, or ResourceHandle identity",
    "downstream artifacts must cite promoted player identity evidence before replacing fail-closed blockers",
}
REQUIRED_BLOCKED_DOWNSTREAM = {
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "player_lookup",
    "storage_persistence",
    "mutation",
    "return_override",
    "send_chat_identity",
    "operator_ingress",
    "resource_handle_identity",
}
REQUIRED_NON_CLAIMS = {
    "candidate-only owner-token SDK consumer planning contract",
    "does not add public header symbols",
    "does not reserve final C symbol names",
    "does not add capability bits",
    "does not add callback ABI",
    "does not edit runtime C++",
    "does not promote obelisk.player_identity.v1",
    "does not resolve abi.layout, sdk.consumer, lifecycle.owner_cleanup, separation.downstream_surfaces, runtime.lifecycle_evidence, public_sdk, or v1_completion",
    "does not promote permissions/admin, command response, commands/replies, lookup, persistence, mutation, return override, ResourceHandle identity, or send-chat identity",
}
FORBIDDEN_STRUCTURED_CLAIM_KEYS = {
    "acceptedforcontractreview",
    "promotionready",
    "publicabiready",
    "publicabiavailable",
    "publiccallbackabinow",
    "publiccapabilitybitsnow",
    "publicheaderallowed",
    "publicheadersymbolsnow",
    "publicsdkready",
    "publicsdkv1completionclaim",
    "runtimeenabled",
    "runtimeready",
    "stableclaimallowed",
    "v1completionevidence",
    "v1completionready",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--public-abi-preflight-candidate", type=Path, default=DEFAULT_PUBLIC_ABI_PREFLIGHT)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def normalized_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def truthy_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "ready", "allowed", "available", "enabled", "promoted"}
    if isinstance(value, list):
        return bool(value)
    return False


def collect_structured_overclaims(value: Any, path: str = "$") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if normalized_key(str(key)) in FORBIDDEN_STRUCTURED_CLAIM_KEYS and truthy_claim_value(item):
                claims.append({"path": item_path, "key": key, "value": item})
            claims.extend(collect_structured_overclaims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_structured_overclaims(item, f"{path}[{index}]"))
    return claims


def string_set(payload: dict[str, Any], key: str) -> set[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def require_strings(
    payload: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
) -> None:
    missing = sorted(required - string_set(payload, key))
    if missing:
        add(blockers, f"{key}_missing_required", f"$.{key}", missing=missing)


def section(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        add(blockers, f"{key}_missing", f"$.{key}")
        return {}
    return value


def validate_preflight(
    path: Path,
    public_header: Path,
    blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        preflight_payload = public_abi_preflight.load_json(path)
        private_payload = public_abi_preflight.private_layout.load_json(public_abi_preflight.DEFAULT_PRIVATE_LAYOUT)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        add(blockers, "public_abi_preflight_candidate_unreadable", "--public-abi-preflight-candidate", error=str(exc))
        return {}, {"accepted_for_candidate_review": False, "blockers": ["public_abi_preflight_candidate_unreadable"]}

    preflight_blockers: list[dict[str, Any]] = []
    header_scan = public_abi_preflight.scan_public_header(public_header, preflight_blockers)
    public_abi_preflight.validate_manifest(preflight_payload, private_payload, preflight_blockers)
    if preflight_blockers:
        add(
            blockers,
            "public_abi_preflight_candidate_not_accepted",
            "--public-abi-preflight-candidate",
            input_blockers=[blocker["reason"] for blocker in preflight_blockers],
        )
    return preflight_payload, {
        "accepted_for_candidate_review": not preflight_blockers,
        "blockers": [blocker["reason"] for blocker in preflight_blockers],
        "blocker_details": preflight_blockers,
        "public_header_scan": header_scan,
    }


def field_names(summary: dict[str, Any]) -> list[str]:
    fields = summary.get("fields")
    if not isinstance(fields, list):
        return []
    return [item for item in fields if isinstance(item, str)]


def validate_layout_summary(
    payload: dict[str, Any],
    preflight_payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    abi_layout = section(payload, "abi_layout", blockers)
    if not abi_layout:
        return
    if abi_layout.get("status") != "required_before_promotion":
        add(blockers, "abi_layout_status_mismatch", "$.abi_layout.status", value=abi_layout.get("status"))
    if abi_layout.get("public_symbols_allowed") is not False:
        add(
            blockers,
            "abi_layout_public_symbols_allowed_not_false",
            "$.abi_layout.public_symbols_allowed",
            value=abi_layout.get("public_symbols_allowed"),
        )
    require_strings(abi_layout, "required_checks", REQUIRED_ABI_LAYOUT_CHECKS, blockers)

    event = abi_layout.get("event_payload_summary")
    descriptor = abi_layout.get("descriptor_summary")
    if not isinstance(event, dict):
        add(blockers, "abi_layout_event_payload_summary_missing", "$.abi_layout.event_payload_summary")
        event = {}
    if not isinstance(descriptor, dict):
        add(blockers, "abi_layout_descriptor_summary_missing", "$.abi_layout.descriptor_summary")
        descriptor = {}
    expected_event = preflight_payload.get("event_payload") if isinstance(preflight_payload, dict) else {}
    expected_descriptor = preflight_payload.get("descriptor") if isinstance(preflight_payload, dict) else {}
    if (
        event.get("struct_size") != expected_event.get("struct_size")
        or event.get("alignment") != expected_event.get("alignment")
        or field_names(event) != field_names(expected_event)
    ):
        add(blockers, "abi_layout_event_payload_preflight_drift", "$.abi_layout.event_payload_summary")
    if (
        descriptor.get("struct_size") != expected_descriptor.get("struct_size")
        or descriptor.get("alignment") != expected_descriptor.get("alignment")
        or field_names(descriptor) != field_names(expected_descriptor)
    ):
        add(blockers, "abi_layout_descriptor_preflight_drift", "$.abi_layout.descriptor_summary")


def validate_manifest(payload: dict[str, Any], preflight_payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", value=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", value=payload.get("surface"))
    for key, expected in (
        ("artifact_status", "candidate_only"),
        ("visibility", "planning_contract"),
        ("status", "blocked"),
    ):
        if payload.get(key) != expected:
            add(blockers, f"{key}_mismatch", f"$.{key}", value=payload.get(key))
    for key in ("candidate_only", "accepted_for_candidate_review"):
        if payload.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.{key}", value=payload.get(key))
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
        "public_sdk_v1_completion_claim",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", value=payload.get(key))
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", value=payload.get(key))

    accepted_inputs = payload.get("accepted_inputs")
    if not isinstance(accepted_inputs, dict):
        add(blockers, "accepted_inputs_missing", "$.accepted_inputs")
    elif accepted_inputs.get(PUBLIC_ABI_PREFLIGHT_INPUT) is not True:
        add(blockers, "public_abi_preflight_input_not_true", f"$.accepted_inputs.{PUBLIC_ABI_PREFLIGHT_INPUT}")

    sources = payload.get("source_artifacts")
    if not isinstance(sources, dict):
        add(blockers, "source_artifacts_missing", "$.source_artifacts")
    elif sources.get("public_abi_preflight_candidate") != str(DEFAULT_PUBLIC_ABI_PREFLIGHT):
        add(
            blockers,
            "source_public_abi_preflight_candidate_mismatch",
            "$.source_artifacts.public_abi_preflight_candidate",
            value=sources.get("public_abi_preflight_candidate"),
        )

    require_strings(payload, "required_before_promotion", REQUIRED_BEFORE_PROMOTION, blockers)
    require_strings(payload, "does_not_resolve", REQUIRED_DOES_NOT_RESOLVE, blockers)
    require_strings(payload, "non_claims", REQUIRED_NON_CLAIMS, blockers)
    validate_layout_summary(payload, preflight_payload, blockers)

    sdk = section(payload, "sdk_consumer", blockers)
    if sdk:
        if sdk.get("status") != "required_before_promotion":
            add(blockers, "sdk_consumer_status_mismatch", "$.sdk_consumer.status", value=sdk.get("status"))
        if sdk.get("public_sdk_ready") is not False:
            add(blockers, "sdk_consumer_public_sdk_ready_not_false", "$.sdk_consumer.public_sdk_ready")
        require_strings(sdk, "required_checks", REQUIRED_SDK_CONSUMER_CHECKS, blockers)

    cleanup = section(payload, "lifecycle_owner_cleanup", blockers)
    if cleanup:
        if cleanup.get("status") != "required_before_promotion":
            add(
                blockers,
                "lifecycle_owner_cleanup_status_mismatch",
                "$.lifecycle_owner_cleanup.status",
                value=cleanup.get("status"),
            )
        if cleanup.get("registration_model") != "owner_token_handle":
            add(
                blockers,
                "lifecycle_owner_cleanup_registration_model_mismatch",
                "$.lifecycle_owner_cleanup.registration_model",
                value=cleanup.get("registration_model"),
            )
        require_strings(cleanup, "required_checks", REQUIRED_OWNER_CLEANUP_CHECKS, blockers)

    downstream = section(payload, "downstream_separation", blockers)
    if downstream:
        if downstream.get("status") != "blocked_until_player_identity_promoted":
            add(
                blockers,
                "downstream_separation_status_mismatch",
                "$.downstream_separation.status",
                value=downstream.get("status"),
            )
        if downstream.get("consumption_allowed_now") is not False:
            add(
                blockers,
                "downstream_separation_consumption_allowed_now_not_false",
                "$.downstream_separation.consumption_allowed_now",
                value=downstream.get("consumption_allowed_now"),
            )
        require_strings(downstream, "must_remain_blocked", REQUIRED_BLOCKED_DOWNSTREAM, blockers)
        require_strings(downstream, "required_checks", REQUIRED_DOWNSTREAM_CHECKS, blockers)

    nested_claims = [
        claim
        for claim in collect_structured_overclaims(
            {
                "abi_layout": payload.get("abi_layout"),
                "sdk_consumer": payload.get("sdk_consumer"),
                "lifecycle_owner_cleanup": payload.get("lifecycle_owner_cleanup"),
                "downstream_separation": payload.get("downstream_separation"),
            }
        )
    ]
    if nested_claims:
        add(
            blockers,
            "nested_public_runtime_or_completion_claims",
            "$",
            claims=nested_claims,
        )


def build_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    preflight_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "ready": not blockers,
        "valid": not blockers,
        "status": payload.get("status"),
        "candidate_only": payload.get("candidate_only") is True,
        "accepted_for_candidate_review": payload.get("accepted_for_candidate_review") is True and not blockers,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_claim": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "required_before_promotion": payload.get("required_before_promotion", []),
        "does_not_resolve": payload.get("does_not_resolve", []),
        "abi_layout": payload.get("abi_layout", {}),
        "sdk_consumer": payload.get("sdk_consumer", {}),
        "lifecycle_owner_cleanup": payload.get("lifecycle_owner_cleanup", {}),
        "downstream_separation": payload.get("downstream_separation", {}),
        "public_abi_preflight_candidate": preflight_report,
        "public_or_runtime_claims": [
            claim
            for detail in blockers
            if detail.get("reason") == "nested_public_runtime_or_completion_claims"
            for claim in detail.get("claims", [])
        ],
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": payload.get("non_claims", []),
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    try:
        payload = load_json(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"--manifest invalid: {exc}") from exc
    preflight_payload, preflight_report = validate_preflight(args.public_abi_preflight_candidate, args.public_header, blockers)
    validate_manifest(payload, preflight_payload, blockers)
    report = build_report(payload, blockers, preflight_report=preflight_report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("player identity owner-token SDK consumer contract: " + ("ok" if report["ready"] else "blocked"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
