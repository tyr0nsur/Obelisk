#!/usr/bin/env python3
"""Read-only readiness check for the internal Mission copied-bool lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import validate_offline_artifact_gate as offline_gate
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z"
)
DEFAULT_MANIFEST_NAME = "mission-copied-bool-policy-slice.json"
EXPECTED_MANIFEST_SHA256 = "f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945"
REPORT_SCHEMA = "obelisk.mission-copied-bool-readiness-check.v1"
POLICY_SCHEMA = "obelisk.mission-copied-bool-policy-slice.v1"
INPUT_TARGET_SET = "mission-compact-intake"
OUTPUT_TARGET_SET = "mission-copied-bool-policy-slice"
EXPECTED_INPUT_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
    "MissionType.GetPlayerUsableItems",
}
EXPECTED_COPIED_TARGETS = {
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
}
EXPECTED_COPIED_FIELDS = {
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
}
EXPECTED_REDACTED_FIELDS = {
    "MissionType.AddPlayerToMission.PlayerCharacter",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
    "MissionType.BPOnPlayerRemovedFromMission.Player",
    "MissionType.BPOnPlayerRemovedFromMission.Controller",
    "MissionType.GetPlayerUsableItems.Character",
    "MissionType.GetPlayerUsableItems.OutItemIDs",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "does not expose UE pointers",
    "does not promote public SDK callbacks",
    "does not promote runtime hook wiring",
    "does not copy player/controller/character object refs",
)
FORBIDDEN_COPIED_RE = re.compile(
    r"(?:PlayerCharacter|PlayerPawn|Controller|OutItemIDs|GetPlayerUsableItems|identity|"
    r"lookup|mutation|object_refs|public_sdk|resource_handle|return_override|runtime|ue_pointer)",
    re.IGNORECASE,
)
FORBIDDEN_TRUE_READY_KEYS = {
    "dispatcher_ready",
    "mission_payload_decoding_ready",
    "mission_sdk_ready",
    "mutation_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_mission_sdk_ready",
    "public_sdk_ready",
    "return_override_ready",
    "runtime_hook_ready",
    "runtime_hooks_ready",
    "runtime_ready",
    "v1_complete",
    "v1_completion",
    "v1_ready",
} | offline_gate.MISSION_COPIED_BOOL_FORBIDDEN_TRUE_READY_KEYS
ALLOWED_OVERCLAIM_TEXT_PREFIXES = ("$.non_claims", "$.safety_summary.explicitly_excluded")
MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES = {
    "abi ready": "public_abi",
    "allows mutation": "mutation",
    "allows return override": "return_override",
    "authority promoted": "authority",
    "authority ready": "authority",
    "authoritative identity": "authority_identity",
    "c abi ready": "public_abi",
    "hook wiring ready": "runtime_hooks",
    "identity promoted": "identity",
    "identity ready": "identity",
    "mission authority": "authority",
    "mission identity": "identity",
    "mission sdk": "mission_sdk",
    "mutation enabled": "mutation",
    "mutation path": "mutation",
    "mutation ready": "mutation",
    "mutation supported": "mutation",
    "object identity": "identity",
    "player authority": "authority",
    "player identity": "identity",
    "public abi": "public_abi",
    "return override enabled": "return_override",
    "return override ready": "return_override",
    "return override supported": "return_override",
    "return overrides": "return_override",
    "runtime hook ready": "runtime_hooks",
    "runtime hooks enabled": "runtime_hooks",
    "runtime hooks ready": "runtime_hooks",
    "v1 complete": "v1_completion",
    "v1 completion": "v1_completion",
    "v1 done": "v1_completion",
    "v1 ready": "v1_completion",
    "version 1 complete": "v1_completion",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Mission copied-bool candidate readiness without promoting a public SDK."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Offline artifact root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Mission copied-bool policy-slice manifest. Defaults to --root/mission-copied-bool-policy-slice.json.",
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
        append_blocker(
            blockers,
            "manifest_sha256_mismatch",
            expected=expected_sha256,
            value=manifest_sha256,
        )
    return parsed


def require_set(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    actual: Any,
    expected: set[str],
) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    if actual_set != expected:
        append_blocker(
            blockers,
            reason,
            missing=sorted(expected - actual_set),
            unexpected=sorted(actual_set - expected),
        )
    return actual_set


def validate_generated_from(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    generated_from = policy.get("generated_from")
    if not isinstance(generated_from, dict):
        append_blocker(blockers, "generated_from_missing")
        return {}
    if generated_from.get("snapshot_schema") != "obelisk.ufunction-chain.snapshot.v1":
        append_blocker(blockers, "snapshot_schema_mismatch", value=generated_from.get("snapshot_schema"))
    snapshots = generated_from.get("input_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 4:
        append_blocker(
            blockers,
            "input_snapshot_count_mismatch",
            expected=4,
            value=len(snapshots) if isinstance(snapshots, list) else None,
        )
        return {}

    sources: dict[str, dict[str, str]] = {}
    targets: set[str] = set()
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            append_blocker(blockers, "input_snapshot_entry_invalid", index=index)
            continue
        snapshot_id = snapshot.get("id")
        snapshot_sha256 = snapshot.get("sha256")
        target = snapshot.get("target")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            append_blocker(blockers, "input_snapshot_id_invalid", index=index)
            continue
        if snapshot_id in sources:
            append_blocker(blockers, "input_snapshot_id_duplicate", index=index, snapshot_id=snapshot_id)
        if not isinstance(snapshot_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256):
            append_blocker(blockers, "input_snapshot_sha256_invalid", index=index, snapshot_id=snapshot_id)
            continue
        if not isinstance(target, str) or target not in EXPECTED_INPUT_TARGETS:
            append_blocker(blockers, "input_snapshot_target_invalid", index=index, snapshot_id=snapshot_id, target=target)
            continue
        sources[snapshot_id] = {"sha256": snapshot_sha256, "target": target}
        targets.add(target)
    if targets != EXPECTED_INPUT_TARGETS:
        append_blocker(
            blockers,
            "input_snapshot_targets_mismatch",
            missing=sorted(EXPECTED_INPUT_TARGETS - targets),
            unexpected=sorted(targets - EXPECTED_INPUT_TARGETS),
        )
    return sources


def validate_source_snapshot(
    entry: dict[str, Any],
    *,
    index: int,
    field_key: str,
    reason_prefix: str,
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    source_snapshot = entry.get("source_snapshot")
    source_snapshot_sha256 = entry.get("source_snapshot_sha256")
    if not isinstance(source_snapshot, str) or source_snapshot not in sources:
        append_blocker(blockers, f"{reason_prefix}_source_snapshot_unknown", index=index, field=entry.get(field_key))
        return
    source = sources[source_snapshot]
    if source_snapshot_sha256 != source["sha256"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_sha256_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["sha256"],
            value=source_snapshot_sha256,
        )
    if entry.get("target") != source["target"]:
        append_blocker(
            blockers,
            f"{reason_prefix}_source_snapshot_target_mismatch",
            index=index,
            field=entry.get(field_key),
            expected=source["target"],
            value=entry.get("target"),
        )


def validate_copied_bool_entries(
    policy: dict[str, Any],
    copied_fields: set[str],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("copied_bools")
    if not isinstance(entries, list):
        append_blocker(blockers, "copied_bools_missing")
        return
    if len(entries) != 5:
        append_blocker(blockers, "copied_bool_count_mismatch", expected=5, value=len(entries))

    entry_fields: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "copied_bool_entry_not_object", index=index)
            continue
        copied_field = entry.get("copied_field")
        if isinstance(copied_field, str):
            entry_fields.add(copied_field)
        if copied_field not in copied_fields:
            append_blocker(blockers, "copied_bool_entry_field_unexpected", index=index, copied_field=copied_field)
        required_values = {
            "type": "bool",
            "property_class": "BoolProperty",
            "evidence_status": "copied-mission-bool-only",
            "bool_field_size": 1,
            "bool_byte_offset": 0,
            "byte_mask": "0x01",
            "field_mask": "0xff",
            "native_bool": False,
        }
        for key, expected in required_values.items():
            if entry.get(key) != expected:
                append_blocker(
                    blockers,
                    "copied_bool_entry_metadata_mismatch",
                    index=index,
                    copied_field=copied_field,
                    field=key,
                    expected=expected,
                    value=entry.get(key),
                )
        validate_source_snapshot(
            entry,
            index=index,
            field_key="copied_field",
            reason_prefix="copied_bool_entry",
            sources=sources,
            blockers=blockers,
        )
    if entry_fields != copied_fields:
        append_blocker(
            blockers,
            "copied_bool_entry_coverage_mismatch",
            missing=sorted(copied_fields - entry_fields),
            unexpected=sorted(entry_fields - copied_fields),
        )


def validate_redacted_source_entries(
    policy: dict[str, Any],
    sources: dict[str, dict[str, str]],
    blockers: list[dict[str, Any]],
) -> None:
    entries = policy.get("redacted_mission_fields")
    if not isinstance(entries, list):
        append_blocker(blockers, "redacted_mission_fields_missing")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            append_blocker(blockers, "redacted_mission_field_entry_not_object", index=index)
            continue
        validate_source_snapshot(
            entry,
            index=index,
            field_key="redacted_field",
            reason_prefix="redacted_mission_field",
            sources=sources,
            blockers=blockers,
        )


def validate_internal_only_boundaries(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    gate_blockers = offline_gate.validate_mission_copied_bool_policy_slice_manifest(
        policy,
        label="mission-copied-bool-readiness",
        mode="consume",
    )
    for blocker in gate_blockers:
        if not isinstance(blocker, dict):
            append_blocker(blockers, "offline_artifact_gate_blocker_unparseable", value=blocker)
            continue
        reason = blocker.get("reason")
        append_blocker(
            blockers,
            reason if isinstance(reason, str) else "offline_artifact_gate_blocker_missing_reason",
            source="offline_artifact_gate",
            label=blocker.get("label"),
            expected=blocker.get("expected"),
            recorded=blocker.get("recorded"),
        )

    for trail, _ in offline_gate.collect_ready_overclaims(policy):
        append_blocker(blockers, "readiness_overclaim", field=trail)
    for trail, value in offline_gate.collect_bool_fields(policy):
        key = trail.rsplit(".", 1)[-1]
        if key == "not_artifact_gate" and value is False:
            append_blocker(blockers, "not_artifact_gate_contradiction", field=trail)
        if key == "consume_only" and value is False:
            append_blocker(blockers, "consume_only_not_true", field=trail)
        if value is True and key in FORBIDDEN_TRUE_READY_KEYS:
            append_blocker(blockers, "runtime_public_readiness_overclaim", field=trail)
    for trail, _, reason in offline_gate.collect_candidate_public_overclaims(
        policy,
        allowed_prefixes=ALLOWED_OVERCLAIM_TEXT_PREFIXES,
    ):
        append_blocker(blockers, "runtime_public_claim_overclaim", field=trail, claim=reason)
    for trail, raw_value in offline_gate.collect_string_fields(policy):
        if any(trail.startswith(prefix) for prefix in ALLOWED_OVERCLAIM_TEXT_PREFIXES):
            continue
        text = raw_value.casefold()
        for needle, reason in MISSION_CANDIDATE_FORBIDDEN_CLAIM_PHRASES.items():
            if needle in text:
                append_blocker(blockers, "mission_candidate_claim_overclaim", field=trail, claim=reason)


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        append_blocker(blockers, "schema_mismatch", value=policy.get("schema"))
    if policy.get("input_target_set") != INPUT_TARGET_SET:
        append_blocker(blockers, "input_target_set_mismatch", value=policy.get("input_target_set"))
    if policy.get("output_target_set") != OUTPUT_TARGET_SET:
        append_blocker(blockers, "output_target_set_mismatch", value=policy.get("output_target_set"))
    if policy.get("policy_status") != "evidence-only":
        append_blocker(blockers, "policy_status_not_evidence_only", value=policy.get("policy_status"))
    if policy.get("snapshot_root") != "redacted":
        append_blocker(blockers, "snapshot_root_not_redacted", value=policy.get("snapshot_root"))
    if policy.get("missing_targets") != []:
        append_blocker(blockers, "missing_targets_present", value=policy.get("missing_targets"))

    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "coverage_missing")
        coverage = {}
    input_targets = require_set(
        blockers,
        reason="input_target_coverage_mismatch",
        actual=coverage.get("input_targets"),
        expected=EXPECTED_INPUT_TARGETS,
    )
    copied_targets = require_set(
        blockers,
        reason="copied_target_coverage_mismatch",
        actual=coverage.get("copied_targets"),
        expected=EXPECTED_COPIED_TARGETS,
    )
    copied_fields = require_set(
        blockers,
        reason="copied_field_coverage_mismatch",
        actual=coverage.get("copied_fields"),
        expected=EXPECTED_COPIED_FIELDS,
    )
    redacted_fields = require_set(
        blockers,
        reason="redacted_field_coverage_mismatch",
        actual=coverage.get("redacted_fields"),
        expected=EXPECTED_REDACTED_FIELDS,
    )
    if coverage.get("status") != "complete":
        append_blocker(blockers, "coverage_status_not_complete", value=coverage.get("status"))

    for copied_field in copied_fields:
        if FORBIDDEN_COPIED_RE.search(copied_field):
            append_blocker(blockers, "forbidden_copied_field", copied_field=copied_field)

    if "MissionType.GetPlayerUsableItems" in copied_targets:
        append_blocker(blockers, "get_player_usable_items_copied_target_not_allowed")
    if any(field.startswith("MissionType.GetPlayerUsableItems.") for field in copied_fields):
        append_blocker(blockers, "get_player_usable_items_copied_field_not_allowed")

    sources = validate_generated_from(policy, blockers)
    validate_copied_bool_entries(policy, copied_fields, sources, blockers)
    validate_redacted_source_entries(policy, sources, blockers)

    safety_summary = policy.get("safety_summary")
    if not isinstance(safety_summary, dict):
        append_blocker(blockers, "safety_summary_missing")
    else:
        required_safety = {
            "artifact_status": "evidence_only",
            "intended_use": "offline_review_only",
            "promotion_ready": False,
            "copied_bool_count": len(EXPECTED_COPIED_FIELDS),
            "redacted_field_count": len(EXPECTED_REDACTED_FIELDS),
        }
        for key, expected in required_safety.items():
            if safety_summary.get(key) != expected:
                append_blocker(
                    blockers,
                    "safety_summary_mismatch",
                    field=key,
                    expected=expected,
                    value=safety_summary.get(key),
                )

    non_claims = policy.get("non_claims")
    if not isinstance(non_claims, list):
        append_blocker(blockers, "non_claims_missing")
        non_claims_text = ""
    else:
        non_claims_text = "\n".join(str(item) for item in non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)

    validate_internal_only_boundaries(policy, blockers)

    return {
        "input_targets": sorted(input_targets),
        "copied_targets": sorted(copied_targets),
        "copied_fields": sorted(copied_fields),
        "redacted_fields": sorted(redacted_fields),
        "copied_bool_count": len(policy.get("copied_bools", [])) if isinstance(policy.get("copied_bools"), list) else 0,
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
                "promote_mode_mission_copied_bool_policy_slice_evidence_only",
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
        "public_sdk_ready": False,
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
            "does not promote Mission SDK, runtime Mission callbacks, mission identity, player identity, lookup, arrays, mutation, return override, or ResourceHandle",
            "does not replace owner-token API, plugin cleanup, SDK consumer, public ABI, lifecycle, privacy, or live-ops promotion gates",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.root, args.manifest, args.expected_manifest_sha256, args.skip_artifact_gates)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
