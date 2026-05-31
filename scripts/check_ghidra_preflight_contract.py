#!/usr/bin/env python3
"""Fail-closed static checks for Obelisk Ghidra headless preflight scripts."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPTS = (
    REPO_ROOT / "scripts" / "ghidra" / "DumpFuObjectArrayWindows.java",
    REPO_ROOT / "scripts" / "ghidra" / "DumpWeakHelperCallerModes.java",
)
DEFAULT_SCAN_ROOTS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "scripts",
    REPO_ROOT / "agent-skills",
)
REQUIRED_KEYS = (
    "expected_sha256",
    "expected_language",
    "expected_image_base",
    "expected_window_count",
)
REQUIRED_NON_PROMOTION_MARKERS = (
    "status=candidate-only static orientation",
    "not_artifact_gate=true",
    "promotion_ready=false",
    "not consume or promote evidence",
)
UNKNOWN_ARG_MARKER = "unknown_arg"
ZERO_IMAGE_BASE_PATTERNS = (
    re.compile(r"\bexpected_image_base\s*=\s*0x0\b"),
    re.compile(r"\bimage_base\s*=\s*0x0\b"),
    re.compile(r"--expected-image-base\s+0x0\b"),
)


def iter_text_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix.lower() in {".h", ".hpp", ".cpp", ".c", ".md", ".py", ".java", ".json", ".sh", ".txt"}
    ]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def validate_script(path: Path, blockers: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for key in REQUIRED_KEYS:
        if f'"{key}"' not in text:
            blockers.append(f"{display_path(path)}: missing {key} preflight key")
    for marker in REQUIRED_NON_PROMOTION_MARKERS:
        if marker not in text:
            blockers.append(f"{display_path(path)}: missing non-promotional marker {marker}")
    if UNKNOWN_ARG_MARKER not in text:
        blockers.append(f"{display_path(path)}: unknown preflight keys are not explicitly rejected")
    if "must_not_be_zero" not in text or "expectedImageBase == 0" not in text:
        blockers.append(f"{display_path(path)}: expected_image_base zero is not explicitly rejected")


def validate_scan_roots(roots: tuple[Path, ...], blockers: list[str]) -> None:
    for root in roots:
        for path in iter_text_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in ZERO_IMAGE_BASE_PATTERNS:
                for match in pattern.finditer(text):
                    try:
                        rel = path.relative_to(REPO_ROOT)
                    except ValueError:
                        rel = path
                    line = text.count("\n", 0, match.start()) + 1
                    blockers.append(f"{rel}:{line}: forbidden zero Ghidra image-base example")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", action="append", type=Path, default=[])
    parser.add_argument("--scan-root", action="append", type=Path, default=[])
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    scripts = tuple(args.script) if args.script else DEFAULT_SCRIPTS
    scan_roots = tuple(args.scan_root) if args.scan_root else DEFAULT_SCAN_ROOTS

    blockers: list[str] = []
    for script in scripts:
        path = script if script.is_absolute() else REPO_ROOT / script
        if not path.exists():
            blockers.append(f"{path}: script_missing")
            continue
        validate_script(path, blockers)

    validate_scan_roots(tuple(root if root.is_absolute() else REPO_ROOT / root for root in scan_roots), blockers)
    if blockers:
        print("ghidra preflight contract failed closed:", file=sys.stderr)
        for blocker in blockers:
            print(f"- {blocker}", file=sys.stderr)
        return 1
    print("ghidra preflight contract ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
