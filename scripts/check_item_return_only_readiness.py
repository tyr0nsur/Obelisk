#!/usr/bin/env python3
"""Read-only readiness check for the internal item return-only lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path("/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z")
DEFAULT_MANIFEST_NAME = "item-return-only-policy-slice.json"
EXPECTED_MANIFEST_SHA256 = "53ac249aa107eb059ee420de8e939cc4117fb3590d651025a0bb6286625b1849"
REPORT_SCHEMA = "obelisk.item-return-only-readiness-check.v1"
POLICY_SCHEMA = "obelisk.item-return-only-policy-slice.v1"
INPUT_TARGET_SET = "item-compact-intake"
OUTPUT_TARGET_SET = "item-return-only-policy-slice"
EXPECTED_INPUT_TARGETS = {
    "PrimalItem.AllowEquipItem",
    "PrimalItem.CanRepair",
    "PrimalItem.CraftBlueprint",
    "PrimalItem.UseItemOntoItem",
}
EXPECTED_COPIED_TARGETS = {
    "PrimalItem.AllowEquipItem",
    "PrimalItem.CanRepair",
    "PrimalItem.UseItemOntoItem",
}
EXPECTED_COPIED_FIELDS = {
    "PrimalItem.AllowEquipItem.ReturnValue",
    "PrimalItem.CanRepair.ReturnValue",
    "PrimalItem.UseItemOntoItem.ReturnValue",
}
EXPECTED_EXCLUDED_FIELDS = {
    "PrimalItem.AllowEquipItem.toInventory",
    "PrimalItem.CanRepair.bIgnoreInventoryRequirement",
    "PrimalItem.CraftBlueprint.bConsumeResources",
    "PrimalItem.UseItemOntoItem.DestinationItem",
    "PrimalItem.UseItemOntoItem.AdditionalData",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "does not promote public SDK callbacks",
    "does not expose UE pointers",
    "does not copy CraftBlueprint",
)
FORBIDDEN_COPIED_RE = re.compile(
    r"(?:CraftBlueprint|toInventory|DestinationItem|AdditionalData|bIgnoreInventoryRequirement|"
    r"bConsumeResources|identity|lookup|mutation|object_refs|public_sdk|resource_handle|return_override|"
    r"runtime|ue_pointer)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate item return-only candidate readiness without promoting an Inventory/Items SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Item return-only policy-slice manifest. Defaults to --root/item-return-only-policy-slice.json.",
    )
    parser.add_argument(
        "--expected-manifest-sha256",
        default=EXPECTED_MANIFEST_SHA256,
        help="Expected direct manifest SHA256. Defaults to the reviewed durable artifact.",
    )
    parser.add_argument(
        "--skip-artifact-gates",
        action="store_true",
        help="Skip consume/promote gate subprocesses for hermetic policy-fixture tests.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def run_gate(root: Path, manifest: Path, mode: str) -> tuple[int, dict[str, Any] | None, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "validate_offline_artifact_gate.py"),
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--mode",
            mode,
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            payload = None
    return result.returncode, payload, result.stderr.strip()


def read_policy(manifest: Path, blockers: list[dict[str, Any]], expected_sha256: str) -> dict[str, Any] | None:
    try:
        content = manifest.read_bytes()
        manifest_sha256 = hashlib.sha256(content).hexdigest()
        parsed = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(manifest), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(manifest), detail=str(exc))
        return None
    if not isinstance(parsed, dict):
        append_blocker(blockers, "manifest_not_object", path=str(manifest))
        return None
    if manifest_sha256 != expected_sha256:
        append_blocker(blockers, "manifest_sha256_mismatch", expected=expected_sha256, value=manifest_sha256)
    return parsed


def require_set(blockers: list[dict[str, Any]], *, reason: str, actual: Any, expected: set[str]) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    if actual_set != expected:
        append_blocker(blockers, reason, missing=sorted(expected - actual_set), unexpected=sorted(actual_set - expected))
    return actual_set


def validate_return_bool_entries(
    policy: dict[str, Any], copied_fields: set[str], blockers: list[dict[str, Any]]
) -> None:
    entries = policy.get("copied_return_bools")
    if not isinstance(entries, list):
        append_blocker(blockers, "copied_return_bools_missing")
        return
    if len(entries) != 3:
        append_blocker(blockers, "copied_return_bool_count_mismatch", expected=3, value=len(entries))

    entry_fields: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "copied_return_bool_entry_not_object", index=index)
            continue
        copied_field = entry.get("copied_field")
        if isinstance(copied_field, str):
            entry_fields.add(copied_field)
        if copied_field not in copied_fields:
            append_blocker(blockers, "copied_return_bool_entry_field_unexpected", index=index, copied_field=copied_field)
        for key, expected in {
            "type": "bool",
            "field": "ReturnValue",
            "direction": "return",
            "property_class": None,
            "evidence_status": "copied-return-bool-only",
            "element_size": 1,
        }.items():
            if key == "property_class":
                continue
            if entry.get(key) != expected:
                append_blocker(
                    blockers,
                    "copied_return_bool_entry_metadata_mismatch",
                    index=index,
                    copied_field=copied_field,
                    field=key,
                    expected=expected,
                    value=entry.get(key),
                )
        bool_masks = entry.get("bool_masks")
        if not isinstance(bool_masks, dict):
            append_blocker(blockers, "copied_return_bool_masks_missing", index=index, copied_field=copied_field)
        else:
            if bool_masks.get("byte_mask") != "0x01":
                append_blocker(blockers, "copied_return_bool_mask_mismatch", index=index, field="byte_mask")
            if bool_masks.get("field_mask") != "0xff":
                append_blocker(blockers, "copied_return_bool_mask_mismatch", index=index, field="field_mask")
    if entry_fields != copied_fields:
        append_blocker(
            blockers,
            "copied_return_bool_entry_coverage_mismatch",
            missing=sorted(copied_fields - entry_fields),
            unexpected=sorted(entry_fields - copied_fields),
        )


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "coverage_missing")
        coverage = {}
    input_targets = require_set(
        blockers, reason="input_target_coverage_mismatch", actual=coverage.get("input_targets"), expected=EXPECTED_INPUT_TARGETS
    )
    copied_targets = require_set(
        blockers, reason="copied_target_coverage_mismatch", actual=coverage.get("copied_targets"), expected=EXPECTED_COPIED_TARGETS
    )
    copied_fields = require_set(
        blockers, reason="copied_field_coverage_mismatch", actual=coverage.get("copied_fields"), expected=EXPECTED_COPIED_FIELDS
    )
    excluded_fields = require_set(
        blockers, reason="excluded_field_coverage_mismatch", actual=coverage.get("excluded_fields"), expected=EXPECTED_EXCLUDED_FIELDS
    )
    if coverage.get("status") != "complete":
        append_blocker(blockers, "coverage_status_not_complete", value=coverage.get("status"))

    for copied_field in copied_fields:
        if FORBIDDEN_COPIED_RE.search(copied_field):
            append_blocker(blockers, "forbidden_copied_field", copied_field=copied_field)
    for forbidden_prefix in ("PrimalItem.CraftBlueprint.",):
        if any(field.startswith(forbidden_prefix) for field in copied_fields):
            append_blocker(blockers, "craftblueprint_copied_field_not_allowed")

    validate_return_bool_entries(policy, copied_fields, blockers)

    safety = policy.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    if safety.get("artifact_status") != "evidence_only":
        append_blocker(blockers, "safety_artifact_status_invalid", value=safety.get("artifact_status"))
    if safety.get("promotion_ready") is not False:
        append_blocker(blockers, "safety_promotion_ready_not_false", value=safety.get("promotion_ready"))
    if safety.get("intended_use") != "offline_review_only":
        append_blocker(blockers, "safety_intended_use_invalid", value=safety.get("intended_use"))
    if safety.get("copied_bool_count") != 3:
        append_blocker(blockers, "safety_copied_bool_count_mismatch", value=safety.get("copied_bool_count"))
    if safety.get("excluded_field_count") != 5:
        append_blocker(blockers, "safety_excluded_field_count_mismatch", value=safety.get("excluded_field_count"))

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)

    return {
        "input_targets": sorted(input_targets),
        "copied_targets": sorted(copied_targets),
        "copied_fields": sorted(copied_fields),
        "excluded_fields": sorted(excluded_fields),
        "copied_return_bool_count": len(policy.get("copied_return_bools", []))
        if isinstance(policy.get("copied_return_bools"), list)
        else 0,
    }


def build_report(
    root_arg: Path, manifest_arg: Path | None, expected_manifest_sha256: str, skip_artifact_gates: bool = False
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    root = safe_path(root_arg, "--root", blockers)
    manifest_path = manifest_arg if manifest_arg is not None else root_arg / DEFAULT_MANIFEST_NAME
    manifest = safe_path(manifest_path, "--manifest", blockers)

    summary: dict[str, Any] = {}
    consume_gate: dict[str, Any] = {"returncode": None, "status": None}
    promote_gate: dict[str, Any] = {"returncode": None, "status": None}
    if root is not None and manifest is not None:
        policy = read_policy(manifest, blockers, expected_manifest_sha256)
        if policy is not None:
            summary = validate_policy(policy, blockers)
        if skip_artifact_gates:
            consume_gate = {"returncode": None, "status": "skipped"}
            promote_gate = {"returncode": None, "status": "skipped", "blocker_reasons": []}
        else:
            consume_rc, consume_payload, consume_stderr = run_gate(root, manifest, "consume")
            consume_gate = {
                "returncode": consume_rc,
                "status": consume_payload.get("status") if isinstance(consume_payload, dict) else None,
                "stderr": consume_stderr,
            }
            if consume_rc != 0 or consume_gate["status"] != "accepted":
                append_blocker(blockers, "consume_gate_not_accepted", returncode=consume_rc, status=consume_gate["status"])
            promote_rc, promote_payload, promote_stderr = run_gate(root, manifest, "promote")
            promote_blockers = (
                promote_payload.get("blockers")
                if isinstance(promote_payload, dict) and isinstance(promote_payload.get("blockers"), list)
                else []
            )
            promote_reasons = sorted(
                blocker.get("reason")
                for blocker in promote_blockers
                if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str)
            )
            promote_gate = {
                "returncode": promote_rc,
                "status": promote_payload.get("status") if isinstance(promote_payload, dict) else None,
                "blocker_reasons": promote_reasons,
                "stderr": promote_stderr,
            }
            required_promote_reasons = {
                "promote_mode_item_return_policy_slice_evidence_only",
                "promote_mode_manifest_has_non_claims",
            }
            if promote_rc == 0 or promote_gate["status"] != "blocked":
                append_blocker(blockers, "promote_gate_not_blocked", returncode=promote_rc, status=promote_gate["status"])
            if not required_promote_reasons.issubset(set(promote_reasons)):
                append_blocker(
                    blockers,
                    "promote_gate_missing_required_blockers",
                    missing=sorted(required_promote_reasons - set(promote_reasons)),
                )

    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "not_artifact_gate": True,
        "public_inventory_sdk_ready": False,
        "public_items_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        "root": str(root if root is not None else root_arg),
        "manifest": str(manifest if manifest is not None else manifest_path),
        "expected_manifest_sha256": expected_manifest_sha256,
        "consume_gate": consume_gate,
        "promote_gate": promote_gate,
        "summary": summary,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "does not promote Inventory SDK, Items SDK, item identity, inventory identity, lookup, mutation, return override, ResourceHandle, runtime hooks, or public module callbacks",
            "does not replace public ABI, SDK consumer, lifecycle, privacy, second-source, or live-ops promotion gates",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.manifest, args.expected_manifest_sha256, args.skip_artifact_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
