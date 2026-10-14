#!/usr/bin/env python3
"""Static guardrails for the internal player principal runtime path."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CMAKE_LISTS = REPO_ROOT / "CMakeLists.txt"
PLAYER_PRINCIPAL_REGISTRY_TESTS = (
    REPO_ROOT / "tests" / "core" / "PlayerPrincipalRegistryTests.cpp"
)
PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR_TESTS = (
    REPO_ROOT / "tests" / "core" / "PlayerPrincipalLifecycleApplicatorTests.cpp"
)
PROCESS_EVENT_HOOK = REPO_ROOT / "hooks" / "ProcessEventHook.cpp"
PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER = (
    REPO_ROOT / "hooks" / "ProcessEventPlayerPrincipalLifecycleObserver.cpp"
)
PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR = (
    REPO_ROOT / "hooks" / "ProcessEventPlayerPrincipalLifecycleApplicator.cpp"
)
PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION = (
    REPO_ROOT / "hooks" / "ProcessEventPlayerPrincipalLifecycleCorrelation.cpp"
)
PLAYER_PRINCIPAL_LIFECYCLE_REFLECTION = (
    REPO_ROOT / "ue" / "PlayerPrincipalLifecycleReflection.cpp"
)
PUBLIC_OBELISK_HEADER_ROOT = REPO_ROOT / "include" / "obelisk"
PUBLIC_OBELISK_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

PLAYER_PRINCIPAL_HOOK_PATH_FILES = (
    "hooks/ProcessEventHook.cpp",
    "hooks/ProcessEventPlayerPrincipalLifecycleObserver.h",
    "hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp",
    "hooks/ProcessEventPlayerPrincipalLifecycleApplicator.h",
    "hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp",
    "hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.h",
    "hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.cpp",
)
PLAYER_PRINCIPAL_INTERNAL_REGISTRY_APPLICATOR_CORRELATION_FILES = (
    "core/PlayerPrincipalRegistry.h",
    "core/PlayerPrincipalRegistry.cpp",
    "hooks/ProcessEventPlayerPrincipalLifecycleApplicator.h",
    "hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp",
    "hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.h",
    "hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.cpp",
)

PROCESS_LOCAL_SUBJECT_TOKEN_TERMS = (
    "ProcessLocalSubjectToken",
    "RedactedProcessLocalSubjectTokens",
    "SubjectToken",
    "subjectToken",
    "subject_token",
)

PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_MESSAGE = (
    "PlayerPrincipalLifecycleObserver event sequence={}"
)
PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_KEYS = (
    "sequence",
    "role",
    "target",
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
)
PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_ARGUMENTS = (
    "runtimeEventSequence",
    "ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRoleName(observation.Role)",
    "ProcessEventPlayerPrincipalLifecycleObserver::LifecycleTargetName(observation.Function)",
    "LifecycleBoolFieldsCsv(observation)",
    "LifecycleBoolValuesCsv(observation)",
    "observation.RedactedCount",
    "LifecycleRedactedFieldsCsv(observation)",
    "ProcessEventPlayerPrincipalLifecycleObserver::PrincipalActionName(observation.Action)",
    "LifecycleApplyStatusName(applyResult.Status)",
    "LifecycleCorrelationStatusName(observation, logoutCorrelationPrincipal, applyResult)",
)
PLAYER_PRINCIPAL_LIFECYCLE_APPLY_STATUSES = {
    "unsupported_observation",
    "session_start_created",
    "session_start_allocation_failed",
    "session_start_rejected_noop",
    "session_end_unresolved_noop",
    "session_end_invalidated",
    "session_end_duplicate_noop",
    "session_end_stale_noop",
    "registry_failure",
    "unknown",
}
PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_STATUSES = {
    "not_applicable",
    "missing",
    "matched",
    "duplicate",
    "stale",
    "unresolved",
}
PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_UNSAFE_LOG_PATTERNS = (
    (r"\bProcessLocalSubjectToken\b", "private process-local subject token"),
    (r"\bRedactedProcessLocalSubjectTokens\b", "private process-local subject token storage"),
    (r"\bsubject[_A-Za-z0-9]*token\b", "private subject token"),
    (r"\b(?:principal_)?handle\b", "principal handle"),
    (r"\bprincipal_generation\s*=", "principal generation value"),
    (r"\bapplyResult\s*\.\s*Principal\b", "principal token/result value"),
    (r"\b(?:params|raw_params|rawParams)\b", "raw ProcessEvent params"),
    (r"\b(?:UObject|UFunction|void\s*\*|reinterpret_cast|uobject[_A-Za-z0-9]*pointer)\b", "UE pointer"),
    (r"\b(?:steamid|steam_id|SteamID|SteamId|eosid|eos_id|EOSID|EOSId)\b", "platform identity"),
    (r"\b(?:ipaddress|ip_address|IPAddress|IpAddress)\b", "IP identity"),
    (r"\b(?:playername|player_name|PlayerName)\b", "player-name identity"),
)
PLAYER_PRINCIPAL_PUBLIC_EXPORT_PATTERNS = (
    (r'\bextern\s+"C"\b', 'extern "C" ABI export'),
    (r"\bOBELISK_API\b", "public SDK export/import macro"),
    (r"\bOBELISK_[A-Z0-9_]*EXPORT\b", "public export macro"),
    (r'__attribute__\s*\(\s*\(\s*visibility\s*\(\s*"default"\s*\)\s*\)\s*\)',
     "default symbol visibility attribute"),
    (r"\b__declspec\s*\(\s*(?:dllexport|dllimport)\s*\)", "dllexport/dllimport attribute"),
)
PLAYER_PRINCIPAL_RAW_UE_POINTER_PATTERNS = (
    (r"\bUObject\b", "UObject type"),
    (r"\bUFunction\b", "UFunction type"),
    (r"\bFString\b", "FString type"),
    (r"\bGNames\b", "GNames reference"),
    (r"\bGObjects\b", "GObjects reference"),
    (r"\buintptr_t\b", "pointer-sized integer storage"),
    (r"\breinterpret_cast\s*<", "raw pointer reinterpret_cast"),
    (r"\b(?:const\s+)?void\s*\*", "raw void pointer"),
)

TEST_HOOK_FILES = {
    "core/PlayerPrincipalRegistry.h": {
        "guard": "OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS",
        "tokens": (
            "SetNextHandleForTesting",
            "SetMaxRetainedInvalidatedPrincipalsForTesting",
            "SetGenerationForTesting",
        ),
    },
    "core/PlayerPrincipalRegistry.cpp": {
        "guard": "OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS",
        "tokens": (
            "SetNextHandleForTesting",
            "SetMaxRetainedInvalidatedPrincipalsForTesting",
            "SetGenerationForTesting",
        ),
    },
    "core/PlayerPrincipalEventDispatcher.h": {
        "guard": "OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS",
        "tokens": (
            "SetNextRegistrationIdForTesting",
            "SetNextGenerationForTesting",
            "FailNextDeferredDestroyFailureRecordForTesting",
            "FailNextFailedOwnerDestroyRetrySetupForTesting",
        ),
    },
    "core/PlayerPrincipalEventDispatcher.cpp": {
        "guard": "OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS",
        "tokens": (
            "SetNextRegistrationIdForTesting",
            "SetNextGenerationForTesting",
            "FailNextDeferredDestroyFailureRecordForTesting",
            "FailNextFailedOwnerDestroyRetrySetupForTesting",
        ),
    },
}


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def extract_braced_body_span(text: str, match: re.Match[str]) -> tuple[int, int]:
    start = text.find("{", match.end())
    if start == -1:
        raise AssertionError("matched function has no body")

    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start + 1, index
    raise AssertionError("matched function body is not balanced")


def extract_braced_body(text: str, match: re.Match[str]) -> str:
    start, end = extract_braced_body_span(text, match)
    return text[start:end]


def extract_function_body(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.S)
    if match is None:
        raise AssertionError(f"function pattern not found: {pattern}")
    return extract_braced_body(text, match)


def split_top_level_arguments(arguments: str) -> list[str]:
    values: list[str] = []
    depth = 0
    start = 0
    in_string = False
    in_char = False
    escaped = False

    for index, char in enumerate(arguments):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if in_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_char = False
            continue

        if char == '"':
            in_string = True
        elif char == "'":
            in_char = True
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            values.append(arguments[start:index].strip())
            start = index + 1

    values.append(arguments[start:].strip())
    return values


def extract_call_arguments_span_at(text: str, call_index: int) -> tuple[str, int, int]:
    open_paren = text.find("(", call_index)
    if open_paren == -1:
        raise AssertionError("call has no opening parenthesis")

    depth = 0
    in_string = False
    in_char = False
    escaped = False
    for index in range(open_paren, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if in_char:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_char = False
            continue

        if char == '"':
            in_string = True
        elif char == "'":
            in_char = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1:index], open_paren, index + 1

    raise AssertionError("call argument list is not balanced")


def extract_call_arguments_at(text: str, call_index: int) -> str:
    arguments, _, _ = extract_call_arguments_span_at(text, call_index)
    return arguments


def find_call_index(text: str, call_name: str, start: int = 0) -> int:
    match = re.search(rf"\b{re.escape(call_name)}\s*\(", text[start:], re.S)
    if match is None:
        raise AssertionError(f"call not found: {call_name}")
    return start + match.start()


def extract_calls(text: str, call_pattern: str) -> list[tuple[str, str, int]]:
    calls: list[tuple[str, str, int]] = []
    for match in re.finditer(call_pattern, text, re.S):
        arguments = extract_call_arguments_at(text, match.start())
        line_number = text.count("\n", 0, match.start()) + 1
        calls.append((match.group(0).split("(", 1)[0].strip(), arguments, line_number))
    return calls


def extract_info_log_arguments_containing(text: str, message_fragment: str) -> list[str]:
    message_index = text.find(message_fragment)
    if message_index == -1:
        raise AssertionError(f"OBELISK_INFO message not found: {message_fragment}")

    call_index = text.rfind("OBELISK_INFO", 0, message_index)
    if call_index == -1:
        raise AssertionError(f"OBELISK_INFO call not found for message: {message_fragment}")
    return split_top_level_arguments(extract_call_arguments_at(text, call_index))


def cpp_string_literal_text(expression: str) -> str:
    fragments = re.findall(r'"((?:\\.|[^"\\])*)"', expression, re.S)
    if not fragments:
        raise AssertionError(f"C++ string literal not found: {expression!r}")
    return "".join(fragments)


def format_keys(format_text: str) -> list[str]:
    return re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)=", format_text)


def returned_string_literals(body: str) -> set[str]:
    return set(re.findall(r'\breturn\s+"([^"\\]*(?:\\.[^"\\]*)*)"\s*;', body))


def compact_cpp_expression(expression: str) -> str:
    return re.sub(r"\s+", "", expression)


def expression_mentions_identifier(expression: str, identifier: str) -> bool:
    return re.search(rf"\b{re.escape(identifier)}\b", expression) is not None


def extract_variable_initializer(text: str, variable: str) -> str:
    match = re.search(
        rf"\b{re.escape(variable)}\b\s*=\s*(?P<expression>[^;]+);",
        text,
        re.S,
    )
    if match is None:
        raise AssertionError(f"variable initializer not found: {variable}")
    return match.group("expression").strip()


def extract_designated_initializer_fields(initializer: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in split_top_level_arguments(initializer.strip().rstrip(",")):
        if not item:
            continue
        match = re.match(r"\.\s*(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)\Z", item, re.S)
        if match is None:
            raise AssertionError(f"unsupported designated initializer item: {item!r}")
        fields[match.group("field")] = match.group("value").strip()
    return fields


def extract_case_group_until_return(body: str, case_label: str) -> str:
    match = re.search(rf"\bcase\s+{re.escape(case_label)}\s*:", body)
    if match is None:
        raise AssertionError(f"case label not found: {case_label}")
    return_match = re.search(r"\breturn\b[^;]*;", body[match.start():], re.S)
    if return_match is None:
        raise AssertionError(f"case label has no terminating return: {case_label}")
    return body[match.start(): match.start() + return_match.end()]


def extract_process_local_event_context_declaration(body: str) -> tuple[str, str, int, int]:
    match = re.search(
        r"\bProcessEventPlayerPrincipalLifecycleApplicator::ProcessLocalEventContext\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*",
        body,
        re.S,
    )
    if match is None:
        raise AssertionError("ProcessLocalEventContext declaration not found")
    initializer_start, initializer_end = extract_braced_body_span(body, match)
    return match.group("name"), body[initializer_start:initializer_end], match.start(), initializer_end + 1


def assert_expression_not_budget_derived(
    test: unittest.TestCase,
    expression: str,
    forbidden_budget_sources: set[str],
    message: str,
) -> None:
    compact_expression = compact_cpp_expression(expression)
    for token in ("s_PlayerPrincipalLifecycleObservations", "gate.LogLimit"):
        test.assertNotIn(token, compact_expression, message)

    referenced_budget_sources = sorted(
        source
        for source in forbidden_budget_sources
        if expression_mentions_identifier(expression, source)
    )
    test.assertFalse(
        referenced_budget_sources,
        f"{message} Expression {expression!r} references logging-budget-derived "
        f"source(s): {referenced_budget_sources}.",
    )


def cpp_identifiers(expression: str) -> list[str]:
    return re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)


def fallback_principal_identifiers(expression: str) -> list[str]:
    fallback_terms = (
        "fake",
        "last",
        "latest",
        "previous",
        "prev",
        "cached",
        "recent",
    )
    identifiers = []
    for identifier in cpp_identifiers(expression):
        lowered = identifier.lower()
        if "principal" in lowered and any(term in lowered for term in fallback_terms):
            identifiers.append(identifier)
    return identifiers


def assert_no_synthetic_logout_correlation_source(
    test: unittest.TestCase,
    source: str,
    message: str,
) -> None:
    forbidden_identifiers = fallback_principal_identifiers(source)
    test.assertFalse(
        forbidden_identifiers,
        f"{message} Found fake/last-principal-style identifier(s): {forbidden_identifiers}.",
    )
    for forbidden_pattern in (
        r"\bObelisk::Core::PlayerPrincipalToken\s*[{(]",
        r"\bPlayerPrincipalToken\s*[{(]",
        r"\bAllocatePrincipal\s*\(",
        r"\bReactivatePrincipal\s*\(",
        r"(?:\.|->)\s*Principal\b",
    ):
        test.assertIsNone(
            re.search(forbidden_pattern, source),
            f"{message} Logout correlation must not synthesize or reuse a principal token "
            f"through pattern {forbidden_pattern!r}.",
        )


def private_logout_correlation_source(
    body: str,
    apply_call_index: int,
    correlation_argument: str,
) -> str:
    source_parts = [correlation_argument]
    identifiers = cpp_identifiers(correlation_argument)
    pre_apply_body = body[:apply_call_index]
    for identifier in identifiers:
        try:
            source_parts.append(extract_variable_initializer(pre_apply_body, identifier))
        except AssertionError:
            pass
    return "\n".join(source_parts)


def lifecycle_logging_budget_derived_variables(body: str) -> set[str]:
    derived: set[str] = set()
    reserve_call_pattern = re.compile(
        r"\bTryReserveObservationBudget\s*\(\s*"
        r"(?P<counter>[^,]+?)\s*,\s*"
        r"(?P<limit>[^,]+?)\s*,\s*"
        r"(?P<out>[A-Za-z_][A-Za-z0-9_]*)\s*\)",
        re.S,
    )
    for match in reserve_call_pattern.finditer(body):
        counter = compact_cpp_expression(match.group("counter"))
        limit = compact_cpp_expression(match.group("limit"))
        if "s_PlayerPrincipalLifecycleObservations" in counter or "gate.LogLimit" in limit:
            derived.add(match.group("out"))

    assignment_pattern = re.compile(
        r"(?:\b(?:const\s+)?(?:auto|bool|uint64_t|std::uint64_t|[A-Za-z_][A-Za-z0-9_:<>]*)\s+)?"
        r"(?P<target>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<expression>[^;]+);",
        re.S,
    )
    changed = True
    while changed:
        changed = False
        for match in assignment_pattern.finditer(body):
            target = match.group("target")
            expression = match.group("expression")
            compact_expression = compact_cpp_expression(expression)
            if target in derived:
                continue
            if (
                "s_PlayerPrincipalLifecycleObservations" in compact_expression
                or "gate.LogLimit" in compact_expression
                or any(expression_mentions_identifier(expression, source) for source in derived)
            ):
                derived.add(target)
                changed = True

    return derived


def signed_guards_for_condition(condition: str) -> set[tuple[str, str]]:
    guards: set[tuple[str, str]] = set()
    for match in re.finditer(r"(!?)\s*defined\s*\(?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)?", condition):
        sign = "-" if match.group(1) else "+"
        guards.add((sign, match.group(2)))
    return guards


def active_preprocessor_guards_by_line(text: str) -> dict[int, set[tuple[str, str]]]:
    active_by_line: dict[int, set[tuple[str, str]]] = {}
    stack: list[set[tuple[str, str]]] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#ifdef"):
            macro = stripped.removeprefix("#ifdef").strip()
            stack.append({("+", macro)})
            active_by_line[line_number] = set().union(*stack) if stack else set()
            continue
        if stripped.startswith("#ifndef"):
            macro = stripped.removeprefix("#ifndef").strip()
            stack.append({("-", macro)})
            active_by_line[line_number] = set().union(*stack) if stack else set()
            continue
        if stripped.startswith("#if"):
            stack.append(signed_guards_for_condition(stripped.removeprefix("#if")))
            active_by_line[line_number] = set().union(*stack) if stack else set()
            continue
        if stripped.startswith("#elif"):
            if stack:
                stack[-1] = signed_guards_for_condition(stripped.removeprefix("#elif"))
            active_by_line[line_number] = set().union(*stack) if stack else set()
            continue
        if stripped.startswith("#else"):
            if stack:
                stack[-1] = {("else", macro) for _, macro in stack[-1]}
            active_by_line[line_number] = set().union(*stack) if stack else set()
            continue
        if stripped.startswith("#endif"):
            active_by_line[line_number] = set().union(*stack) if stack else set()
            if stack:
                stack.pop()
            continue

        active_by_line[line_number] = set().union(*stack) if stack else set()

    return active_by_line


def extract_lifecycle_drift_constants(text: str) -> dict[str, int]:
    uncommented = strip_c_comments(text)
    constants: dict[str, int] = {}
    pattern = re.compile(
        r"constexpr\s+int32_t\s+"
        r"(?P<name>kObserved(?:HandleNewPlayer|CheckJoinInProgress|OnLogout)[A-Za-z0-9_]*)"
        r"\s*=\s*(?P<value>-?\d+)\s*;"
    )
    for match in pattern.finditer(uncommented):
        constants[match.group("name")] = int(match.group("value"))
    return constants


def extract_lifecycle_drift_chain_block(text: str, name: str) -> str:
    uncommented = strip_c_comments(text)
    pattern = re.compile(
        rf"constexpr\s+std::array<[^;]+?>\s+{re.escape(name)}\s*\{{\{{"
        r"(?P<body>.*?)\}\};",
        re.S,
    )
    match = pattern.search(uncommented)
    if match is None:
        raise AssertionError(f"drift chain block not found: {name}")
    return compact_cpp_expression(match.group("body"))


class PlayerPrincipalRuntimeGuardrailsTest(unittest.TestCase):
    def test_player_principal_test_hooks_require_explicit_test_hook_macros(self) -> None:
        for relative_path, spec in TEST_HOOK_FILES.items():
            with self.subTest(file=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                active_by_line = active_preprocessor_guards_by_line(uncommented)

                auto_enable_guard = re.search(
                    r"!\s*defined\s*\(?\s*obelisk_EXPORTS\s*\)?|#\s*ifndef\s+obelisk_EXPORTS\b",
                    uncommented,
                )
                self.assertIsNone(
                    auto_enable_guard,
                    f"{relative_path} must not auto-enable test hooks outside libobelisk builds; "
                    "use the explicit player principal test-hook macro instead.",
                )

                expected_guard = ("+", spec["guard"])
                for token in spec["tokens"]:
                    token_lines = [
                        line_number
                        for line_number, line in enumerate(uncommented.splitlines(), start=1)
                        if token in line
                    ]
                    self.assertTrue(token_lines, f"{relative_path} is missing expected test hook {token}")

                    for line_number in token_lines:
                        active_guards = active_by_line[line_number]
                        self.assertIn(
                            expected_guard,
                            active_guards,
                            f"{relative_path}:{line_number} {token} must be guarded by {spec['guard']}.",
                        )
                        self.assertNotIn(
                            ("-", "obelisk_EXPORTS"),
                            active_guards,
                            f"{relative_path}:{line_number} {token} must not be enabled by !defined(obelisk_EXPORTS).",
                        )

    def test_player_principal_registry_bounded_retention_keeps_cxx_guardrail(self) -> None:
        tests_text = strip_c_comments(PLAYER_PRINCIPAL_REGISTRY_TESTS.read_text(encoding="utf-8"))
        body = extract_function_body(
            tests_text,
            r"void\s+TestInvalidatedPrincipalRetentionIsBoundedWithoutHandleReuse\s*\(",
        )
        compact_body = compact_cpp_expression(body)

        for expected in (
            "registry.SetMaxRetainedInvalidatedPrincipalsForTesting(2)",
            "registry.LogoutPrincipal(first)",
            "registry.LogoutPrincipal(second)",
            "registry.LogoutPrincipal(third)",
            "registry.RetainedInvalidatedCount()==2",
            "registry.Lookup(first).Status==PlayerPrincipalLookupStatus::UnknownHandle",
            "registry.Lookup(second).Status==PlayerPrincipalLookupStatus::Invalidated",
            "registry.Lookup(third).Status==PlayerPrincipalLookupStatus::Invalidated",
            "registry.SetNextHandleForTesting(first.Handle)",
            "afterPrune.Handle>third.Handle",
        ):
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    compact_body,
                    "PlayerPrincipalRegistryTests.cpp must keep focused behavioral coverage "
                    "for bounded invalidated-principal retention, retained-count accounting, "
                    "and no reuse of an evicted handle.",
                )

        main_body = extract_function_body(tests_text, r"int\s+main\s*\(")
        self.assertIn(
            "TestInvalidatedPrincipalRetentionIsBoundedWithoutHandleReuse();",
            compact_cpp_expression(main_body),
            "PlayerPrincipalRegistryTests.cpp must invoke the bounded-retention test.",
        )

        cmake_text = CMAKE_LISTS.read_text(encoding="utf-8")
        target_match = re.search(
            r"add_executable\s*\(\s*player_principal_registry_tests(?P<body>.*?)\)",
            cmake_text,
            re.S,
        )
        self.assertIsNotNone(
            target_match,
            "CMakeLists.txt must keep the PlayerPrincipalRegistry test executable.",
        )
        target_body = target_match.group("body")
        self.assertIn(
            "tests/core/PlayerPrincipalRegistryTests.cpp",
            target_body,
            "player_principal_registry_tests must compile the registry C++ behavioral tests.",
        )
        self.assertIn(
            "core/PlayerPrincipalRegistry.cpp",
            target_body,
            "player_principal_registry_tests must compile the registry implementation under test.",
        )

        compile_definitions_match = re.search(
            r"target_compile_definitions\s*\(\s*player_principal_registry_tests(?P<body>.*?)\)",
            cmake_text,
            re.S,
        )
        self.assertIsNotNone(
            compile_definitions_match,
            "player_principal_registry_tests must keep explicit test-hook compile definitions.",
        )
        self.assertIn(
            "OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS=1",
            compile_definitions_match.group("body"),
            "player_principal_registry_tests must explicitly enable registry test hooks.",
        )
        self.assertRegex(
            cmake_text,
            r"add_test\s*\(\s*NAME\s+PlayerPrincipalRegistryTests\s+COMMAND\s+"
            r"player_principal_registry_tests\s*\)",
            "CMakeLists.txt must register PlayerPrincipalRegistryTests with CTest.",
        )

    def test_player_principal_lifecycle_no_evidence_edges_keep_cxx_guardrail(self) -> None:
        tests_text = strip_c_comments(
            PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR_TESTS.read_text(encoding="utf-8")
        )

        def compact_test_body(test_name: str) -> str:
            return compact_cpp_expression(
                extract_function_body(tests_text, rf"void\s+{test_name}\s*\(")
            )

        expected_by_test = {
            "TestSessionEndWithoutCorrelationDoesNotInvalidate": (
                "ApplyLifecycleObservationToRegistry(registry,MakeEndObservation(999))",
                "end.Status==Applicator::ApplyStatus::SessionEndUnresolvedNoop",
                "!end.RegistryChanged",
                "RequireNoRegistryPointer(end,",
                "!end.Principal.HasValidShape()",
                "end.InvalidationReasons==0",
                "!end.PrincipalLive",
                "registry.Validate(start.Principal)",
                "registry.LiveCount()==1",
            ),
            "TestSessionEndWithSuppliedPrincipalButNoBoundProofDoesNotInvalidate": (
                "!Correlation::TryResolveLogoutCorrelation(endObservation,resolvedLogoutCorrelation)",
                "ApplyLifecycleObservationToRegistry(registry,endObservation,&start.Principal,&endContext)",
                "end.Status==Applicator::ApplyStatus::SessionEndUnresolvedNoop",
                "!end.RegistryChanged",
                "RequireNoRegistryPointer(end,",
                "!end.Principal.HasValidShape()",
                "end.InvalidationReasons==0",
                "!end.PrincipalLive",
                "registry.Validate(start.Principal)",
                "registry.LiveCount()==1",
            ),
            "TestSessionEndInvalidationRequiresRetainedLogoutProof": (
                "registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0)",
                "end.Status==Applicator::ApplyStatus::SessionEndStaleNoop",
                "!end.ValidatedLifecycleEvent",
                "!end.RegistryChanged",
                "!end.PrincipalLive",
                "registry.Lookup(start.Principal).Status==Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle",
                "registry.LiveCount()==0",
                "registry.RetainedInvalidatedCount()==0",
                "!Correlation::TryResolveLogoutCorrelation(endObservation,resolvedLogoutCorrelation)",
            ),
            "TestRejectedAndDiagnosticObservationsDoNotAllocate": (
                "MakeCheckJoinRejectedObservation()",
                "result.Status==Applicator::ApplyStatus::SessionStartRejectedNoop",
                "!result.RegistryChanged",
                "RequireNoRegistryPointer(result,",
                "registry.LiveCount()==0",
            ),
            "TestInternalDispatchBridgeRejectsRejectedNoopWithRegistryProof": (
                ".Status=Applicator::ApplyStatus::SessionStartRejectedNoop",
                ".Registry=&registry",
                "DispatchLifecycleApplyResultToInternalSubscribers(forgedRejected,MakeCheckJoinRejectedObservation())==0",
                "capture.Calls==0",
            ),
            "TestInternalDispatchBridgeRejectsPrunedTerminalProof": (
                "registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0)",
                "end.Status==Applicator::ApplyStatus::SessionEndStaleNoop",
                "!end.ValidatedLifecycleEvent",
                "!end.RegistryChanged",
                "registry.Lookup(end.Principal).Status==Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle",
                "DispatchLifecycleApplyResultToInternalSubscribers(end,endObservation)==0",
                "capture.Calls==0",
            ),
        }

        for test_name, expected_fragments in expected_by_test.items():
            body = compact_test_body(test_name)
            for expected in expected_fragments:
                with self.subTest(test=test_name, expected=expected):
                    self.assertIn(
                        expected,
                        body,
                        "PlayerPrincipalLifecycleApplicatorTests.cpp must keep focused "
                        "coverage proving logout-only/unresolved, pruned terminal, and "
                        "rejected-start lifecycle observations stay no-evidence unless "
                        "fresh registry/correlation proof validates them.",
                    )

        main_body = compact_cpp_expression(extract_function_body(tests_text, r"int\s+main\s*\("))
        for test_name in expected_by_test:
            with self.subTest(invoked=test_name):
                self.assertIn(
                    f"{test_name}();",
                    main_body,
                    "PlayerPrincipalLifecycleApplicatorTests.cpp must invoke the C++ "
                    "no-evidence lifecycle guardrail test.",
                )

    def test_process_event_hook_applies_player_principal_lifecycle_before_log_gate(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)

        self.assertTrue(
            '#include "ProcessEventPlayerPrincipalLifecycleApplicator.h"' in uncommented,
            "ProcessEventHook.cpp must include the lifecycle applicator before it can update "
            "PlayerPrincipalRegistry from copied lifecycle observations.",
        )

        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )
        active_body = extract_function_body(
            uncommented,
            r"static\s+bool\s+IsPlayerPrincipalLifecycleObserverActive\s*\(",
        )
        self.assertIn(
            "IsPlayerPrincipalLifecycleObserverEnabled()",
            active_body,
            "ProcessEventHook.cpp should keep the player-principal lifecycle route active "
            "when the observer gate is enabled.",
        )
        for logging_budget_token in (
            "HasObservationBudgetRemaining",
            "TryReserveObservationBudget",
            "LogLimit",
        ):
            self.assertNotIn(
                logging_budget_token,
                active_body,
                "IsPlayerPrincipalLifecycleObserverActive must not depend on logging budget; "
                "otherwise nameIndex routing can stop before the registry applicator runs.",
            )

        copy_call_index = body.find("TryBuildCopiedLifecycleObservationAfterOriginal")
        self.assertNotEqual(
            copy_call_index,
            -1,
            "ObservePlayerPrincipalLifecycleAfterOriginal should still build the copied lifecycle observation.",
        )

        after_copy = body[copy_call_index:]
        early_log_gate = re.search(
            r"if\s*\(\s*!\s*ProcessEventPlayerPrincipalLifecycleObserver::ShouldLogObservation\s*\(",
            after_copy,
            re.S,
        )
        guardrail_window = after_copy[: early_log_gate.start()] if early_log_gate else after_copy

        applicator_call = re.search(
            r"\bApplyLifecycleObservationToRegistry\s*\(",
            guardrail_window,
        )
        self.assertIsNotNone(
            applicator_call,
            "ProcessEventHook.cpp must apply the copied player-principal lifecycle observation "
            "to PlayerPrincipalRegistry before any ShouldLogObservation early return, so registry "
            "state is not gated by diagnostic logging budget.",
        )
        registry_singleton = re.search(
            r"\bPlayerPrincipalRegistry::Get\s*\(",
            guardrail_window,
        )
        self.assertIsNotNone(
            registry_singleton,
            "ProcessEventHook.cpp must pass the process-lifetime PlayerPrincipalRegistry singleton "
            "to the lifecycle applicator before the logging-only early return.",
        )

    def test_process_event_hook_builds_process_local_context_after_copied_observation(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )

        validation_match = re.search(
            r"if\s*\(\s*!\s*ProcessEventPlayerPrincipalLifecycleObserver::"
            r"TryBuildCopiedLifecycleObservationAfterOriginal\s*\(",
            body,
            re.S,
        )
        self.assertIsNotNone(
            validation_match,
            "ObservePlayerPrincipalLifecycleAfterOriginal must validate the copied lifecycle "
            "observation before building runtime event context.",
        )
        _, validation_failure_block_end = extract_braced_body_span(body, validation_match)

        context_name, context_initializer, context_index, context_end = (
            extract_process_local_event_context_declaration(body)
        )
        self.assertGreater(
            context_index,
            validation_failure_block_end,
            "ProcessEventHook.cpp must create ProcessLocalEventContext only after "
            "TryBuildCopiedLifecycleObservationAfterOriginal has accepted the copied observation.",
        )
        context_fields = extract_designated_initializer_fields(context_initializer)
        self.assertEqual(
            set(context_fields),
            {"EventSequence", "ServerProcessEpoch"},
            "ProcessLocalEventContext should contain only process-local event metadata.",
        )

        sequence_initializer = extract_variable_initializer(body, "runtimeEventSequence")
        self.assertEqual(
            compact_cpp_expression(sequence_initializer),
            "NextPlayerPrincipalLifecycleRuntimeEventSequence()",
            "ProcessEventHook.cpp must generate runtimeEventSequence from the dedicated "
            "runtime event sequence helper.",
        )
        self.assertEqual(
            compact_cpp_expression(context_fields["EventSequence"]),
            "runtimeEventSequence",
            "ProcessLocalEventContext.EventSequence must use the generated runtime event sequence.",
        )
        self.assertEqual(
            compact_cpp_expression(context_fields["ServerProcessEpoch"]),
            "GetPlayerPrincipalLifecycleServerProcessEpoch()",
            "ProcessLocalEventContext.ServerProcessEpoch must use the process-local epoch helper.",
        )

        apply_call_index = find_call_index(body, "ApplyLifecycleObservationToRegistry", context_end)
        apply_arguments, _, apply_call_end = extract_call_arguments_span_at(body, apply_call_index)
        apply_values = split_top_level_arguments(apply_arguments)
        self.assertEqual(
            len(apply_values),
            4,
            "ApplyLifecycleObservationToRegistry must receive registry, observation, optional "
            "correlation, and ProcessLocalEventContext arguments.",
        )
        self.assertIn(
            "PlayerPrincipalRegistry::Get()",
            compact_cpp_expression(apply_values[0]),
            "ApplyLifecycleObservationToRegistry must update the process-lifetime registry singleton.",
        )
        self.assertEqual(
            compact_cpp_expression(apply_values[1]),
            "observation",
            "ApplyLifecycleObservationToRegistry must receive the copied lifecycle observation.",
        )
        self.assertEqual(
            compact_cpp_expression(apply_values[3]),
            f"&{context_name}",
            "ApplyLifecycleObservationToRegistry must receive the ProcessLocalEventContext created "
            "after copied observation validation.",
        )

        dispatch_call_index = find_call_index(
            body,
            "DispatchLifecycleApplyResultToInternalSubscribers",
            apply_call_end,
        )
        dispatch_arguments, _, dispatch_call_end = extract_call_arguments_span_at(body, dispatch_call_index)
        dispatch_values = split_top_level_arguments(dispatch_arguments)
        self.assertEqual(
            [compact_cpp_expression(argument) for argument in dispatch_values],
            ["applyResult", "observation"],
            "ProcessEventHook.cpp must pass the lifecycle apply result and copied observation "
            "to the internal player-principal dispatch bridge.",
        )
        log_gate_index = body.find("if (!logReserved", apply_call_end)
        self.assertNotEqual(
            log_gate_index,
            -1,
            "ProcessEventHook.cpp must keep the logging-budget gate after runtime apply/dispatch.",
        )
        self.assertLess(
            dispatch_call_index,
            log_gate_index,
            "ProcessEventHook.cpp must invoke the internal player-principal dispatch bridge before "
            "the logging-budget early return.",
        )

        post_copy_runtime_region = body[validation_failure_block_end:dispatch_call_end]
        for logging_budget_token in (
            "TryReserveObservationBudget",
            "ShouldLogObservation",
            "logReserved",
            "observationNumber",
            "s_PlayerPrincipalLifecycleObservations",
            "gate.LogLimit",
        ):
            self.assertNotIn(
                logging_budget_token,
                post_copy_runtime_region,
                "The post-copy runtime context/applicator path must stay independent from the "
                "diagnostic logging budget counter; logging budget state belongs only to log emission.",
            )

    def test_observer_budget_prefilter_uses_metadata_only_first_pass(self) -> None:
        text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"Attempt\s+TryObserveInvocation\s*\(",
        )

        metadata_call_index = find_call_index(body, "TryIdentifyInvocationWithTokenMode")
        metadata_arguments, _, metadata_call_end = extract_call_arguments_span_at(body, metadata_call_index)
        self.assertIn(
            "ProcessLocalSubjectTokenMode::MetadataOnly",
            metadata_arguments,
            "TryObserveInvocation's first lifecycle recognition pass must not read/copy params "
            "before the post-recognition budget recheck.",
        )
        self.assertNotIn(
            "ProcessLocalSubjectTokenMode::Skip",
            metadata_arguments,
            "TryObserveInvocation must reserve Skip for explicitly budgeted diagnostic paths; "
            "the accepted-event metadata prefilter should be param-copy-free.",
        )

        budget_recheck_index = body.find(
            "HasObservationBudgetRemaining",
            metadata_call_end,
        )
        self.assertNotEqual(
            budget_recheck_index,
            -1,
            "TryObserveInvocation must re-check budget after metadata-only recognition.",
        )
        self.assertLess(
            metadata_call_end,
            budget_recheck_index,
            "TryObserveInvocation should re-check budget immediately after the metadata-only pass.",
        )
        final_assign_index = body.find(
            "ProcessLocalSubjectTokenMode::Assign",
            metadata_call_end,
        )
        self.assertNotEqual(
            final_assign_index,
            -1,
            "TryObserveInvocation must keep the final copied pass that assigns process-local "
            "subject tokens after the metadata-only prefilter.",
        )
        self.assertLess(
            budget_recheck_index,
            final_assign_index,
            "TryObserveInvocation must re-check budget before the final token-assigning pass.",
        )

    def test_process_event_hook_does_not_pass_synthetic_logout_correlation_token(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )

        apply_call_index = find_call_index(body, "ApplyLifecycleObservationToRegistry")
        apply_arguments = split_top_level_arguments(
            extract_call_arguments_at(body, apply_call_index)
        )
        self.assertEqual(
            len(apply_arguments),
            4,
            "ApplyLifecycleObservationToRegistry must keep the explicit optional logout "
            "correlation argument separate from event context.",
        )

        correlation_argument = apply_arguments[2]
        correlation_source = private_logout_correlation_source(
            body,
            apply_call_index,
            correlation_argument,
        )
        assert_no_synthetic_logout_correlation_source(
            self,
            correlation_source,
            "ProcessEventHook.cpp must not pass a fake, cached, previous, or last-principal "
            "token to ApplyLifecycleObservationToRegistry.",
        )

        if compact_cpp_expression(correlation_argument) == "nullptr":
            return

        lowered_source = correlation_source.lower()
        self.assertIn(
            "correl",
            lowered_source,
            "Non-null session_end correlation passed by ProcessEventHook.cpp must come from "
            "an explicit private correlation helper/token path.",
        )
        self.assertRegex(
            lowered_source,
            r"logout|session_?end",
            "Non-null player-principal correlation must be scoped to logout/session_end, "
            "not a generic last-principal fallback.",
        )
        self.assertNotRegex(
            correlation_source,
            r"\bObeliskPlayerPrincipal[A-Za-z0-9_]*\b",
            "Private logout correlation must not use public ObeliskPlayerPrincipal* ABI tokens.",
        )

    def test_lifecycle_applicator_session_end_uses_only_explicit_correlation_token(self) -> None:
        text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"ApplyResult\s+ApplyLifecycleObservationToRegistry\s*\(",
        )

        session_end_index = body.find("case Obelisk::Core::PlayerPrincipalEventKind::SessionEnd")
        self.assertNotEqual(
            session_end_index,
            -1,
            "ApplyLifecycleObservationToRegistry must keep an explicit session_end branch.",
        )
        lookup_index = body.find("registry.Lookup", session_end_index)
        logout_index = body.find("registry.LogoutPrincipal", session_end_index)
        self.assertNotEqual(
            lookup_index,
            -1,
            "session_end registry lookup must use the explicit correlated logout token.",
        )
        self.assertNotEqual(
            logout_index,
            -1,
            "session_end registry logout must use the explicit correlated logout token.",
        )

        pre_lookup = body[session_end_index:lookup_index]
        self.assertIn(
            "correlatedLogoutPrincipal",
            pre_lookup,
            "session_end must validate the optional correlatedLogoutPrincipal before lookup.",
        )
        self.assertIn(
            "HasValidShape",
            pre_lookup,
            "session_end must reject missing or malformed logout correlation tokens before lookup.",
        )
        self.assertIn(
            "IsFreshResolvedLogoutCorrelation",
            pre_lookup,
            "session_end must verify the resolved logout correlation against current "
            "event-sequence/server-epoch proof before registry lookup.",
        )
        fresh_check_index = pre_lookup.find("IsFreshResolvedLogoutCorrelation")
        self.assertNotEqual(
            fresh_check_index,
            -1,
            "session_end must keep an explicit freshness check before registry lookup.",
        )
        compact_fresh_failure_region = compact_cpp_expression(pre_lookup[fresh_check_index:])
        self.assertIn(
            "returnResult(ApplyStatus::SessionEndUnresolvedNoop,event);",
            compact_fresh_failure_region,
            "A resolved-but-unfresh logout correlation must remain unresolved before registry "
            "lookup, so stale/equal/epoch-drift context cannot return a principal-shaped "
            "status without fresh local proof.",
        )
        self.assertNotIn(
            "SessionEndStaleNoop,*correlatedLogoutPrincipal",
            compact_fresh_failure_region,
            "The pre-lookup freshness failure path must not return a token-bearing stale "
            "result; stale/duplicate statuses are only safe after fresh local proof reaches "
            "the registry lookup.",
        )
        assert_no_synthetic_logout_correlation_source(
            self,
            pre_lookup,
            "ApplyLifecycleObservationToRegistry session_end must not invent a fake/last-principal "
            "correlation before registry lookup.",
        )

        _, _, logout_call_end = extract_call_arguments_span_at(body, logout_index)
        session_end_mutation_region = body[session_end_index:logout_call_end]
        self.assertNotRegex(
            session_end_mutation_region,
            r"\bPlayerPrincipalRegistry::Get\s*\(",
            "The applicator must use its injected registry and explicit correlation token, "
            "not a hidden singleton/fallback lookup path.",
        )
        for expected in (
            "registry.Lookup(*correlatedLogoutPrincipal)",
            "registry.LogoutPrincipal(*correlatedLogoutPrincipal)",
        ):
            self.assertIn(
                expected,
                compact_cpp_expression(session_end_mutation_region),
                "session_end correlation must flow through the explicit correlatedLogoutPrincipal token.",
            )

    def test_process_local_subject_tokens_are_not_logged(self) -> None:
        log_call_pattern = r"\bOBELISK_(?:INFO|WARN|ERROR)\s*\("

        for relative_path in PLAYER_PRINCIPAL_HOOK_PATH_FILES:
            with self.subTest(file=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                log_calls = extract_calls(uncommented, log_call_pattern)

                for macro_name, arguments, line_number in log_calls:
                    for token_term in PROCESS_LOCAL_SUBJECT_TOKEN_TERMS:
                        self.assertNotIn(
                            token_term,
                            arguments,
                            f"{relative_path}:{line_number} {macro_name} must not format or "
                            f"emit private ProcessLocalSubjectToken data; found {token_term!r}.",
                        )

    def test_public_obelisk_headers_do_not_expose_process_local_subject_tokens(self) -> None:
        header_paths = sorted(PUBLIC_OBELISK_HEADER_ROOT.rglob("*.h"))
        self.assertTrue(header_paths, "Expected public Obelisk headers under include/obelisk.")

        for header_path in header_paths:
            relative_path = header_path.relative_to(REPO_ROOT).as_posix()
            with self.subTest(file=relative_path):
                text = header_path.read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                for token_term in PROCESS_LOCAL_SUBJECT_TOKEN_TERMS:
                    self.assertNotIn(
                        token_term,
                        uncommented,
                        f"{relative_path} must not expose private ProcessLocalSubjectToken "
                        f"internals through the public ABI/header surface; found {token_term!r}.",
                    )

    def test_copied_lifecycle_observation_retains_subject_tokens_only_for_new_player_and_exiting(self) -> None:
        text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"uint64_t\s+CopyableProcessLocalSubjectToken\s*\(",
        )

        for allowed_field in ("NewPlayer", "Exiting"):
            with self.subTest(field=allowed_field):
                case_group = extract_case_group_until_return(
                    body,
                    f"LifecycleField::{allowed_field}",
                )
                self.assertIn(
                    "field.ProcessLocalSubjectToken",
                    case_group,
                    f"Copied lifecycle observations should retain private subject tokens only "
                    f"for {allowed_field}.",
                )

        for forbidden_field in ("PlayerData", "PlayerCharacter"):
            with self.subTest(field=forbidden_field):
                case_group = extract_case_group_until_return(
                    body,
                    f"LifecycleField::{forbidden_field}",
                )
                compact_case_group = compact_cpp_expression(case_group)
                self.assertNotIn(
                    "field.ProcessLocalSubjectToken",
                    case_group,
                    f"Copied lifecycle observations must redact {forbidden_field} without "
                    "retaining its private subject token.",
                )
                self.assertRegex(
                    compact_case_group,
                    r"return(?:uint64_t\{0\}|0);",
                    f"CopyableProcessLocalSubjectToken must return zero for {forbidden_field}.",
                )

        self.assertIn(
            "IsAssignedProcessLocalSubjectToken(field.ProcessLocalSubjectToken)",
            body,
            "CopyableProcessLocalSubjectToken must route copied subject-token decisions "
            "through the sentinel-aware assigned-token helper.",
        )
        assigned_token_body = extract_function_body(
            uncommented,
            r"bool\s+IsAssignedProcessLocalSubjectToken\s*\(",
        )
        self.assertIn(
            "std::numeric_limits<uint64_t>::max()",
            assigned_token_body,
            "IsAssignedProcessLocalSubjectToken must reserve the validate-only private "
            "subject-token sentinel instead of allowing it into lifecycle observations.",
        )

    def test_validate_only_subject_token_sentinel_is_not_canonical_copied_state(self) -> None:
        observer_text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER.read_text(encoding="utf-8")
        observer_uncommented = strip_c_comments(observer_text)
        validation_helper_body = extract_function_body(
            observer_uncommented,
            r"void\s+ReplaceValidateOnlySubjectTokenSentinelForCopiedValidation\s*\(",
        )
        self.assertIn(
            "std::numeric_limits<uint64_t>::max()",
            validation_helper_body,
            "The observer's pre-budget validation pass may recognize the validate-only "
            "sentinel only through an explicit local helper.",
        )

        canonical_checks = (
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER,
                r"bool\s+HasCanonicalHandleNewPlayerRedactedSubjectShape\s*\(",
            ),
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER,
                r"bool\s+HasCanonicalOnLogoutRedactedSubjectShape\s*\(",
            ),
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR,
                r"bool\s+HasCanonicalSessionStartSubjectTokenShape\s*\(",
            ),
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR,
                r"bool\s+HasCanonicalSessionEndSubjectTokenShape\s*\(",
            ),
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION,
                r"bool\s+TryGetCanonicalSessionStartSubjectToken\s*\(",
            ),
            (
                PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION,
                r"bool\s+TryGetCanonicalSessionEndSubjectToken\s*\(",
            ),
        )
        for source_path, function_pattern in canonical_checks:
            with self.subTest(file=source_path.relative_to(REPO_ROOT).as_posix(),
                              function=function_pattern):
                body = extract_function_body(
                    strip_c_comments(source_path.read_text(encoding="utf-8")),
                    function_pattern,
                )
                self.assertIn(
                    "std::numeric_limits<uint64_t>::max()",
                    body,
                    "Copied lifecycle subject-token canonical checks must reject the "
                    "validate-only sentinel before registry or correlation state can use it.",
                )

    def test_lifecycle_reflection_does_not_retain_raw_ue_pointer_keys_for_subject_tokens(self) -> None:
        text = PLAYER_PRINCIPAL_LIFECYCLE_REFLECTION.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        self.assertNotIn(
            "TokensByObjectAddress",
            uncommented,
            "Lifecycle reflection must not retain raw UE object addresses for private subject tokens.",
        )
        self.assertIsNone(
            re.search(r"std::unordered_map\s*<\s*uintptr_t\s*,\s*uint64_t\s*>", uncommented),
            "Lifecycle reflection must key private subject-token maps by process-local "
            "fingerprints, not raw uintptr_t UE addresses.",
        )

    def test_lifecycle_drift_tables_match_between_reflection_and_observer(self) -> None:
        reflection_text = PLAYER_PRINCIPAL_LIFECYCLE_REFLECTION.read_text(encoding="utf-8")
        observer_text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER.read_text(encoding="utf-8")

        self.assertEqual(
            extract_lifecycle_drift_constants(reflection_text),
            extract_lifecycle_drift_constants(observer_text),
            "Player-principal lifecycle observed drift constants must stay identical "
            "between UE reflection and the hook-side copied observer.",
        )

        for chain_name in (
            "kObservedHandleNewPlayerDriftChains",
            "kObservedCheckJoinInProgressDriftChains",
        ):
            with self.subTest(chain=chain_name):
                self.assertEqual(
                    extract_lifecycle_drift_chain_block(reflection_text, chain_name),
                    extract_lifecycle_drift_chain_block(observer_text, chain_name),
                    f"{chain_name} must stay in sync between reflection and observer.",
                )

    def test_hook_logout_correlation_uses_private_helper_not_fallback_cache(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        self.assertIn(
            '#include "ProcessEventPlayerPrincipalLifecycleCorrelation.h"',
            uncommented,
            "ProcessEventHook.cpp must use the private lifecycle correlation helper.",
        )
        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )

        resolve_call_index = find_call_index(body, "TryResolveLogoutCorrelation")
        apply_call_index = find_call_index(body, "ApplyLifecycleObservationToRegistry", resolve_call_index)
        apply_arguments, _, apply_call_end = extract_call_arguments_span_at(body, apply_call_index)
        apply_values = split_top_level_arguments(apply_arguments)
        self.assertEqual(
            compact_cpp_expression(apply_values[2]),
            "logoutCorrelationPrincipal",
            "ApplyLifecycleObservationToRegistry must receive only the explicit logout "
            "correlation helper result as its optional session_end token.",
        )
        self.assertLess(
            resolve_call_index,
            apply_call_index,
            "The hook must resolve logout/session_end correlation before applying the lifecycle observation.",
        )

        correlation_initializer = extract_variable_initializer(body, "logoutCorrelationPrincipal")
        compact_initializer = compact_cpp_expression(correlation_initializer)
        self.assertIn(
            "ProcessEventPlayerPrincipalLifecycleCorrelation::TryResolveLogoutCorrelation"
            "(observation,correlatedLogoutPrincipal)",
            compact_initializer,
            "The hook's optional correlation token must come from the private logout correlation helper.",
        )
        self.assertIn(
            "?&correlatedLogoutPrincipal:nullptr",
            compact_initializer,
            "The hook must pass no correlation token unless the private helper resolved one.",
        )
        assert_no_synthetic_logout_correlation_source(
            self,
            correlation_initializer,
            "ProcessEventHook.cpp logout correlation initializer must not use latest, "
            "previous, cached, or synthetic fallback principal/token state.",
        )

        bind_call_index = find_call_index(body, "BindSessionStartCorrelation", apply_call_end)
        clear_call_index = find_call_index(body, "ClearSessionEndCorrelation", bind_call_index)
        self.assertLess(
            apply_call_index,
            bind_call_index,
            "Session-start correlation binding must happen after registry apply, when the "
            "new principal token is explicit.",
        )
        self.assertLess(
            bind_call_index,
            clear_call_index,
            "Session-end correlation cleanup must remain an explicit private helper call, "
            "not a latest/previous/cache hook-side heuristic.",
        )

        correlation_text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION.read_text(encoding="utf-8")
        correlation_uncommented = strip_c_comments(correlation_text)
        resolve_body = extract_function_body(
            correlation_uncommented,
            r"bool\s+TryResolveLogoutCorrelation\s*\(",
        )
        compact_resolve_body = compact_cpp_expression(resolve_body)
        self.assertIn(
            "observation.Role!=ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionEnd",
            compact_resolve_body,
            "TryResolveLogoutCorrelation must be scoped to session_end observations.",
        )
        self.assertIn(
            "TryGetCanonicalSessionEndSubjectToken(observation,subjectToken)",
            compact_resolve_body,
            "TryResolveLogoutCorrelation must correlate logout only through the canonical "
            "session_end subject-token helper.",
        )
        canonical_end_body = extract_function_body(
            correlation_uncommented,
            r"bool\s+TryGetCanonicalSessionEndSubjectToken\s*\(",
        )
        compact_canonical_end_body = compact_cpp_expression(canonical_end_body)
        for expected in (
            "observation.RedactedCount!=1",
            "observation.RedactedStorage[0]!=LifecycleField::Exiting",
            "observation.RedactedProcessLocalSubjectTokens[0]==0",
        ):
            with self.subTest(canonical_session_end_check=expected):
                self.assertIn(
                    expected,
                    compact_canonical_end_body,
                    "The canonical session_end subject-token helper must require exactly "
                    "one Exiting redaction with a non-zero private subject token.",
                )
        assert_no_synthetic_logout_correlation_source(
            self,
            canonical_end_body,
            "Canonical session_end subject-token extraction must not use latest, previous, "
            "cached, or synthetic fallback principal/token state.",
        )

    def test_lifecycle_correlation_rejects_epoch_drift_and_stale_logout_clears(self) -> None:
        text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)

        epoch_drift_body = extract_function_body(
            uncommented,
            r"bool\s+IsServerEpochDrift\s*\(",
        )
        compact_epoch_drift_body = compact_cpp_expression(epoch_drift_body)
        for expected in (
            "HasStoredProofContext(previous)",
            "HasProofContext(result)",
            "previous.ServerProcessEpoch!=result.ServerProcessEpoch",
        ):
            with self.subTest(epoch_drift_check=expected):
                self.assertIn(
                    expected,
                    compact_epoch_drift_body,
                    "Server-epoch drift must be detected only from nonzero stored/current "
                    "process-local proof context.",
                )

        start_bind_body = extract_function_body(
            uncommented,
            r"void\s+BindSessionStartCorrelation\s*\(",
        )
        compact_start_bind_body = compact_cpp_expression(start_bind_body)
        self.assertIn(
            "IsServerEpochDrift(previous->second,result)",
            compact_start_bind_body,
            "Session-start correlation binding must reject replacement starts from a "
            "different server process epoch.",
        )
        self.assertIn(
            "PlayerPrincipalInvalidationReason::RuntimeReset",
            start_bind_body,
            "Epoch-drift replacement starts must invalidate the newly-created principal "
            "with a runtime-reset reason instead of superseding the existing correlation.",
        )
        self.assertLess(
            compact_start_bind_body.find("IsServerEpochDrift(previous->second,result)"),
            compact_start_bind_body.find("SupersedePreviousPrincipalIfLive"),
            "Epoch-drift starts must fail closed before any normal supersede/rebind path.",
        )

        fresh_clear_body = extract_function_body(
            uncommented,
            r"bool\s+IsFreshSessionEndClear\s*\(",
        )
        compact_fresh_clear_body = compact_cpp_expression(fresh_clear_body)
        for expected in (
            "HasStoredProofContext(entry)",
            "HasProofContext(result)",
            "entry.ServerProcessEpoch==result.ServerProcessEpoch",
            "result.EventSequence>entry.EventSequence",
        ):
            with self.subTest(fresh_clear_check=expected):
                self.assertIn(
                    expected,
                    compact_fresh_clear_body,
                    "Session-end correlation cleanup must require a newer logout result "
                    "from the same process-local server epoch.",
                )

        clear_body = extract_function_body(
            uncommented,
            r"void\s+ClearSessionEndCorrelation\s*\(",
        )
        compact_clear_body = compact_cpp_expression(clear_body)
        self.assertIn(
            "IsFreshSessionEndClear(found->second,result)",
            compact_clear_body,
            "ClearSessionEndCorrelation must reject stale/equal-order and epoch-drift logout "
            "results before removing private correlation state.",
        )
        self.assertLess(
            compact_clear_body.find("IsFreshSessionEndClear(found->second,result)"),
            compact_clear_body.find("PrincipalsBySubjectToken.erase"),
            "Freshness validation must happen before erasing the private correlation entry.",
        )

        fresh_context_body = extract_function_body(
            uncommented,
            r"bool\s+IsFreshSessionEndContext\s*\(",
        )
        compact_fresh_context_body = compact_cpp_expression(fresh_context_body)
        for expected in (
            "HasStoredProofContext(entry)",
            "HasProofContext(context)",
            "entry.ServerProcessEpoch==context->ServerProcessEpoch",
            "context->EventSequence>entry.EventSequence",
        ):
            with self.subTest(fresh_context_check=expected):
                self.assertIn(
                    expected,
                    compact_fresh_context_body,
                    "Pre-apply session-end correlation validation must require a newer logout "
                    "context from the same process-local server epoch.",
                )

        fresh_resolve_body = extract_function_body(
            uncommented,
            r"bool\s+IsFreshResolvedLogoutCorrelation\s*\(",
        )
        compact_fresh_resolve_body = compact_cpp_expression(fresh_resolve_body)
        for expected in (
            "HasProofContext(eventContext)",
            "TryGetCanonicalSessionEndSubjectToken(observation,subjectToken)",
            "found->second.AmbiguousLogoutRejectBudget!=0",
            "IsSamePrincipal(found->second.Principal,principal)",
            "IsFreshSessionEndContext(found->second,eventContext)",
        ):
            with self.subTest(fresh_resolved_logout_check=expected):
                self.assertIn(
                    expected,
                    compact_fresh_resolve_body,
                    "Resolved logout correlation must still fail closed before registry mutation "
                    "unless subject, principal, ambiguity, epoch, and sequence proof match.",
                )

        resolve_body = extract_function_body(
            uncommented,
            r"bool\s+TryResolveLogoutCorrelation\s*\(",
        )
        self.assertIn(
            "HasStoredProofContext(found->second)",
            resolve_body,
            "TryResolveLogoutCorrelation must not resolve entries without nonzero stored "
            "event-sequence/server-epoch proof context.",
        )

    def test_process_event_hook_runtime_sequence_counter_is_independent_from_log_budget(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)

        self.assertRegex(
            uncommented,
            r"static\s+std::atomic<uint64_t>\s+s_PlayerPrincipalLifecycleRuntimeEvents\s*\{\s*0\s*\};",
            "ProcessEventHook.cpp must keep a dedicated runtime event sequence counter.",
        )
        body = extract_function_body(
            uncommented,
            r"static\s+uint64_t\s+NextPlayerPrincipalLifecycleRuntimeEventSequence\s*\(",
        )
        self.assertIn(
            "s_PlayerPrincipalLifecycleRuntimeEvents",
            body,
            "Runtime event sequence generation must use the dedicated runtime event counter.",
        )
        for forbidden in (
            "s_PlayerPrincipalLifecycleObservations",
            "gate.LogLimit",
            "TryReserveObservationBudget",
            "ShouldLogObservation",
        ):
            self.assertNotIn(
                forbidden,
                body,
                "Runtime event sequence generation must not depend on the log budget counter "
                "or log emission predicates.",
            )

    def test_process_event_hook_server_process_epoch_is_nonzero_process_local(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"static\s+uint64_t\s+GetPlayerPrincipalLifecycleServerProcessEpoch\s*\(",
        )
        compact_body = compact_cpp_expression(body)

        self.assertIn(
            "std::chrono::steady_clock::now().time_since_epoch().count()",
            compact_body,
            "ServerProcessEpoch must be process-local runtime metadata, not persisted wall-clock identity.",
        )
        self.assertIn(
            "getpid()",
            compact_body,
            "ServerProcessEpoch must include the current server process id.",
        )
        self.assertIn(
            "staticconstuint64_tepoch=[]",
            compact_body,
            "ServerProcessEpoch should be stable within one server process.",
        )
        self.assertIn(
            "returnvalue==0?uint64_t{1}:value;",
            compact_body,
            "ServerProcessEpoch must be forced nonzero before it is returned.",
        )
        self.assertIn(
            "returnepoch;",
            compact_body,
            "GetPlayerPrincipalLifecycleServerProcessEpoch must return the process-local epoch.",
        )
        for forbidden in (
            "s_PlayerPrincipalLifecycleObservations",
            "gate.LogLimit",
            "TryReserveObservationBudget",
            "ShouldLogObservation",
            "std::chrono::system_clock",
            "std::time",
        ):
            self.assertNotIn(
                forbidden,
                body,
                "ServerProcessEpoch must stay independent from log budget state and persisted/wall-clock identity.",
            )

    def test_process_event_hook_event_sequence_is_not_sourced_from_logging_budget(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )

        event_log_arguments = extract_info_log_arguments_containing(
            body,
            PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_MESSAGE,
        )
        self.assertGreaterEqual(
            len(event_log_arguments),
            2,
            "PlayerPrincipalLifecycleObserver event logging should pass a runtime sequence argument.",
        )
        sequence_argument = event_log_arguments[1]

        forbidden_budget_sources = lifecycle_logging_budget_derived_variables(body)
        referenced_budget_sources = sorted(
            source
            for source in forbidden_budget_sources
            if expression_mentions_identifier(sequence_argument, source)
        )
        self.assertFalse(
            referenced_budget_sources,
            "ProcessEventHook.cpp must not use the logging observation counter as the source "
            "for internal player-principal runtime event sequence. The sequence argument "
            f"{sequence_argument!r} is derived from {referenced_budget_sources}; use a distinct "
            "runtime event sequence that is independent of s_PlayerPrincipalLifecycleObservations "
            "and gate.LogLimit.",
        )
        compact_sequence_argument = compact_cpp_expression(sequence_argument)
        self.assertNotIn(
            "s_PlayerPrincipalLifecycleObservations",
            compact_sequence_argument,
            "Player-principal runtime event sequence must be independent of "
            "s_PlayerPrincipalLifecycleObservations.",
        )
        self.assertNotIn(
            "gate.LogLimit",
            compact_sequence_argument,
            "Player-principal runtime event sequence must be independent of gate.LogLimit.",
        )

    def test_player_principal_lifecycle_observer_event_log_is_status_only_and_identity_safe(self) -> None:
        text = PROCESS_EVENT_HOOK.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        body = extract_function_body(
            uncommented,
            r"static\s+void\s+ObservePlayerPrincipalLifecycleAfterOriginal\s*\(",
        )

        event_log_arguments = extract_info_log_arguments_containing(
            body,
            PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_MESSAGE,
        )
        event_format = cpp_string_literal_text(event_log_arguments[0])
        self.assertEqual(
            format_keys(event_format),
            list(PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_KEYS),
            "PlayerPrincipalLifecycleObserver event logs must stay limited to the reviewed "
            "safe key set.",
        )
        self.assertIn(
            "apply_status={}",
            event_format,
            "PlayerPrincipalLifecycleObserver event logs must include a fixed-vocabulary "
            "apply_status field.",
        )
        self.assertIn(
            "correlation_status={}",
            event_format,
            "PlayerPrincipalLifecycleObserver event logs must include a fixed-vocabulary "
            "correlation_status field.",
        )
        self.assertIn(
            "principal_id_logged=false",
            event_format,
            "PlayerPrincipalLifecycleObserver event logs must explicitly state that no "
            "principal handle/id was logged.",
        )
        self.assertIn(
            "principal_generation_logged=false",
            event_format,
            "PlayerPrincipalLifecycleObserver event logs must explicitly state that no "
            "principal generation was logged.",
        )

        compact_arguments = tuple(
            compact_cpp_expression(argument)
            for argument in event_log_arguments[1:]
        )
        expected_arguments = tuple(
            compact_cpp_expression(argument)
            for argument in PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_EVENT_ARGUMENTS
        )
        self.assertEqual(
            compact_arguments,
            expected_arguments,
            "PlayerPrincipalLifecycleObserver event logs must format only copied lifecycle "
            "metadata plus safe apply/correlation status helpers.",
        )

        apply_status_body = extract_function_body(
            uncommented,
            r"static\s+const\s+char\*\s+LifecycleApplyStatusName\s*\(",
        )
        correlation_status_body = extract_function_body(
            uncommented,
            r"static\s+const\s+char\*\s+LifecycleCorrelationStatusName\s*\(",
        )
        self.assertEqual(
            returned_string_literals(apply_status_body),
            PLAYER_PRINCIPAL_LIFECYCLE_APPLY_STATUSES,
            "LifecycleApplyStatusName must return only reviewed safe status tokens.",
        )
        self.assertEqual(
            returned_string_literals(correlation_status_body),
            PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_STATUSES,
            "LifecycleCorrelationStatusName must return only reviewed safe correlation tokens.",
        )

        inspected_log_source = "\n".join(event_log_arguments)
        inspected_status_source = "\n".join((apply_status_body, correlation_status_body))
        for pattern, description in PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER_UNSAFE_LOG_PATTERNS:
            with self.subTest(forbidden=description):
                self.assertIsNone(
                    re.search(pattern, inspected_log_source, re.I),
                    f"PlayerPrincipalLifecycleObserver event log line must not format {description}.",
                )
                self.assertIsNone(
                    re.search(pattern, inspected_status_source, re.I),
                    f"PlayerPrincipalLifecycleObserver status helpers must not return or inspect "
                    f"{description}.",
                )

    def test_lifecycle_applicator_applies_process_local_context_before_registry_actions(self) -> None:
        text = PROCESS_EVENT_PLAYER_PRINCIPAL_LIFECYCLE_APPLICATOR.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)

        context_body = extract_function_body(uncommented, r"void\s+ApplyEventContext\s*\(")
        self.assertIn(
            "if (!context)",
            context_body,
            "ApplyEventContext must tolerate missing internal context for focused tests and fallback callers.",
        )
        self.assertIn(
            "event.EventSequence = context->EventSequence;",
            context_body,
            "ApplyEventContext must copy the process-local event sequence into the internal event view.",
        )
        self.assertIn(
            "event.ServerProcessEpoch = context->ServerProcessEpoch;",
            context_body,
            "ApplyEventContext must copy the process-local server epoch into the internal event view.",
        )

        body = extract_function_body(
            uncommented,
            r"ApplyResult\s+ApplyLifecycleObservationToRegistry\s*\(",
        )
        build_event_call_index = find_call_index(body, "TryBuildPlayerPrincipalEventView")
        apply_context_call_index = find_call_index(body, "ApplyEventContext", build_event_call_index)
        switch_index = body.find("switch (event.Kind)")
        self.assertNotEqual(
            switch_index,
            -1,
            "ApplyLifecycleObservationToRegistry must still route registry actions through event.Kind.",
        )
        self.assertLess(
            build_event_call_index,
            apply_context_call_index,
            "The applicator can only apply ProcessLocalEventContext after copied observation "
            "validation has produced an internal event view.",
        )
        self.assertLess(
            apply_context_call_index,
            switch_index,
            "The applicator must copy ProcessLocalEventContext into the event before registry actions.",
        )
        apply_context_arguments = split_top_level_arguments(
            extract_call_arguments_at(body, apply_context_call_index)
        )
        self.assertEqual(
            [compact_cpp_expression(argument) for argument in apply_context_arguments],
            ["eventContext", "event"],
            "ApplyLifecycleObservationToRegistry must pass its eventContext parameter to ApplyEventContext.",
        )

    def test_player_principal_hook_path_does_not_reference_public_header_tokens(self) -> None:
        public_header_token = re.compile(r"\bObeliskPlayerPrincipal[A-Za-z0-9_]*\b")

        for relative_path in PLAYER_PRINCIPAL_HOOK_PATH_FILES:
            with self.subTest(file=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                match = public_header_token.search(uncommented)
                found_token = match.group(0) if match else None
                self.assertIsNone(
                    match,
                    f"{relative_path} must keep the internal hook path separate from public "
                    f"ABI/SDK player-principal tokens; found {found_token!r}.",
                )

    def test_player_principal_registry_applicator_correlation_do_not_declare_public_exports(self) -> None:
        for relative_path in PLAYER_PRINCIPAL_INTERNAL_REGISTRY_APPLICATOR_CORRELATION_FILES:
            with self.subTest(file=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                for pattern, description in PLAYER_PRINCIPAL_PUBLIC_EXPORT_PATTERNS:
                    self.assertIsNone(
                        re.search(pattern, uncommented),
                        f"{relative_path} must remain an internal runtime implementation and "
                        f"must not declare {description}.",
                    )

    def test_player_principal_registry_applicator_correlation_do_not_retain_raw_ue_pointers(self) -> None:
        for relative_path in PLAYER_PRINCIPAL_INTERNAL_REGISTRY_APPLICATOR_CORRELATION_FILES:
            with self.subTest(file=relative_path):
                text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                uncommented = strip_c_comments(text)
                for pattern, description in PLAYER_PRINCIPAL_RAW_UE_POINTER_PATTERNS:
                    self.assertIsNone(
                        re.search(pattern, uncommented),
                        f"{relative_path} must keep only copied/process-local player-principal "
                        f"values and must not retain or expose {description}.",
                    )

    def test_obelisk_shared_library_keeps_hidden_visibility_for_player_principal_internals(self) -> None:
        text = CMAKE_LISTS.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        self.assertRegex(
            uncommented,
            r"set_target_properties\s*\(\s*obelisk\s+PROPERTIES\s+"
            r"CXX_VISIBILITY_PRESET\s+hidden\s*\)",
            "libobelisk must keep hidden C++ symbol visibility so internal "
            "player-principal runtime types do not become public ABI symbols.",
        )
        self.assertRegex(
            uncommented,
            r"set_target_properties\s*\(\s*obelisk\s+PROPERTIES\s+"
            r"VISIBILITY_INLINES_HIDDEN\s+1\s*\)",
            "libobelisk must keep inline visibility hidden for internal "
            "player-principal runtime helpers.",
        )

    def test_public_obelisk_api_does_not_expose_player_principal_abi_symbols(self) -> None:
        text = PUBLIC_OBELISK_API_HEADER.read_text(encoding="utf-8")
        uncommented = strip_c_comments(text)
        forbidden_public_tokens = (
            r"\bObeliskPlayerPrincipal[A-Za-z0-9_]*\b",
            r"\bPlayerPrincipal(?:Registry|Token|Lookup|Invalidation|Lifecycle)[A-Za-z0-9_]*\b",
            r"\bProcessEventPlayerPrincipalLifecycle[A-Za-z0-9_]*\b",
        )
        for pattern in forbidden_public_tokens:
            with self.subTest(pattern=pattern):
                match = re.search(pattern, uncommented)
                found_token = match.group(0) if match else None
                self.assertIsNone(
                    match,
                    "include/obelisk/ObeliskApi.h must not expose player-principal "
                    f"runtime/ABI symbols in the v1 SDK surface; found {found_token!r}.",
                )


if __name__ == "__main__":
    unittest.main()
