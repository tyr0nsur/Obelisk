#!/usr/bin/env python3
"""Summarize isolated ReflectionScanner capture logs.

This is intentionally passive: it only reads copied log files or stdin and does
not touch server state, marker files, or runtime configuration.
"""

from __future__ import annotations

import argparse
import json
import re
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
                )
            )

    return xrefs


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


def parse_logs(paths: list[str], objdump_xrefs_path: Path | None = None) -> dict[str, object]:
    uobjects: list[UObjectValidation] = []
    fnames: list[FNameProbe] = []
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
        normalize_hex(item.global_address)
        for item in candidate_globals
    )
    static_xrefs = (
        parse_objdump_xrefs(objdump_xrefs_path, static_targets)
        if objdump_xrefs_path is not None
        else {}
    )

    return {
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
        "gname_table_candidates": summarize_gname_tables(fnames),
        "delayed_globals": [asdict(item) for item in delayed],
        "candidate_globals": [asdict(item) for item in candidate_globals],
        "static_xrefs": {
            target: [asdict(item) for item in refs]
            for target, refs in sorted(static_xrefs.items())
        },
    }


def print_human(summary: dict[str, object]) -> None:
    reject_markers = summary["reject_markers"]
    uobjects = summary["uobject_validations"]
    fnames = summary["fname_probes"]
    delayed = summary["delayed_globals"]
    candidate_globals = summary["candidate_globals"]
    static_xrefs = summary["static_xrefs"]

    print("ReflectionScanner capture summary")
    print(f"files: {', '.join(summary['files'])}")
    print(f"candidate globals: {len(candidate_globals)}")
    print(f"delayed globals: {len(delayed)}")
    print(f"UObject validations: {len(uobjects)}")
    print(f"FName probes: {len(fnames)}")

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
                    "  line {line}: {instruction_address} {instruction}".format(**ref)
                )


def main() -> int:
    args = parse_args()
    summary = parse_logs(args.logs, args.objdump_xrefs)

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
