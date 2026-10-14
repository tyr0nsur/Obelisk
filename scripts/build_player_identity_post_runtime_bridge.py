#!/usr/bin/env python3
"""Build the offline post-runtime player-identity bridge artifacts.

This combines the already accepted runtime evidence into the next local artifacts:
a reviewed identity public-contract decision record, a hash-bound player-identity
promotion certificate, and an optional public SDK surfaces copy. The report is
non-authorizing and does not claim SDK, runtime, stable, P0, publication, or Plugin Hub
readiness.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import build_player_identity_promotion_certificate as certificate_builder
import build_player_identity_public_contract_decision_record as decision_builder
import build_player_identity_runtime_principal_lifecycle_evidence_bundle as bundle_builder
import check_permissions_admin_public_readiness as permissions_readiness
import check_player_identity_public_contract_decision_record as decision_checker
import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "obelisk.player-identity-post-runtime-bridge-build-report.v1"
STRICT_APPROVED_RUNTIME_CHECKER = (
    Path(__file__).resolve().with_name(
        "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
    )
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
)
DEFAULT_DECISION_NAME = "reviewed-identity-public-contract-decision-record.json"
DEFAULT_CERTIFICATE_NAME = "player-identity-promotion-certificate.json"
DEFAULT_SURFACES_NAME = "public-sdk-surfaces.with-player-identity-certificate.json"
NON_CLAIM = (
    "offline post-runtime player-identity bridge build only; does not authorize live "
    "operations, runtime capture, public header/API/ABI, runtime readiness, public SDK "
    "readiness, SDK/P0 progress, stable SDK claims, Plugin Hub, publication, or v1 "
    "completion"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--evidence-dir",
        type=Path,
        help="Copied live-validation evidence dir with approved-bundle outputs.",
    )
    source.add_argument(
        "--approved-runtime-bundle-dir",
        type=Path,
        help=(
            "Directory containing approved-runtime-principal-lifecycle-evidence.json "
            "and approved-runtime-principal-lifecycle-evidence.check.json."
        ),
    )
    source.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        help="Accepted approved runtime lifecycle evidence manifest JSON.",
    )
    parser.add_argument(
        "--strict-approved-runtime-check-report",
        type=Path,
        help=(
            "Strict consume-mode approved-runtime checker report. Required with "
            "--approved-runtime-evidence; derived from --evidence-dir otherwise."
        ),
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=certificate_builder.SURFACES,
        help="Base public SDK surfaces manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Repo-local output directory for generated bridge artifacts.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a build report JSON.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return certificate_builder.sha256_file(path)


def artifact(path: Path, *, schema: str | None = None) -> dict[str, str]:
    payload = {"path": str(path), "sha256": sha256_file(path)}
    if schema is not None:
        payload["schema"] = schema
    return payload


def safe_input_file(path: Path, label: str) -> Path:
    return decision_builder.safe_input_file(path, label)


def repo_local_output_dir(path: Path) -> Path:
    protected_paths.reject_symlink_component(path, "--output-dir")
    resolved_parent = protected_paths.reject_protected_output_path(
        path.expanduser().parent,
        "--output-dir parent",
    )
    resolved_parent.mkdir(parents=True, exist_ok=True)
    resolved = protected_paths.reject_protected_output_path(path, "--output-dir")
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise SystemExit(
            "--output-dir must be under the Obelisk repo root so generated certificate "
            f"bindings can use repo-relative paths: {resolved}"
        ) from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def load_json(path: Path, label: str) -> dict[str, Any]:
    return decision_builder.load_json_file(path, label)


def compact_value(value: Any) -> str:
    rendered = repr(value)
    if len(rendered) > 120:
        return rendered[:117] + "..."
    return rendered


def json_mismatches(expected: Any, actual: Any, *, path: str = "$", limit: int = 8) -> list[str]:
    if limit <= 0 or expected == actual:
        return []
    if type(expected) is not type(actual):
        return [
            f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"
        ]
    if isinstance(expected, dict):
        mismatches: list[str] = []
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            mismatches.append(f"{path}.{key}: missing from supplied report")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(actual_keys - expected_keys):
            mismatches.append(f"{path}.{key}: unexpected in supplied report")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(expected_keys & actual_keys):
            mismatches.extend(
                json_mismatches(
                    expected[key],
                    actual[key],
                    path=f"{path}.{key}",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if isinstance(expected, list):
        mismatches = []
        if len(expected) != len(actual):
            mismatches.append(
                f"{path}: expected list length {len(expected)}, got {len(actual)}"
            )
            if len(mismatches) >= limit:
                return mismatches
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            mismatches.extend(
                json_mismatches(
                    expected_item,
                    actual_item,
                    path=f"{path}[{index}]",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    return [
        f"{path}: expected {compact_value(expected)}, got {compact_value(actual)}"
    ]


def strict_checker_report_for(approved_runtime_path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(STRICT_APPROVED_RUNTIME_CHECKER),
            "--json",
            str(approved_runtime_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(
            "approved runtime evidence failed strict checker replay: "
            + (detail or f"exit code {result.returncode}")
        )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "strict approved runtime checker replay did not emit valid JSON"
        ) from exc
    if not isinstance(report, dict):
        raise SystemExit("strict approved runtime checker replay did not emit an object")
    return report


def validate_strict_report_replay(
    *,
    approved_runtime_path: Path,
    strict_report_path: Path,
) -> dict[str, Any]:
    supplied_report = load_json(
        strict_report_path,
        "--strict-approved-runtime-check-report",
    )
    if supplied_report.get("schema") != STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA:
        raise SystemExit(
            "--strict-approved-runtime-check-report schema mismatch: "
            f"expected {STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA}, "
            f"got {supplied_report.get('schema')}"
        )
    expected_report = strict_checker_report_for(approved_runtime_path)
    mismatches = json_mismatches(expected_report, supplied_report)
    if mismatches:
        raise SystemExit(
            "--strict-approved-runtime-check-report is stale or not bound to "
            "--approved-runtime-evidence: "
            + "; ".join(mismatches)
        )
    return supplied_report


def approved_runtime_artifact_identity(approved_runtime: dict[str, Any]) -> dict[str, Any]:
    identity = approved_runtime.get("output_artifact_identity")
    if not isinstance(identity, dict):
        raise SystemExit(
            "--approved-runtime-evidence missing output_artifact_identity binding"
        )
    return identity


def validate_decision_record_bridge_binding(
    *,
    approved_runtime: dict[str, Any],
    strict_report: dict[str, Any],
    strict_report_path: Path,
    decision_record: dict[str, Any],
) -> None:
    identity = approved_runtime_artifact_identity(approved_runtime)
    binding = decision_record.get("approved_runtime_evidence_binding")
    if not isinstance(binding, dict):
        raise SystemExit(
            "generated decision record missing approved_runtime_evidence_binding"
        )
    expected_binding = decision_checker.approved_runtime_evidence_binding_from_manifest(
        approved_runtime
    )
    binding_mismatches = json_mismatches(
        expected_binding,
        binding,
        path="$.approved_runtime_evidence_binding",
    )
    if binding_mismatches:
        raise SystemExit(
            "generated decision record approved runtime evidence binding mismatch: "
            + "; ".join(binding_mismatches)
        )
    for field in ("artifact_kind", "artifact_sha256", "evidence_pack_id"):
        if binding.get(field) != identity.get(field):
            raise SystemExit(
                "generated decision record approved runtime evidence binding mismatch: "
                f"{field} expected {compact_value(identity.get(field))}, "
                f"got {compact_value(binding.get(field))}"
            )

    strict_ref = decision_record.get("strict_approved_runtime_checker_contract_report")
    if not isinstance(strict_ref, dict):
        raise SystemExit(
            "generated decision record missing strict approved runtime checker report binding"
        )
    strict_path = strict_ref.get("path")
    if strict_path != str(strict_report_path):
        raise SystemExit(
            "generated decision record strict checker report path mismatch: "
            f"expected {strict_report_path}, got {strict_path}"
        )
    if strict_ref.get("sha256") != sha256_file(strict_report_path):
        raise SystemExit(
            "generated decision record strict checker report hash mismatch"
        )
    if strict_ref.get("required_report_schema") != strict_report.get("schema"):
        raise SystemExit(
            "generated decision record strict checker report schema binding mismatch"
        )


CERTIFICATE_DECISION_SUMMARY_FIELDS = (
    "schema",
    "artifact_id",
    "surface",
    "review_status",
    "accepted_for_contract_review",
    "active_after_resolved_input",
    "resolved_decision_keys",
    "public_contract_allowed",
    "public_header_allowed",
    "public_api_ready",
    "public_abi_ready",
    "public_sdk_ready",
    "runtime_ready",
    "server_operations_authorized",
    "runtime_capture_authorized",
    "workspace_writes_authorized",
    "live_ops_authorized",
    "commands_ready",
    "lookup_ready",
    "permissions_ready",
    "promotion_ready",
    "v1_completion_evidence",
)


def validate_certificate_decision_bridge_binding(
    *,
    decision_record: dict[str, Any],
    certificate: dict[str, Any],
) -> None:
    evidence = certificate.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("generated player identity certificate missing evidence object")
    summary = evidence.get("identity_public_contract_decision_record")
    if not isinstance(summary, dict):
        raise SystemExit(
            "generated player identity certificate missing decision record summary"
        )
    for field in CERTIFICATE_DECISION_SUMMARY_FIELDS:
        if field not in summary:
            raise SystemExit(
                "generated player identity certificate decision record summary missing "
                f"{field}"
            )
        if summary.get(field) != decision_record.get(field):
            raise SystemExit(
                "generated player identity certificate decision record summary mismatch: "
                f"{field} expected {compact_value(decision_record.get(field))}, "
                f"got {compact_value(summary.get(field))}"
            )


def validate_certificate_decision_record_artifact_binding(
    *,
    decision_record: dict[str, Any],
    decision_record_path: Path,
    certificate: dict[str, Any],
) -> None:
    evidence = certificate.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("generated player identity certificate missing evidence object")
    artifact = evidence.get("identity_public_contract_decision_record_artifact")
    if not isinstance(artifact, dict):
        raise SystemExit(
            "generated player identity certificate missing full decision record "
            "artifact binding"
        )
    expected_artifact = certificate_builder.decision_record_artifact_binding(
        decision_record=decision_record,
        decision_record_path=decision_record_path,
    )
    mismatches = json_mismatches(
        expected_artifact,
        artifact,
        path="$.evidence.identity_public_contract_decision_record_artifact",
    )
    if mismatches:
        raise SystemExit(
            "generated player identity certificate full decision record artifact "
            "binding mismatch: "
            + "; ".join(mismatches)
        )
    expected_payload_sha256 = expected_artifact["canonical_payload_sha256"]
    if (
        evidence.get("identity_public_contract_decision_record_payload_sha256")
        != expected_payload_sha256
    ):
        raise SystemExit(
            "generated player identity certificate full decision record payload "
            "hash mismatch"
        )


def validate_certificate_decision_runtime_binding(
    *,
    approved_runtime: dict[str, Any],
    decision_record: dict[str, Any],
    certificate: dict[str, Any],
) -> None:
    evidence = certificate.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("generated player identity certificate missing evidence object")
    binding_digest = evidence.get(
        "identity_public_contract_decision_record_runtime_binding"
    )
    if not isinstance(binding_digest, dict):
        raise SystemExit(
            "generated player identity certificate missing decision record runtime "
            "binding digest"
        )
    expected_digest = certificate_builder.validate_decision_record_runtime_binding(
        decision_record=decision_record,
        approved_runtime_evidence=approved_runtime,
    )
    mismatches = json_mismatches(expected_digest, binding_digest)
    if mismatches:
        raise SystemExit(
            "generated player identity certificate decision record runtime binding "
            "digest mismatch: "
            + "; ".join(mismatches)
        )
    certificate_builder.validate_post_runtime_bridge_constraints(
        certificate,
        label="$.player_identity_certificate",
    )
    certificate_builder.validate_post_runtime_bridge_constraints(
        evidence,
        label="$.player_identity_certificate.evidence",
    )


def validate_generated_bridge_bindings(
    *,
    approved_runtime_path: Path,
    strict_report_path: Path,
    decision_record_path: Path,
    decision_record: dict[str, Any],
    certificate: dict[str, Any],
) -> dict[str, bool]:
    approved_runtime = load_json(
        approved_runtime_path,
        "--approved-runtime-evidence",
    )
    strict_report = load_json(
        strict_report_path,
        "--strict-approved-runtime-check-report",
    )
    decision_builder.validate_strict_report_bound_to_manifest(
        supplied_report=strict_report,
        approved_runtime_evidence=approved_runtime,
        approved_runtime_path=approved_runtime_path,
    )
    validate_decision_record_bridge_binding(
        approved_runtime=approved_runtime,
        strict_report=strict_report,
        strict_report_path=strict_report_path,
        decision_record=decision_record,
    )
    certificate_builder.validate_decision_record_runtime_manifest_ref(
        decision_record=decision_record,
        approved_runtime_path=approved_runtime_path,
    )
    validate_certificate_decision_bridge_binding(
        decision_record=decision_record,
        certificate=certificate,
    )
    validate_certificate_decision_record_artifact_binding(
        decision_record=decision_record,
        decision_record_path=decision_record_path,
        certificate=certificate,
    )
    validate_certificate_decision_runtime_binding(
        approved_runtime=approved_runtime,
        decision_record=decision_record,
        certificate=certificate,
    )
    return {
        "strict_report_replayed": True,
        "decision_record_bound_to_approved_runtime_evidence": True,
        "decision_record_accepted_for_contract_review": True,
        "decision_record_bound_to_strict_report": True,
        "certificate_bound_to_decision_record_summary": True,
        "certificate_bound_to_full_decision_record_artifact": True,
        "certificate_bound_to_decision_record_approved_runtime_binding": True,
        "certificate_post_runtime_bridge_constraints": True,
    }


def evidence_dir_paths(evidence_dir: Path) -> tuple[Path, Path]:
    approved_bundle_dir = evidence_dir / "approved-bundle"
    approved_bundle = approved_bundle_dir / "approved-runtime-principal-lifecycle-evidence.json"
    strict_report = (
        approved_bundle_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
    )
    if approved_bundle.is_file() and strict_report.is_file():
        return (
            safe_input_file(approved_bundle, "--evidence-dir approved runtime evidence"),
            safe_input_file(
                strict_report,
                "--evidence-dir strict approved runtime check report",
            ),
        )

    report = bundle_builder.classify_preflight_evidence_dir(evidence_dir)
    if report.get("approved_runtime_evidence_present") is not True:
        blockers = report.get("blockers", [])
        detail = ", ".join(str(blocker) for blocker in blockers[:8])
        raise SystemExit(
            "--evidence-dir must already contain checker-accepted approved runtime "
            f"evidence: {detail}"
        )
    approved_bundle = Path(str(report.get("approved_bundle_path", "")))
    strict_report = approved_bundle.with_suffix(".check.json")
    return (
        safe_input_file(approved_bundle, "--evidence-dir approved runtime evidence"),
        safe_input_file(strict_report, "--evidence-dir strict approved runtime check report"),
    )


def approved_runtime_bundle_dir_paths(bundle_dir: Path) -> tuple[Path, Path]:
    protected_paths.reject_symlink_component(bundle_dir, "--approved-runtime-bundle-dir")
    manifest = bundle_dir / "approved-runtime-principal-lifecycle-evidence.json"
    strict_report = bundle_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
    return (
        safe_input_file(manifest, "--approved-runtime-bundle-dir approved runtime evidence"),
        safe_input_file(strict_report, "--approved-runtime-bundle-dir strict approved runtime check report"),
    )


def resolve_runtime_inputs(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.evidence_dir is not None:
        if args.strict_approved_runtime_check_report is not None:
            raise SystemExit(
                "--strict-approved-runtime-check-report is derived from --evidence-dir"
            )
        return evidence_dir_paths(args.evidence_dir)
    if args.approved_runtime_bundle_dir is not None:
        if args.strict_approved_runtime_check_report is not None:
            raise SystemExit(
                "--strict-approved-runtime-check-report is derived from --approved-runtime-bundle-dir"
            )
        return approved_runtime_bundle_dir_paths(args.approved_runtime_bundle_dir)
    if args.strict_approved_runtime_check_report is None:
        raise SystemExit(
            "--strict-approved-runtime-check-report is required with --approved-runtime-evidence"
        )
    return (
        safe_input_file(args.approved_runtime_evidence, "--approved-runtime-evidence"),
        safe_input_file(
            args.strict_approved_runtime_check_report,
            "--strict-approved-runtime-check-report",
        ),
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_decision_record(
    *,
    approved_runtime_path: Path,
    strict_report_path: Path,
    output: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    approved_runtime = load_json(approved_runtime_path, "--approved-runtime-evidence")
    if approved_runtime.get("schema") != decision_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND:
        raise SystemExit(
            "--approved-runtime-evidence schema mismatch: "
            f"expected {decision_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND}, "
            f"got {approved_runtime.get('schema')}"
        )
    strict_report = load_json(
        strict_report_path,
        "--strict-approved-runtime-check-report",
    )
    base_record = load_json(REPO_ROOT / decision_checker.DEFAULT_RECORD, "--base-record")
    record = decision_builder.build_record(
        base_record=base_record,
        approved_runtime_evidence=approved_runtime,
        approved_runtime_path=approved_runtime_path,
        strict_report_path=strict_report_path,
    )
    validation_report = decision_builder.validate_generated_record(record)
    validate_decision_record_bridge_binding(
        approved_runtime=approved_runtime,
        strict_report=strict_report,
        strict_report_path=strict_report_path,
        decision_record=record,
    )
    write_json(output, record)
    return record, validation_report


def build_certificate_and_surfaces(
    *,
    approved_runtime_path: Path,
    decision_record: dict[str, Any],
    decision_record_path: Path,
    surfaces_path: Path,
    certificate_path: Path,
    output_surfaces: Path,
) -> tuple[dict[str, str], list[dict[str, Any]], dict[str, Any]]:
    surfaces = load_json(surfaces_path, "--public-sdk-surfaces")
    approved_runtime = load_json(approved_runtime_path, "--approved-runtime-evidence")
    certificate_builder.validate_decision_record(decision_record)
    promoted_surfaces, identity_surface = certificate_builder.promote_identity_surface_for_certificate(
        surfaces=surfaces,
        approved_runtime_evidence=approved_runtime,
    )
    certificate = certificate_builder.build_certificate(
        identity_surface=identity_surface,
        approved_runtime_evidence=approved_runtime,
        approved_runtime_path=approved_runtime_path,
        decision_record=decision_record,
        decision_record_path=decision_record_path,
    )
    validate_certificate_decision_bridge_binding(
        decision_record=decision_record,
        certificate=certificate,
    )
    write_json(certificate_path, certificate)
    binding = certificate_builder.repo_relative_binding(certificate_path)
    identity_surface.setdefault("evidence", {})["player_identity_promotion_certificate"] = binding
    binding_valid, binding_blockers = certificate_builder.validate_certificate_binding(identity_surface)
    if not binding_valid:
        raise SystemExit(
            "generated player identity promotion certificate failed validation: "
            + ", ".join(blocker["reason"] for blocker in binding_blockers[:8])
        )
    write_json(output_surfaces, promoted_surfaces)
    return binding, binding_blockers, certificate


def main() -> int:
    args = parse_args()
    approved_runtime_path, strict_report_path = resolve_runtime_inputs(args)
    validate_strict_report_replay(
        approved_runtime_path=approved_runtime_path,
        strict_report_path=strict_report_path,
    )
    output_dir = repo_local_output_dir(args.output_dir)
    surfaces_path = safe_input_file(args.public_sdk_surfaces, "--public-sdk-surfaces")
    decision_record_path = output_dir / DEFAULT_DECISION_NAME
    certificate_path = output_dir / DEFAULT_CERTIFICATE_NAME
    output_surfaces_path = output_dir / DEFAULT_SURFACES_NAME

    decision_record, decision_validation = build_decision_record(
        approved_runtime_path=approved_runtime_path,
        strict_report_path=strict_report_path,
        output=decision_record_path,
    )
    certificate_binding, certificate_blockers, certificate = build_certificate_and_surfaces(
        approved_runtime_path=approved_runtime_path,
        decision_record=decision_record,
        decision_record_path=decision_record_path,
        surfaces_path=surfaces_path,
        certificate_path=certificate_path,
        output_surfaces=output_surfaces_path,
    )
    bridge_binding_checks = validate_generated_bridge_bindings(
        approved_runtime_path=approved_runtime_path,
        strict_report_path=strict_report_path,
        decision_record_path=decision_record_path,
        decision_record=decision_record,
        certificate=certificate,
    )

    report = {
        "schema": REPORT_SCHEMA,
        "status": "built",
        "source": {
            "approved_runtime_evidence": artifact(
                approved_runtime_path,
                schema=decision_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
            ),
            "strict_approved_runtime_check_report": artifact(strict_report_path),
        },
        "generated_artifacts": {
            "decision_record": artifact(
                decision_record_path,
                schema=decision_checker.SCHEMA,
            ),
            "player_identity_certificate": artifact(
                certificate_path,
                schema=permissions_readiness.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
            ),
            "surfaces": artifact(output_surfaces_path),
        },
        "certificate_binding": certificate_binding,
        "certificate_binding_blocker_count": len(certificate_blockers),
        "bridge_binding_checks": bridge_binding_checks,
        "ready": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "stable_claim_allowed": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "non_claim": NON_CLAIM,
        "post_runtime_bridge_constraints": (
            certificate_builder.post_runtime_bridge_constraints()
        ),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
