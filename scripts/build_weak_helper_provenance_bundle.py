#!/usr/bin/env python3
"""Archive weak-helper static provenance artifacts into a reproducible bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import (  # noqa: E402
    REPO_ROOT,
    SERVER_ROOT,
    SHA256_RE,
    is_approved_offline_workspace_path,
    is_relative_to,
    reject_protected_input_path,
    reject_protected_output_path,
    require_ignored_output_path,
    safe_component,
    sha256_file,
)
from build_core_dump_evidence_pack import detect_obelisk_commit  # noqa: E402


BUNDLE_SCHEMA = "obelisk.weak-helper-provenance-bundle.v1"
BUNDLE_ARTIFACT_PROVENANCE_SCHEMA = "obelisk.weak-helper-bundled-artifact-provenance.v1"
PRODUCER = Path(__file__).name
PATH_KEYS = {
    "artifact",
    "binary",
    "copied_to",
    "file",
    "path",
    "source",
    "stderr",
    "stdout",
}


def parse_label_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must be LABEL=PATH")
    label, raw_path = value.split("=", 1)
    label = safe_component(label.strip(), "artifact label")
    if not raw_path.strip():
        raise argparse.ArgumentTypeError("artifact path must not be empty")
    return label, Path(raw_path)


def key_names_path(value: object) -> bool:
    normalized = str(value).casefold()
    return normalized in PATH_KEYS or normalized.endswith("_path") or normalized.endswith("_file")


def protected_path_detail(path: Path, *, base_dir: Path | None = None) -> str | None:
    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() or base_dir is None else base_dir / expanded
    if candidate.is_absolute() and is_relative_to(candidate, SERVER_ROOT) and not is_approved_offline_workspace_path(candidate):
        return str(candidate)
    resolved = candidate.resolve()
    if is_relative_to(resolved, SERVER_ROOT) and not is_approved_offline_workspace_path(candidate):
        return str(resolved)
    return None


def find_protected_path(value: object, *, base_dir: Path, trail: str = "provenance_sidecar") -> dict[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if isinstance(child, str) and key_names_path(key):
                detail = protected_path_detail(Path(child), base_dir=base_dir)
                if detail is not None:
                    return {"field": child_trail, "path": detail}
            elif isinstance(child, (dict, list)):
                found = find_protected_path(child, base_dir=base_dir, trail=child_trail)
                if found is not None:
                    return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_protected_path(child, base_dir=base_dir, trail=f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str):
        detail = protected_path_detail(Path(value), base_dir=base_dir)
        if detail is not None:
            return {"field": trail, "path": detail}
    return None


def invalid_provenance(path: Path, reason: str, **details: object) -> dict[str, object]:
    return {"path": str(path), "verified": False, "reason": reason, **details}


def validate_source_provenance(
    *,
    provenance_path: Path,
    artifact_sha256: str,
    binary_sha256: str,
) -> dict[str, object]:
    try:
        payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return invalid_provenance(provenance_path, "malformed_provenance_sidecar")
    except OSError as exc:
        return invalid_provenance(provenance_path, "unreadable_provenance_sidecar", detail=str(exc))
    if not isinstance(payload, dict):
        return invalid_provenance(
            provenance_path,
            "provenance_sidecar_not_object",
            recorded_type=type(payload).__name__,
        )
    protected = find_protected_path(payload, base_dir=provenance_path.parent)
    if protected is not None:
        return invalid_provenance(
            provenance_path,
            "protected_path_in_provenance_sidecar",
            source_provenance_field=protected["field"],
            protected_path=protected["path"],
        )
    if payload.get("verified") is not True:
        return invalid_provenance(provenance_path, "provenance_sidecar_not_verified")
    recorded_binary_sha = payload.get("binary_sha256")
    if recorded_binary_sha != binary_sha256:
        return invalid_provenance(
            provenance_path,
            "provenance_binary_sha256_mismatch",
            expected_binary_sha256=binary_sha256,
            recorded_binary_sha256=recorded_binary_sha,
        )
    recorded_artifact_sha = payload.get("artifact_sha256")
    if recorded_artifact_sha != artifact_sha256:
        return invalid_provenance(
            provenance_path,
            "provenance_artifact_sha256_mismatch",
            expected_artifact_sha256=artifact_sha256,
            recorded_artifact_sha256=recorded_artifact_sha,
        )
    return {
        "path": str(provenance_path),
        "verified": True,
        "schema": payload.get("schema"),
        "producer": payload.get("producer"),
        "tool": payload.get("tool"),
        "command": payload.get("command"),
        "binary_sha256": recorded_binary_sha,
        "artifact_sha256": recorded_artifact_sha,
    }


def artifact_filename(label: str, source: Path) -> str:
    suffix = "".join(source.suffixes)
    return f"{label}{suffix}" if suffix else label


def reject_artifact_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing to overwrite symlinked bundle artifact: {path}")


def write_json(path: Path, payload: dict[str, object]) -> None:
    reject_artifact_symlink(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def artifact_blockers(artifacts: list[dict[str, object]]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for artifact in artifacts:
        provenance = artifact.get("source_provenance")
        if not isinstance(provenance, dict) or provenance.get("verified") is not True:
            blockers.append(
                {
                    "reason": "unverified_source_provenance",
                    "artifact": artifact.get("label"),
                    "detail": provenance.get("reason") if isinstance(provenance, dict) else "missing_provenance_record",
                }
            )
    return blockers


def build_artifact_record(
    *,
    label: str,
    source: Path,
    output_dir: Path,
    binary_sha256: str,
) -> dict[str, object]:
    resolved_source = reject_protected_input_path(source, f"--artifact {label}")
    source_sha256 = sha256_file(resolved_source)
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    copied_to = artifacts_dir / artifact_filename(label, resolved_source)
    reject_artifact_symlink(copied_to)
    shutil.copyfile(resolved_source, copied_to)
    copied_sha256 = sha256_file(copied_to)

    source_provenance_path = Path(f"{resolved_source}.provenance.json")
    source_provenance: dict[str, object] = {
        "path": str(source_provenance_path),
        "verified": False,
        "reason": "missing_provenance_sidecar",
    }
    if source_provenance_path.exists() or source_provenance_path.is_symlink():
        resolved_provenance = reject_protected_input_path(source_provenance_path, f"--artifact {label} provenance")
        source_provenance = validate_source_provenance(
            provenance_path=resolved_provenance,
            artifact_sha256=source_sha256,
            binary_sha256=binary_sha256,
        )

    output_provenance = {
        "schema": BUNDLE_ARTIFACT_PROVENANCE_SCHEMA,
        "verified": bool(source_provenance.get("verified")),
        "producer": PRODUCER,
        "binary_sha256": binary_sha256,
        "artifact_sha256": copied_sha256,
        "source_artifact_sha256": source_sha256,
        "source_provenance": source_provenance,
    }
    output_provenance_path = Path(f"{copied_to}.provenance.json")
    write_json(output_provenance_path, output_provenance)

    return {
        "label": label,
        "source": str(resolved_source),
        "source_sha256": source_sha256,
        "copied_to": str(copied_to),
        "copied_sha256": copied_sha256,
        "output_provenance": str(output_provenance_path),
        "source_provenance": source_provenance,
    }


def build_bundle(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = reject_protected_output_path(args.output_dir, "--output-dir")
    require_ignored_output_path(output_dir, "--output-dir")
    if output_dir.exists() and output_dir.is_symlink():
        raise SystemExit(f"--output-dir must not be a symlink: {output_dir}")

    binary = reject_protected_input_path(args.binary, "--binary")
    binary_sha256 = sha256_file(binary)
    output_dir.mkdir(parents=True, exist_ok=True)

    seen_labels: set[str] = set()
    artifacts: list[dict[str, object]] = []
    for label, source in args.artifact:
        if label in seen_labels:
            raise SystemExit(f"duplicate artifact label: {label}")
        seen_labels.add(label)
        artifacts.append(
            build_artifact_record(
                label=label,
                source=source,
                output_dir=output_dir,
                binary_sha256=binary_sha256,
            )
        )

    blockers = artifact_blockers(artifacts)
    promotion_ready = not blockers
    manifest: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "obelisk_commit": detect_obelisk_commit(REPO_ROOT),
        "producer": PRODUCER,
        "bundle_kind": "weak_helper_provenance_archive",
        "binary": {
            "path": str(binary),
            "sha256": binary_sha256,
        },
        "artifacts": artifacts,
        "promotion_ready": promotion_ready,
        "promotion_gate": {
            "ready": promotion_ready,
            "blockers": blockers,
        },
        "non_claims": [
            "Archival provenance bundle only; it does not promote public ResourceHandle semantics.",
            "Does not expose UObject pointers, object indices, serials, names, outers, or GObjects offsets.",
            "Does not authorize runtime probes, live-server validation, mutation, or return override.",
        ],
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def validate_bundle_manifest(path: Path) -> dict[str, object]:
    manifest_path = reject_protected_input_path(path, "--validate")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[dict[str, object]] = []
    if not isinstance(payload, dict):
        raise SystemExit(f"{manifest_path}: bundle manifest must be a JSON object")
    if payload.get("schema") != BUNDLE_SCHEMA:
        errors.append(
            {
                "reason": "bundle_schema_mismatch",
                "expected_schema": BUNDLE_SCHEMA,
                "recorded_schema": payload.get("schema"),
            }
        )
    binary = payload.get("binary")
    binary_sha256 = binary.get("sha256") if isinstance(binary, dict) else None
    if not isinstance(binary_sha256, str) or SHA256_RE.fullmatch(binary_sha256) is None:
        errors.append({"reason": "invalid_binary_sha256", "recorded_binary_sha256": binary_sha256})

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append({"reason": "missing_artifacts"})
        artifacts = []

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append({"reason": "artifact_not_object", "index": index})
            continue
        copied_to = artifact.get("copied_to")
        copied_sha256 = artifact.get("copied_sha256")
        output_provenance = artifact.get("output_provenance")
        if not isinstance(copied_to, str) or not copied_to:
            errors.append({"reason": "artifact_missing_copied_to", "index": index})
            continue
        artifact_path = reject_protected_input_path(Path(copied_to), f"{manifest_path}: artifacts[{index}].copied_to")
        actual_sha256 = sha256_file(artifact_path)
        if actual_sha256 != copied_sha256:
            errors.append(
                {
                    "reason": "artifact_sha256_mismatch",
                    "artifact": artifact.get("label"),
                    "expected_sha256": copied_sha256,
                    "actual_sha256": actual_sha256,
                }
            )
        if not isinstance(output_provenance, str) or not output_provenance:
            errors.append({"reason": "artifact_missing_output_provenance", "artifact": artifact.get("label")})
            continue
        provenance_path = reject_protected_input_path(
            Path(output_provenance),
            f"{manifest_path}: artifacts[{index}].output_provenance",
        )
        try:
            provenance_payload = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append({"reason": "malformed_output_provenance", "artifact": artifact.get("label")})
            continue
        if not isinstance(provenance_payload, dict):
            errors.append({"reason": "output_provenance_not_object", "artifact": artifact.get("label")})
            continue
        if provenance_payload.get("schema") != BUNDLE_ARTIFACT_PROVENANCE_SCHEMA:
            errors.append({"reason": "output_provenance_schema_mismatch", "artifact": artifact.get("label")})
        if provenance_payload.get("artifact_sha256") != actual_sha256:
            errors.append({"reason": "output_provenance_artifact_sha256_mismatch", "artifact": artifact.get("label")})
        if isinstance(binary_sha256, str) and provenance_payload.get("binary_sha256") != binary_sha256:
            errors.append({"reason": "output_provenance_binary_sha256_mismatch", "artifact": artifact.get("label")})

    recorded_ready = payload.get("promotion_ready")
    blockers = artifact_blockers([artifact for artifact in artifacts if isinstance(artifact, dict)])
    expected_ready = not blockers
    if recorded_ready is not expected_ready:
        errors.append(
            {
                "reason": "promotion_ready_mismatch",
                "recorded_promotion_ready": recorded_ready,
                "expected_promotion_ready": expected_ready,
            }
        )
    return {
        "schema": BUNDLE_SCHEMA,
        "manifest": str(manifest_path),
        "valid": not errors,
        "promotion_ready": expected_ready,
        "blockers": blockers,
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--binary", type=Path, help="Copied/offline ShooterGameServer path.")
    mode.add_argument("--validate", type=Path, help="Validate an existing weak-helper bundle manifest.")
    parser.add_argument("--output-dir", type=Path, help="Directory for the archival bundle.")
    parser.add_argument(
        "--artifact",
        action="append",
        type=parse_label_path,
        default=[],
        metavar="LABEL=PATH",
        help="Weak-helper provenance artifact to archive. Repeat for each copied artifact.",
    )
    parser.add_argument("--json", action="store_true", help="Print the manifest or validation result as JSON.")
    args = parser.parse_args()
    if args.binary:
        if args.output_dir is None:
            raise SystemExit("--output-dir is required in build mode")
        if not args.artifact:
            raise SystemExit("at least one --artifact is required in build mode")
    else:
        if args.output_dir is not None or args.artifact:
            raise SystemExit("--validate mode does not accept --output-dir or --artifact")
    return args


def main() -> int:
    args = parse_args()
    if args.validate:
        result = validate_bundle_manifest(args.validate)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["valid"] else 1
    manifest = build_bundle(args)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
