#!/usr/bin/env python3
"""Normalize ARK MessageOfTheDay values without using an INI rewriter."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SCHEMA = "obelisk.ark-motd-normalizer.v1"
MOTD_SECTION = "MessageOfTheDay"
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
MESSAGE_RE = re.compile(r"^(\s*Message\s*=\s*)(.*)$")
KEY_RE = re.compile(r"^\s*[A-Za-z0-9_.-]+\s*=")
COMMENT_RE = re.compile(r"^\s*[;#]")


@dataclass(frozen=True)
class Line:
    body: str
    eol: str


@dataclass(frozen=True)
class NormalizeResult:
    normalized_text: str
    changed: bool
    message_entries: int
    continuation_lines_collapsed: int
    message_physical_lines_before: int
    escaped_newline_boundaries_preserved: int


@dataclass(frozen=True)
class DecodedText:
    text: str
    encoding: str


@dataclass(frozen=True)
class PathSafety:
    path: Path
    resolved_path: Path
    protected_path: bool
    protected_path_allowed: bool


def split_line(line: str) -> Line:
    if line.endswith("\r\n"):
        return Line(line[:-2], "\r\n")
    if line.endswith("\n"):
        return Line(line[:-1], "\n")
    if line.endswith("\r"):
        return Line(line[:-1], "\r")
    return Line(line, "")


def section_name(body: str) -> str | None:
    match = SECTION_RE.match(body)
    if not match:
        return None
    return match.group(1).strip()


def is_key_line(body: str) -> bool:
    return KEY_RE.match(body) is not None


def is_comment_or_blank_line(body: str) -> bool:
    return not body.strip() or COMMENT_RE.match(body) is not None


def is_under_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_path_safety(path: Path, *, allow_protected_path: bool) -> PathSafety:
    expanded = path.expanduser()
    try:
        resolved = expanded.resolve(strict=False)
    except OSError as exc:
        raise ValueError(f"failed to resolve {path}: {exc}") from exc

    direct_protected = expanded.is_absolute() and is_under_path(expanded, PROTECTED_SERVER_ROOT)
    resolved_protected = is_under_path(resolved, PROTECTED_SERVER_ROOT)
    protected_path = direct_protected or resolved_protected
    if protected_path and not allow_protected_path:
        raise ValueError(
            f"{path} resolves under protected server root {PROTECTED_SERVER_ROOT}; "
            "copy the INI to an offline path or pass --allow-protected-path only inside "
            "an approved maintenance workflow"
        )
    return PathSafety(
        path=path,
        resolved_path=resolved,
        protected_path=protected_path,
        protected_path_allowed=allow_protected_path and protected_path,
    )


def decode_ini_bytes(data: bytes) -> DecodedText:
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return DecodedText(data.decode("utf-16"), "utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return DecodedText(data.decode("utf-8-sig"), "utf-8-sig")
    sample = data[:4096]
    if sample:
        odd_nuls = sample[1::2].count(0)
        even_nuls = sample[0::2].count(0)
        if odd_nuls > max(8, len(sample) // 8):
            return DecodedText(data.decode("utf-16le"), "utf-16le")
        if even_nuls > max(8, len(sample) // 8):
            return DecodedText(data.decode("utf-16be"), "utf-16be")
    return DecodedText(data.decode("utf-8"), "utf-8")


def append_motd_piece(current: str, piece: str) -> tuple[str, bool]:
    if current.endswith(r"\n") or piece.startswith(r"\n") or (
        current.endswith("\\") and piece.startswith("n")
    ):
        return current + piece, True
    return current + r"\n" + piece, False


def join_motd_values(values: list[str]) -> tuple[str, int]:
    if not values:
        return "", 0
    joined = values[0]
    escaped_boundaries = 0
    for value in values[1:]:
        joined, preserved = append_motd_piece(joined, value)
        if preserved:
            escaped_boundaries += 1
    return joined, escaped_boundaries


def normalize_motd_text(text: str) -> NormalizeResult:
    raw_lines = text.splitlines(keepends=True)
    lines = [split_line(line) for line in raw_lines]
    output: list[str] = []
    in_motd = False
    message_entries = 0
    continuation_lines_collapsed = 0
    message_physical_lines_before = 0
    escaped_newline_boundaries_preserved = 0

    index = 0
    while index < len(lines):
        line = lines[index]
        current_section = section_name(line.body)
        if current_section is not None:
            in_motd = current_section.lower() == MOTD_SECTION.lower()
            output.append(line.body + line.eol)
            index += 1
            continue

        message_match = MESSAGE_RE.match(line.body) if in_motd else None
        if not message_match:
            output.append(line.body + line.eol)
            index += 1
            continue

        message_entries += 1
        prefix, first_value = message_match.groups()
        values = [first_value]
        next_index = index + 1
        while next_index < len(lines):
            next_line = lines[next_index]
            if section_name(next_line.body) is not None:
                break
            if is_key_line(next_line.body):
                break
            if is_comment_or_blank_line(next_line.body):
                break
            values.append(next_line.body)
            next_index += 1

        continuation_count = len(values) - 1
        joined_value, escaped_boundaries = join_motd_values(values)
        continuation_lines_collapsed += continuation_count
        message_physical_lines_before += len(values)
        escaped_newline_boundaries_preserved += escaped_boundaries
        output.append(prefix + joined_value + line.eol)
        index = next_index

    normalized_text = "".join(output)
    return NormalizeResult(
        normalized_text=normalized_text,
        changed=normalized_text != text,
        message_entries=message_entries,
        continuation_lines_collapsed=continuation_lines_collapsed,
        message_physical_lines_before=message_physical_lines_before,
        escaped_newline_boundaries_preserved=escaped_newline_boundaries_preserved,
    )


def build_report(
    safety: PathSafety,
    result: NormalizeResult,
    *,
    encoding: str,
    wrote: bool,
    check: bool,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "path": str(safety.path),
        "resolved_path": str(safety.resolved_path),
        "protected_path": safety.protected_path,
        "protected_path_allowed": safety.protected_path_allowed,
        "encoding": encoding,
        "changed": result.changed,
        "wrote": wrote,
        "check": check,
        "message_entries": result.message_entries,
        "message_physical_lines_before": result.message_physical_lines_before,
        "continuation_lines_collapsed": result.continuation_lines_collapsed,
        "escaped_newline_boundaries_preserved": result.escaped_newline_boundaries_preserved,
        "ready": not result.changed or wrote,
        "non_claim": (
            "MOTD normalization only; this does not start, stop, restart, authorize, "
            "or validate an ARK server and is not Obelisk runtime evidence."
        ),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fold physical newlines in [MessageOfTheDay] Message= values into literal "
            "\\n sequences while leaving the rest of GameUserSettings.ini untouched."
        )
    )
    parser.add_argument("path", type=Path, help="GameUserSettings.ini path to inspect.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite the file in place when normalization is needed.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when normalization would change the file.",
    )
    parser.add_argument(
        "--allow-protected-path",
        action="store_true",
        help=(
            "Allow a path that is directly or symlink-resolved under /servidor/ark. "
            "This bypasses only the tool guard and does not authorize live server work."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        safety = resolve_path_safety(
            args.path,
            allow_protected_path=args.allow_protected_path,
        )
    except ValueError as exc:
        print(f"refusing protected path: {exc}", file=sys.stderr)
        return 2

    target_path = safety.resolved_path
    try:
        decoded = decode_ini_bytes(target_path.read_bytes())
    except UnicodeDecodeError as exc:
        print(f"failed to decode {args.path}: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"failed to read {args.path}: {exc}", file=sys.stderr)
        return 2

    result = normalize_motd_text(decoded.text)
    wrote = False
    if args.write and result.changed:
        try:
            target_path.write_bytes(result.normalized_text.encode(decoded.encoding))
        except OSError as exc:
            print(f"failed to write {args.path}: {exc}", file=sys.stderr)
            return 2
        wrote = True

    report = build_report(safety, result, encoding=decoded.encoding, wrote=wrote, check=args.check)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif result.changed:
        action = "normalized" if wrote else "would normalize"
        print(
            f"{action}: {args.path}; collapsed "
            f"{result.continuation_lines_collapsed} MOTD continuation line(s)"
        )
    else:
        print(f"already normalized: {args.path}")

    if args.check and result.changed and not wrote:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
