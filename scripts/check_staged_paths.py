#!/usr/bin/env python3
"""Fail unless the staged path set exactly matches the expected checkpoint paths."""

from __future__ import annotations

import argparse
import subprocess
import sys


DEFAULT_DIFF_FILTER = "ACDMRTUXB"


def is_windows_absolute_path(path: str) -> bool:
    return len(path) >= 3 and path[1] == ":" and path[2] == "/" and path[0].isalpha()


def normalize_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = raw_path.strip()
        if not path:
            continue
        path = path.replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if (
            path in {".", "/"}
            or path.startswith("/")
            or is_windows_absolute_path(path)
            or any(part == ".." for part in path.split("/"))
        ):
            raise ValueError(f"expected path must be repository-relative: {raw_path}")
        if path not in seen:
            normalized.append(path)
            seen.add(path)
    return sorted(normalized)


def paths_from_name_status(output: str) -> list[str]:
    fields = output.split("\0")
    if fields and fields[-1] == "":
        fields.pop()

    paths: list[str] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if not status:
            continue

        status_code = status[0]
        if status_code in {"C", "R"}:
            if index + 1 >= len(fields):
                raise ValueError(f"malformed git name-status output for {status}")
            source_path = fields[index]
            target_path = fields[index + 1]
            index += 2
            if status_code == "R":
                paths.append(source_path)
            paths.append(target_path)
            continue

        if index >= len(fields):
            raise ValueError(f"malformed git name-status output for {status}")
        paths.append(fields[index])
        index += 1

    return paths


def staged_paths(*, diff_filter: str = DEFAULT_DIFF_FILTER) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z", f"--diff-filter={diff_filter}"],
        check=True,
        text=True,
        capture_output=True,
    )
    return normalize_paths(paths_from_name_status(result.stdout))


def path_mismatches(expected: list[str], actual: list[str]) -> tuple[list[str], list[str]]:
    expected_set = set(normalize_paths(expected))
    actual_set = set(normalize_paths(actual))
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    return missing, extra


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that staged added/copied/modified/renamed/typechanged/unmerged/unknown/"
            "broken/deleted paths exactly match the expected checkpoint path list."
        )
    )
    parser.add_argument(
        "expected_paths",
        nargs="+",
        help="Repository-relative paths expected in the staged checkpoint.",
    )
    parser.add_argument(
        "--diff-filter",
        default=DEFAULT_DIFF_FILTER,
        help=f"git diff --diff-filter value to inspect. Default: {DEFAULT_DIFF_FILTER}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        expected = normalize_paths(args.expected_paths)
        actual = staged_paths(diff_filter=args.diff_filter)
        missing, extra = path_mismatches(expected, actual)
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"check_staged_paths failed: {exc}", file=sys.stderr)
        return 2

    if missing or extra:
        print("staged checkpoint paths do not match expected paths", file=sys.stderr)
        if missing:
            print("missing expected paths:", file=sys.stderr)
            for path in missing:
                print(f"  {path}", file=sys.stderr)
        if extra:
            print("unexpected staged paths:", file=sys.stderr)
            for path in extra:
                print(f"  {path}", file=sys.stderr)
        return 1

    for path in expected:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
