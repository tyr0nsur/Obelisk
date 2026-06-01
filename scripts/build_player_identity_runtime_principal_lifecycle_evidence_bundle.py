#!/usr/bin/env python3
"""Build the offline approved player-principal lifecycle evidence bundle.

This helper starts from an already copied/sanitized Obelisk log. It does not read live
server logs, does not start servers, and does not promote public player identity.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_output_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
WINDOW_MANIFEST_CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
OFFLINE_GATE = SCRIPT_DIR / "validate_offline_artifact_gate.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copied-log", required=True, type=Path, help="Copied/sanitized Obelisk log.")
    parser.add_argument("--window-manifest", required=True, type=Path, help="Approved operational window manifest.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Bundle output directory.")
    parser.add_argument("--obelisk-commit", required=True, help="Reviewed Obelisk commit recorded in evidence.")
    parser.add_argument("--reviewed-by", required=True, help="Reviewer token/name for the approved manifest.")
    parser.add_argument("--review-note", required=True, help="Short consume-only review note.")
    return parser.parse_args()


def run_command(command: list[str], *, stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    if stdout_path is None:
        return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with stdout_path.open("w", encoding="utf-8") as stdout:
        result = subprocess.run(command, check=False, text=True, stdout=stdout, stderr=subprocess.PIPE)
    if result.returncode != 0 and not result.stderr.strip():
        try:
            result.stderr = stdout_path.read_text(encoding="utf-8")
        except OSError:
            pass
    return result


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise SystemExit(f"{label} failed with exit {result.returncode}: {stderr}")


def require_expected_failure(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        raise SystemExit(f"{label} unexpectedly passed; evidence bundle overclaims readiness")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def require_window_matches_summary(window: dict[str, Any], summary: dict[str, Any], copied_log: Path) -> None:
    if window.get("schema") != "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1":
        raise SystemExit("window manifest check schema mismatch")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        raise SystemExit("window manifest check is not ready")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        raise SystemExit("window manifest check missing copied_log")
    window_path = Path(str(copied.get("path", ""))).expanduser().resolve()
    requested_path = copied_log.expanduser().resolve()
    if window_path != requested_path:
        raise SystemExit("window manifest copied_log.path does not match --copied-log")
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("runtime observer summary missing evidence.sources[0]")
    source = sources[0]
    source_path = Path(str(source.get("path", ""))).expanduser().resolve()
    if source_path != requested_path:
        raise SystemExit("runtime observer summary source path does not match --copied-log")
    if copied.get("sha256") != source.get("sha256"):
        raise SystemExit("window manifest copied_log.sha256 does not match runtime observer summary")
    evidence_commit = evidence.get("obelisk_commit") if isinstance(evidence, dict) else None
    if window.get("obelisk_commit") != evidence_commit:
        raise SystemExit("window manifest obelisk_commit does not match runtime observer summary")
    modules = summary.get("modules")
    principal = modules.get("player_principal_lifecycle") if isinstance(modules, dict) else None
    functions = principal.get("functions") if isinstance(principal, dict) else None
    gate = functions.get("observer_gate") if isinstance(functions, dict) else None
    details = gate.get("details") if isinstance(gate, dict) else None
    gate_limits = details.get("limit") if isinstance(details, dict) else None
    if gate_limits != [10]:
        raise SystemExit("runtime observer summary gate limit does not match exact first-window log budget")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser()
    reject_symlink_component(output_dir, "--output-dir")
    output_dir = reject_protected_output_path(output_dir, "--output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "runtime-observer-summary.json"
    window_check_path = output_dir / "player-principal-lifecycle-window-manifest.check.json"
    manifest_path = output_dir / "approved-runtime-principal-lifecycle-evidence.json"
    check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
    promote_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.promote-check.json"
    public_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json"
    runtime_check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json"
    gate_path = output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json"
    report_path = output_dir / "evidence-bundle-report.json"

    require_success(
        run_command(
            [
                sys.executable,
                str(WINDOW_MANIFEST_CHECKER),
                "--json",
                str(args.window_manifest),
            ],
            stdout_path=window_check_path,
        ),
        "check player principal lifecycle window manifest",
    )
    require_success(
        run_command(
            [
                sys.executable,
                str(ANALYZER),
                "--obelisk-commit",
                args.obelisk_commit,
                "--fail-on-quality-blockers",
                str(args.copied_log),
            ],
            stdout_path=summary_path,
        ),
        "analyze_runtime_observer_log",
    )
    window_check = load_json(window_check_path)
    summary = load_json(summary_path)
    require_window_matches_summary(window_check, summary, args.copied_log)
    require_success(
        run_command(
            [
                sys.executable,
                str(BUILDER),
                "--source-summary",
                str(summary_path),
                "--window-manifest-check",
                str(window_check_path),
                "--output",
                str(manifest_path),
                "--reviewed-by",
                args.reviewed_by,
                "--review-note",
                args.review_note,
            ]
        ),
        "build approved runtime principal lifecycle manifest",
    )
    require_success(
        run_command(
            [
                sys.executable,
                str(CHECKER),
                "--json",
                str(manifest_path),
            ],
            stdout_path=check_path,
        ),
        "check approved runtime principal lifecycle evidence",
    )
    negative_checks = (
        ("promote", "--promote", promote_check_path),
        ("public-readiness", "--public-readiness", public_check_path),
        ("runtime-readiness", "--runtime-readiness", runtime_check_path),
    )
    for label, flag, path in negative_checks:
        require_expected_failure(
            run_command(
                [
                    sys.executable,
                    str(CHECKER),
                    "--json",
                    flag,
                    str(manifest_path),
                ],
                stdout_path=path,
            ),
            f"check approved runtime principal lifecycle evidence {label}",
        )
    require_success(
        run_command(
            [
                sys.executable,
                str(OFFLINE_GATE),
                "--root",
                str(output_dir),
                "--mode",
                "consume",
                "--json",
                "--manifest",
                str(manifest_path),
            ],
            stdout_path=gate_path,
        ),
        "validate offline artifact consume gate",
    )

    check = load_json(check_path)
    promote_check = load_json(promote_check_path)
    public_check = load_json(public_check_path)
    runtime_check = load_json(runtime_check_path)
    gate = load_json(gate_path)
    report = {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
        "status": "accepted",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "source_log": str(args.copied_log),
        "operational_window": {
            "check": str(window_check_path),
            "copied_log_sha256": window_check.get("copied_log", {}).get("sha256"),
            "manifest_ready": window_check.get("operational_window_manifest_ready"),
            "obelisk_commit": window_check.get("obelisk_commit"),
            "run_id": window_check.get("run_id"),
            "target": window_check.get("target"),
        },
        "outputs": {
            "summary": str(summary_path),
            "window_manifest_check": str(window_check_path),
            "manifest": str(manifest_path),
            "check": str(check_path),
            "promote_check": str(promote_check_path),
            "public_readiness_check": str(public_check_path),
            "runtime_readiness_check": str(runtime_check_path),
            "consume_gate": str(gate_path),
        },
        "summary_modules": sorted(summary.get("modules", {}).keys()),
        "observed_runtime_cases": check.get("observed_runtime_cases", []),
        "negative_readiness_checks": {
            "promote_ready": promote_check.get("ready"),
            "public_readiness_ready": public_check.get("ready"),
            "runtime_readiness_ready": runtime_check.get("ready"),
        },
        "consume_gate_status": gate.get("status"),
        "non_claim": (
            "offline consume bundle only; does not authorize server operations, Discord, "
            "GitHub publication, public identity, permissions, commands, runtime readiness, "
            "or v1 SDK completion"
        ),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
