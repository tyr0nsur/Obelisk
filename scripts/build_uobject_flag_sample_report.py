#!/usr/bin/env python3
"""Build a redacted candidate-only UObject flag sample report from static artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import SHA256_RE, reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.uobject-flag-sample-report.v1"
TRANSITION_MATRIX_SCHEMA = "obelisk.uobject-flag-transition-matrix.v1"
POLICY_REPORT_SCHEMA = "obelisk.uobject-flag-policy-report.v1"
SUPPORTED_INPUT_SCHEMAS = {TRANSITION_MATRIX_SCHEMA, POLICY_REPORT_SCHEMA}
CONSUME_GATE_SCHEMA = "obelisk.offline-artifact-gate-result.v1"
REQUIRED_MASKS = ("0x100", "0x4000", "0x8000")
NON_CLAIMS = (
    "does_not_promote_resourcehandle",
    "does_not_claim_post_callback_lookup",
    "does_not_assign_public_lifecycle_flag_names",
    "does_not_claim_mutation_or_return_override_safety",
)
REMAINING_BLOCKERS = (
    "static_only_evidence",
    "no_runtime_object_samples",
    "no_rejected_runtime_object_samples",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} does not exist") from exc
    except OSError as exc:
        raise SystemExit(f"{label} is unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return payload


def consume_gate_record(
    path: Path,
    *,
    source_schema: str,
    source_artifact_sha256: str,
    source_binary_sha256: str,
) -> dict[str, Any]:
    payload = load_json(path, "consume gate")
    blockers: list[str] = []
    if payload.get("schema") != CONSUME_GATE_SCHEMA:
        blockers.append("consume_gate_schema_mismatch")
    if payload.get("status") != "accepted":
        blockers.append("consume_gate_status_not_accepted")
    if payload.get("mode") != "consume":
        blockers.append("consume_gate_mode_not_consume")
    gate_blockers = payload.get("blockers")
    if gate_blockers != []:
        blockers.append("consume_gate_has_blockers")
    if payload.get("binary_sha256") != source_binary_sha256:
        blockers.append("consume_gate_binary_sha256_mismatch")

    manifests = payload.get("manifests")
    matching_manifest = None
    if isinstance(manifests, list):
        for manifest in manifests:
            if (
                isinstance(manifest, dict)
                and manifest.get("schema") == source_schema
                and manifest.get("sha256") == source_artifact_sha256
            ):
                matching_manifest = manifest
                break
    if matching_manifest is None:
        blockers.append("consume_gate_artifact_sha256_mismatch")

    if blockers:
        raise SystemExit(f"consume gate incomplete for {source_schema}: {','.join(blockers)}")
    return {
        "schema": CONSUME_GATE_SCHEMA,
        "status": "accepted",
        "mode": "consume",
        "gate_sha256": sha256_file(path),
        "artifact_sha256": source_artifact_sha256,
        "binary_sha256": source_binary_sha256,
        "blocker_count": 0,
        "path_redacted": True,
    }


def source_record(path: Path, payload: dict[str, Any], consume_gate_path: Path) -> dict[str, Any]:
    schema = payload.get("schema")
    if schema not in SUPPORTED_INPUT_SCHEMAS:
        raise SystemExit(f"unsupported input schema: {schema}")
    if payload.get("status") != "candidate_blocked":
        raise SystemExit(f"{schema} input must have status=candidate_blocked")
    if payload.get("promotion_ready") is True:
        raise SystemExit(f"{schema} input must not be promotion_ready")
    binary = payload.get("binary")
    if not isinstance(binary, dict) or binary.get("path_redacted") is not True:
        raise SystemExit(f"{schema} input must redact binary path")
    binary_sha256 = binary.get("sha256")
    if not isinstance(binary_sha256, str) or SHA256_RE.fullmatch(binary_sha256) is None:
        raise SystemExit(f"{schema} input must include binary.sha256")
    artifact_sha256 = sha256_file(path)
    return {
        "schema": schema,
        "artifact_sha256": artifact_sha256,
        "binary_sha256": binary_sha256,
        "path_redacted": True,
        "consume_gate": consume_gate_record(
            reject_protected_input_path(consume_gate_path, "--consume-gate"),
            source_schema=schema,
            source_artifact_sha256=artifact_sha256,
            source_binary_sha256=binary_sha256,
        ),
    }


def collect_matrix_samples(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    samples: dict[str, dict[str, Any]] = {}
    matrix = payload.get("transition_matrix")
    if not isinstance(matrix, dict):
        return samples
    for mask, entry in matrix.items():
        if mask not in REQUIRED_MASKS or not isinstance(entry, dict):
            continue
        samples[mask] = {
            "mask": mask,
            "uobject_field": entry.get("uobject_field", "+0x8"),
            "sample_kind": "static_transition_candidate",
            "public_lifecycle_name_assigned": entry.get("public_lifecycle_name_assigned") is True,
            "promotion_ready": entry.get("promotion_ready") is True,
            "support": sorted(set(entry.get("predicate_windows", []) + entry.get("mutation_windows", []))),
        }
    return samples


def merge_policy_support(samples: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    candidates = payload.get("policy_candidates")
    if not isinstance(candidates, list):
        return
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        mask = candidate.get("mask")
        if mask not in REQUIRED_MASKS:
            continue
        sample = samples.setdefault(
            mask,
            {
                "mask": mask,
                "uobject_field": "+0x8",
                "sample_kind": "static_policy_candidate",
                "public_lifecycle_name_assigned": False,
                "promotion_ready": False,
                "support": [],
            },
        )
        had_transition_support = sample.get("sample_kind") == "static_transition_candidate"
        support = set(sample.get("support", []))
        support.update(str(item) for item in candidate.get("support", []) if isinstance(item, str))
        sample["support"] = sorted(support)
        sample["sample_kind"] = "static_policy_and_transition_candidate" if had_transition_support else "static_policy_candidate"
        if candidate.get("ue_lifecycle_name") not in (None, "not_promoted"):
            sample["public_lifecycle_name_assigned"] = True


def build_report(inputs: list[Path], consume_gates: list[Path]) -> dict[str, Any]:
    if not inputs:
        raise SystemExit("at least one --input is required")
    if len(consume_gates) != len(inputs):
        raise SystemExit("--consume-gate count must match --input count")

    sources: list[dict[str, Any]] = []
    samples: dict[str, dict[str, Any]] = {}
    binary_sha256: str | None = None
    for index, raw_path in enumerate(inputs):
        path = reject_protected_input_path(raw_path, f"--input[{index}]")
        payload = load_json(path, f"--input[{index}]")
        record = source_record(path, payload, consume_gates[index])
        if binary_sha256 is None:
            binary_sha256 = record["binary_sha256"]
        elif binary_sha256 != record["binary_sha256"]:
            raise SystemExit("all inputs must use the same binary.sha256")
        sources.append(record)
        samples.update(collect_matrix_samples(payload))
        merge_policy_support(samples, payload)

    missing = sorted(set(REQUIRED_MASKS).difference(samples))
    if missing:
        raise SystemExit(f"missing required masks: {','.join(missing)}")
    source_schemas = {source["schema"] for source in sources}
    if source_schemas != SUPPORTED_INPUT_SCHEMAS:
        missing_schemas = ",".join(sorted(SUPPORTED_INPUT_SCHEMAS.difference(source_schemas)))
        raise SystemExit(f"missing required source schema coverage: {missing_schemas}")
    for mask, sample in samples.items():
        if sample.get("promotion_ready") is True:
            raise SystemExit(f"{mask} sample must not be promotion_ready")
        if sample.get("public_lifecycle_name_assigned") is True:
            raise SystemExit(f"{mask} sample must not assign public lifecycle names")

    return {
        "schema": SCHEMA,
        "status": "candidate_blocked",
        "promotion_ready": False,
        "resource_handle_claim": False,
        "post_callback_resource_handle_ready": False,
        "binary": {"sha256": binary_sha256, "path_redacted": True},
        "source_artifacts": sources,
        "flag_samples": [samples[mask] for mask in REQUIRED_MASKS],
        "non_claims": list(NON_CLAIMS),
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "redaction": {
            "paths": "redacted",
            "raw_snippets": "omitted",
            "addresses": "omitted_or_source_artifact_only",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--consume-gate", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    report = build_report(args.input, args.consume_gate)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
