#!/usr/bin/env python3
"""Summarize isolated ReflectionScanner capture logs.

This is intentionally passive: it only reads copied log files or stdin and does
not touch server state, marker files, or runtime configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


UOBJECT_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>\S+) UObject validation: "
    r"object=(?P<object>\S+) score=(?P<score>\d+)/(?P<score_max>\d+) "
    r"vtable_exec=(?P<vtable_exec>\w+) "
    r"class_readable_or_null=(?P<class_readable_or_null>\w+) "
    r"outer_readable_or_null=(?P<outer_readable_or_null>\w+) "
    r"fname_plausible=(?P<fname_plausible>\w+) "
    r"flags_plausible=(?P<flags_plausible>\w+) "
    r"internal_plausible=(?P<internal_plausible>\w+)"
)

FNAME_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>\S+) FName indirect-table probe: "
    r"(?:source_global=(?P<source_global>\S+) )?"
    r"table=(?P<table>\S+) score=(?P<score>\d+)/(?P<score_max>\d+) "
    r"readable_clues=(?P<readable_clues>\d+)/(?P<readable_clues_max>\d+) "
    r"matched_clues=(?P<matched_clues>\d+)/(?P<matched_clues_max>\d+) "
    r"num_elements=(?P<num_elements>-?\d+) num_chunks=(?P<num_chunks>-?\d+) "
    r"none='(?P<none>[^']*)' "
    r"client_message='(?P<client_message>[^']*)' "
    r"server_chat='(?P<server_chat>[^']*)'"
)

FNAME_REJECT_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>\S+) FName indirect-table reject: "
    r"(?:source_global=(?P<source_global>\S+) )?"
    r"table=(?P<table>\S+) reason=(?P<reason>\S+) "
    r"readable_clues=(?P<readable_clues>\d+)/(?P<readable_clues_max>\d+) "
    r"matched_clues=(?P<matched_clues>\d+)/(?P<matched_clues_max>\d+) "
    r"num_elements=(?P<num_elements>-?\d+) num_chunks=(?P<num_chunks>-?\d+) "
    r"none='(?P<none>[^']*)' "
    r"client_message='(?P<client_message>[^']*)' "
    r"server_chat='(?P<server_chat>[^']*)'"
)

STATIC_FNAME_ROOT_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>StaticFNameRoot) FName static-root probe: "
    r"slot=(?P<slot>\S+) table=(?P<table>\S+) "
    r"score=(?P<score>\d+)/(?P<score_max>\d+) "
    r"readable_clues=(?P<readable_clues>\d+)/(?P<readable_clues_max>\d+) "
    r"matched_clues=(?P<matched_clues>\d+)/(?P<matched_clues_max>\d+) "
    r"header_index_ok=(?P<header_index_ok>\d+)/(?P<header_index_ok_max>\d+) "
    r"num_elements=(?P<num_elements>-?\d+) num_chunks=(?P<num_chunks>-?\d+) "
    r"none='(?P<none>[^']*)' "
    r"client_message='(?P<client_message>[^']*)' "
    r"server_chat='(?P<server_chat>[^']*)'"
)

STATIC_FNAME_ROOT_REJECT_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>StaticFNameRoot) FName static-root reject: "
    r"slot=(?P<slot>\S+) table=(?P<table>\S+) reason=(?P<reason>\S+) "
    r"readable_clues=(?P<readable_clues>\d+)/(?P<readable_clues_max>\d+) "
    r"matched_clues=(?P<matched_clues>\d+)/(?P<matched_clues_max>\d+) "
    r"header_index_ok=(?P<header_index_ok>\d+)/(?P<header_index_ok_max>\d+) "
    r"num_elements=(?P<num_elements>-?\d+) num_chunks=(?P<num_chunks>-?\d+) "
    r"none='(?P<none>[^']*)' "
    r"client_message='(?P<client_message>[^']*)' "
    r"server_chat='(?P<server_chat>[^']*)'"
)

STATIC_FNAME_ROOT_SAMPLE_RE = re.compile(
    r"\[ReflectionScanner\] StaticFNameRoot FName sample: "
    r"slot=(?P<slot>\S+) table=(?P<table>\S+) "
    r"target=(?P<target>\S+) "
    r"(?:source_global=(?P<source_global>\S+) )?"
    r"object=(?P<object>\S+) "
    r"index=(?P<index>\d+) "
    r"header_index_ok=(?P<header_index_ok>true|false) "
    r"name='(?P<name>[^']*)' "
    r"status=(?P<status>match|mismatch|reject) "
    r"reason=(?P<reason>\S+)"
    r"(?: num_elements=(?P<num_elements>-?\d+) num_chunks=(?P<num_chunks>-?\d+))?"
)

DELAYED_RE = re.compile(
    r"\[ReflectionScanner\] delayed global resolved after (?P<seconds>\d+)s: "
    r"(?P<target>\S+) (?P<global>\S+) -> (?P<value>\S+)"
)

CANDIDATE_RE = re.compile(
    r"\[ReflectionScanner\] (?P<target>\S+) candidate global "
    r"(?P<global>\S+) -> (?P<value>\S+)"
)

OBJDUMP_XREF_RE = re.compile(
    r"^\s*(?P<address>[0-9a-fA-F]+):\s+(?P<body>.*?)"
    r"(?:#|<)\s*(?P<target>0x[0-9a-fA-F]+)"
)


@dataclass(frozen=True)
class LogMatch:
    line: int
    text: str


@dataclass(frozen=True)
class UObjectValidation:
    line: int
    target: str
    object: str
    score: int
    score_max: int
    vtable_exec: str
    class_readable_or_null: str
    outer_readable_or_null: str
    fname_plausible: str
    flags_plausible: str
    internal_plausible: str


@dataclass(frozen=True)
class FNameProbe:
    line: int
    target: str
    source_global: str
    table: str
    score: int
    score_max: int
    readable_clues: int
    readable_clues_max: int
    matched_clues: int
    matched_clues_max: int
    num_elements: int
    num_chunks: int
    none: str
    client_message: str
    server_chat: str

    @property
    def exact_name_match(self) -> bool:
        return (
            self.matched_clues == 3
            and self.matched_clues_max == 3
            and self.none == "None"
            and self.client_message == "ClientMessage"
            and self.server_chat == "ServerChat"
        )

    @property
    def plausible_counts(self) -> bool:
        return 9622 < self.num_elements < 10_000_000 and 0 < self.num_chunks <= 128

    @property
    def research_candidate(self) -> bool:
        return self.exact_name_match and self.plausible_counts


@dataclass(frozen=True)
class FNameReject:
    line: int
    target: str
    source_global: str
    table: str
    reason: str
    readable_clues: int
    readable_clues_max: int
    matched_clues: int
    matched_clues_max: int
    num_elements: int
    num_chunks: int
    none: str
    client_message: str
    server_chat: str


@dataclass(frozen=True)
class StaticFNameRootProbe:
    line: int
    target: str
    slot: str
    table: str
    score: int
    score_max: int
    readable_clues: int
    readable_clues_max: int
    matched_clues: int
    matched_clues_max: int
    header_index_ok: int
    header_index_ok_max: int
    num_elements: int
    num_chunks: int
    none: str
    client_message: str
    server_chat: str

    @property
    def exact_name_match(self) -> bool:
        return (
            self.matched_clues == 3
            and self.matched_clues_max == 3
            and self.none == "None"
            and self.client_message == "ClientMessage"
            and self.server_chat == "ServerChat"
        )

    @property
    def plausible_counts(self) -> bool:
        return 9622 < self.num_elements < 10_000_000 and 0 < self.num_chunks <= 128

    @property
    def valid_header_indices(self) -> bool:
        return self.header_index_ok == 3 and self.header_index_ok_max == 3

    @property
    def research_candidate(self) -> bool:
        return (
            self.exact_name_match
            and self.valid_header_indices
            and self.plausible_counts
        )


@dataclass(frozen=True)
class StaticFNameRootReject:
    line: int
    target: str
    slot: str
    table: str
    reason: str
    readable_clues: int
    readable_clues_max: int
    matched_clues: int
    matched_clues_max: int
    header_index_ok: int
    header_index_ok_max: int
    num_elements: int
    num_chunks: int
    none: str
    client_message: str
    server_chat: str


@dataclass(frozen=True)
class StaticFNameRootSample:
    line: int
    slot: str
    table: str
    target: str
    source_global: str
    object: str
    index: int
    header_index_ok: bool
    name: str
    status: str
    reason: str
    num_elements: int | None
    num_chunks: int | None


@dataclass(frozen=True)
class DelayedGlobal:
    line: int
    seconds: int
    target: str
    global_address: str
    value: str


@dataclass(frozen=True)
class CandidateGlobal:
    line: int
    target: str
    global_address: str
    value: str


@dataclass(frozen=True)
class StaticXref:
    line: int
    instruction_address: str
    target_address: str
    instruction: str
    access: str


def classify_xref_access(instruction: str) -> str:
    tokens = instruction.lower().split()
    while tokens and re.fullmatch(r"[0-9a-f]{2}", tokens[0]):
        tokens.pop(0)

    if not tokens:
        return "unknown"

    mnemonic = tokens[0]
    if mnemonic.startswith("call"):
        return "call"
    if mnemonic.startswith("j"):
        return "jump"
    if mnemonic == "lea":
        return "address"

    operands = " ".join(tokens[1:])
    if "(%rip)" in operands:
        parts = [part.strip() for part in operands.split(",", 1)]
        if len(parts) == 2:
            return "load" if "(%rip)" in parts[0] else "store"

    if "[rip" in operands:
        parts = [part.strip() for part in operands.split(",", 1)]
        if len(parts) == 2:
            return "store" if "[rip" in parts[0] else "load"

    return "other"


def normalize_hex(value: str) -> str:
    try:
        return f"0x{int(value, 16):x}"
    except ValueError:
        return value.lower()


def summarize_gname_tables(fnames: list[FNameProbe]) -> list[dict[str, object]]:
    probes_by_table: dict[str, list[FNameProbe]] = {}
    for probe in fnames:
        probes_by_table.setdefault(probe.table, []).append(probe)

    summaries: list[dict[str, object]] = []
    for table, probes in sorted(probes_by_table.items()):
        research_probes = [probe for probe in probes if probe.research_candidate]
        exact_name_matches = [probe for probe in probes if probe.exact_name_match]
        plausible_count_matches = [probe for probe in probes if probe.plausible_counts]
        distinct_source_globals = sorted(
            {
                probe.source_global
                for probe in research_probes
                if probe.source_global != "unknown"
            }
        )
        distinct_targets = sorted({probe.target for probe in research_probes})
        repeat_confirmed = bool(research_probes) and (
            len(distinct_source_globals) > 1 or len(distinct_targets) > 1
        )

        reasons: list[str] = []
        if not exact_name_matches:
            reasons.append("no exact None/ClientMessage/ServerChat 3/3 clue match")
        if not plausible_count_matches:
            reasons.append("no plausible element/chunk count")
        if research_probes and not repeat_confirmed:
            reasons.append("single-source evidence only")
        if any(probe.matched_clues < probe.matched_clues_max for probe in probes):
            reasons.append("partial clue match observed")
        if any(
            probe.none not in ("", "None")
            or probe.client_message not in ("", "ClientMessage")
            or probe.server_chat not in ("", "ServerChat")
            for probe in probes
        ):
            reasons.append("preview mismatch observed")
        if not reasons:
            reasons.append("repeat-confirmed exact clue match")

        best_probe = max(
            probes,
            key=lambda probe: (
                probe.research_candidate,
                probe.matched_clues,
                probe.readable_clues,
                probe.score,
            ),
        )
        summaries.append(
            {
                "table": table,
                "status": "research-candidate" if repeat_confirmed else "rejected",
                "reason": "; ".join(reasons),
                "line_count": len(probes),
                "lines": [probe.line for probe in probes],
                "research_candidate_count": len(research_probes),
                "distinct_source_globals": distinct_source_globals,
                "distinct_targets": distinct_targets,
                "best_score": best_probe.score,
                "best_score_max": best_probe.score_max,
                "best_matched_clues": best_probe.matched_clues,
                "best_matched_clues_max": best_probe.matched_clues_max,
                "best_num_elements": best_probe.num_elements,
                "best_num_chunks": best_probe.num_chunks,
            }
        )

    return summaries


def summarize_fname_rejects(rejects: list[FNameReject]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[FNameReject]] = {}
    for reject in rejects:
        key = (reject.target, reject.source_global, reject.reason)
        groups.setdefault(key, []).append(reject)

    summaries: list[dict[str, object]] = []
    for (target, source_global, reason), items in sorted(groups.items()):
        best_item = max(
            items,
            key=lambda item: (
                item.matched_clues,
                item.readable_clues,
                item.num_elements,
                item.num_chunks,
            ),
        )
        summaries.append(
            {
                "target": target,
                "source_global": source_global,
                "reason": reason,
                "count": len(items),
                "lines": [item.line for item in items],
                "tables": sorted({item.table for item in items}),
                "best_readable_clues": best_item.readable_clues,
                "best_readable_clues_max": best_item.readable_clues_max,
                "best_matched_clues": best_item.matched_clues,
                "best_matched_clues_max": best_item.matched_clues_max,
                "best_num_elements": best_item.num_elements,
                "best_num_chunks": best_item.num_chunks,
                "best_none": best_item.none,
                "best_client_message": best_item.client_message,
                "best_server_chat": best_item.server_chat,
            }
        )

    return summaries


def reflectionscanner_promotion_gate(
    *,
    repeat_confirmed_gname_table_count: int,
    reject_marker_count: int,
    static_xrefs_actionable: bool,
    binary_metadata_present: bool,
    objdump_xrefs_present: bool,
) -> dict[str, object]:
    blockers: list[dict[str, object]] = [
        {
            "reason": "reflectionscanner_research_candidate_only",
            "detail": (
                "ReflectionScanner analyzer output may identify research candidates "
                "but is never direct promotion evidence."
            ),
        },
        {
            "reason": "needs_second_isolated_capture_or_static_path",
            "detail": (
                "Promotion requires a second isolated capture or an independent "
                "static validation path."
            ),
        },
        {
            "reason": "gobjects_not_validated_by_reflectionscanner_pack",
            "detail": (
                "This pack does not prove GUObjectArray/GObjects layout, object count, "
                "sample membership, or object/name resolution."
            ),
        },
    ]

    conditional_blockers = {
        "reject_markers_present": reject_marker_count,
        "no_repeat_confirmed_gnames_candidate": repeat_confirmed_gname_table_count == 0,
        "non_actionable_static_xrefs": not static_xrefs_actionable,
        "missing_binary_metadata": not binary_metadata_present,
        "missing_objdump_xrefs": not objdump_xrefs_present,
    }

    if reject_marker_count:
        blockers.append(
            {
                "reason": "reject_markers_present",
                "count": reject_marker_count,
                "detail": "Copied logs contain unsafe marker lines such as legacy plugins or native exec probes.",
            }
        )
    if conditional_blockers["no_repeat_confirmed_gnames_candidate"]:
        blockers.append(
            {
                "reason": "no_repeat_confirmed_gnames_candidate",
                "detail": "No repeat-confirmed GNames table candidate is present in this analyzer output.",
            }
        )
    if conditional_blockers["non_actionable_static_xrefs"]:
        blockers.append(
            {
                "reason": "non_actionable_static_xrefs",
                "detail": "No actionable objdump xref evidence was attached for the candidate roots.",
            }
        )
    if conditional_blockers["missing_binary_metadata"]:
        blockers.append(
            {
                "reason": "missing_binary_metadata",
                "detail": "The analyzer output does not include hashed binary metadata.",
            }
        )
    if conditional_blockers["missing_objdump_xrefs"]:
        blockers.append(
            {
                "reason": "missing_objdump_xrefs",
                "detail": "The analyzer output does not include an objdump xref artifact path.",
            }
        )

    return {
        "gate_type": "reflectionscanner_evidence_pack_v1",
        "ready": False,
        "scope": "research_candidate_only",
        "promotable": {
            "gnames": False,
            "gobjects": False,
        },
        "blockers": blockers,
        "conditional_blockers": conditional_blockers,
        "summary": (
            "ReflectionScanner evidence packs are candidate-ranking artifacts only; "
            "do not promote GNames, GObjects, or runtime offsets directly from them."
        ),
    }


def count_by(items: list[StaticFNameRootSample], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, field))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def parse_objdump_xrefs(path: Path, targets: set[str]) -> dict[str, list[StaticXref]]:
    normalized_targets = {normalize_hex(target) for target in targets}
    xrefs: dict[str, list[StaticXref]] = {target: [] for target in normalized_targets}

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = OBJDUMP_XREF_RE.search(line.rstrip("\n"))
            if not match:
                continue

            target = normalize_hex(match.group("target"))
            if target not in normalized_targets:
                continue

            xrefs[target].append(
                StaticXref(
                    line=line_number,
                    instruction_address=f"0x{int(match.group('address'), 16):x}",
                    target_address=target,
                    instruction=" ".join(match.group("body").split()),
                    access=classify_xref_access(match.group("body")),
                )
            )

    return xrefs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_obelisk_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short=12", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze copied Obelisk logs from an isolated ReflectionScanner capture. "
            "Use '-' to read from stdin."
        )
    )
    parser.add_argument("logs", nargs="+", help="Log file path(s), or '-' for stdin.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero when reject markers are present or no repeat-confirmed "
            "matched_clues=3/3 FName research candidate is found."
        ),
    )
    parser.add_argument(
        "--objdump-xrefs",
        type=Path,
        help=(
            "Annotate candidate source globals with references from a pre-generated "
            "objdump -d text file. This is offline evidence only."
        ),
    )
    parser.add_argument(
        "--binary",
        type=Path,
        help=(
            "Attach offline binary metadata to the summary evidence pack. The analyzer "
            "hashes the file but does not execute or modify it."
        ),
    )
    parser.add_argument(
        "--obelisk-commit",
        help=(
            "Override the Obelisk commit recorded in the evidence pack. Defaults to the "
            "current repository HEAD when available."
        ),
    )
    return parser.parse_args()


def iter_lines(paths: list[str]) -> Iterable[tuple[str, int, str]]:
    for raw_path in paths:
        if raw_path == "-":
            for line_number, line in enumerate(sys.stdin, start=1):
                yield "<stdin>", line_number, line.rstrip("\n")
            continue

        path = Path(raw_path)
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                yield str(path), line_number, line.rstrip("\n")


def parse_logs(
    paths: list[str],
    objdump_xrefs_path: Path | None = None,
    binary_path: Path | None = None,
    obelisk_commit: str | None = None,
) -> dict[str, object]:
    uobjects: list[UObjectValidation] = []
    fnames: list[FNameProbe] = []
    fname_rejects: list[FNameReject] = []
    static_fname_root_probes: list[StaticFNameRootProbe] = []
    static_fname_root_rejects: list[StaticFNameRootReject] = []
    static_fname_root_samples: list[StaticFNameRootSample] = []
    delayed: list[DelayedGlobal] = []
    candidate_globals: list[CandidateGlobal] = []
    reject_markers: list[LogMatch] = []
    files: set[str] = set()

    for source, line_number, line in iter_lines(paths):
        files.add(source)

        if "[NativeExecProbe] installed" in line or "[LegacyPlugin]" in line:
            reject_markers.append(LogMatch(line_number, line))

        if match := UOBJECT_RE.search(line):
            groups = match.groupdict()
            uobjects.append(
                UObjectValidation(
                    line=line_number,
                    target=groups["target"],
                    object=groups["object"],
                    score=int(groups["score"]),
                    score_max=int(groups["score_max"]),
                    vtable_exec=groups["vtable_exec"],
                    class_readable_or_null=groups["class_readable_or_null"],
                    outer_readable_or_null=groups["outer_readable_or_null"],
                    fname_plausible=groups["fname_plausible"],
                    flags_plausible=groups["flags_plausible"],
                    internal_plausible=groups["internal_plausible"],
                )
            )
            continue

        if match := FNAME_RE.search(line):
            groups = match.groupdict()
            fnames.append(
                FNameProbe(
                    line=line_number,
                    target=groups["target"],
                    source_global=groups.get("source_global") or "unknown",
                    table=groups["table"],
                    score=int(groups["score"]),
                    score_max=int(groups["score_max"]),
                    readable_clues=int(groups["readable_clues"]),
                    readable_clues_max=int(groups["readable_clues_max"]),
                    matched_clues=int(groups["matched_clues"]),
                    matched_clues_max=int(groups["matched_clues_max"]),
                    num_elements=int(groups["num_elements"]),
                    num_chunks=int(groups["num_chunks"]),
                    none=groups["none"],
                    client_message=groups["client_message"],
                    server_chat=groups["server_chat"],
                )
            )
            continue

        if match := FNAME_REJECT_RE.search(line):
            groups = match.groupdict()
            fname_rejects.append(
                FNameReject(
                    line=line_number,
                    target=groups["target"],
                    source_global=groups.get("source_global") or "unknown",
                    table=groups["table"],
                    reason=groups["reason"],
                    readable_clues=int(groups["readable_clues"]),
                    readable_clues_max=int(groups["readable_clues_max"]),
                    matched_clues=int(groups["matched_clues"]),
                    matched_clues_max=int(groups["matched_clues_max"]),
                    num_elements=int(groups["num_elements"]),
                    num_chunks=int(groups["num_chunks"]),
                    none=groups["none"],
                    client_message=groups["client_message"],
                    server_chat=groups["server_chat"],
                )
            )
            continue

        if match := STATIC_FNAME_ROOT_RE.search(line):
            groups = match.groupdict()
            static_fname_root_probes.append(
                StaticFNameRootProbe(
                    line=line_number,
                    target=groups["target"],
                    slot=groups["slot"],
                    table=groups["table"],
                    score=int(groups["score"]),
                    score_max=int(groups["score_max"]),
                    readable_clues=int(groups["readable_clues"]),
                    readable_clues_max=int(groups["readable_clues_max"]),
                    matched_clues=int(groups["matched_clues"]),
                    matched_clues_max=int(groups["matched_clues_max"]),
                    header_index_ok=int(groups["header_index_ok"]),
                    header_index_ok_max=int(groups["header_index_ok_max"]),
                    num_elements=int(groups["num_elements"]),
                    num_chunks=int(groups["num_chunks"]),
                    none=groups["none"],
                    client_message=groups["client_message"],
                    server_chat=groups["server_chat"],
                )
            )
            continue

        if match := STATIC_FNAME_ROOT_REJECT_RE.search(line):
            groups = match.groupdict()
            static_fname_root_rejects.append(
                StaticFNameRootReject(
                    line=line_number,
                    target=groups["target"],
                    slot=groups["slot"],
                    table=groups["table"],
                    reason=groups["reason"],
                    readable_clues=int(groups["readable_clues"]),
                    readable_clues_max=int(groups["readable_clues_max"]),
                    matched_clues=int(groups["matched_clues"]),
                    matched_clues_max=int(groups["matched_clues_max"]),
                    header_index_ok=int(groups["header_index_ok"]),
                    header_index_ok_max=int(groups["header_index_ok_max"]),
                    num_elements=int(groups["num_elements"]),
                    num_chunks=int(groups["num_chunks"]),
                    none=groups["none"],
                    client_message=groups["client_message"],
                    server_chat=groups["server_chat"],
                )
            )
            continue

        if match := STATIC_FNAME_ROOT_SAMPLE_RE.search(line):
            groups = match.groupdict()
            static_fname_root_samples.append(
                StaticFNameRootSample(
                    line=line_number,
                    slot=groups["slot"],
                    table=groups["table"],
                    target=groups["target"],
                    source_global=groups.get("source_global") or "unknown",
                    object=groups["object"],
                    index=int(groups["index"]),
                    header_index_ok=groups["header_index_ok"] == "true",
                    name=groups["name"],
                    status=groups["status"],
                    reason=groups["reason"],
                    num_elements=int(groups["num_elements"])
                    if groups.get("num_elements")
                    else None,
                    num_chunks=int(groups["num_chunks"])
                    if groups.get("num_chunks")
                    else None,
                )
            )
            continue

        if match := DELAYED_RE.search(line):
            groups = match.groupdict()
            delayed.append(
                DelayedGlobal(
                    line=line_number,
                    seconds=int(groups["seconds"]),
                    target=groups["target"],
                    global_address=groups["global"],
                    value=groups["value"],
                )
            )
            continue

        if match := CANDIDATE_RE.search(line):
            groups = match.groupdict()
            candidate_globals.append(
                CandidateGlobal(
                    line=line_number,
                    target=groups["target"],
                    global_address=groups["global"],
                    value=groups["value"],
                )
            )

    table_counts: dict[str, int] = {}
    research_table_counts: dict[str, int] = {}
    table_targets: dict[str, set[str]] = {}
    table_source_globals: dict[str, set[str]] = {}
    for probe in fnames:
        table_counts[probe.table] = table_counts.get(probe.table, 0) + 1
        if probe.research_candidate:
            research_table_counts[probe.table] = research_table_counts.get(probe.table, 0) + 1
            table_targets.setdefault(probe.table, set()).add(probe.target)
            if probe.source_global != "unknown":
                table_source_globals.setdefault(probe.table, set()).add(probe.source_global)

    static_targets = {
        normalize_hex(probe.source_global)
        for probe in fnames
        if probe.source_global != "unknown"
    }
    static_targets.update(
        normalize_hex(reject.source_global)
        for reject in fname_rejects
        if reject.source_global != "unknown"
    )
    static_targets.update(normalize_hex(probe.slot) for probe in static_fname_root_probes)
    static_targets.update(normalize_hex(reject.slot) for reject in static_fname_root_rejects)
    static_targets.update(normalize_hex(sample.slot) for sample in static_fname_root_samples)
    static_targets.update(
        normalize_hex(sample.source_global)
        for sample in static_fname_root_samples
        if sample.source_global != "unknown"
    )
    static_targets.update(
        normalize_hex(item.global_address)
        for item in candidate_globals
    )
    static_xrefs = (
        parse_objdump_xrefs(objdump_xrefs_path, static_targets)
        if objdump_xrefs_path is not None
        else {}
    )
    static_xref_access_counts: dict[str, int] = {}
    for refs in static_xrefs.values():
        for ref in refs:
            static_xref_access_counts[ref.access] = (
                static_xref_access_counts.get(ref.access, 0) + 1
            )

    table_summaries = summarize_gname_tables(fnames)
    binary_metadata: dict[str, object] | None = None
    if binary_path is not None:
        binary_metadata = {
            "path": str(binary_path),
            "sha256": sha256_file(binary_path),
            "size_bytes": binary_path.stat().st_size,
        }

    repeat_confirmed_tables = [
        item for item in table_summaries if item["status"] == "research-candidate"
    ]
    fname_reject_reason_counts: dict[str, int] = {}
    for reject in fname_rejects:
        fname_reject_reason_counts[reject.reason] = (
            fname_reject_reason_counts.get(reject.reason, 0) + 1
        )

    fname_reject_groups = summarize_fname_rejects(fname_rejects)
    static_fname_root_candidates = [
        item for item in static_fname_root_probes if item.research_candidate
    ]
    static_fname_root_reject_reason_counts: dict[str, int] = {}
    for reject in static_fname_root_rejects:
        static_fname_root_reject_reason_counts[reject.reason] = (
            static_fname_root_reject_reason_counts.get(reject.reason, 0) + 1
        )
    promotion_gate = reflectionscanner_promotion_gate(
        repeat_confirmed_gname_table_count=len(repeat_confirmed_tables),
        reject_marker_count=len(reject_markers),
        static_xrefs_actionable=bool(static_xref_access_counts),
        binary_metadata_present=binary_metadata is not None,
        objdump_xrefs_present=objdump_xrefs_path is not None,
    )

    return {
        "evidence_pack": {
            "obelisk_commit": obelisk_commit
            if obelisk_commit is not None
            else detect_obelisk_commit(Path(__file__).resolve().parents[1]),
            "logs": sorted(files),
            "binary": binary_metadata,
            "objdump_xrefs": str(objdump_xrefs_path) if objdump_xrefs_path else None,
            "static_xref_access_counts": dict(sorted(static_xref_access_counts.items())),
            "reject_marker_count": len(reject_markers),
            "fname_probe_count": len(fnames),
            "fname_reject_count": len(fname_rejects),
            "fname_reject_reason_counts": dict(sorted(fname_reject_reason_counts.items())),
            "static_fname_root_probe_count": len(static_fname_root_probes),
            "static_fname_root_reject_count": len(static_fname_root_rejects),
            "static_fname_root_reject_reason_counts": dict(
                sorted(static_fname_root_reject_reason_counts.items())
            ),
            "static_fname_root_sample_count": len(static_fname_root_samples),
            "static_fname_root_sample_status_counts": count_by(
                static_fname_root_samples, "status"
            ),
            "static_fname_root_sample_reason_counts": count_by(
                static_fname_root_samples, "reason"
            ),
            "static_fname_root_sample_target_counts": count_by(
                static_fname_root_samples, "target"
            ),
            "static_fname_root_candidate_count": len(static_fname_root_candidates),
            "gname_table_candidate_count": len(repeat_confirmed_tables),
            "status": (
                "research-candidate"
                if repeat_confirmed_tables and not reject_markers
                else "inconclusive"
            ),
            "promotion_gate": promotion_gate,
        },
        "files": sorted(files),
        "reject_markers": [asdict(item) for item in reject_markers],
        "uobject_validations": [asdict(item) for item in uobjects],
        "fname_probes": [
            {
                **asdict(item),
                "exact_name_match": item.exact_name_match,
                "plausible_counts": item.plausible_counts,
                "research_candidate": item.research_candidate,
                "repeat_confirmed_candidate": item.research_candidate
                and (
                    len(table_source_globals.get(item.table, set())) > 1
                    or len(table_targets.get(item.table, set())) > 1
                ),
                "table_seen_count": table_counts[item.table],
                "table_research_candidate_count": research_table_counts.get(item.table, 0),
                "distinct_source_globals": sorted(table_source_globals.get(item.table, set())),
                "distinct_targets": sorted(table_targets.get(item.table, set())),
            }
            for item in fnames
        ],
        "fname_rejects": [asdict(item) for item in fname_rejects],
        "fname_reject_groups": fname_reject_groups,
        "static_fname_root_probes": [
            {
                **asdict(item),
                "exact_name_match": item.exact_name_match,
                "valid_header_indices": item.valid_header_indices,
                "plausible_counts": item.plausible_counts,
                "research_candidate": item.research_candidate,
            }
            for item in static_fname_root_probes
        ],
        "static_fname_root_rejects": [
            asdict(item) for item in static_fname_root_rejects
        ],
        "static_fname_root_samples": [
            asdict(item) for item in static_fname_root_samples
        ],
        "gname_table_candidates": table_summaries,
        "delayed_globals": [asdict(item) for item in delayed],
        "candidate_globals": [asdict(item) for item in candidate_globals],
        "static_xrefs": {
            target: [asdict(item) for item in refs]
            for target, refs in sorted(static_xrefs.items())
        },
    }


def print_human(summary: dict[str, object]) -> None:
    evidence_pack = summary["evidence_pack"]
    reject_markers = summary["reject_markers"]
    uobjects = summary["uobject_validations"]
    fnames = summary["fname_probes"]
    fname_rejects = summary["fname_rejects"]
    fname_reject_groups = summary["fname_reject_groups"]
    static_fname_root_probes = summary["static_fname_root_probes"]
    static_fname_root_rejects = summary["static_fname_root_rejects"]
    static_fname_root_samples = summary["static_fname_root_samples"]
    delayed = summary["delayed_globals"]
    candidate_globals = summary["candidate_globals"]
    static_xrefs = summary["static_xrefs"]

    print("ReflectionScanner capture summary")
    print(f"obelisk commit: {evidence_pack['obelisk_commit']}")
    if evidence_pack["binary"]:
        binary = evidence_pack["binary"]
        print(
            "binary: {path} sha256={sha256} size={size_bytes}".format(**binary)
        )
    if evidence_pack["objdump_xrefs"]:
        print(f"objdump xrefs: {evidence_pack['objdump_xrefs']}")
    print(f"evidence status: {evidence_pack['status']}")
    print(f"files: {', '.join(summary['files'])}")
    print(f"candidate globals: {len(candidate_globals)}")
    print(f"delayed globals: {len(delayed)}")
    print(f"UObject validations: {len(uobjects)}")
    print(f"FName probes: {len(fnames)}")
    print(f"FName rejects: {len(fname_rejects)}")
    print(f"Static FName root probes: {len(static_fname_root_probes)}")
    print(f"Static FName root rejects: {len(static_fname_root_rejects)}")
    print(f"Static FName root samples: {len(static_fname_root_samples)}")

    if reject_markers:
        print("\nreject markers:")
        for marker in reject_markers:
            print(f"- line {marker['line']}: {marker['text']}")
    else:
        print("\nreject markers: none")

    exact_candidates = [item for item in fnames if item["research_candidate"]]
    repeat_confirmed = [item for item in fnames if item["repeat_confirmed_candidate"]]
    print(f"\nFName exact candidates: {len(exact_candidates)}")
    print(f"FName repeat-confirmed candidates: {len(repeat_confirmed)}")
    for item in exact_candidates:
        repeated = "repeated" if item["repeat_confirmed_candidate"] else "single"
        print(
            "- line {line}: target={target} source_global={source_global} table={table} score={score}/{score_max} "
            "matched={matched_clues}/{matched_clues_max} elements={num_elements} "
            "chunks={num_chunks} table_seen={table_seen_count} distinct_globals={distinct_global_count} "
            "distinct_targets={distinct_target_count} ({repeated})".format(
                **item,
                distinct_global_count=len(item["distinct_source_globals"]),
                distinct_target_count=len(item["distinct_targets"]),
                repeated=repeated,
            )
        )

    print("\nGNames table triage:")
    table_candidates = summary["gname_table_candidates"]
    if not table_candidates:
        print("- none")
    for item in table_candidates:
        print(
            "- table={table} status={status} lines={lines} research_hits={research_candidate_count} "
            "distinct_globals={distinct_global_count} distinct_targets={distinct_target_count} reason={reason}".format(
                **item,
                distinct_global_count=len(item["distinct_source_globals"]),
                distinct_target_count=len(item["distinct_targets"]),
            )
        )

    weak_fnames = [item for item in fnames if not item["repeat_confirmed_candidate"]]
    if weak_fnames:
        print("\nweak or rejected FName probes:")
        for item in weak_fnames:
            print(
                "- line {line}: target={target} source_global={source_global} table={table} matched={matched_clues}/"
                "{matched_clues_max} none='{none}' client_message='{client_message}' "
                "server_chat='{server_chat}' elements={num_elements} chunks={num_chunks}".format(
                    **item
                )
            )

    if fname_rejects:
        reason_counts = evidence_pack["fname_reject_reason_counts"]
        print("\nFName reject reasons:")
        for reason, count in reason_counts.items():
            print(f"- {reason}: {count}")
        print("\nFName reject samples:")
        for item in fname_rejects[:10]:
            print(
                "- line {line}: target={target} source_global={source_global} table={table} "
                "reason={reason} matched={matched_clues}/{matched_clues_max} "
                "elements={num_elements} chunks={num_chunks}".format(**item)
            )
        print("\nFName reject groups:")
        for item in fname_reject_groups[:10]:
            print(
                "- target={target} source_global={source_global} reason={reason} "
                "count={count} lines={lines} tables={table_count} "
                "best_matched={best_matched_clues}/{best_matched_clues_max} "
                "best_elements={best_num_elements} best_chunks={best_num_chunks}".format(
                    **item,
                    table_count=len(item["tables"]),
                )
            )

    static_root_candidates = [
        item for item in static_fname_root_probes if item["research_candidate"]
    ]
    print(f"\nStatic FName root candidates: {len(static_root_candidates)}")
    for item in static_root_candidates:
        print(
            "- line {line}: slot={slot} table={table} score={score}/{score_max} "
            "matched={matched_clues}/{matched_clues_max} elements={num_elements} "
            "chunks={num_chunks} header_index_ok={header_index_ok}/"
            "{header_index_ok_max}".format(**item)
        )

    weak_static_roots = [
        item for item in static_fname_root_probes if not item["research_candidate"]
    ]
    if weak_static_roots:
        print("\nweak or rejected static FName root probes:")
        for item in weak_static_roots:
            print(
                "- line {line}: slot={slot} table={table} matched={matched_clues}/"
                "{matched_clues_max} header_index_ok={header_index_ok}/"
                "{header_index_ok_max} none='{none}' client_message='{client_message}' "
                "server_chat='{server_chat}' elements={num_elements} "
                "chunks={num_chunks}".format(**item)
            )

    if static_fname_root_rejects:
        reason_counts = evidence_pack["static_fname_root_reject_reason_counts"]
        print("\nStatic FName root reject reasons:")
        for reason, count in reason_counts.items():
            print(f"- {reason}: {count}")
        print("\nStatic FName root reject samples:")
        for item in static_fname_root_rejects[:10]:
            print(
                "- line {line}: slot={slot} table={table} reason={reason} "
                "matched={matched_clues}/{matched_clues_max} elements={num_elements} "
                "chunks={num_chunks} header_index_ok={header_index_ok}/"
                "{header_index_ok_max}".format(**item)
            )

    if static_fname_root_samples:
        print("\nStatic FName root sample summary:")
        print("status:")
        for status, count in evidence_pack["static_fname_root_sample_status_counts"].items():
            print(f"- {status}: {count}")
        print("reasons:")
        for reason, count in evidence_pack["static_fname_root_sample_reason_counts"].items():
            print(f"- {reason}: {count}")
        print("targets:")
        for target, count in evidence_pack["static_fname_root_sample_target_counts"].items():
            print(f"- {target}: {count}")
        print("samples:")
        for item in static_fname_root_samples[:10]:
            print(
                "- line {line}: slot={slot} table={table} target={target} "
                "source_global={source_global} object={object} index={index} "
                "header_index_ok={header_index_ok} "
                "status={status} reason={reason} name='{name}'".format(**item)
            )

    print("\ntop UObject validation scores:")
    top_uobjects = sorted(
        uobjects,
        key=lambda item: (item["score"], item["target"], item["line"]),
        reverse=True,
    )[:10]
    if not top_uobjects:
        print("- none")
    for item in top_uobjects:
        print(
            "- line {line}: target={target} object={object} score={score}/{score_max} "
            "vtable_exec={vtable_exec} fname_plausible={fname_plausible}".format(**item)
        )

    if static_xrefs:
        print("\nstatic xrefs:")
        for target, refs in static_xrefs.items():
            if not refs:
                print(f"- {target}: none")
                continue
            print(f"- {target}: {len(refs)} reference(s)")
            for ref in refs[:5]:
                print(
                    "  line {line}: {instruction_address} access={access} {instruction}".format(**ref)
                )


def main() -> int:
    args = parse_args()
    summary = parse_logs(
        args.logs,
        objdump_xrefs_path=args.objdump_xrefs,
        binary_path=args.binary,
        obelisk_commit=args.obelisk_commit,
    )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human(summary)

    if args.strict:
        has_reject_markers = bool(summary["reject_markers"])
        has_repeat_confirmed_candidate = any(
            item["status"] == "research-candidate"
            for item in summary["gname_table_candidates"]
        )
        if has_reject_markers or not has_repeat_confirmed_candidate:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
