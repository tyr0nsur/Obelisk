#!/usr/bin/env python3
"""Plan or run the minimal offline second-source core intake."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FNAME_INDICES = (
    "None=0",
    "ClientMessage=4884",
    "ServerChat=9619",
    "SetActiveMissionDebugFlags=9622",
)
DEFAULT_GOBJECTS_SAMPLE_INDICES = ("0", "1", "25447")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute the minimal offline second-source intake for an already "
            "approved independent ARK core artifact. The default mode prints commands "
            "only and never touches live servers."
        )
    )
    parser.add_argument("--binary", required=True, help="Matching ShooterGameServer binary path.")
    parser.add_argument("--core", required=True, help="Independent core artifact path.")
    parser.add_argument("--pack-dir", required=True, help="Evidence pack output directory.")
    parser.add_argument(
        "--snapshot-root",
        required=True,
        help="Output root for regenerated candidate UFunction snapshots.",
    )
    parser.add_argument(
        "--verified-fname-root-slot",
        required=True,
        help="Artifact-specific verified FName root slot address, for example 0x1234.",
    )
    parser.add_argument(
        "--gobjects-candidate",
        required=True,
        help="Artifact-specific GObjects candidate address, for example 0x595b7e0.",
    )
    parser.add_argument(
        "--fname-index",
        action="append",
        default=[],
        metavar="LABEL=INDEX",
        help=(
            "FName clue to pass while scanning the artifact. Repeatable. Defaults to "
            "the current stable clue set."
        ),
    )
    parser.add_argument(
        "--gobjects-sample-index",
        action="append",
        default=[],
        metavar="INDEX",
        help="GObjects sample index. Repeatable. Defaults to 0, 1, and 25447.",
    )
    parser.add_argument(
        "--target-set",
        default="minimal-second-source-intake",
        help="UFunction target set to regenerate and compare.",
    )
    parser.add_argument(
        "--base-root",
        default="tests/fixtures/ufunction_snapshots",
        help="Committed primary UFunction snapshot root.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the commands. Without this flag, only print the reproducible plan.",
    )
    return parser.parse_args()


def rel_or_abs(path: str) -> str:
    return str(Path(path).expanduser())


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    pack_dir = rel_or_abs(args.pack_dir)
    manifest = str(Path(pack_dir) / "manifest.json")
    fname_indices = args.fname_index or list(DEFAULT_FNAME_INDICES)
    sample_indices = args.gobjects_sample_index or list(DEFAULT_GOBJECTS_SAMPLE_INDICES)

    scan_command = [
        "python3",
        "scripts/build_core_dump_evidence_pack.py",
        "--binary",
        rel_or_abs(args.binary),
        "--core",
        rel_or_abs(args.core),
        "--output-dir",
        pack_dir,
        "--scan-fname-tables",
        "--no-default-fname-indices",
    ]
    for item in fname_indices:
        scan_command.extend(["--fname-index", item])

    sample_command = [
        "python3",
        "scripts/build_core_dump_evidence_pack.py",
        "--binary",
        rel_or_abs(args.binary),
        "--core",
        rel_or_abs(args.core),
        "--output-dir",
        pack_dir,
        "--fname-root-slot",
        f"verified_fname_root_slot={args.verified_fname_root_slot}",
        "--gobjects-candidate",
        f"gobjects={args.gobjects_candidate}",
    ]
    for item in sample_indices:
        sample_command.extend(["--gobjects-sample-index", item])

    regenerate_command = [
        "python3",
        "scripts/regenerate_ufunction_snapshots.py",
        "--core",
        rel_or_abs(args.core),
        "--evidence-pack-manifest",
        manifest,
        "--output-root",
        rel_or_abs(args.snapshot_root),
        "--target-set",
        args.target_set,
        "--write",
    ]

    compare_command = [
        "python3",
        "scripts/compare_reflection_snapshots.py",
        "--base-root",
        rel_or_abs(args.base_root),
        "--candidate-root",
        rel_or_abs(args.snapshot_root),
        "--target-set",
        args.target_set,
        "--json",
    ]

    return [scan_command, sample_command, regenerate_command, compare_command]


def main() -> int:
    args = parse_args()
    commands = build_commands(args)

    if not args.execute:
        print("# Dry run: pass --execute to run these offline commands.")
        for command in commands:
            print(shlex.join(command))
        return 0

    for command in commands:
        print(f"\n==> {shlex.join(command)}", flush=True)
        subprocess.run(command, cwd=REPO_ROOT, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
