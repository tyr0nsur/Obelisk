#!/usr/bin/env python3
"""Validate that a release tag dereferences to the intended Git ref."""

from __future__ import annotations

import argparse
import subprocess
import sys


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def resolve_ref(ref: str) -> str:
    return git("rev-parse", "--verify", f"{ref}^{{commit}}")


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail unless a release tag exists and dereferences to the intended commit. "
            "Use this immediately before pushing a release tag."
        )
    )
    parser.add_argument("--tag", required=True, help="Release tag to verify, for example v0.1.0-rc.1.")
    parser.add_argument(
        "--ref",
        default="HEAD",
        help="Intended release ref to compare against. Default: HEAD.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Treat a missing tag as success after verifying the intended ref exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        expected_commit = resolve_ref(args.ref)
    except subprocess.CalledProcessError as exc:
        print(f"release tag check failed: cannot resolve ref {args.ref!r}: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    if not tag_exists(args.tag):
        if args.allow_missing:
            print(f"{args.tag} missing; intended ref {args.ref} resolves to {expected_commit}")
            return 0
        print(f"release tag check failed: tag {args.tag!r} does not exist", file=sys.stderr)
        return 1

    try:
        tag_commit = resolve_ref(f"refs/tags/{args.tag}")
    except subprocess.CalledProcessError as exc:
        print(f"release tag check failed: cannot dereference tag {args.tag!r}: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    if tag_commit != expected_commit:
        print(
            "release tag check failed: tag/ref mismatch\n"
            f"  tag: {args.tag} -> {tag_commit}\n"
            f"  ref: {args.ref} -> {expected_commit}",
            file=sys.stderr,
        )
        return 1

    print(f"{args.tag} matches {args.ref} at {expected_commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
