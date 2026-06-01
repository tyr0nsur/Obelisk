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


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
BUILDER = SCRIPT_DIR / "build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
CHECKER = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
OFFLINE_GATE = SCRIPT_DIR / "validate_offline_artifact_gate.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copied-log", required=True, type=Path, help="Copied/sanitized Obelisk log.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Bundle output directory.")
    parser.add_argument("--obelisk-commit", required=True, help="Reviewed Obelisk commit recorded in evidence.")
    parser.add_argument("--reviewed-by", required=True, help="Reviewer token/name for the approved manifest.")
    parser.add_argument("--review-note", required=True, help="Short consume-only review note.")
    return parser.parse_args()


def run_command(command: list[str], *, stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    if stdout_path is None:
        return subprocess.run(command, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with stdout_path.open("w", encoding="utf-8") as stdout:
        return subprocess.run(command, check=False, text=True, stdout=stdout, stderr=subprocess.PIPE)


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise SystemExit(f"{label} failed with exit {result.returncode}: {stderr}")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "runtime-observer-summary.json"
    manifest_path = output_dir / "approved-runtime-principal-lifecycle-evidence.json"
    check_path = output_dir / "approved-runtime-principal-lifecycle-evidence.check.json"
    gate_path = output_dir / "approved-runtime-principal-lifecycle-evidence.consume-gate.json"
    report_path = output_dir / "evidence-bundle-report.json"

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
    require_success(
        run_command(
            [
                sys.executable,
                str(BUILDER),
                "--source-summary",
                str(summary_path),
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

    summary = load_json(summary_path)
    check = load_json(check_path)
    gate = load_json(gate_path)
    report = {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
        "status": "accepted",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "source_log": str(args.copied_log),
        "outputs": {
            "summary": str(summary_path),
            "manifest": str(manifest_path),
            "check": str(check_path),
            "consume_gate": str(gate_path),
        },
        "summary_modules": sorted(summary.get("modules", {}).keys()),
        "observed_runtime_cases": check.get("observed_runtime_cases", []),
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
