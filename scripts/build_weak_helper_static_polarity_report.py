#!/usr/bin/env python3
"""Build a redacted candidate-only weak-helper static polarity report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.weak-helper-static-polarity-report.v1"
EVIDENCE_KIND = "static_weak_helper_polarity_candidate"
PROVENANCE_SCHEMAS = {
    "obelisk.offline-artifact-provenance.v1",
    "obelisk.static-artifact-provenance.v1",
    "obelisk.weak-helper-bundled-artifact-provenance.v1",
}
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
PATH_KEY_RE = re.compile(r"(?:^|_)(path|file|source|artifact|binary|core|stdout|stderr|copied_to)$")

NON_CLAIMS = (
    "does_not_unlock_resource_handle",
    "does_not_promote_post_callback_lookup",
    "does_not_assign_public_lifecycle_names",
    "does_not_claim_lookup_safety",
    "does_not_claim_mutation_or_return_override_safety",
)

REMAINING_BLOCKERS = (
    "static_only_evidence",
    "no_runtime_negative_samples",
    "no_second_source_lifecycle_semantics",
    "no_public_lifecycle_names",
    "no_public_resource_handle_contract",
    "no_post_callback_lifetime_contract",
    "no_lookup_contract",
    "no_mutation_contract",
    "no_return_override_contract",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_count(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise SystemExit(f"{path} is unreadable: {exc}") from exc


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


def parse_artifact(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--artifact must be LABEL=PATH")
    raw_label, raw_path = value.split("=", 1)
    label = raw_label.strip()
    if LABEL_RE.fullmatch(label) is None:
        raise argparse.ArgumentTypeError(f"unsafe artifact label: {label}")
    if not raw_path:
        raise argparse.ArgumentTypeError("--artifact path must not be empty")
    return label, Path(raw_path)


def key_names_path(key: object) -> bool:
    text = str(key).casefold()
    return bool(PATH_KEY_RE.search(text)) or text.endswith("_path") or text.endswith("_file")


def collect_path_fields(value: object, *, trail: str = "$", path_context: bool = False) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            child_path_context = key_names_path(key)
            if isinstance(child, str) and child_path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=child_path_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            if isinstance(child, str) and path_context:
                found.append((child_trail, child))
            elif isinstance(child, (dict, list)):
                found.extend(collect_path_fields(child, trail=child_trail, path_context=path_context))
    return found


def validate_provenance(
    path: Path,
    *,
    label: str,
    binary_sha256: str,
    artifact_sha256: str,
) -> dict[str, Any]:
    provenance_path = reject_protected_input_path(
        path.with_name(path.name + ".provenance.json"),
        f"--artifact {label} provenance",
    )
    payload = load_json(provenance_path, f"--artifact {label} provenance")
    blockers: list[str] = []
    if payload.get("schema") not in PROVENANCE_SCHEMAS:
        blockers.append("provenance_schema_mismatch")
    if payload.get("verified") is not True:
        blockers.append("provenance_not_verified")
    if payload.get("binary_sha256") != binary_sha256:
        blockers.append("provenance_binary_sha256_mismatch")
    if payload.get("artifact_sha256") != artifact_sha256:
        blockers.append("provenance_artifact_sha256_mismatch")
    for trail, raw_path in collect_path_fields(payload):
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = provenance_path.parent / candidate
        try:
            reject_protected_input_path(candidate, f"--artifact {label} provenance {trail}")
        except SystemExit:
            blockers.append(f"provenance_protected_path_field:{trail}")
    if blockers:
        raise SystemExit(f"--artifact {label} provenance incomplete: {','.join(blockers)}")
    return {
        "schema": payload.get("schema"),
        "verified": True,
        "binary_sha256": binary_sha256,
        "artifact_sha256": artifact_sha256,
        "sidecar_sha256": sha256_file(provenance_path),
        "path_redacted": True,
    }


def summarize_artifacts(artifacts: list[tuple[str, Path]], *, binary_sha256: str) -> dict[str, dict[str, Any]]:
    if not artifacts:
        raise SystemExit("at least one --artifact is required")

    seen: set[str] = set()
    summaries: dict[str, dict[str, Any]] = {}
    for label, raw_path in artifacts:
        if label in seen:
            raise SystemExit(f"duplicate --artifact label: {label}")
        seen.add(label)
        path = reject_protected_input_path(raw_path, f"--artifact {label}")
        try:
            artifact_sha256 = sha256_file(path)
        except FileNotFoundError as exc:
            raise SystemExit(f"--artifact {label} does not exist") from exc
        except OSError as exc:
            raise SystemExit(f"--artifact {label} is unreadable: {exc}") from exc
        summaries[label] = {
            "sha256": artifact_sha256,
            "bytes": byte_count(path),
            "path_redacted": True,
            "provenance": validate_provenance(
                path,
                label=label,
                binary_sha256=binary_sha256,
                artifact_sha256=artifact_sha256,
            ),
        }
    return summaries


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    binary = reject_protected_input_path(args.binary, "--binary")
    try:
        binary_sha256 = sha256_file(binary)
    except FileNotFoundError as exc:
        raise SystemExit("--binary does not exist") from exc
    except OSError as exc:
        raise SystemExit(f"--binary is unreadable: {exc}") from exc

    artifact_summaries = summarize_artifacts(args.artifact or [], binary_sha256=binary_sha256)
    source_pack_label = args.source_pack or next(iter(artifact_summaries))
    source_pack = artifact_summaries.get(source_pack_label)
    if source_pack is None:
        raise SystemExit(f"--source-pack must match an --artifact label: {source_pack_label}")
    return {
        "schema": SCHEMA,
        "evidence_kind": EVIDENCE_KIND,
        "status": "candidate_blocked",
        "promotion_ready": False,
        "binary": {
            "sha256": binary_sha256,
            "byte_count": byte_count(binary),
            "path_redacted": True,
        },
        "builder_contract": {
            "input_kind": "provenance_gated_static_artifact_paths",
            "fail_closed": True,
            "requires_live_server": False,
            "candidate_only": True,
            "promotion_ready": False,
            "resource_handle_claim": False,
            "public_lifecycle_names_assigned": False,
            "lookup_promotion": False,
            "mutation_promotion": False,
            "return_override_promotion": False,
            "raw_snippets_included": False,
        },
        "source_pack": {"id": source_pack_label, **source_pack},
        "inputs": artifact_summaries,
        "static_polarity_summary": {
            "candidate": "weak_helper_flag_polarity_static_only",
            "promotion_ready": False,
            "semantic_names": "not_promoted",
            "raw_snippets": "omitted",
        },
        "non_claims": list(NON_CLAIMS),
        "remaining_blockers": list(REMAINING_BLOCKERS),
        "redaction": {
            "paths": "redacted",
            "raw_snippets": "omitted",
            "public_lifecycle_names": "omitted",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--artifact", action="append", type=parse_artifact, default=[], metavar="LABEL=PATH")
    parser.add_argument(
        "--source-pack",
        help="Artifact label to summarize as source_pack. Defaults to the first --artifact.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output")
    payload = build_payload(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
