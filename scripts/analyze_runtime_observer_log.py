#!/usr/bin/env python3
"""Summarize gated runtime observer evidence from copied Obelisk logs.

The analyzer is intentionally passive. It reads sanitized or copied logs and turns
module observer lines into structured evidence that can be compared across chat,
inventory, structures, or future reflected modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import protected_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
LOG_PREFIX = r"(?:\[[^\]]+\]\s+)*"
PLAYER_PRINCIPAL_LIFECYCLE_MODULE = "player_principal_lifecycle"
REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
RUNTIME_OBSERVER_NON_CLAIMS = [
    "runtime observer analyzer summaries are passive copied-log summaries only",
    "approved_runtime_evidence remains false",
    "runtime_evidence_ready remains false",
    "copied-log readiness fields are not runtime readiness or approval",
    "accepted_count is an observer-line counter and does not approve runtime evidence",
    "diagnostic candidates, gate-only logs, passive-monitor transcripts, and unmerged multi-source logs remain non-evidence",
    "does not promote player identity, runtime readiness, public SDK readiness, or v1 completion",
]
SAFE_DETAIL_KEYS = {
    "chat": {
        "ServerSendChatMessage": {"send_mode", "send_mode_name", "send_mode_known"},
    },
    "player_principal_lifecycle": {
        "ShooterGameMode.HandleNewPlayer": {
            "copied_bool_fields",
            "copied_bool_values",
            "delivery_claim",
            "apply_status",
            "correlation_status",
            "post_original",
            "principal_action",
            "principal_generation_logged",
            "principal_id_logged",
            "redacted_count",
            "redacted_fields",
            "role",
        },
        "ShooterGameMode.OnLogout": {
            "copied_bool_fields",
            "copied_bool_values",
            "delivery_claim",
            "apply_status",
            "correlation_status",
            "post_original",
            "principal_action",
            "principal_generation_logged",
            "principal_id_logged",
            "redacted_count",
            "redacted_fields",
            "role",
        },
        "ShooterGameMode.CheckJoinInProgress": {
            "copied_bool_fields",
            "copied_bool_values",
            "delivery_claim",
            "apply_status",
            "correlation_status",
            "post_original",
            "principal_action",
            "principal_generation_logged",
            "principal_id_logged",
            "redacted_count",
            "redacted_fields",
            "role",
        },
    },
    "item_return": {
        "AllowEquipItem": {"callbacks", "field_mask"},
        "CanRepair": {"callbacks", "field_mask"},
        "UseItemOntoItem": {"callbacks", "field_mask"},
    },
}
PROMOTION_ONLY_BLOCKERS = {"runtime_observer_evidence_only"}
PLAYER_PRINCIPAL_SAFE_APPLY_CORRELATION = {
    ("session_start", "session_start_created", "not_applicable"),
    ("session_start_rejected", "session_start_rejected_noop", "not_applicable"),
    ("session_end", "session_end_invalidated", "matched"),
}
PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS = ("bIsFromLogin", "ReturnValue")
PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES = ("1", "0")
PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE = "ShooterGameMode.CheckJoinInProgress(1,0)"
PLAYER_PRINCIPAL_CHECK_JOIN_REDACTED_FIELDS = ("NewPlayer",)
DOWNSTREAM_RUNTIME_EVIDENCE_APPROVAL_AUTHORITY = "downstream_bundle_checker_only"
PLAYER_PRINCIPAL_STRICT_SESSION_START_CASE = {
    "target": "ShooterGameMode.HandleNewPlayer",
    "role": "session_start",
    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
    "copied_bool_values": ["1", "1"],
    "principal_action": "candidate_created",
    "apply_status": "session_start_created",
    "correlation_status": "not_applicable",
}
PLAYER_PRINCIPAL_STRICT_REJECTED_START_CASE = {
    "target": "ShooterGameMode.CheckJoinInProgress",
    "role": "session_start_rejected",
    "copied_bool_fields": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS),
    "copied_bool_values": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES),
    "principal_action": "none",
    "apply_status": "session_start_rejected_noop",
    "correlation_status": "not_applicable",
}
PLAYER_PRINCIPAL_STRICT_SESSION_END_CASE = {
    "target": "ShooterGameMode.OnLogout",
    "role": "session_end",
    "copied_bool_fields": [],
    "copied_bool_values": [],
    "principal_action": "candidate_invalidated",
    "apply_status": "session_end_invalidated",
    "correlation_status": "matched",
}
PLAYER_PRINCIPAL_STRICT_CASES_BY_ROLE = {
    str(case["role"]): case
    for case in (
        PLAYER_PRINCIPAL_STRICT_SESSION_START_CASE,
        PLAYER_PRINCIPAL_STRICT_REJECTED_START_CASE,
        PLAYER_PRINCIPAL_STRICT_SESSION_END_CASE,
    )
}
PLAYER_PRINCIPAL_STRICT_CASE_KEYS = (
    "target",
    "role",
    "copied_bool_fields",
    "copied_bool_values",
    "principal_action",
    "apply_status",
    "correlation_status",
)
PLAYER_PRINCIPAL_ALLOWED_DUPLICATE_CONTEXT_ROLES = frozenset(
    ("session_start", "session_end")
)


GATE_RE = re.compile(
    LOG_PREFIX
    + r"Experimental (?P<module>[A-Za-z0-9_]+) reflection enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{64})\.?"
)
ITEM_RETURN_GATE_RE = re.compile(
    LOG_PREFIX
    + r"Experimental item return event producer enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{64})\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_GATE_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleObserver enabled binary_sha256=(?P<sha256>[a-fA-F0-9]{64}) "
    r"target_set=(?P<target_set>players-lifecycle-anchor-candidates) "
    r"limit=(?P<limit>\d+) dispatch_limit=(?P<dispatch_limit>\d+) "
    r"delivery_claim=(?P<delivery_claim>[^.\s]+) principal_claim=(?P<principal_claim>[^.\s]+)\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleObserver event sequence=(?P<sequence>\d+) "
    r"role=(?P<role>session_start|session_end|session_start_rejected) "
    r"target=(?P<target>ShooterGameMode\.(?:HandleNewPlayer|OnLogout|CheckJoinInProgress)) "
    r"post_original=(?P<post_original>true|false) "
    r"copied_bool_fields=(?P<copied_bool_fields>\S*) "
    r"copied_bool_values=(?P<copied_bool_values>\S*) "
    r"redacted_count=(?P<redacted_count>\d+) "
    r"redacted_fields=(?P<redacted_fields>\S*) "
    r"principal_action=(?P<principal_action>candidate_created|candidate_invalidated|none) "
    r"apply_status=(?P<apply_status>unsupported_observation|session_start_created|session_start_allocation_failed|session_start_rejected_noop|session_end_unresolved_noop|session_end_invalidated|session_end_duplicate_noop|session_end_stale_noop|registry_failure) "
    r"correlation_status=(?P<correlation_status>not_applicable|missing|matched|duplicate|stale|unresolved) "
    r"principal_id_logged=(?P<principal_id_logged>true|false) "
    r"principal_generation_logged=(?P<principal_generation_logged>true|false) "
    r"delivery_claim=(?P<delivery_claim>[^.\s]+)\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATE_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleDiagnostic candidate (?P<rest>.+)"
)
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_ENABLED_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled "
    r"target_set=players-lifecycle-anchor-candidates limit=(?P<limit>\d+) "
    r"params_logged=false identity_logged=false evidence_claim=none principal_claim=none\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_ENABLED_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleDiagnostic function-FName near-miss logging enabled "
    r"scan_limit=(?P<scan_limit>\d+) params_logged=false identity_logged=false "
    r"evidence_claim=none principal_claim=none\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING_ENABLED_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleDiagnostic route-sampling enabled "
    r"sample_limit=(?P<sample_limit>\d+) params_logged=false identity_logged=false "
    r"evidence_claim=none principal_claim=none\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleDiagnostic route-sample sequence=(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+) fname_number=(?P<fname_number>-?\d+) "
    r"post_original=true accepted_lifecycle_target=false reflection_probe=false "
    r"params_logged=false identity_logged=false evidence_claim=none\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
PASSIVE_MONITOR_METADATA_RE = re.compile(
    r"^(?:passive_monitor_session\b|tick utc=|query(?:_warning)? instance=|"
    r"linuxgsm_skipped instance=|rcon_listplayers instance=|player_presence_context\b|"
    r"player_presence_detected instance=|"
    r"observer_tail instance=|observer instance=|player_presence_linger_(?:start|extend|complete)\b|"
    r"passive_snapshot_(?:captured|failed)\b|runtime_window(?:_|\b)|"
    r"(?:player_)?notice(?:_|\b)|beta_notice(?:_|\b)|confirmed_(?:beta_)?notice(?:_|\b))"
)
PROCESS_EVENT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) ProcessEvent #(?P<sequence>\d+) "
    r"function=(?P<function>\S+) fname_index=(?P<fname_index>-?\d+)"
    r"(?: outer_fname_index=(?P<outer_fname_index>-?\d+))?"
    r"(?: params=(?P<params>0x[0-9a-fA-F]+))? "
    r"fields=(?P<field_count>\d+)"
    r"(?: metadata_only=(?P<metadata_only>true|false))?"
)
FIELD_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) field (?P<field>\S+) "
    r"offset=(?P<offset>0x[0-9a-fA-F]+) size=(?P<size>\d+) (?P<rest>.*)"
)
REJECT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) rejected #(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+)"
    r"(?: function=(?P<function>\S+))? reason=(?P<reason>.+)"
)
ITEM_RETURN_REJECT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected item return rejected #(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+) reason=(?P<reason>.+)"
)
ITEM_RETURN_DISPATCH_RE = re.compile(
    LOG_PREFIX
    + r"Reflected item return dispatched #(?P<sequence>\d+) "
    r"function=(?P<function>\S+) fname_index=(?P<fname_index>-?\d+) "
    r"callbacks=(?P<callbacks>\d+) field_mask=(?P<field_mask>\S+)"
)
DETAIL_RE = re.compile(
    LOG_PREFIX + r"Reflected (?P<module>[A-Za-z0-9_]+) (?P<function>\S+) (?P<rest>.+)"
)
KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\S+)")
RUNTIME_LOADED_RE = re.compile(LOG_PREFIX + r"Obelisk Runtime Loaded Native \(LD_PRELOAD\)")
PROCESS_EVENT_CANDIDATES_RE = re.compile(
    LOG_PREFIX + r"ProcessEvent vtable-derived pattern candidates found: (?P<count>\d+)"
)
PROCESS_EVENT_CANDIDATE_RE = re.compile(
    LOG_PREFIX + r"ProcessEvent candidate\[(?P<index>\d+)\] = (?P<address>0x[0-9a-fA-F]+)"
)
PROCESS_EVENT_FOUND_RE = re.compile(
    LOG_PREFIX + r"Found ProcessEvent at address: (?P<address>0x[0-9a-fA-F]+)"
)
PROCESS_EVENT_HOOK_INSTALLED_RE = re.compile(
    LOG_PREFIX
    + r"ProcessEvent absolute x64 hook installed successfully\. "
    r"patch_size=(?P<patch_size>\d+) trampoline=(?P<trampoline>0x[0-9a-fA-F]+)"
)
PROCESS_EVENT_DETOUR_HIT_RE = re.compile(
    LOG_PREFIX
    + r"ProcessEvent detour hit #(?P<sequence>\d+) "
    r"object=(?P<object>\S+) function=(?P<function>\S+) params=(?P<params>\S+) "
    r"fname_index=(?P<fname_index>-?\d+) fname_number=(?P<fname_number>-?\d+)"
)
REFLECTION_SCANNER_DISABLED_RE = re.compile(
    LOG_PREFIX + r"ReflectionScanner disabled\. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 .*"
)
PLUGINS_DISABLED_RE = re.compile(
    LOG_PREFIX + r"Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1\."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def is_relative_to(path: Path, parent: Path) -> bool:
    return protected_paths.is_under_path(path, parent)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def bool_from_text(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def parse_key_values(text: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(text)}


def int_or_text(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def normalized_detail_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def detail_looks_identity_like(value: str) -> bool:
    normalized = normalized_detail_token(value)
    return any(
        fragment in normalized
        for fragment in PLAYER_PRINCIPAL_FORBIDDEN_CSV_TOKENS
        | PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_FORBIDDEN_VALUE_FRAGMENTS
    )


def detail_looks_raw_player_text(value: str) -> bool:
    normalized = normalized_detail_token(value)
    return any(fragment in normalized for fragment in {"chatmessage", "message", "rawtext", "text"})


def redacted_detail_label(key: str) -> str:
    if detail_looks_identity_like(key):
        return "identity_like_detail"
    if detail_looks_raw_player_text(key):
        return "raw_player_text_detail"
    return "unapproved_detail"


def add_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


LOG_BRACKET_PREFIX_RE = re.compile(r"^\s*(?:\[(?P<value>[^\]]+)\]\s*)+")
LOG_LEVEL_TOKENS = {"debug", "info", "warning", "warn", "error", "critical", "trace"}
LOG_CLOCK_TIMESTAMP_RE = re.compile(
    r"^(?P<hour>\d{1,2}):(?P<minute>\d{2}):(?P<second>\d{2})(?P<fraction>\.[0-9]+)?$"
)
LOG_ISO_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.[0-9]+)?Z$"
)


def extract_log_timestamp_prefix(line: str) -> str | None:
    """Return the first bracket prefix that looks like a time, not a log level."""
    prefix = LOG_BRACKET_PREFIX_RE.match(line)
    if prefix is None:
        return None
    for value in re.findall(r"\[([^\]]+)\]\s*", prefix.group(0)):
        if value.strip().lower() not in LOG_LEVEL_TOKENS:
            return value.strip()
    return None


def log_timestamp_order_key(line: str) -> tuple[str, float] | None:
    timestamp = extract_log_timestamp_prefix(line)
    if timestamp is None:
        return None

    if LOG_ISO_UTC_TIMESTAMP_RE.fullmatch(timestamp):
        try:
            parsed = datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
        except ValueError:
            return None
        return ("iso_utc", parsed.timestamp())

    match = LOG_CLOCK_TIMESTAMP_RE.fullmatch(timestamp)
    if match is None:
        return None
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    second = int(match.group("second"))
    if hour > 23 or minute > 59 or second > 59:
        return None
    fraction = float(match.group("fraction") or "0")
    return ("clock", float(hour * 3600 + minute * 60 + second) + fraction)


def record_latest_observer_line(
    record: dict[str, Any],
    *,
    source_index: int,
    line_number: int,
    line: str,
    kind: str,
) -> None:
    record["latest_observer_line"] = {
        "source_index": source_index,
        "line_number": line_number,
        "timestamp_prefix": extract_log_timestamp_prefix(line),
        "kind": kind,
    }


def record_player_principal_non_observer_line(
    record: dict[str, Any],
    *,
    source_index: int,
    line_number: int,
    line: str,
    kind: str,
) -> None:
    record_latest_observer_line(
        record,
        source_index=source_index,
        line_number=line_number,
        line=line,
        kind=kind,
    )
    record["non_observer_lifecycle_lines"] += 1


def record_player_principal_passive_monitor_line(
    record: dict[str, Any],
    *,
    source_index: int,
    line_number: int,
    line: str,
) -> None:
    record_latest_observer_line(
        record,
        source_index=source_index,
        line_number=line_number,
        line=line,
        kind="passive_monitor_metadata",
    )
    record["passive_monitor_metadata_lines"] += 1


PLAYER_PRINCIPAL_FORBIDDEN_CSV_TOKENS = {
    "eosid",
    "fname_index",
    "fnames",
    "gobjects",
    "ipaddress",
    "playerdataid",
    "playerid",
    "playername",
    "raw_params",
    "raw_pointer",
    "resourcehandle",
    "steamid",
    "tribeid",
    "uobject_address",
    "uobjectpointer",
    "uniquenetid",
}
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_PROPERTY_FNAME_CHAIN_FIELDS = {
    "expected_property_FName_chain": ("expected", "expected_property_fname_chain"),
    "expected_property_fname_chain": ("expected", "expected_property_fname_chain"),
    "expected_property_fname_indices": ("expected", "expected_property_fname_chain"),
    "expected_property_name_index_chain": ("expected", "expected_property_fname_chain"),
    "expected_property_name_indices": ("expected", "expected_property_fname_chain"),
    "observed_property_FName_chain": ("observed", "observed_property_fname_chain"),
    "observed_property_fname_chain": ("observed", "observed_property_fname_chain"),
    "observed_property_fname_indices": ("observed", "observed_property_fname_chain"),
    "observed_property_name_index_chain": ("observed", "observed_property_fname_chain"),
    "observed_property_name_indices": ("observed", "observed_property_fname_chain"),
}
_LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_FIELD_PATTERN = "|".join(
    re.escape(key)
    for key in sorted(
        PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_PROPERTY_FNAME_CHAIN_FIELDS,
        key=len,
        reverse=True,
    )
)
LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_FIELD_RE = re.compile(
    r"(?:^|_)(?P<source_key>"
    + _LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_FIELD_PATTERN
    + r")(?:=|_)(?P<chain>-?\d+(?:[._,]-?\d+)*)"
)
LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_MARKER_RE = re.compile(
    r"(?:^|_)(?P<source_key>"
    + _LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_FIELD_PATTERN
    + r")(?:=|_)"
)
LIFECYCLE_PROPERTY_FNAME_CHAIN_RE = re.compile(r"^-?\d+(?:[._,]-?\d+)*$")
LIFECYCLE_PROPERTY_FNAME_CHAIN_MAX_LENGTH = 64
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_ALLOWED_KEYS = {
    "accepted_lifecycle_target",
    "copy_status",
    "copied_bool_fields",
    "copied_bool_values",
    "diagnostic_shape",
    "evidence_claim",
    "fname_index",
    "identity_logged",
    "params_logged",
    "post_original",
    "read_status",
    "reason",
    "redacted_count",
    "redacted_fields",
    "reflection_status",
    "sequence",
    "target",
    *PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_PROPERTY_FNAME_CHAIN_FIELDS,
}
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_REQUIRED_KEYS = {
    "accepted_lifecycle_target",
    "evidence_claim",
    "fname_index",
    "identity_logged",
    "params_logged",
    "post_original",
    "sequence",
    "target",
}
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_TARGETS = {
    "GameMode.K2_PostLogin",
    "ShooterGameMode.CheckJoinInProgress",
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
    "ShooterGameMode.OnPostLogin__DelegateSignature",
    "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
}
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_READ_STATUSES = {
    "disabled",
    "implausible",
    "invalid_argument",
    "ok",
    "out_of_bounds",
    "unknown",
    "unreadable",
    "unsupported_layout",
}
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_FORBIDDEN_VALUE_FRAGMENTS = {
    "classobject",
    "eosid",
    "ipaddress",
    "params",
    "playerdataid",
    "playerid",
    "playername",
    "pointer",
    "raw_pointer",
    "resourcehandle",
    "steamid",
    "tribeid",
    "uniquenetid",
}
LIFECYCLE_PROPERTY_FNAME_MISMATCH_PREFIX = "lifecycle_property_FName_mismatch"
LIFECYCLE_PROPERTY_FNAME_DRIFT_PREFIX = "lifecycle_property_FName_drift"
DIAGNOSTIC_LIFECYCLE_PROPERTY_FNAME_MISMATCH_NON_EVIDENCE = (
    "diagnostic_lifecycle_property_fname_mismatch_non_evidence"
)
DIAGNOSTIC_CHECK_JOIN_IN_PROGRESS_NON_EVIDENCE = (
    "diagnostic_check_join_in_progress_non_evidence"
)
DIAGNOSTIC_ROUTE_SAMPLE_NON_EVIDENCE = "diagnostic_route_sample_non_evidence"
DIAGNOSTIC_REJECTED_DRIFT_NON_EVIDENCE = "diagnostic_rejected_drift_non_evidence"
DIAGNOSTIC_PROPERTY_FNAME_CHAIN_NON_EVIDENCE = "diagnostic_property_fname_chain_non_evidence"
PLAYER_PRINCIPAL_DIAGNOSTIC_CHECK_JOIN_BLOCKER = (
    "player_principal_diagnostic_check_join_in_progress_non_evidence"
)
PLAYER_PRINCIPAL_EVENT_SPLIT_NON_EVIDENCE = (
    "player_principal_lifecycle_event_split_non_evidence"
)
PLAYER_PRINCIPAL_EVENT_SPLIT_LABELS = (
    ("accepted_observer_event", "accepted observer event"),
    ("copy_status_rejected", "copy_status=rejected"),
    ("diagnostic_route_sample", "diagnostic route sample"),
    ("diagnostic_candidate", "diagnostic candidate"),
    ("session_end_unresolved_noop_missing", "session_end_unresolved_noop/missing"),
    (
        "missing_exact_check_join_in_progress_1_0",
        "missing exact CheckJoinInProgress(1,0)",
    ),
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_RICH_RE = re.compile(
    r"^"
    + re.escape(LIFECYCLE_PROPERTY_FNAME_MISMATCH_PREFIX)
    + r"_expected_name_index_(?P<expected>-?\d+)_observed_count_(?P<observed_count>\d+)(?:_.+)?$"
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_COMPACT_RE = re.compile(
    r"^"
    + re.escape(LIFECYCLE_PROPERTY_FNAME_MISMATCH_PREFIX)
    + r"_expected_(?P<expected>-?\d+)_observed_(?P<observed>-?\d+(?:_-?\d+)*)$"
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON_CHAIN_RE = re.compile(
    r"^"
    + re.escape(LIFECYCLE_PROPERTY_FNAME_MISMATCH_PREFIX)
    + r"_expected_name_index_(?P<expected>-?\d+)(?:_.+?)?"
    + r"_observed_property_fname_chain(?:=|_)(?P<observed>-?\d+(?:[._,]-?\d+)*)(?:_.+)?$"
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_PROP_NAME_RE = re.compile(
    r"(?:^|_)prop_(?P<index>\d+)_name_index_(?P<name_index>-?\d+)(?=_|$)"
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_TRUNCATED_RE = re.compile(
    r"(?:^|_)truncated(?:_|$)"
)
LIFECYCLE_PROPERTY_FNAME_MISMATCH_OPTIONAL_SUMMARY_KEYS = (
    "observed_present_count",
    "observed_name_indices_complete",
    "truncated",
)
LIFECYCLE_PROPERTY_FNAME_DRIFT_INT_RE = re.compile(
    r"(?:^|_)(?P<key>function_name_index|outer_name_index|drift_count)_(?P<value>-?\d+)(?=_|$)"
)
LIFECYCLE_PROPERTY_FNAME_DRIFT_ENTRY_RE = re.compile(
    r"(?:^|_)drift_(?P<index>\d+)_position_(?P<position>-?\d+)"
    r"_drift_(?P=index)_expected_name_index_(?P<expected>-?\d+)"
    r"_drift_(?P=index)_observed_name_index_(?P<observed>-?\d+)"
    r"_drift_(?P=index)_delta_(?P<delta>-?\d+)(?=_|$)"
)
PLAYER_PRINCIPAL_LIFECYCLE_REJECTED_DRIFT_TARGETS = {
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
}


def parse_space_key_values(text: str) -> dict[str, str] | None:
    if text.endswith("."):
        text = text[:-1]
    if not text:
        return None
    values: dict[str, str] = {}
    for token in text.split():
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if not key or not value or key in values:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_]+", key):
            return None
        values[key] = value
    return values


def safe_diagnostic_token(value: str) -> bool:
    if not PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_SAFE_TOKEN_RE.fullmatch(value):
        return False
    lowered = value.lower()
    normalized = re.sub(r"[_\.\:-]+", "", lowered)
    if "0x" in lowered or "0x" in normalized:
        return False
    return not any(
        fragment in normalized
        for fragment in PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_FORBIDDEN_VALUE_FRAGMENTS
    )


def parse_property_fname_chain(value: str) -> list[int] | None:
    if not LIFECYCLE_PROPERTY_FNAME_CHAIN_RE.fullmatch(value):
        return None
    indices = [int(part) for part in re.split(r"[._,]", value)]
    if not 1 <= len(indices) <= LIFECYCLE_PROPERTY_FNAME_CHAIN_MAX_LENGTH:
        return None
    return indices


def diagnostic_property_fname_chain_entries(
    details: dict[str, str],
) -> list[dict[str, Any]] | None:
    entries: list[dict[str, Any]] = []
    for source_key, value in sorted(details.items()):
        chain_field = PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_PROPERTY_FNAME_CHAIN_FIELDS.get(
            source_key
        )
        if chain_field is None:
            continue
        chain = parse_property_fname_chain(value)
        if chain is None:
            return None
        chain_kind, field = chain_field
        entries.append(
            {
                "source_key": source_key,
                "field": field,
                "chain_kind": chain_kind,
                "name_indices": chain,
                "name_index_count": len(chain),
            }
        )
    reason = details.get("reason")
    if reason is not None:
        reason_entries = diagnostic_property_fname_chain_entries_from_reason(reason)
        if reason_entries is None:
            return None
        entries.extend(reason_entries)
    return entries


def diagnostic_property_fname_chain_key(entry: dict[str, Any]) -> str:
    chain = ".".join(str(index) for index in entry["name_indices"])
    return f"{entry['field']}:{chain}"


def diagnostic_property_fname_chain_entries_from_reason(
    reason: str,
) -> list[dict[str, Any]] | None:
    entries: list[dict[str, Any]] = []
    for marker in LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_MARKER_RE.finditer(reason):
        match = LIFECYCLE_PROPERTY_FNAME_CHAIN_REASON_FIELD_RE.match(
            reason,
            marker.start(),
        )
        if match is None:
            return None
        source_key = match.group("source_key")
        chain_field = PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_PROPERTY_FNAME_CHAIN_FIELDS[
            source_key
        ]
        chain = parse_property_fname_chain(match.group("chain"))
        if chain is None:
            return None
        chain_kind, field = chain_field
        entries.append(
            {
                "source_key": f"reason.{source_key}",
                "field": field,
                "chain_kind": chain_kind,
                "name_indices": chain,
                "name_index_count": len(chain),
            }
        )
    return entries


def add_diagnostic_property_fname_chain_metadata(
    record: dict[str, Any],
    details: dict[str, str],
    *,
    source_index: int,
    line_number: int,
    line: str,
) -> None:
    entries = diagnostic_property_fname_chain_entries(details)
    if not entries:
        return

    sequence = int(details["sequence"])
    summaries = record["diagnostic_candidate_property_fname_chains"]
    for entry in entries:
        summary_key = diagnostic_property_fname_chain_key(entry)
        summary = summaries.setdefault(
            summary_key,
            {
                "field": entry["field"],
                "chain_kind": entry["chain_kind"],
                "name_indices": entry["name_indices"],
                "name_index_count": entry["name_index_count"],
                "source_keys": [],
                "count": 0,
                "target_counts": Counter(),
                "read_status_counts": Counter(),
                "fname_indices": [],
                "first_sequence": None,
                "latest_sequence": None,
                "latest_occurrence": None,
            },
        )
        add_unique(summary["source_keys"], entry["source_key"])
        summary["count"] += 1
        target = details["target"]
        summary["target_counts"][target] += 1
        read_status = details.get("read_status")
        if read_status:
            summary["read_status_counts"][read_status] += 1
        add_unique(summary["fname_indices"], int(details["fname_index"]))
        if summary["first_sequence"] is None or sequence < summary["first_sequence"]:
            summary["first_sequence"] = sequence
        if summary["latest_sequence"] is None or sequence >= summary["latest_sequence"]:
            summary["latest_sequence"] = sequence
            summary["latest_occurrence"] = {
                "source_index": source_index,
                "line_number": line_number,
                "timestamp_prefix": extract_log_timestamp_prefix(line),
                "target": target,
            }


def lifecycle_property_fname_mismatch_key(expected: int, observed: list[int]) -> str:
    return f"expected_{expected}_observed_" + "_".join(str(value) for value in observed)


def lifecycle_property_fname_mismatch_optional_summary_fields(
    record: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: record[key]
        for key in LIFECYCLE_PROPERTY_FNAME_MISMATCH_OPTIONAL_SUMMARY_KEYS
        if key in record
    }


def lifecycle_property_fname_mismatch_summary(reason: str) -> dict[str, Any] | None:
    if match := LIFECYCLE_PROPERTY_FNAME_MISMATCH_COMPACT_RE.fullmatch(reason):
        observed = [int(value) for value in match.group("observed").split("_")]
        expected = int(match.group("expected"))
        return {
            "summary": lifecycle_property_fname_mismatch_key(expected, observed),
            "expected_name_index": expected,
            "observed_count": len(observed),
            "observed_name_indices": observed,
        }

    if match := LIFECYCLE_PROPERTY_FNAME_MISMATCH_REASON_CHAIN_RE.fullmatch(reason):
        observed = [
            int(value)
            for value in re.split(r"[._,]", match.group("observed"))
        ]
        expected = int(match.group("expected"))
        return {
            "summary": lifecycle_property_fname_mismatch_key(expected, observed),
            "expected_name_index": expected,
            "observed_count": len(observed),
            "observed_name_indices": observed,
        }

    match = LIFECYCLE_PROPERTY_FNAME_MISMATCH_RICH_RE.fullmatch(reason)
    if not match:
        return None

    expected = int(match.group("expected"))
    observed_count = int(match.group("observed_count"))
    if observed_count < 1:
        return None

    observed_by_index: dict[int, int] = {}
    for property_match in LIFECYCLE_PROPERTY_FNAME_MISMATCH_PROP_NAME_RE.finditer(reason):
        index = int(property_match.group("index"))
        if index in observed_by_index:
            return None
        observed_by_index[index] = int(property_match.group("name_index"))

    if sorted(observed_by_index) != list(range(observed_count)):
        observed_indices = sorted(observed_by_index)
        is_partial_truncated_prefix = (
            bool(LIFECYCLE_PROPERTY_FNAME_MISMATCH_TRUNCATED_RE.search(reason))
            and 0 < len(observed_indices) < observed_count
            and observed_indices == list(range(len(observed_indices)))
        )
        if not is_partial_truncated_prefix:
            return None
        observed = [observed_by_index[index] for index in observed_indices]
        return {
            "summary": lifecycle_property_fname_mismatch_key(expected, observed),
            "expected_name_index": expected,
            "observed_count": observed_count,
            "observed_name_indices": observed,
            "observed_present_count": len(observed),
            "observed_name_indices_complete": False,
            "truncated": True,
        }

    observed = [observed_by_index[index] for index in range(observed_count)]
    return {
        "summary": lifecycle_property_fname_mismatch_key(expected, observed),
        "expected_name_index": expected,
        "observed_count": observed_count,
        "observed_name_indices": observed,
    }


def lifecycle_property_fname_mismatch_target_record() -> dict[str, Any]:
    return {
        "count": 0,
        "read_status_counts": Counter(),
        "fname_indices": [],
        "first_sequence": None,
        "latest_sequence": None,
        "latest_occurrence": None,
    }


def add_lifecycle_property_fname_mismatch_summary(
    record: dict[str, Any],
    details: dict[str, str],
    *,
    source_index: int,
    line_number: int,
    line: str,
) -> None:
    reason = details.get("reason")
    if reason is None:
        return
    summary = lifecycle_property_fname_mismatch_summary(reason)
    if summary is None:
        return
    summary_key = summary["summary"]
    if not summary.get("observed_name_indices_complete", True):
        summary_key = f"{summary_key}_partial_observed_count_{summary['observed_count']}"
    sequence = int(details["sequence"])
    summaries = record["diagnostic_candidate_lifecycle_property_fname_mismatches"]
    entry = summaries.setdefault(
        summary_key,
        {
            **summary,
            "count": 0,
            "reason_counts": Counter(),
            "target_counts": Counter(),
            "read_status_counts": Counter(),
            "fname_indices": [],
            "first_sequence": None,
            "latest_sequence": None,
            "latest_occurrence": None,
            "target_details": {},
        },
    )
    entry["count"] += 1
    entry["reason_counts"][reason] += 1
    target = details["target"]
    entry["target_counts"][target] += 1
    read_status = details.get("read_status")
    if read_status:
        entry["read_status_counts"][read_status] += 1
    add_unique(entry["fname_indices"], int(details["fname_index"]))
    if entry["first_sequence"] is None or sequence < entry["first_sequence"]:
        entry["first_sequence"] = sequence
    if entry["latest_sequence"] is None or sequence >= entry["latest_sequence"]:
        entry["latest_sequence"] = sequence
        entry["latest_occurrence"] = {
            "source_index": source_index,
            "line_number": line_number,
            "timestamp_prefix": extract_log_timestamp_prefix(line),
            "target": details["target"],
        }
    target_entry = entry["target_details"].setdefault(
        target,
        lifecycle_property_fname_mismatch_target_record(),
    )
    target_entry["count"] += 1
    if read_status:
        target_entry["read_status_counts"][read_status] += 1
    add_unique(target_entry["fname_indices"], int(details["fname_index"]))
    if target_entry["first_sequence"] is None or sequence < target_entry["first_sequence"]:
        target_entry["first_sequence"] = sequence
    if target_entry["latest_sequence"] is None or sequence >= target_entry["latest_sequence"]:
        target_entry["latest_sequence"] = sequence
        target_entry["latest_occurrence"] = {
            "source_index": source_index,
            "line_number": line_number,
            "timestamp_prefix": extract_log_timestamp_prefix(line),
        }


def lifecycle_property_fname_drift_summary(reason: str) -> dict[str, Any] | None:
    if not reason.startswith(LIFECYCLE_PROPERTY_FNAME_DRIFT_PREFIX):
        return None

    values = {
        match.group("key"): int(match.group("value"))
        for match in LIFECYCLE_PROPERTY_FNAME_DRIFT_INT_RE.finditer(reason)
    }
    drifts = [
        {
            "index": int(match.group("index")),
            "position": int(match.group("position")),
            "expected_name_index": int(match.group("expected")),
            "observed_name_index": int(match.group("observed")),
            "delta": int(match.group("delta")),
        }
        for match in LIFECYCLE_PROPERTY_FNAME_DRIFT_ENTRY_RE.finditer(reason)
    ]
    drifts.sort(key=lambda item: item["index"])
    summary: dict[str, Any] = {
        "reason_kind": LIFECYCLE_PROPERTY_FNAME_DRIFT_PREFIX,
    }
    if "function_name_index" in values:
        summary["function_name_index"] = values["function_name_index"]
    if "outer_name_index" in values:
        summary["outer_name_index"] = values["outer_name_index"]
    if "drift_count" in values:
        summary["drift_count"] = values["drift_count"]
    if drifts:
        summary["drifts"] = drifts
    return summary


def player_principal_lifecycle_rejected_drift_summary(
    details: dict[str, str],
    *,
    line_number: int,
    line: str,
) -> dict[str, Any] | None:
    target = details.get("target")
    reason = details.get("reason")
    if (
        target not in PLAYER_PRINCIPAL_LIFECYCLE_REJECTED_DRIFT_TARGETS
        or details.get("accepted_lifecycle_target") != "true"
        or details.get("reflection_status") != "rejected"
        or reason is None
    ):
        return None
    drift = lifecycle_property_fname_drift_summary(reason)
    if drift is None:
        return None
    return {
        "target": target,
        "sequence": int(details["sequence"]),
        "line_number": line_number,
        "timestamp_prefix": extract_log_timestamp_prefix(line),
        "fname_index": int(details["fname_index"]),
        "reflection_status": "rejected",
        "read_status": details.get("read_status"),
        "reason": reason,
        **drift,
        "evidence_claim": "none",
        "evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "ready": False,
        "readiness_gate": "none",
    }


def record_player_principal_lifecycle_rejected_drift(
    record: dict[str, Any],
    details: dict[str, str],
    *,
    line_number: int,
    line: str,
) -> None:
    summary = player_principal_lifecycle_rejected_drift_summary(
        details,
        line_number=line_number,
        line=line,
    )
    if summary is None:
        return
    target = summary["target"]
    record["diagnostic_candidate_rejected_drift_count"] += 1
    record["diagnostic_candidate_rejected_drift_target_counts"][target] += 1
    latest = record["diagnostic_candidate_latest_rejected_drift_by_target"].get(target)
    if latest is None or summary["sequence"] >= latest["sequence"]:
        record["diagnostic_candidate_latest_rejected_drift_by_target"][target] = summary


def check_join_in_progress_shape(copied_bool_values: str) -> str:
    return f"ShooterGameMode.CheckJoinInProgress({copied_bool_values})"


def record_player_principal_lifecycle_check_join_diagnostic(
    record: dict[str, Any],
    details: dict[str, str],
    *,
    line_number: int,
    line: str,
) -> None:
    if details.get("diagnostic_shape") != "CheckJoinInProgress":
        return

    copied_bool_values = details.get("copied_bool_values")
    if copied_bool_values is None:
        return

    sequence = int(details["sequence"])
    shape = check_join_in_progress_shape(copied_bool_values)
    record["diagnostic_candidate_check_join_in_progress_count"] += 1
    record["diagnostic_candidate_check_join_in_progress_shape_counts"][shape] += 1
    record["diagnostic_candidate_check_join_in_progress_accepted_target_counts"][
        details["accepted_lifecycle_target"]
    ] += 1
    record["diagnostic_candidate_check_join_in_progress_reflection_status_counts"][
        details.get("reflection_status", "missing")
    ] += 1
    record["diagnostic_candidate_check_join_in_progress_copy_status_counts"][
        details.get("copy_status", "none")
    ] += 1

    if tuple(copied_bool_values.split(",")) != PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES:
        return

    record["diagnostic_candidate_check_join_in_progress_strict_shape_count"] += 1
    if details.get("copy_status") == "rejected":
        record["diagnostic_candidate_check_join_in_progress_strict_shape_copy_rejected_count"] += 1

    latest = record["diagnostic_candidate_check_join_in_progress_latest_strict_shape"]
    if latest is None or sequence >= latest["sequence"]:
        record["diagnostic_candidate_check_join_in_progress_latest_strict_shape"] = {
            "sequence": sequence,
            "line_number": line_number,
            "timestamp_prefix": extract_log_timestamp_prefix(line),
            "target": details["target"],
            "diagnostic_shape": "CheckJoinInProgress",
            "copied_bool_fields": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS),
            "copied_bool_values": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES),
            "strict_shape": PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE,
            "accepted_lifecycle_target": details["accepted_lifecycle_target"] == "true",
            "reflection_status": details.get("reflection_status"),
            "copy_status": details.get("copy_status", "none"),
            "evidence_claim": "none",
            "evidence_classification": DIAGNOSTIC_CHECK_JOIN_IN_PROGRESS_NON_EVIDENCE,
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "ready": False,
            "readiness_gate": "none",
        }


def csv_values(
    value: str,
    *,
    allowed: set[str] | None = None,
    allow_duplicates: bool = False,
) -> list[str] | None:
    if value == "":
        return []
    parts = value.split(",")
    if any(part == "" for part in parts):
        return None
    if not allow_duplicates and len(set(parts)) != len(parts):
        return None
    for part in parts:
        lowered = part.lower()
        if lowered in PLAYER_PRINCIPAL_FORBIDDEN_CSV_TOKENS:
            return None
        if allowed is not None and part not in allowed:
            return None
    return parts


def player_principal_lifecycle_gate_is_safe(match: re.Match[str]) -> bool:
    limit = int(match.group("limit"))
    return (
        match.group("target_set") == "players-lifecycle-anchor-candidates"
        and 1 <= limit <= 10
        and match.group("dispatch_limit") == "0"
        and match.group("delivery_claim") == "none"
        and match.group("principal_claim") == "none"
    )


def player_principal_lifecycle_event_is_safe(match: re.Match[str]) -> bool:
    return player_principal_lifecycle_event_unsafe_reason(match) is None


def player_principal_lifecycle_event_unsafe_reason(match: re.Match[str]) -> str | None:
    target = match.group("target")
    role = match.group("role")
    post_original = match.group("post_original")
    copied_bool_fields = csv_values(
        match.group("copied_bool_fields"),
        allowed={"bIsFromLogin", "ReturnValue"},
    )
    copied_bool_values = csv_values(
        match.group("copied_bool_values"),
        allowed={"0", "1"},
        allow_duplicates=True,
    )
    redacted_count = int(match.group("redacted_count"))
    redacted_fields = csv_values(
        match.group("redacted_fields"),
        allowed={"NewPlayer", "PlayerData", "PlayerCharacter", "Exiting"},
    )
    principal_action = match.group("principal_action")
    apply_status = match.group("apply_status")
    correlation_status = match.group("correlation_status")

    if (
        copied_bool_fields is None
        or copied_bool_values is None
        or redacted_fields is None
        or match.group("principal_id_logged") != "false"
        or match.group("principal_generation_logged") != "false"
        or match.group("delivery_claim") != "none"
    ):
        return "unsafe_or_unapproved_fields"
    if post_original != "true":
        return "pre_original_or_unproven_original_event"
    if (role, apply_status, correlation_status) not in PLAYER_PRINCIPAL_SAFE_APPLY_CORRELATION:
        if apply_status == "unsupported_observation":
            return "unsupported_observation_outcome"
        if apply_status == "registry_failure":
            return "registry_failure_outcome"
        if role == "session_end":
            if apply_status in {
                "session_end_unresolved_noop",
                "session_end_duplicate_noop",
                "session_end_stale_noop",
            }:
                return f"{apply_status}_outcome"
            if apply_status != "session_end_invalidated":
                return "session_end_apply_status_not_invalidated"
            return f"session_end_correlation_status_{correlation_status}"
        return "apply_or_correlation_status_mismatch"

    if target == "ShooterGameMode.HandleNewPlayer":
        if copied_bool_fields != ["bIsFromLogin", "ReturnValue"]:
            return "unsafe_or_unapproved_fields"
        if len(copied_bool_values) != 2:
            return "unsafe_or_unapproved_fields"
        if redacted_count != 3 or redacted_fields != ["NewPlayer", "PlayerData", "PlayerCharacter"]:
            return "unsafe_or_unapproved_fields"
        is_from_login = copied_bool_values[0]
        return_value = copied_bool_values[1]
        if role == "session_start":
            if principal_action != "candidate_created" or copied_bool_values != ["1", "1"]:
                return "session_start_semantics_mismatch"
            return None
        if role == "session_start_rejected":
            if principal_action != "none" or (is_from_login != "0" and return_value != "0"):
                return "session_start_rejected_semantics_mismatch"
            return "superseded_handle_new_player_rejected_start_non_evidence"
        return "target_role_mismatch"

    if target == "ShooterGameMode.CheckJoinInProgress":
        if role != "session_start_rejected":
            return "target_role_mismatch"
        if len(copied_bool_fields) != 2 or len(copied_bool_values) != 2:
            return "unsafe_or_unapproved_fields"
        if tuple(copied_bool_fields) != PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS:
            if set(copied_bool_fields) == set(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS):
                return "check_join_in_progress_copied_bool_fields_order_mismatch"
            return "unsafe_or_unapproved_fields"
        if redacted_count != 1 or tuple(redacted_fields) != PLAYER_PRINCIPAL_CHECK_JOIN_REDACTED_FIELDS:
            return "unsafe_or_unapproved_fields"
        if principal_action != "none":
            return "session_start_rejected_semantics_mismatch"
        if tuple(copied_bool_values) != PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES:
            return "unsupported_check_join_in_progress_bool_tuple"
        return None

    if target == "ShooterGameMode.OnLogout":
        if role != "session_end":
            return "target_role_mismatch"
        if (
            copied_bool_fields != []
            or copied_bool_values != []
            or redacted_count != 1
            or redacted_fields != ["Exiting"]
        ):
            return "unsafe_or_unapproved_fields"
        if principal_action != "candidate_invalidated":
            return "session_end_semantics_mismatch"
        return None

    return "target_role_mismatch"


def player_principal_lifecycle_event_has_quality_violation(
    record: dict[str, Any],
    *,
    sequence: int,
    line: str,
) -> bool:
    violation = False
    seen_sequences = record["_player_principal_seen_sequences"]
    last_sequence = record["_player_principal_last_sequence"]
    log_limit = record["_player_principal_log_limit"]
    if (
        sequence < 1
        or sequence in seen_sequences
        or (last_sequence is not None and sequence <= last_sequence)
        or (log_limit is not None and sequence > log_limit)
    ):
        record["sequence_quality_violations"] += 1
        violation = True

    timestamp_key = log_timestamp_order_key(line)
    last_timestamp_key = record["_player_principal_last_timestamp_key"]
    if (
        timestamp_key is not None
        and last_timestamp_key is not None
        and timestamp_key[0] == last_timestamp_key[0]
        and timestamp_key[1] < last_timestamp_key[1]
    ):
        record["timestamp_quality_violations"] += 1
        violation = True

    seen_sequences.add(sequence)
    if not violation:
        record["_player_principal_last_sequence"] = sequence
        if timestamp_key is not None:
            record["_player_principal_last_timestamp_key"] = timestamp_key
    return violation


def player_principal_lifecycle_diagnostic_candidate_details(line: str) -> dict[str, str] | None:
    match = PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATE_RE.fullmatch(line)
    if not match:
        return None

    details = parse_space_key_values(match.group("rest"))
    if details is None:
        return None
    if set(details) - PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_ALLOWED_KEYS:
        return None
    if not PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_REQUIRED_KEYS.issubset(details):
        return None
    if details["evidence_claim"] != "none":
        return None
    if details["params_logged"] != "false" or details["identity_logged"] != "false":
        return None
    if details["post_original"] != "true":
        return None
    if details["accepted_lifecycle_target"] not in {"true", "false"}:
        return None
    if not details["sequence"].isdigit() or int(details["sequence"]) < 1:
        return None
    if not re.fullmatch(r"-?\d+", details["fname_index"]):
        return None
    if details["target"] not in PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_TARGETS:
        return None
    if not safe_diagnostic_token(details["target"]):
        return None
    if diagnostic_property_fname_chain_entries(details) is None:
        return None

    reflection_status = details.get("reflection_status")
    if reflection_status is not None and reflection_status not in {"matched", "rejected"}:
        return None
    copy_status = details.get("copy_status")
    if copy_status is not None and copy_status != "rejected":
        return None
    read_status = details.get("read_status")
    if read_status is not None and read_status not in PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_READ_STATUSES:
        return None
    reason = details.get("reason")
    if reason is not None and not safe_diagnostic_token(reason):
        return None
    if reflection_status == "rejected" and (read_status is None or reason is None):
        return None
    diagnostic_shape = details.get("diagnostic_shape")
    if diagnostic_shape is not None and diagnostic_shape not in {
        "CheckJoinInProgress",
        "FunctionFNameNearMiss",
        "K2_PostLogin",
    }:
        return None
    has_copied_bool_diagnostic = any(
        key in details for key in ("copied_bool_fields", "copied_bool_values")
    )
    has_redacted_diagnostic = any(key in details for key in ("redacted_count", "redacted_fields"))
    if diagnostic_shape == "CheckJoinInProgress" and (
        has_copied_bool_diagnostic or has_redacted_diagnostic
    ):
        if (
            details["target"] != "ShooterGameMode.CheckJoinInProgress"
            or reflection_status != "matched"
            or details.get("copied_bool_fields") != "bIsFromLogin,ReturnValue"
            or details.get("redacted_count") != "1"
            or details.get("redacted_fields") != "NewPlayer"
        ):
            return None
        if details["accepted_lifecycle_target"] == "true":
            if copy_status != "rejected":
                return None
        elif copy_status is not None:
            return None
        copied_bool_values = details.get("copied_bool_values")
        if copied_bool_values not in {"0,0", "0,1", "1,0", "1,1"}:
            return None
    elif diagnostic_shape == "FunctionFNameNearMiss":
        if (
            details["accepted_lifecycle_target"] != "false"
            or reflection_status != "matched"
            or details.get("read_status") != "ok"
            or details.get("reason") is None
            or details.get("copy_status") is not None
            or has_copied_bool_diagnostic
            or has_redacted_diagnostic
        ):
            return None
    elif diagnostic_shape == "K2_PostLogin":
        if (
            details["target"] != "GameMode.K2_PostLogin"
            or details["accepted_lifecycle_target"] != "false"
            or has_copied_bool_diagnostic
        ):
            return None
        if has_redacted_diagnostic:
            if (
                reflection_status != "matched"
                or details.get("copy_status") is not None
                or details.get("redacted_count") != "1"
                or details.get("redacted_fields") != "NewPlayer"
            ):
                return None
        elif reflection_status == "matched" and copy_status is None:
            return None
    elif has_copied_bool_diagnostic or has_redacted_diagnostic:
        return None
    return details


def module_record() -> dict[str, Any]:
    return {
        "gate_sha256": [],
        "source_indices": [],
        "source_merge_explicit": False,
        "accepted_count": 0,
        "metadata_only_count": 0,
        "rejected_count": 0,
        "functions": {},
        "fields": {},
        "reject_reasons": {},
        "redacted_detail_keys": Counter(),
        "malformed_observer_lines": 0,
        "orphan_field_lines": 0,
        "out_of_order_field_lines": 0,
        "field_count_mismatches": 0,
        "sequence_quality_violations": 0,
        "timestamp_quality_violations": 0,
        "event_before_gate_lines": 0,
        "observed_event_cases": [],
        "observer_gate_count": 0,
        "diagnostic_candidate_count": 0,
        "diagnostic_candidate_max_sequence": None,
        "diagnostic_log_limits": [],
        "diagnostic_near_miss_scan_limits": [],
        "diagnostic_route_sample_count": 0,
        "diagnostic_route_sample_max_sequence": None,
        "diagnostic_route_sample_limits": [],
        "diagnostic_route_sample_fname_index_counts": Counter(),
        "diagnostic_route_sample_latest": None,
        "diagnostic_candidate_target_counts": Counter(),
        "diagnostic_candidate_copy_status_counts": Counter(),
        "diagnostic_candidate_reason_counts": Counter(),
        "diagnostic_candidate_read_status_counts": Counter(),
        "diagnostic_candidate_property_fname_chains": {},
        "diagnostic_candidate_lifecycle_property_fname_mismatches": {},
        "diagnostic_candidate_rejected_drift_count": 0,
        "diagnostic_candidate_rejected_drift_target_counts": Counter(),
        "diagnostic_candidate_latest_rejected_drift_by_target": {},
        "diagnostic_candidate_check_join_in_progress_count": 0,
        "diagnostic_candidate_check_join_in_progress_shape_counts": Counter(),
        "diagnostic_candidate_check_join_in_progress_accepted_target_counts": Counter(),
        "diagnostic_candidate_check_join_in_progress_reflection_status_counts": Counter(),
        "diagnostic_candidate_check_join_in_progress_copy_status_counts": Counter(),
        "diagnostic_candidate_check_join_in_progress_strict_shape_count": 0,
        "diagnostic_candidate_check_join_in_progress_strict_shape_copy_rejected_count": 0,
        "diagnostic_candidate_check_join_in_progress_latest_strict_shape": None,
        "unsafe_lifecycle_event_reasons": Counter(),
        "lifecycle_rejected_observer_event_count": 0,
        "lifecycle_event_split_counts": Counter(),
        "latest_observer_line": None,
        "non_observer_lifecycle_lines": 0,
        "passive_monitor_metadata_lines": 0,
        "_player_principal_gate_seen_by_source": set(),
        "_player_principal_last_sequence": None,
        "_player_principal_last_timestamp_key": None,
        "_player_principal_seen_sequences": set(),
        "_player_principal_log_limit": None,
        "_player_principal_diagnostic_log_limits_by_source": {},
        "_player_principal_diagnostic_max_sequence_by_source": {},
        "_player_principal_route_sample_limits_by_source": {},
        "_player_principal_route_sample_max_sequence_by_source": {},
    }


def runtime_record() -> dict[str, Any]:
    return {
        "loaded_native_ld_preload": False,
        "process_event_candidate_count": None,
        "process_event_candidates": [],
        "process_event_address": None,
        "process_event_hook_installed": False,
        "process_event_hook_patch_size": None,
        "broad_process_event_trace_lines": 0,
        "reflection_scanner_disabled": False,
        "plugins_disabled": False,
        "passive_monitor_metadata_lines": 0,
    }


def function_record() -> dict[str, Any]:
    return {
        "accepted": 0,
        "metadata_only": 0,
        "fname_indices": [],
        "outer_fname_indices": [],
        "field_counts": [],
        "details": defaultdict(list),
        "fields": {},
    }


def field_record() -> dict[str, Any]:
    return {
        "count": 0,
        "offsets": [],
        "sizes": [],
        "has_range": Counter(),
        "sensitive": Counter(),
    }


def normalize_function(record: dict[str, Any]) -> dict[str, Any]:
    details = {
        key: sorted(values, key=lambda item: str(item))
        for key, values in record["details"].items()
    }
    return {
        "accepted": record["accepted"],
        "metadata_only": record["metadata_only"],
        "fname_indices": sorted(record["fname_indices"]),
        "outer_fname_indices": sorted(record["outer_fname_indices"]),
        "field_counts": sorted(record["field_counts"]),
        "details": details,
        "fields": {
            name: normalize_field(field)
            for name, field in sorted(record["fields"].items())
        },
    }


def normalize_field(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": record["count"],
        "offsets": sorted(record["offsets"]),
        "sizes": sorted(record["sizes"]),
        "has_range": dict(sorted(record["has_range"].items())),
        "sensitive": dict(sorted(record["sensitive"].items())),
    }


def normalize_lifecycle_property_fname_mismatches(
    records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "summary": record["summary"],
            "expected_name_index": record["expected_name_index"],
            "observed_count": record["observed_count"],
            "observed_name_indices": record["observed_name_indices"],
            **lifecycle_property_fname_mismatch_optional_summary_fields(record),
            "count": record["count"],
            "target_counts": dict(sorted(record["target_counts"].items())),
            "read_status_counts": dict(sorted(record["read_status_counts"].items())),
            "fname_indices": sorted(record["fname_indices"]),
            "first_sequence": record["first_sequence"],
            "latest_sequence": record["latest_sequence"],
            "latest_occurrence": record["latest_occurrence"],
            "evidence_claim": "none",
            "evidence_classification": (
                DIAGNOSTIC_LIFECYCLE_PROPERTY_FNAME_MISMATCH_NON_EVIDENCE
            ),
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "readiness_gate": "none",
            "reason_counts": dict(sorted(record["reason_counts"].items())),
        }
        for _, record in sorted(records.items())
    ]


def normalize_lifecycle_property_fname_mismatch_compact_summary(
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    patterns = [
        {
            "summary": record["summary"],
            "expected_name_index": record["expected_name_index"],
            "observed_count": record["observed_count"],
            "observed_name_indices": record["observed_name_indices"],
            **lifecycle_property_fname_mismatch_optional_summary_fields(record),
            "count": record["count"],
            "target_counts": dict(sorted(record["target_counts"].items())),
            "read_status_counts": dict(sorted(record["read_status_counts"].items())),
            "fname_indices": sorted(record["fname_indices"]),
            "latest_sequence": record["latest_sequence"],
        }
        for _, record in sorted(records.items())
    ]
    return {
        "count": sum(pattern["count"] for pattern in patterns),
        "evidence_claim": "none",
        "evidence_classification": (
            DIAGNOSTIC_LIFECYCLE_PROPERTY_FNAME_MISMATCH_NON_EVIDENCE
        ),
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "readiness_gate": "none",
        "patterns": patterns,
    }


def normalize_lifecycle_property_fname_mismatch_target_summary(
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    target_summaries: dict[str, dict[str, Any]] = {}
    for _, record in sorted(records.items()):
        for target, target_record in sorted(record.get("target_details", {}).items()):
            target_summary = target_summaries.setdefault(
                target,
                {
                    "target": target,
                    "count": 0,
                    "patterns": [],
                },
            )
            target_summary["count"] += target_record["count"]
            target_summary["patterns"].append(
                {
                    "summary": record["summary"],
                    "expected_name_index": record["expected_name_index"],
                    "observed_count": record["observed_count"],
                    "observed_name_indices": record["observed_name_indices"],
                    **lifecycle_property_fname_mismatch_optional_summary_fields(record),
                    "count": target_record["count"],
                    "read_status_counts": dict(
                        sorted(target_record["read_status_counts"].items())
                    ),
                    "fname_indices": sorted(target_record["fname_indices"]),
                    "first_sequence": target_record["first_sequence"],
                    "latest_sequence": target_record["latest_sequence"],
                    "latest_occurrence": target_record["latest_occurrence"],
                }
            )

    targets = []
    for _, target_summary in sorted(target_summaries.items()):
        target_summary["pattern_count"] = len(target_summary["patterns"])
        targets.append(target_summary)

    return {
        "count": sum(target["count"] for target in targets),
        "target_count": len(targets),
        "evidence_claim": "none",
        "evidence_classification": (
            DIAGNOSTIC_LIFECYCLE_PROPERTY_FNAME_MISMATCH_NON_EVIDENCE
        ),
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "readiness_gate": "none",
        "targets": targets,
    }


def normalize_diagnostic_property_fname_chain_metadata(
    records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries = [
        {
            "field": record["field"],
            "chain_kind": record["chain_kind"],
            "source_keys": sorted(record["source_keys"]),
            "complete_chain_summary": True,
            "name_index_count": record["name_index_count"],
            "name_indices": record["name_indices"],
            "count": record["count"],
            "target_counts": dict(sorted(record["target_counts"].items())),
            "read_status_counts": dict(sorted(record["read_status_counts"].items())),
            "fname_indices": sorted(record["fname_indices"]),
            "first_sequence": record["first_sequence"],
            "latest_sequence": record["latest_sequence"],
            "latest_occurrence": record["latest_occurrence"],
            "evidence_claim": "none",
            "evidence_classification": DIAGNOSTIC_PROPERTY_FNAME_CHAIN_NON_EVIDENCE,
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "readiness_gate": "none",
            "can_satisfy_lifecycle_role": False,
            "can_satisfy_complete_triplet": False,
        }
        for _, record in sorted(records.items())
    ]
    return {
        "count": sum(entry["count"] for entry in entries),
        "chain_count": len(entries),
        "evidence_claim": "none",
        "evidence_classification": DIAGNOSTIC_PROPERTY_FNAME_CHAIN_NON_EVIDENCE,
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "readiness_gate": "none",
        "can_satisfy_lifecycle_role": False,
        "can_satisfy_complete_triplet": False,
        "entries": entries,
        "non_claim": (
            "compact diagnostic property/FName chains are metadata only and cannot "
            "satisfy lifecycle roles, complete triplets, readiness, or approval"
        ),
    }


def normalize_check_join_in_progress_diagnostic_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": record["diagnostic_candidate_check_join_in_progress_count"],
        "strict_required_shape": PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE,
        "strict_shape_candidate_count": record[
            "diagnostic_candidate_check_join_in_progress_strict_shape_count"
        ],
        "strict_shape_copy_rejected_count": record[
            "diagnostic_candidate_check_join_in_progress_strict_shape_copy_rejected_count"
        ],
        "shape_counts": dict(
            sorted(record["diagnostic_candidate_check_join_in_progress_shape_counts"].items())
        ),
        "accepted_lifecycle_target_counts": dict(
            sorted(
                record[
                    "diagnostic_candidate_check_join_in_progress_accepted_target_counts"
                ].items()
            )
        ),
        "reflection_status_counts": dict(
            sorted(
                record[
                    "diagnostic_candidate_check_join_in_progress_reflection_status_counts"
                ].items()
            )
        ),
        "copy_status_counts": dict(
            sorted(record["diagnostic_candidate_check_join_in_progress_copy_status_counts"].items())
        ),
        "latest_strict_shape_candidate": record[
            "diagnostic_candidate_check_join_in_progress_latest_strict_shape"
        ],
        "can_satisfy_session_start_rejected_anchor": False,
        "required_observer_event_role": "session_start_rejected",
        "required_observer_event_shape": {
            "target": "ShooterGameMode.CheckJoinInProgress",
            "copied_bool_fields": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS),
            "copied_bool_values": list(PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES),
            "redacted_fields": list(PLAYER_PRINCIPAL_CHECK_JOIN_REDACTED_FIELDS),
        },
        "evidence_claim": "none",
        "evidence_classification": DIAGNOSTIC_CHECK_JOIN_IN_PROGRESS_NON_EVIDENCE,
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "readiness_gate": "none",
        "non_claim": (
            "diagnostic CheckJoinInProgress candidates are breadcrumbs only; even an "
            "exact CheckJoinInProgress(1,0) tuple must be observed as a valid observer "
            "event and accepted by downstream evidence checks before it can count"
        ),
    }


def player_principal_lifecycle_rejected_event_split_code(
    match: re.Match[str],
) -> str | None:
    if (
        match.group("role") == "session_end"
        and match.group("target") == "ShooterGameMode.OnLogout"
        and match.group("apply_status") == "session_end_unresolved_noop"
        and match.group("correlation_status") == "missing"
    ):
        return "session_end_unresolved_noop_missing"
    return None


def player_principal_lifecycle_exact_check_join_observer_event_count(
    record: dict[str, Any],
) -> int:
    return sum(
        1
        for event in record["observed_event_cases"]
        if (
            event.get("target") == "ShooterGameMode.CheckJoinInProgress"
            and event.get("role") == "session_start_rejected"
            and tuple(event.get("copied_bool_fields", []))
            == PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS
            and tuple(event.get("copied_bool_values", []))
            == PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES
        )
    )


def normalize_player_principal_lifecycle_event_split_summary(
    record: dict[str, Any],
) -> dict[str, Any]:
    copy_status_counts = dict(
        sorted(record["diagnostic_candidate_copy_status_counts"].items())
    )
    copy_status_rejected_count = copy_status_counts.get("rejected", 0)
    diagnostic_candidate_copy_status_count = sum(copy_status_counts.values())
    diagnostic_candidate_without_copy_status_count = max(
        record["diagnostic_candidate_count"] - diagnostic_candidate_copy_status_count,
        0,
    )
    exact_check_join_observer_event_count = (
        player_principal_lifecycle_exact_check_join_observer_event_count(record)
    )
    class_counts = {
        "accepted_observer_event": record["accepted_count"],
        "copy_status_rejected": copy_status_rejected_count,
        "diagnostic_route_sample": record["diagnostic_route_sample_count"],
        "diagnostic_candidate": diagnostic_candidate_without_copy_status_count,
        "session_end_unresolved_noop_missing": record["lifecycle_event_split_counts"][
            "session_end_unresolved_noop_missing"
        ],
        "missing_exact_check_join_in_progress_1_0": (
            0 if exact_check_join_observer_event_count else 1
        ),
    }
    return {
        "evidence_classification": PLAYER_PRINCIPAL_EVENT_SPLIT_NON_EVIDENCE,
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "ready": False,
        "readiness_gate": "none",
        "classes": [
            {
                "code": code,
                "label": label,
                "count": class_counts[code],
            }
            for code, label in PLAYER_PRINCIPAL_EVENT_SPLIT_LABELS
        ],
        "class_counts": class_counts,
        "class_counts_are_exclusive_for_observed_lines": True,
        "observer_event_counts": {
            "accepted_observer_event": record["accepted_count"],
            "rejected_or_non_evidence_observer_event": record[
                "lifecycle_rejected_observer_event_count"
            ],
        },
        "diagnostic_candidate_total_count": record["diagnostic_candidate_count"],
        "diagnostic_candidate_without_copy_status_count": (
            diagnostic_candidate_without_copy_status_count
        ),
        "copy_status_counts": copy_status_counts,
        "diagnostic_route_sample_count": record["diagnostic_route_sample_count"],
        "session_end_unresolved_noop_missing_count": class_counts[
            "session_end_unresolved_noop_missing"
        ],
        "strict_required_observer_event_shape": {
            "target": "ShooterGameMode.CheckJoinInProgress",
            "role": "session_start_rejected",
            "copied_bool_fields": list(
                PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_FIELDS
            ),
            "copied_bool_values": list(
                PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_BOOL_VALUES
            ),
            "redacted_fields": list(PLAYER_PRINCIPAL_CHECK_JOIN_REDACTED_FIELDS),
        },
        "strict_required_shape": PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE,
        "accepted_exact_check_join_observer_event_count": (
            exact_check_join_observer_event_count
        ),
        "required_exact_check_join_observer_event_present": (
            exact_check_join_observer_event_count > 0
        ),
        "missing_exact_check_join_in_progress_1_0": (
            exact_check_join_observer_event_count == 0
        ),
        "diagnostic_exact_check_join_shape_candidate_count": record[
            "diagnostic_candidate_check_join_in_progress_strict_shape_count"
        ],
        "can_satisfy_lifecycle_role": False,
        "can_satisfy_complete_triplet": False,
        "can_promote_runtime_readiness": False,
    }


def module_blockers(record: dict[str, Any]) -> list[str]:
    blockers = ["runtime_observer_evidence_only"]
    if len(record["gate_sha256"]) == 0:
        blockers.append("missing_experimental_gate")
    if len(record["gate_sha256"]) > 1:
        blockers.append("mixed_binary_sha256")
    if len(record["source_indices"]) > 1 and not record["source_merge_explicit"]:
        blockers.append("multiple_sources_same_module")
    if (
        record["accepted_count"] == 0
        and record["metadata_only_count"] == 0
        and record["rejected_count"] == 0
    ):
        blockers.append("no_accepted_or_rejected_observer_lines")
    if record["malformed_observer_lines"] > 0:
        blockers.append("malformed_observer_lines")
    if record["orphan_field_lines"] > 0:
        blockers.append("orphan_field_lines")
    if record["out_of_order_field_lines"] > 0:
        blockers.append("out_of_order_field_lines")
    if record["field_count_mismatches"] > 0:
        blockers.append("field_count_mismatch")
    if record["sequence_quality_violations"] > 0:
        blockers.append("sequence_quality_violation")
    if record["timestamp_quality_violations"] > 0:
        blockers.append("timestamp_quality_violation")
    if record["event_before_gate_lines"] > 0:
        blockers.append("player_principal_event_before_safe_gate")
    if record.get("non_observer_lifecycle_lines", 0) > 0:
        blockers.append("player_principal_non_observer_lifecycle_lines")
    if record.get("passive_monitor_metadata_lines", 0) > 0:
        blockers.append("player_principal_passive_monitor_metadata_lines")
    if (
        record.get("diagnostic_candidate_count", 0) > 0
        or record.get("diagnostic_log_limits")
        or record.get("diagnostic_near_miss_scan_limits")
        or record.get("diagnostic_route_sample_count", 0) > 0
        or record.get("diagnostic_route_sample_limits")
    ):
        blockers.append("player_principal_diagnostic_candidates_non_evidence")
    if (
        record.get("diagnostic_route_sample_count", 0) > 0
        or record.get("diagnostic_route_sample_limits")
    ):
        blockers.append("player_principal_route_samples_non_evidence")
    if record.get("diagnostic_candidate_check_join_in_progress_count", 0) > 0:
        blockers.append(PLAYER_PRINCIPAL_DIAGNOSTIC_CHECK_JOIN_BLOCKER)
    if record.get("diagnostic_candidate_rejected_drift_count", 0) > 0:
        blockers.append(DIAGNOSTIC_REJECTED_DRIFT_NON_EVIDENCE)
    if (
        record.get("observer_gate_count", 0) != 1
        and record.get("functions", {}).get("observer_gate") is not None
    ):
        blockers.append("player_principal_observer_gate_count_mismatch")
    if record["redacted_detail_keys"]:
        blockers.append("redacted_sensitive_or_unapproved_details")
    return blockers


def player_principal_lifecycle_accepted_roles(record: dict[str, Any]) -> list[str]:
    observed = {
        case.get("role")
        for case in record["observed_event_cases"]
        if isinstance(case, dict)
    }
    return [
        role
        for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES
        if role in observed
    ]


def player_principal_lifecycle_compact_case(case: dict[str, Any]) -> dict[str, Any]:
    return {key: case.get(key) for key in PLAYER_PRINCIPAL_STRICT_CASE_KEYS}


def player_principal_lifecycle_triplet_selection_summary(
    triplet: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            key: event.get(key)
            for key in ("index", "sequence", "role", "target")
            if key in event
        }
        for event in triplet
    ]


def player_principal_lifecycle_strict_triplet_selection(
    observed_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_events: list[dict[str, Any]] = []
    for index, case in enumerate(observed_cases):
        if not isinstance(case, dict):
            continue
        compact_case = player_principal_lifecycle_compact_case(case)
        expected = PLAYER_PRINCIPAL_STRICT_CASES_BY_ROLE.get(str(compact_case.get("role")))
        if compact_case != expected:
            continue
        exact_events.append(
            {
                **case,
                "index": index,
                "role": compact_case.get("role"),
                "target": compact_case.get("target"),
            }
        )

    by_role: dict[str, list[dict[str, Any]]] = {
        role: [] for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES
    }
    for event in exact_events:
        role = event.get("role")
        if isinstance(role, str) and role in by_role:
            by_role[role].append(event)

    def strictly_ordered(candidate: list[dict[str, Any]]) -> bool:
        sequences = [event.get("sequence") for event in candidate]
        if not all(isinstance(sequence, int) for sequence in sequences):
            return False
        return all(current > previous for previous, current in zip(sequences, sequences[1:]))

    candidates: list[list[dict[str, Any]]] = []
    for start in by_role["session_start"]:
        for rejected in by_role["session_start_rejected"]:
            for end in by_role["session_end"]:
                candidate = [start, rejected, end]
                if strictly_ordered(candidate):
                    candidates.append(candidate)

    missing_roles = [
        role for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES if not by_role[role]
    ]
    duplicate_context_roles = [
        role
        for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES
        if len(by_role[role]) > 1
    ]

    selected: list[dict[str, Any]] | None = None
    status = "selected"
    forced_ambiguous = len(by_role["session_start_rejected"]) > 1
    if forced_ambiguous:
        selected = None
    elif len(candidates) == 1:
        selected = candidates[0]
    elif candidates and set(duplicate_context_roles).issubset(
        PLAYER_PRINCIPAL_ALLOWED_DUPLICATE_CONTEXT_ROLES
    ):
        selected = min(
            candidates,
            key=lambda candidate: (
                int(candidate[1].get("sequence", 0)),
                -int(candidate[0].get("sequence", 0)),
                int(candidate[2].get("sequence", 0)),
            ),
        )
        status = "selected_with_duplicate_start_end_context"

    if selected is None:
        if forced_ambiguous or len(candidates) > 1:
            status = "ambiguous"
            blockers = ["strict_lifecycle_triplet_ambiguous"]
        elif not missing_roles and not candidates:
            status = "out_of_order"
            blockers = ["strict_lifecycle_triplet_order_mismatch"]
        else:
            status = "missing"
            blockers = ["strict_lifecycle_triplet_missing"]
        return {
            "status": status,
            "accepted": False,
            "candidate_count": len(candidates),
            "selected_sequences": [],
            "selected_roles": [],
            "non_counting_context_event_count": len(exact_events),
            "non_counting_context_roles": duplicate_context_roles,
            "candidate_triplets": [
                player_principal_lifecycle_triplet_selection_summary(candidate)
                for candidate in candidates[:5]
            ],
            "missing_roles": missing_roles,
            "blockers": blockers,
        }

    selected_indices = {event["index"] for event in selected}
    non_counting_context_events = [
        event for event in exact_events if event["index"] not in selected_indices
    ]
    return {
        "status": status,
        "accepted": True,
        "candidate_count": len(candidates),
        "selected_sequences": [event.get("sequence") for event in selected],
        "selected_roles": [event.get("role") for event in selected],
        "non_counting_context_event_count": len(non_counting_context_events),
        "non_counting_context_roles": [
            role
            for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES
            if any(event.get("role") == role for event in non_counting_context_events)
        ],
        "candidate_triplets": [
            player_principal_lifecycle_triplet_selection_summary(selected),
        ],
        "missing_roles": [],
        "blockers": [],
    }


def player_principal_lifecycle_strict_triplet_is_exact(
    selection: dict[str, Any],
) -> bool:
    return (
        selection.get("accepted") is True
        and selection.get("status") == "selected"
        and selection.get("candidate_count") == 1
        and selection.get("non_counting_context_event_count") == 0
        and selection.get("selected_roles") == list(REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
    )


def player_principal_lifecycle_non_evidence_reasons(
    record: dict[str, Any],
    *,
    missing_roles: list[str],
    strict_triplet_selection: dict[str, Any] | None = None,
) -> list[str]:
    reasons = ["runtime_observer_summary_not_approved_runtime_evidence"]
    if len(record["source_indices"]) > 1 and not record["source_merge_explicit"]:
        reasons.append("multiple_sources_same_module")
    if (
        record["accepted_count"] == 0
        and record["metadata_only_count"] == 0
        and record["rejected_count"] == 0
    ):
        reasons.append("no_accepted_or_rejected_observer_lines")
    if (
        record.get("observer_gate_count", 0) > 0
        and record["accepted_count"] == 0
        and record["metadata_only_count"] == 0
        and record["rejected_count"] == 0
        and record.get("diagnostic_candidate_count", 0) == 0
        and record.get("diagnostic_route_sample_count", 0) == 0
        and not record.get("diagnostic_route_sample_limits")
    ):
        reasons.append("observer_gate_only_lifecycle_non_evidence")
    if (
        record.get("diagnostic_candidate_count", 0) > 0
        or record.get("diagnostic_log_limits")
        or record.get("diagnostic_near_miss_scan_limits")
        or record.get("diagnostic_route_sample_count", 0) > 0
        or record.get("diagnostic_route_sample_limits")
    ):
        reasons.append("diagnostic_candidates_non_evidence")
    if (
        record.get("diagnostic_route_sample_count", 0) > 0
        or record.get("diagnostic_route_sample_limits")
    ):
        reasons.append(DIAGNOSTIC_ROUTE_SAMPLE_NON_EVIDENCE)
    if record.get("diagnostic_candidate_check_join_in_progress_count", 0) > 0:
        reasons.append(DIAGNOSTIC_CHECK_JOIN_IN_PROGRESS_NON_EVIDENCE)
    if record.get("diagnostic_candidate_property_fname_chains"):
        reasons.append(DIAGNOSTIC_PROPERTY_FNAME_CHAIN_NON_EVIDENCE)
    if record.get("diagnostic_candidate_lifecycle_property_fname_mismatches"):
        reasons.append(DIAGNOSTIC_LIFECYCLE_PROPERTY_FNAME_MISMATCH_NON_EVIDENCE)
    if record.get("diagnostic_candidate_rejected_drift_count", 0) > 0:
        reasons.append(DIAGNOSTIC_REJECTED_DRIFT_NON_EVIDENCE)
    if record.get("passive_monitor_metadata_lines", 0) > 0:
        reasons.append("passive_monitor_metadata_non_evidence")
    if record.get("non_observer_lifecycle_lines", 0) > 0:
        reasons.append("non_observer_lifecycle_lines_non_evidence")
    if record["malformed_observer_lines"] > 0:
        reasons.append("malformed_observer_lines_non_evidence")
    if record.get("unsafe_lifecycle_event_reasons"):
        reasons.append("invalid_lifecycle_event_shapes_non_evidence")
    if missing_roles:
        reasons.append("required_lifecycle_event_roles_missing")
    if strict_triplet_selection is not None and strict_triplet_selection.get("blockers"):
        reasons.extend(
            f"{blocker}_non_evidence"
            for blocker in strict_triplet_selection["blockers"]
            if blocker != "strict_lifecycle_triplet_missing"
        )
    return reasons


def strict_lifecycle_triplet_candidate_summary(
    *,
    record: dict[str, Any],
    accepted_roles: list[str],
    missing_roles: list[str],
    quality_blockers: list[str],
    event_split_summary: dict[str, Any],
    strict_triplet_selection: dict[str, Any],
    lifecycle_triplet_candidate_present: bool,
) -> dict[str, Any]:
    exact_check_join_count = int(
        event_split_summary.get("accepted_exact_check_join_observer_event_count") or 0
    )
    required_exact_check_join_present = bool(
        event_split_summary.get("required_exact_check_join_observer_event_present")
    )
    if lifecycle_triplet_candidate_present:
        status = "candidate_ready_for_bundle_preflight"
        next_action = "run_approved_runtime_principal_lifecycle_bundle_preflight"
    elif missing_roles:
        status = "blocked_missing_lifecycle_roles"
        next_action = "capture_missing_roles_in_one_clean_observer_window"
    elif quality_blockers:
        status = "blocked_quality_or_non_evidence_context"
        next_action = "capture_clean_observer_window_without_diagnostics_or_invalid_lines"
    elif record["accepted_count"] == 0:
        status = "blocked_no_accepted_observer_events"
        next_action = "wait_for_or_capture_player_lifecycle_observer_events"
    elif strict_triplet_selection.get("status") == "ambiguous":
        status = "blocked_strict_lifecycle_triplet_ambiguous"
        next_action = "capture_one_clean_observer_window_with_exactly_one_rejected_start"
    elif strict_triplet_selection.get("status") == "out_of_order":
        status = "blocked_strict_lifecycle_triplet_order_mismatch"
        next_action = "capture_lifecycle_roles_in_session_start_rejected_session_end_order"
    elif strict_triplet_selection.get("accepted") is True:
        status = "blocked_strict_lifecycle_triplet_not_exact"
        next_action = "capture_one_clean_observer_window_without_duplicate_context_events"
    else:
        status = "blocked_strict_selector_not_ready"
        next_action = "review_observed_event_cases_before_bundle_preflight"

    return {
        "schema": "obelisk.player-principal-lifecycle-strict-triplet-candidate-summary.v1",
        "status": status,
        "candidate_ready_for_bundle_preflight": lifecycle_triplet_candidate_present,
        "approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "can_promote_runtime_readiness": False,
        "can_promote_public_sdk_readiness": False,
        "approval_authority": DOWNSTREAM_RUNTIME_EVIDENCE_APPROVAL_AUTHORITY,
        "required_event_roles": list(REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES),
        "accepted_event_roles": accepted_roles,
        "missing_event_roles": missing_roles,
        "observed_event_count": len(record["observed_event_cases"]),
        "quality_blockers": quality_blockers,
        "strict_rejected_start_expected_shape": PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE,
        "accepted_exact_check_join_observer_event_count": exact_check_join_count,
        "required_exact_check_join_observer_event_present": required_exact_check_join_present,
        "next_action": next_action,
        "next_checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "next_builder": "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
        "non_claim": (
            "Analyzer strict triplet candidate summaries are copied-log routing signals "
            "only. They do not approve runtime evidence, runtime readiness, public SDK "
            "readiness, SDK/P0 progress, publication, or stable SDK claims."
        ),
    }


def safe_detail_keys(module: str, function: str) -> set[str]:
    return SAFE_DETAIL_KEYS.get(module, {}).get(function, set())


def add_source_index(record: dict[str, Any], source_index: int) -> None:
    add_unique(record["source_indices"], source_index)


def observer_lines_from_sources(sources: list[list[str]]) -> list[tuple[int, int, str]]:
    return [
        (source_index, line_number, line)
        for source_index, lines in enumerate(sources)
        for line_number, line in enumerate(lines, start=1)
    ]


def analyze_lines(lines: list[str]) -> dict[str, Any]:
    return analyze_source_lines([lines])


def analyze_source_lines(sources: list[list[str]], *, source_merge_explicit: bool = False) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = defaultdict(module_record)
    runtime = runtime_record()
    active_fields_by_module: dict[tuple[int, str], dict[str, Any]] = {}

    def close_active_context(source_index: int, module: str) -> None:
        key = (source_index, module)
        active = active_fields_by_module.pop(key, None)
        if active and active["remaining"] != 0:
            modules[module]["field_count_mismatches"] += 1

    for source_index, line_number, line in observer_lines_from_sources(sources):
        stripped = line.strip()
        if not stripped:
            continue

        if PASSIVE_MONITOR_METADATA_RE.match(stripped):
            runtime["passive_monitor_metadata_lines"] += 1
            if "PlayerPrincipalLifecycle" in stripped:
                module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
                close_active_context(source_index, module)
                record = modules[module]
                record["source_merge_explicit"] = source_merge_explicit
                add_source_index(record, source_index)
                record_player_principal_passive_monitor_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                )
            continue

        if RUNTIME_LOADED_RE.fullmatch(stripped):
            runtime["loaded_native_ld_preload"] = True
            continue

        if match := PROCESS_EVENT_CANDIDATES_RE.fullmatch(stripped):
            runtime["process_event_candidate_count"] = int(match.group("count"))
            continue

        if match := PROCESS_EVENT_CANDIDATE_RE.fullmatch(stripped):
            add_unique(
                runtime["process_event_candidates"],
                {
                    "index": int(match.group("index")),
                    "address": match.group("address").lower(),
                },
            )
            continue

        if match := PROCESS_EVENT_FOUND_RE.fullmatch(stripped):
            runtime["process_event_address"] = match.group("address").lower()
            continue

        if match := PROCESS_EVENT_HOOK_INSTALLED_RE.fullmatch(stripped):
            runtime["process_event_hook_installed"] = True
            runtime["process_event_hook_patch_size"] = int(match.group("patch_size"))
            continue

        if PROCESS_EVENT_DETOUR_HIT_RE.fullmatch(stripped):
            runtime["broad_process_event_trace_lines"] += 1
            continue

        if REFLECTION_SCANNER_DISABLED_RE.fullmatch(stripped):
            runtime["reflection_scanner_disabled"] = True
            continue

        if PLUGINS_DISABLED_RE.fullmatch(stripped):
            runtime["plugins_disabled"] = True
            continue

        if match := GATE_RE.fullmatch(stripped):
            module = match.group("module")
            close_active_context(source_index, module)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                record = modules[module]
                record["source_merge_explicit"] = source_merge_explicit
                add_source_index(record, source_index)
                record_player_principal_non_observer_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="non_observer_experimental_gate",
                )
                continue
            add_source_index(modules[module], source_index)
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := ITEM_RETURN_GATE_RE.fullmatch(stripped):
            module = "item_return"
            close_active_context(source_index, module)
            add_source_index(modules[module], source_index)
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_GATE_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="observer_gate",
            )
            add_source_index(record, source_index)
            record["source_merge_explicit"] = source_merge_explicit
            if not player_principal_lifecycle_gate_is_safe(match):
                record["malformed_observer_lines"] += 1
                continue
            record["observer_gate_count"] += 1
            record["_player_principal_gate_seen_by_source"].add(source_index)
            record["_player_principal_log_limit"] = int(match.group("limit"))
            add_unique(record["gate_sha256"], match.group("sha256").lower())
            gate_function = "observer_gate"
            record["functions"].setdefault(gate_function, function_record())
            for key in ("target_set", "limit", "dispatch_limit", "delivery_claim", "principal_claim"):
                add_unique(record["functions"][gate_function]["details"][key], int_or_text(match.group(key)))
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_ENABLED_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="diagnostic_enabled",
            )
            add_source_index(record, source_index)
            record["source_merge_explicit"] = source_merge_explicit
            limit = int(match.group("limit"))
            if not 1 <= limit <= 10:
                record["malformed_observer_lines"] += 1
                continue
            add_unique(record["diagnostic_log_limits"], limit)
            source_limits = record["_player_principal_diagnostic_log_limits_by_source"].setdefault(
                source_index,
                [],
            )
            add_unique(source_limits, limit)
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_ENABLED_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="diagnostic_near_miss_enabled",
            )
            add_source_index(record, source_index)
            record["source_merge_explicit"] = source_merge_explicit
            scan_limit = int(match.group("scan_limit"))
            if not 1 <= scan_limit <= 10000:
                record["malformed_observer_lines"] += 1
                continue
            add_unique(record["diagnostic_near_miss_scan_limits"], scan_limit)
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING_ENABLED_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="diagnostic_route_sampling_enabled",
            )
            add_source_index(record, source_index)
            record["source_merge_explicit"] = source_merge_explicit
            sample_limit = int(match.group("sample_limit"))
            if not 1 <= sample_limit <= 10000:
                record["malformed_observer_lines"] += 1
                continue
            add_unique(record["diagnostic_route_sample_limits"], sample_limit)
            source_limits = record["_player_principal_route_sample_limits_by_source"].setdefault(
                source_index,
                [],
            )
            add_unique(source_limits, sample_limit)
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="diagnostic_route_sample",
            )
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            sequence = int(match.group("sequence"))
            if sequence < 1:
                record["malformed_observer_lines"] += 1
                continue
            fname_index = int(match.group("fname_index"))
            fname_number = int(match.group("fname_number"))
            record["diagnostic_route_sample_count"] += 1
            max_sequence = record["diagnostic_route_sample_max_sequence"]
            if max_sequence is None or sequence > max_sequence:
                record["diagnostic_route_sample_max_sequence"] = sequence
            max_by_source = record["_player_principal_route_sample_max_sequence_by_source"]
            max_by_source[source_index] = max(sequence, max_by_source.get(source_index, 0))
            record["diagnostic_route_sample_fname_index_counts"][fname_index] += 1
            latest = record["diagnostic_route_sample_latest"]
            if latest is None or sequence >= latest["sequence"]:
                record["diagnostic_route_sample_latest"] = {
                    "sequence": sequence,
                    "fname_index": fname_index,
                    "fname_number": fname_number,
                    "source_index": source_index,
                    "line_number": line_number,
                    "timestamp_prefix": extract_log_timestamp_prefix(line),
                    "evidence_classification": DIAGNOSTIC_ROUTE_SAMPLE_NON_EVIDENCE,
                    "approved_runtime_evidence": False,
                    "runtime_evidence_ready": False,
                    "ready": False,
                    "readiness_gate": "none",
                }
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            function = match.group("target")
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="observer_event",
            )
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            if source_index not in record["_player_principal_gate_seen_by_source"]:
                record["event_before_gate_lines"] += 1
                record["lifecycle_rejected_observer_event_count"] += 1
                split_code = player_principal_lifecycle_rejected_event_split_code(match)
                if split_code is not None:
                    record["lifecycle_event_split_counts"][split_code] += 1
                continue
            unsafe_reason = player_principal_lifecycle_event_unsafe_reason(match)
            if unsafe_reason is not None:
                record["unsafe_lifecycle_event_reasons"][unsafe_reason] += 1
                record["malformed_observer_lines"] += 1
                record["lifecycle_rejected_observer_event_count"] += 1
                split_code = player_principal_lifecycle_rejected_event_split_code(match)
                if split_code is not None:
                    record["lifecycle_event_split_counts"][split_code] += 1
                continue
            sequence = int(match.group("sequence"))
            if player_principal_lifecycle_event_has_quality_violation(
                record,
                sequence=sequence,
                line=line,
            ):
                record["lifecycle_rejected_observer_event_count"] += 1
                continue
            record["accepted_count"] += 1
            record["observed_event_cases"].append(
                {
                    "sequence": sequence,
                    "target": function,
                    "role": match.group("role"),
                    "copied_bool_fields": csv_values(
                        match.group("copied_bool_fields"),
                        allowed={"bIsFromLogin", "ReturnValue"},
                    ),
                    "copied_bool_values": csv_values(
                        match.group("copied_bool_values"),
                        allowed={"0", "1"},
                        allow_duplicates=True,
                    ),
                    "principal_action": match.group("principal_action"),
                    "apply_status": match.group("apply_status"),
                    "correlation_status": match.group("correlation_status"),
                }
            )
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]
            function_data["accepted"] += 1
            allowed_keys = safe_detail_keys(module, function)
            for key in (
                "role",
                "post_original",
                "copied_bool_fields",
                "copied_bool_values",
                "redacted_count",
                "redacted_fields",
                "principal_action",
                "apply_status",
                "correlation_status",
                "principal_id_logged",
                "principal_generation_logged",
                "delivery_claim",
            ):
                raw_value = match.group(key)
                if key not in allowed_keys:
                    record["redacted_detail_keys"][redacted_detail_label(key)] += 1
                    continue
                add_unique(function_data["details"][key], int_or_text(raw_value))
            continue

        if PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATE_RE.fullmatch(stripped):
            module = PLAYER_PRINCIPAL_LIFECYCLE_MODULE
            close_active_context(source_index, module)
            record = modules[module]
            record_latest_observer_line(
                record,
                source_index=source_index,
                line_number=line_number,
                line=line,
                kind="diagnostic_candidate",
            )
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            details = player_principal_lifecycle_diagnostic_candidate_details(stripped)
            if details is None:
                record["malformed_observer_lines"] += 1
                continue
            sequence = int(details["sequence"])
            record["diagnostic_candidate_count"] += 1
            max_sequence = record["diagnostic_candidate_max_sequence"]
            if max_sequence is None or sequence > max_sequence:
                record["diagnostic_candidate_max_sequence"] = sequence
            max_by_source = record["_player_principal_diagnostic_max_sequence_by_source"]
            max_by_source[source_index] = max(sequence, max_by_source.get(source_index, 0))
            record["diagnostic_candidate_target_counts"][details["target"]] += 1
            if "copy_status" in details:
                record["diagnostic_candidate_copy_status_counts"][
                    details["copy_status"]
                ] += 1
            if "reason" in details:
                reason = details["reason"]
                record["diagnostic_candidate_reason_counts"][reason] += 1
                add_lifecycle_property_fname_mismatch_summary(
                    record,
                    details,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                )
            if "read_status" in details:
                record["diagnostic_candidate_read_status_counts"][details["read_status"]] += 1
            add_diagnostic_property_fname_chain_metadata(
                record,
                details,
                source_index=source_index,
                line_number=line_number,
                line=line,
            )
            record_player_principal_lifecycle_check_join_diagnostic(
                record,
                details,
                line_number=line_number,
                line=line,
            )
            record_player_principal_lifecycle_rejected_drift(
                record,
                details,
                line_number=line_number,
                line=line,
            )
            continue

        if match := PROCESS_EVENT_RE.fullmatch(stripped):
            module = match.group("module")
            function = match.group("function")
            close_active_context(source_index, module)
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                if bool_from_text(match.group("metadata_only")):
                    record["metadata_only_count"] += 1
                record_player_principal_non_observer_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="non_observer_reflected_process_event",
                )
                continue
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]

            metadata_only = bool_from_text(match.group("metadata_only"))
            if metadata_only:
                record["metadata_only_count"] += 1
                function_data["metadata_only"] += 1
            else:
                record["accepted_count"] += 1
                function_data["accepted"] += 1

            add_unique(function_data["fname_indices"], int(match.group("fname_index")))
            if match.group("outer_fname_index") is not None:
                add_unique(function_data["outer_fname_indices"], int(match.group("outer_fname_index")))
            field_count = int(match.group("field_count"))
            add_unique(function_data["field_counts"], field_count)
            if field_count > 0:
                active_fields_by_module[(source_index, module)] = {
                    "function": function,
                    "remaining": field_count,
                }
            continue

        if match := FIELD_RE.fullmatch(stripped):
            module = match.group("module")
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                close_active_context(source_index, module)
                record_player_principal_non_observer_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="non_observer_reflected_field",
                )
                continue
            field = match.group("field")
            fields = record["fields"]
            fields.setdefault(field, field_record())
            field_data = fields[field]
            field_data["count"] += 1
            add_unique(field_data["offsets"], match.group("offset").lower())
            add_unique(field_data["sizes"], int(match.group("size")))

            extra = parse_key_values(match.group("rest"))
            if "has_range" in extra:
                field_data["has_range"][extra["has_range"]] += 1
            if "sensitive" in extra:
                field_data["sensitive"][extra["sensitive"]] += 1

            active_key = (source_index, module)
            active_context = active_fields_by_module.get(active_key)
            if not active_context:
                record["orphan_field_lines"] += 1
                continue

            if active_context["remaining"] <= 0:
                record["out_of_order_field_lines"] += 1
                active_fields_by_module.pop(active_key, None)
                continue

            active_function = active_context["function"]
            functions = record["functions"]
            functions.setdefault(active_function, function_record())
            function_fields = functions[active_function]["fields"]
            function_fields.setdefault(field, field_record())
            function_field_data = function_fields[field]
            function_field_data["count"] += 1
            add_unique(function_field_data["offsets"], match.group("offset").lower())
            add_unique(function_field_data["sizes"], int(match.group("size")))
            if "has_range" in extra:
                function_field_data["has_range"][extra["has_range"]] += 1
            if "sensitive" in extra:
                function_field_data["sensitive"][extra["sensitive"]] += 1

            active_context["remaining"] -= 1
            continue

        if match := REJECT_RE.fullmatch(stripped):
            module = match.group("module")
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            close_active_context(source_index, module)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                record_player_principal_non_observer_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="non_observer_reflected_rejected",
                )
                continue
            record["rejected_count"] += 1
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := ITEM_RETURN_REJECT_RE.fullmatch(stripped):
            module = "item_return"
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            record["rejected_count"] += 1
            close_active_context(source_index, module)
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := ITEM_RETURN_DISPATCH_RE.fullmatch(stripped):
            module = "item_return"
            function = match.group("function")
            close_active_context(source_index, module)
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            record["accepted_count"] += 1
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]
            function_data["accepted"] += 1
            add_unique(function_data["fname_indices"], int(match.group("fname_index")))
            for key in ("callbacks", "field_mask"):
                raw_value = match.group(key)
                if key not in safe_detail_keys(module, function):
                    record["redacted_detail_keys"][redacted_detail_label(key)] += 1
                    continue
                add_unique(function_data["details"][key], int_or_text(raw_value))
            continue

        if match := DETAIL_RE.fullmatch(stripped):
            module = match.group("module")
            function = match.group("function")
            if function in {"ProcessEvent", "field", "rejected"}:
                continue
            details = parse_key_values(match.group("rest"))
            if not details:
                continue
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                record_player_principal_non_observer_line(
                    record,
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="non_observer_reflected_detail",
                )
                continue
            functions = record["functions"]
            functions.setdefault(function, function_record())
            allowed_keys = safe_detail_keys(module, function)
            for key, raw_value in details.items():
                if key not in allowed_keys:
                    record["redacted_detail_keys"][redacted_detail_label(key)] += 1
                    continue
                add_unique(functions[function]["details"][key], int_or_text(raw_value))
            continue

        if (
            "Reflected " in stripped
            or "Experimental " in stripped
            or "PlayerPrincipalLifecycleObserver " in stripped
            or "PlayerPrincipalLifecycleDiagnostic " in stripped
        ):
            match = re.search(r"(?:Reflected|Experimental) (?P<module>[A-Za-z0-9_]+)", stripped)
            module = (
                PLAYER_PRINCIPAL_LIFECYCLE_MODULE
                if (
                    "PlayerPrincipalLifecycleObserver " in stripped
                    or "PlayerPrincipalLifecycleDiagnostic " in stripped
                )
                else (match.group("module") if match else "unknown")
            )
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_source_index(modules[module], source_index)
            if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
                if "PlayerPrincipalLifecycleObserver event" in stripped:
                    modules[module]["lifecycle_rejected_observer_event_count"] += 1
                    role_match = re.search(
                        r"\brole=(session_start_rejected|session_start|session_end)\b",
                        stripped,
                    )
                    if role_match is not None and (
                        "apply_status=" not in stripped or "correlation_status=" not in stripped
                    ):
                        modules[module]["unsafe_lifecycle_event_reasons"][
                            f"old_format_{role_match.group(1)}_without_status_proof"
                        ] += 1
                    else:
                        modules[module]["unsafe_lifecycle_event_reasons"][
                            "malformed_lifecycle_event"
                        ] += 1
                record_latest_observer_line(
                    modules[module],
                    source_index=source_index,
                    line_number=line_number,
                    line=line,
                    kind="malformed_player_principal_line",
                )
            modules[module]["malformed_observer_lines"] += 1

    for source_index, module in list(active_fields_by_module):
        close_active_context(source_index, module)

    normalized_modules: dict[str, Any] = {}
    for module, record in sorted(modules.items()):
        normalized_modules[module] = {
            "gate_sha256": sorted(record["gate_sha256"]),
            "source_indices": sorted(record["source_indices"]),
            "source_merge_explicit": record["source_merge_explicit"],
            "accepted_count": record["accepted_count"],
            "metadata_only_count": record["metadata_only_count"],
            "rejected_count": record["rejected_count"],
            "evidence_status": "observational",
            "evidence_classification": "runtime_observer_module_non_evidence",
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "blockers": module_blockers(record),
            "functions": {
                name: normalize_function(function)
                for name, function in sorted(record["functions"].items())
            },
            "fields": {
                name: normalize_field(field)
                for name, field in sorted(record["fields"].items())
            },
            "reject_reasons": dict(sorted(record["reject_reasons"].items())),
            "redacted_detail_keys": dict(sorted(record["redacted_detail_keys"].items())),
            "malformed_observer_lines": record["malformed_observer_lines"],
            "orphan_field_lines": record["orphan_field_lines"],
            "out_of_order_field_lines": record["out_of_order_field_lines"],
            "field_count_mismatches": record["field_count_mismatches"],
            "sequence_quality_violations": record["sequence_quality_violations"],
            "timestamp_quality_violations": record["timestamp_quality_violations"],
            "event_before_gate_lines": record["event_before_gate_lines"],
            "non_observer_lifecycle_lines": record["non_observer_lifecycle_lines"],
            "passive_monitor_metadata_lines": record["passive_monitor_metadata_lines"],
        }
        if module == PLAYER_PRINCIPAL_LIFECYCLE_MODULE:
            diagnostic_limits_by_source = record[
                "_player_principal_diagnostic_log_limits_by_source"
            ]
            diagnostic_max_by_source = record[
                "_player_principal_diagnostic_max_sequence_by_source"
            ]
            route_sample_limits_by_source = record[
                "_player_principal_route_sample_limits_by_source"
            ]
            route_sample_max_by_source = record[
                "_player_principal_route_sample_max_sequence_by_source"
            ]
            diagnostic_log_budget_reached = any(
                diagnostic_max_by_source.get(source_index, 0) >= limit
                for source_index, limits in diagnostic_limits_by_source.items()
                for limit in limits
            )
            if (
                not diagnostic_log_budget_reached
                and record["diagnostic_candidate_max_sequence"] is not None
                and record["diagnostic_log_limits"]
            ):
                diagnostic_log_budget_reached = (
                    record["diagnostic_candidate_max_sequence"]
                    >= max(record["diagnostic_log_limits"])
                )
            diagnostic_route_sample_budget_reached = any(
                route_sample_max_by_source.get(source_index, 0) >= limit
                for source_index, limits in route_sample_limits_by_source.items()
                for limit in limits
            )
            if (
                not diagnostic_route_sample_budget_reached
                and record["diagnostic_route_sample_max_sequence"] is not None
                and record["diagnostic_route_sample_limits"]
            ):
                diagnostic_route_sample_budget_reached = (
                    record["diagnostic_route_sample_max_sequence"]
                    >= max(record["diagnostic_route_sample_limits"])
                )
            accepted_roles = player_principal_lifecycle_accepted_roles(record)
            missing_roles = [
                role
                for role in REQUIRED_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ROLES
                if role not in accepted_roles
            ]
            lifecycle_role_triplet_quality_blockers = [
                blocker
                for blocker in normalized_modules[module]["blockers"]
                if blocker not in PROMOTION_ONLY_BLOCKERS
            ]
            strict_triplet_selection = player_principal_lifecycle_strict_triplet_selection(
                record["observed_event_cases"]
            )
            strict_triplet_exact = player_principal_lifecycle_strict_triplet_is_exact(
                strict_triplet_selection
            )
            observer_enabled = record["observer_gate_count"] > 0
            accepted_lifecycle_role_set_present = bool(accepted_roles)
            complete_accepted_lifecycle_role_triplet_present = not missing_roles
            lifecycle_triplet_candidate_present = (
                record["accepted_count"] > 0
                and complete_accepted_lifecycle_role_triplet_present
                and strict_triplet_exact
                and not lifecycle_role_triplet_quality_blockers
            )
            accepted_or_rejected_observer_lines_present = (
                record["accepted_count"] > 0
                or record["metadata_only_count"] > 0
                or record["rejected_count"] > 0
            )
            diagnostic_lines_present = (
                record["diagnostic_candidate_count"] > 0
                or bool(record["diagnostic_log_limits"])
                or bool(record["diagnostic_near_miss_scan_limits"])
                or record["diagnostic_route_sample_count"] > 0
                or bool(record["diagnostic_route_sample_limits"])
            )
            passive_monitor_metadata_present = record["passive_monitor_metadata_lines"] > 0
            only_non_evidence_lifecycle_line_classes = (
                record["malformed_observer_lines"] == 0
                and record["non_observer_lifecycle_lines"] == 0
                and record["event_before_gate_lines"] == 0
                and record["sequence_quality_violations"] == 0
                and record["timestamp_quality_violations"] == 0
            )
            observer_gate_only_non_evidence = (
                observer_enabled
                and not accepted_or_rejected_observer_lines_present
                and record["diagnostic_candidate_count"] == 0
                and not record["diagnostic_near_miss_scan_limits"]
                and record["diagnostic_route_sample_count"] == 0
                and not record["diagnostic_route_sample_limits"]
            )
            diagnostic_only_non_evidence = (
                not accepted_or_rejected_observer_lines_present
                and only_non_evidence_lifecycle_line_classes
                and (
                    record["diagnostic_candidate_count"] > 0
                    or bool(record["diagnostic_near_miss_scan_limits"])
                    or record["diagnostic_route_sample_count"] > 0
                    or bool(record["diagnostic_route_sample_limits"])
                )
            )
            passive_only_non_evidence = (
                not accepted_or_rejected_observer_lines_present
                and only_non_evidence_lifecycle_line_classes
                and not diagnostic_lines_present
                and passive_monitor_metadata_present
                and not observer_enabled
                and record["non_observer_lifecycle_lines"] == 0
            )
            diagnostic_or_passive_only_non_evidence = (
                not accepted_or_rejected_observer_lines_present
                and only_non_evidence_lifecycle_line_classes
                and (diagnostic_lines_present or passive_monitor_metadata_present)
            )
            copied_log_ready_but_not_approved_evidence = (
                lifecycle_triplet_candidate_present
                and not normalized_modules[module]["approved_runtime_evidence"]
            )
            invalid_lifecycle_event_non_evidence_reasons = dict(
                sorted(record["unsafe_lifecycle_event_reasons"].items())
            )
            invalid_lifecycle_event_non_evidence_count = sum(
                invalid_lifecycle_event_non_evidence_reasons.values()
            )
            event_split_summary = normalize_player_principal_lifecycle_event_split_summary(
                record
            )
            copied_log_ready_signal = {
                "state": (
                    "copied_log_ready_not_approved"
                    if copied_log_ready_but_not_approved_evidence
                    else "copied_log_incomplete_or_blocked"
                ),
                "evidence_classification": "offline_copied_log_signal_non_evidence",
                "approval_authority": DOWNSTREAM_RUNTIME_EVIDENCE_APPROVAL_AUTHORITY,
                "approved_runtime_evidence": False,
                "runtime_evidence_ready": False,
                "readiness_gate": "none",
                "can_promote_runtime_readiness": False,
                "can_promote_public_sdk_readiness": False,
            }
            normalized_modules[module]["observer_gate_count"] = record["observer_gate_count"]
            normalized_modules[module]["observer_enabled"] = observer_enabled
            normalized_modules[module]["latest_observer_line"] = record["latest_observer_line"]
            normalized_modules[module]["observed_event_cases"] = sorted(
                record["observed_event_cases"],
                key=lambda item: item["sequence"],
            )
            normalized_modules[module]["accepted_lifecycle_event_roles"] = accepted_roles
            normalized_modules[module][
                "accepted_lifecycle_role_set_present"
            ] = accepted_lifecycle_role_set_present
            normalized_modules[module]["missing_lifecycle_event_roles"] = missing_roles
            normalized_modules[module][
                "complete_accepted_lifecycle_role_triplet_present"
            ] = complete_accepted_lifecycle_role_triplet_present
            normalized_modules[module][
                "complete_lifecycle_event_triplet_candidate_present"
            ] = lifecycle_triplet_candidate_present
            normalized_modules[module][
                "lifecycle_role_triplet_quality_blockers"
            ] = lifecycle_role_triplet_quality_blockers
            normalized_modules[module][
                "observer_gate_only_non_evidence"
            ] = observer_gate_only_non_evidence
            normalized_modules[module][
                "accepted_or_rejected_observer_lines_present"
            ] = accepted_or_rejected_observer_lines_present
            normalized_modules[module][
                "diagnostic_lines_present"
            ] = diagnostic_lines_present
            normalized_modules[module][
                "passive_monitor_metadata_present"
            ] = passive_monitor_metadata_present
            normalized_modules[module][
                "passive_only_non_evidence"
            ] = passive_only_non_evidence
            normalized_modules[module][
                "diagnostic_or_passive_only_non_evidence"
            ] = diagnostic_or_passive_only_non_evidence
            normalized_modules[module][
                "copied_log_ready_but_not_approved_evidence"
            ] = copied_log_ready_but_not_approved_evidence
            normalized_modules[module]["copied_log_ready_signal"] = copied_log_ready_signal
            normalized_modules[module][
                "player_principal_lifecycle_event_split_summary"
            ] = event_split_summary
            normalized_modules[module][
                "strict_lifecycle_triplet_candidate_summary"
            ] = strict_lifecycle_triplet_candidate_summary(
                record=record,
                accepted_roles=accepted_roles,
                missing_roles=missing_roles,
                quality_blockers=lifecycle_role_triplet_quality_blockers,
                event_split_summary=event_split_summary,
                strict_triplet_selection=strict_triplet_selection,
                lifecycle_triplet_candidate_present=lifecycle_triplet_candidate_present,
            )
            normalized_modules[module]["copied_log_evidence_review_state"] = (
                "copied_log_ready_not_approved"
                if copied_log_ready_but_not_approved_evidence
                else "copied_log_incomplete_or_blocked"
            )
            normalized_modules[module][
                "approved_runtime_evidence_blocker"
            ] = "approved_runtime_evidence_missing"
            normalized_modules[module]["non_evidence_reasons"] = (
                player_principal_lifecycle_non_evidence_reasons(
                    record,
                    missing_roles=missing_roles,
                    strict_triplet_selection=strict_triplet_selection,
                )
            )
            normalized_modules[module]["diagnostic_candidate_count"] = record[
                "diagnostic_candidate_count"
            ]
            normalized_modules[module]["diagnostic_candidate_max_sequence"] = record[
                "diagnostic_candidate_max_sequence"
            ]
            normalized_modules[module]["diagnostic_log_limits"] = sorted(
                record["diagnostic_log_limits"]
            )
            normalized_modules[module]["diagnostic_near_miss_scan_limits"] = sorted(
                record["diagnostic_near_miss_scan_limits"]
            )
            normalized_modules[module]["diagnostic_route_sample_count"] = record[
                "diagnostic_route_sample_count"
            ]
            normalized_modules[module]["diagnostic_route_sample_max_sequence"] = record[
                "diagnostic_route_sample_max_sequence"
            ]
            normalized_modules[module]["diagnostic_route_sample_limits"] = sorted(
                record["diagnostic_route_sample_limits"]
            )
            normalized_modules[module][
                "diagnostic_route_sample_budget_reached"
            ] = diagnostic_route_sample_budget_reached
            normalized_modules[module]["diagnostic_route_sample_fname_index_counts"] = {
                str(key): value
                for key, value in sorted(
                    record["diagnostic_route_sample_fname_index_counts"].items()
                )
            }
            normalized_modules[module]["diagnostic_route_sample_fname_indices"] = sorted(
                record["diagnostic_route_sample_fname_index_counts"]
            )
            normalized_modules[module]["diagnostic_route_sample_latest"] = record[
                "diagnostic_route_sample_latest"
            ]
            normalized_modules[module][
                "diagnostic_log_budget_reached"
            ] = diagnostic_log_budget_reached
            normalized_modules[module][
                "diagnostic_only_non_evidence"
            ] = diagnostic_only_non_evidence
            normalized_modules[module]["diagnostic_candidate_target_counts"] = dict(
                sorted(record["diagnostic_candidate_target_counts"].items())
            )
            normalized_modules[module]["diagnostic_candidate_copy_status_counts"] = dict(
                sorted(record["diagnostic_candidate_copy_status_counts"].items())
            )
            normalized_modules[module]["diagnostic_candidate_reason_counts"] = dict(
                sorted(record["diagnostic_candidate_reason_counts"].items())
            )
            normalized_modules[module]["diagnostic_candidate_read_status_counts"] = dict(
                sorted(record["diagnostic_candidate_read_status_counts"].items())
            )
            normalized_modules[module][
                "diagnostic_candidate_property_fname_chain_metadata"
            ] = normalize_diagnostic_property_fname_chain_metadata(
                record["diagnostic_candidate_property_fname_chains"]
            )
            normalized_modules[module][
                "diagnostic_check_join_in_progress_summary"
            ] = normalize_check_join_in_progress_diagnostic_summary(record)
            normalized_modules[module]["unsafe_lifecycle_event_reasons"] = dict(
                sorted(record["unsafe_lifecycle_event_reasons"].items())
            )
            normalized_modules[module][
                "invalid_lifecycle_event_evidence_classification"
            ] = (
                "diagnostic_lifecycle_event_non_evidence"
                if invalid_lifecycle_event_non_evidence_count
                else "none"
            )
            normalized_modules[module][
                "invalid_lifecycle_event_non_evidence_count"
            ] = invalid_lifecycle_event_non_evidence_count
            normalized_modules[module][
                "invalid_lifecycle_event_non_evidence_reasons"
            ] = invalid_lifecycle_event_non_evidence_reasons
            normalized_modules[module][
                "diagnostic_candidate_lifecycle_property_fname_mismatches"
            ] = normalize_lifecycle_property_fname_mismatches(
                record["diagnostic_candidate_lifecycle_property_fname_mismatches"]
            )
            normalized_modules[module][
                "diagnostic_lifecycle_property_fname_mismatch_summary"
            ] = normalize_lifecycle_property_fname_mismatch_compact_summary(
                record["diagnostic_candidate_lifecycle_property_fname_mismatches"]
            )
            normalized_modules[module][
                "diagnostic_lifecycle_property_fname_mismatch_target_summary"
            ] = normalize_lifecycle_property_fname_mismatch_target_summary(
                record["diagnostic_candidate_lifecycle_property_fname_mismatches"]
            )
            normalized_modules[module]["diagnostic_candidate_rejected_drift_count"] = record[
                "diagnostic_candidate_rejected_drift_count"
            ]
            normalized_modules[module]["diagnostic_candidate_rejected_drift_target_counts"] = dict(
                sorted(record["diagnostic_candidate_rejected_drift_target_counts"].items())
            )
            normalized_modules[module]["diagnostic_candidate_latest_rejected_drift_by_target"] = {
                target: record["diagnostic_candidate_latest_rejected_drift_by_target"][target]
                for target in sorted(record["diagnostic_candidate_latest_rejected_drift_by_target"])
            }
            normalized_modules[module]["diagnostic_candidate_guardrails"] = [
                guardrail
                for guardrail in (
                    {
                        "code": DIAGNOSTIC_ROUTE_SAMPLE_NON_EVIDENCE,
                        "count": (
                            record["diagnostic_route_sample_count"]
                            + len(record["diagnostic_route_sample_limits"])
                        ),
                        "sample_count": record["diagnostic_route_sample_count"],
                        "limit_count": len(record["diagnostic_route_sample_limits"]),
                        "can_promote": False,
                        "can_satisfy_lifecycle_role": False,
                        "can_satisfy_complete_triplet": False,
                    },
                    {
                        "code": DIAGNOSTIC_CHECK_JOIN_IN_PROGRESS_NON_EVIDENCE,
                        "count": record["diagnostic_candidate_check_join_in_progress_count"],
                        "can_promote": False,
                        "required_runtime_shape": PLAYER_PRINCIPAL_CHECK_JOIN_REJECTED_SHAPE,
                    },
                    {
                        "code": DIAGNOSTIC_PROPERTY_FNAME_CHAIN_NON_EVIDENCE,
                        "count": sum(
                            chain["count"]
                            for chain in record[
                                "diagnostic_candidate_property_fname_chains"
                            ].values()
                        ),
                        "can_promote": False,
                        "can_satisfy_lifecycle_role": False,
                        "can_satisfy_complete_triplet": False,
                    },
                    {
                        "code": DIAGNOSTIC_REJECTED_DRIFT_NON_EVIDENCE,
                        "count": record["diagnostic_candidate_rejected_drift_count"],
                        "can_promote": False,
                        "required_next_step": (
                            "compare distinct sanitized lifecycle snapshot roots before "
                            "another approved runtime-evidence attempt"
                        ),
                    },
                )
                if guardrail["count"] > 0
            ]

    return {
        "schema": "obelisk.runtime-observer-log-summary.v1",
        "review_scope": "runtime_observer_evidence_summary",
        "readiness_gate": "none",
        "ready": False,
        "runtime_evidence_ready": False,
        "approved_runtime_evidence": False,
        "evidence_classification": "runtime_observer_log_summary_non_evidence",
        "non_claims": RUNTIME_OBSERVER_NON_CLAIMS,
        "readiness_boundary": {
            "approval_authority": DOWNSTREAM_RUNTIME_EVIDENCE_APPROVAL_AUTHORITY,
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "readiness_gate": "none",
            "copied_log_ready_signal_can_promote_runtime_readiness": False,
            "copied_log_ready_signal_can_promote_public_sdk_readiness": False,
        },
        "runtime": runtime,
        "modules": normalized_modules,
        "promotion_gate": {
            "gate_type": "runtime_observer_observational_only",
            "ready": False,
            "approval_authority": DOWNSTREAM_RUNTIME_EVIDENCE_APPROVAL_AUTHORITY,
            "blockers": [
                "runtime_observer_evidence_only",
                "requires_isolated_capture_or_second_source_for_promotion",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze copied Obelisk runtime observer log lines into JSON evidence."
    )
    parser.add_argument(
        "--allow-server-path",
        action="store_true",
        help=(
            "Allow direct reads below /servidor/ark. Default refuses those paths so runtime "
            "observer analysis stays on copied or sanitized artifacts."
        ),
    )
    parser.add_argument(
        "--obelisk-commit",
        help="Optional Obelisk commit override recorded in the evidence metadata.",
    )
    parser.add_argument(
        "--fail-on-quality-blockers",
        action="store_true",
        help=(
            "Return non-zero when a module has blockers beyond runtime_observer_evidence_only, "
            "such as missing gates, mixed SHA values, multiple unmerged sources, field-count "
            "problems, malformed observer lines, or redacted details."
        ),
    )
    parser.add_argument(
        "--merge-module-sources",
        action="store_true",
        help=(
            "Allow the same observer module to be summarized across multiple copied logs. "
            "Without this flag, multi-source module summaries are quality blockers."
        ),
    )
    parser.add_argument("logs", nargs="+", type=Path, help="Copied/sanitized Obelisk log files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_lines: list[list[str]] = []
    sources: list[dict[str, Any]] = []

    for path in args.logs:
        expanded = path.expanduser()
        status = protected_paths.protected_path_status(
            expanded,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        resolved = status.resolved
        if status.protected and not args.allow_server_path:
            print(
                f"refusing to read live server path without --allow-server-path: {resolved}",
                file=sys.stderr,
            )
            return 2
        if not resolved.is_file():
            print(f"log does not exist: {resolved}", file=sys.stderr)
            return 2
        text = resolved.read_text(encoding="utf-8")
        lines = text.splitlines()
        sources.append(
            {
                "path": str(resolved),
                "sha256": sha256_file(resolved),
                "line_count": len(lines),
            }
        )
        source_lines.append(lines)

    result = analyze_source_lines(source_lines, source_merge_explicit=bool(args.merge_module_sources))
    result["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": args.obelisk_commit or git_commit(),
        "sources": sources,
        "server_paths_allowed": bool(args.allow_server_path),
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

    if args.fail_on_quality_blockers:
        quality_blockers = []
        if result["runtime"].get("broad_process_event_trace_lines", 0):
            quality_blockers.append(
                "runtime: broad_process_event_trace_lines="
                f"{result['runtime']['broad_process_event_trace_lines']}"
            )
        if result["runtime"].get("passive_monitor_metadata_lines", 0):
            quality_blockers.append(
                "runtime: passive_monitor_metadata_lines="
                f"{result['runtime']['passive_monitor_metadata_lines']}"
            )
        if not result["modules"]:
            quality_blockers.append("no_runtime_observer_evidence")
        for module, payload in result["modules"].items():
            blockers = set(payload["blockers"]) - PROMOTION_ONLY_BLOCKERS
            if blockers:
                quality_blockers.append(f"{module}: {', '.join(sorted(blockers))}")
        if quality_blockers:
            print(
                "runtime observer summary has quality blockers: "
                + "; ".join(quality_blockers),
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
