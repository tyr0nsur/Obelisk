#!/usr/bin/env python3
"""Guardrails that keep experimental gameplay modules out of the public SDK."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_GAMEPLAY_EVENTS_MANIFEST = REPO_ROOT / "docs" / "public_gameplay_events.json"
PUBLIC_API_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
PUBLIC_DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs" / "ARCHITECTURE.md",
    REPO_ROOT / "docs" / "INSTALL.md",
    REPO_ROOT / "docs" / "OPERATOR_CLI.md",
    REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
    REPO_ROOT / "docs" / "RELEASE.md",
    REPO_ROOT / "docs" / "STATUS.md",
    REPO_ROOT / "docs" / "VERSIONING.md",
    REPO_ROOT / "docs" / "oBaseEvents.md",
    REPO_ROOT / ".github" / "pull_request_template.md",
]
V010_CORE_API_CAPABILITY_ALLOWLIST = [
    "OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS",
    "OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS",
    "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
    "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES",
    "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
    "OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING",
    "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
    "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
    "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
]
V010_CORE_OBELISK_API_FIELD_ALLOWLIST = [
    "LogInfo",
    "LogWarn",
    "LogError",
    "RegisterPreProcessEvent",
    "RegisterPostProcessEvent",
    "RegisterPreProcessEventForNameIndex",
    "RegisterPostProcessEventForNameIndex",
    "CallProcessEvent",
    "abi_version",
    "struct_size",
    "capabilities",
    "RegisterPreProcessEventWithOwnerToken",
    "RegisterPostProcessEventWithOwnerToken",
    "RegisterPreProcessEventForNameIndexWithOwnerToken",
    "RegisterPostProcessEventForNameIndexWithOwnerToken",
    "RegisterPreProcessEventWithOwnerTokenHandle",
    "RegisterPostProcessEventWithOwnerTokenHandle",
    "RegisterPreProcessEventForNameIndexWithOwnerTokenHandle",
    "RegisterPostProcessEventForNameIndexWithOwnerTokenHandle",
    "UnregisterProcessEventCallbackWithOwnerToken",
    "RegisterGameplayPolicyEventWithOwnerTokenHandle",
    "UnregisterGameplayPolicyEventWithOwnerToken",
    "DescribeResourceKind",
    "DescribeGameplayPolicyEventKind",
]
UNPROMOTED_GAMEPLAY_SURFACES = (
    "Player",
    "Chat",
    "Tribe",
    "Buff",
    "Inventory",
    "Item",
    "Dino",
    "Structure",
    "Mission",
    "Transfer",
    "Permission",
    "Timer",
    "Admin",
    "Command",
)


def unpromoted_gameplay_tokens() -> list[str]:
    tokens: list[str] = []
    for singular in UNPROMOTED_GAMEPLAY_SURFACES:
        plural = f"{singular}s"
        for term in (singular, plural):
            tokens.extend(
                [
                    f"OBELISK_API_CAPABILITY_{term.upper()}_EVENTS",
                    f"Obelisk{term}",
                    f"RegisterOn{term}",
                    f"Unregister{term}",
                    f"On{term}",
                ]
            )
    return tokens


def public_api_capability_defines(header: str) -> list[str]:
    return re.findall(
        r"^\s*#define\s+(OBELISK_API_CAPABILITY_[A-Z0-9_]+)\b",
        header,
        re.MULTILINE,
    )


def obelisk_api_struct_body(header: str) -> str:
    match = re.search(
        r"typedef\s+struct\s+ObeliskApi\s*\{(?P<body>.*?)\}\s*ObeliskApi\s*;",
        header,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("typedef struct ObeliskApi block not found")
    return match.group("body")


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def obelisk_api_field_names(header: str) -> list[str]:
    body = strip_c_comments(obelisk_api_struct_body(header))
    fields: list[str] = []
    for declaration in body.split(";"):
        declaration = " ".join(declaration.split())
        if not declaration:
            continue
        function_pointer = re.search(r"\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", declaration)
        if function_pointer:
            fields.append(function_pointer.group(1))
            continue
        plain_field = re.search(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?$",
            declaration,
        )
        if plain_field:
            fields.append(plain_field.group(1))
    return fields


class PublicSdkGuardrailTests(unittest.TestCase):
    def test_public_sdk_core_api_surface_matches_v010_allowlist(self) -> None:
        header = PUBLIC_API_HEADER.read_text(encoding="utf-8")

        self.assertEqual(public_api_capability_defines(header), V010_CORE_API_CAPABILITY_ALLOWLIST)
        self.assertEqual(obelisk_api_field_names(header), V010_CORE_OBELISK_API_FIELD_ALLOWLIST)

    def test_cpp_public_sdk_examples_catch_exceptions_at_entry_points(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "tests/sdk_consumer/MinimalNoShutdownPlugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/consumer_plugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/no_shutdown_plugin.cpp",
        ]
        for path in files:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("catch (...)", text)

    def test_handle_callback_guidance_requires_owner_token_capability(self) -> None:
        files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs/oBaseEvents.md",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            if "OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES" in text:
                self.assertIn(
                    "OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS",
                    text,
                    f"{path.relative_to(REPO_ROOT)} documents handle callbacks without owner-token capability",
                )

    def test_public_sdk_guidance_keeps_multi_instance_runtime_state_process_local(self) -> None:
        docs = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md",
        ]
        required_terms = (
            "process-local",
            "owner tokens",
            "worker threads",
            "sockets",
            "caches",
            "mutable",
            "cross-process",
            "locking",
        )

        for path in docs:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                for term in required_terms:
                    self.assertIn(term, text)

    def test_plugin_architecture_defines_public_gameplay_event_promotion_gate(self) -> None:
        text = (REPO_ROOT / "docs/PLUGIN_ARCHITECTURE.md").read_text(encoding="utf-8")

        required_terms = (
            "Gameplay Event Promotion Gate",
            "accepted, distinct second-source",
            "promotion_gate.ready=true",
            "copied into Obelisk-owned POD storage",
            "no `UObject`",
            "`UFunction`",
            "`FString`",
            "raw parameter buffer",
            "append-only in `ObeliskApi`",
            "capability bit",
            "owner-token unregister path",
            "plugin-owner cleanup",
            "SDK consumer tests",
            "runtime-observer log summaries",
            "not a public gameplay event API",
        )

        for term in required_terms:
            self.assertIn(term, text)

    def test_release_docs_define_public_gameplay_event_sdk_gate(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        required_terms = (
            "docs/public_gameplay_events.json",
            "accepted distinct second-source evidence",
            "copied Obelisk-owned payload storage",
            "no\n`UObject`, `UFunction`, `FString`, raw parameter buffer",
            "append-only ABI fields",
            "capability bit",
            "owner-token handle\nregistration",
            "owner-scoped unregister",
            "plugin-owner cleanup",
            "ABI layout tests",
            "installed SDK consumer tests",
            "Runtime-observer summaries do not satisfy this SDK contract gate",
        )

        for term in required_terms:
            self.assertIn(term, text)

    def test_public_gameplay_event_manifest_has_no_undeclared_public_event_capabilities(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        header = (REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h").read_text(encoding="utf-8")

        self.assertEqual(manifest.get("schema"), "obelisk.public-gameplay-events.v1")
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)

        declared_capabilities = {
            event.get("capability") for event in promoted_events if isinstance(event, dict)
        }
        public_event_capabilities = {
            match.group(0)
            for match in re.finditer(r"OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS\b", header)
        }

        self.assertEqual(public_event_capabilities - declared_capabilities, set())

    def test_public_gameplay_event_capability_regex_matches_event_defines(self) -> None:
        header = "#define OBELISK_API_CAPABILITY_STRUCTURE_EVENTS (1ull << 42)\n"
        public_event_capabilities = {
            match.group(0)
            for match in re.finditer(r"OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS\b", header)
        }

        self.assertEqual(public_event_capabilities, {"OBELISK_API_CAPABILITY_STRUCTURE_EVENTS"})

    def test_promoted_public_gameplay_events_declare_required_evidence(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)

        required_boolean_flags = (
            "second_source_ready",
            "copied_obelisk_owned_payload",
            "no_ue_internals_in_public_abi",
            "append_only_abi",
            "capability_gated",
            "owner_token_handle_registration",
            "owner_scoped_unregister",
            "plugin_owner_cleanup",
        )
        required_path_lists = (
            "second_source_reports",
            "abi_tests",
            "sdk_consumer_tests",
            "lifecycle_tests",
            "docs",
        )

        for event in promoted_events:
            with self.subTest(event=event.get("event_id", "<missing>")):
                self.assertIsInstance(event.get("event_id"), str)
                self.assertIsInstance(event.get("capability"), str)
                self.assertRegex(event["capability"], r"^OBELISK_API_CAPABILITY_[A-Z0-9_]+_EVENTS$")
                target_sets = event.get("target_sets")
                self.assertIsInstance(target_sets, list, f"{event.get('event_id')} missing list target_sets")
                self.assertGreater(len(target_sets), 0, f"{event.get('event_id')} has no target_sets")
                for target_set in target_sets:
                    self.assertIsInstance(target_set, str)
                    self.assertNotEqual(target_set.strip(), "")
                    self.assertNotIn("/", target_set)
                backing_target_set = event.get("backing_target_set")
                self.assertIsInstance(backing_target_set, str)
                self.assertIn(backing_target_set, target_sets)
                for flag in required_boolean_flags:
                    self.assertIs(event.get(flag), True, f"{event.get('event_id')} missing {flag}=true")
                public_fields = event.get("public_fields")
                self.assertIsInstance(public_fields, list, f"{event.get('event_id')} missing public_fields")
                for public_field in (
                    "abi_version",
                    "struct_size",
                    "event_kind",
                    "resource_kind",
                    "flags",
                    "field_mask",
                    "bool_values",
                    "int32_values",
                ):
                    self.assertIn(public_field, public_fields)
                self.assertIn(
                    "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                    event.get("resource_kinds", []),
                )
                self.assertIn(
                    "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
                    event.get("event_kind_masks", []),
                )
                event_kinds = event.get("event_kinds")
                self.assertIsInstance(event_kinds, list, f"{event.get('event_id')} missing event_kinds")
                self.assertEqual(len(event_kinds), 8, f"{event.get('event_id')} event kind count drifted")
                for event_kind in event_kinds:
                    self.assertIsInstance(event_kind, dict)
                    self.assertRegex(
                        event_kind.get("kind", ""),
                        r"^OBELISK_GAMEPLAY_POLICY_EVENT_KIND_[A-Z0-9_]+$",
                    )
                    self.assertIsInstance(event_kind.get("stable_name"), str)
                    self.assertIn(event_kind.get("resource_kind"), event.get("resource_kinds", []))
                    self.assertRegex(
                        event_kind.get("event_kind_mask", ""),
                        r"^OBELISK_GAMEPLAY_POLICY_EVENT_MASK_[A-Z0-9_]+$",
                    )
                    self.assertIsInstance(event_kind.get("field_mask"), list)
                    self.assertGreater(len(event_kind["field_mask"]), 0)
                self.assertIn("not promoted", event.get("inventory_sdk", ""))
                for field in required_path_lists:
                    entries = event.get(field)
                    self.assertIsInstance(entries, list, f"{event.get('event_id')} missing list {field}")
                    self.assertGreater(len(entries), 0, f"{event.get('event_id')} has no {field}")
                    for entry in entries:
                        self.assertIsInstance(entry, str)
                        self.assertNotIn("/servidor/ark", entry)
                        self.assertTrue((REPO_ROOT / entry).exists(), f"missing evidence path {entry}")

    def test_public_gameplay_event_readiness_audit_documents_gameplay_policy_event_promotion(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-29-public-gameplay-event-readiness-audit.md"
        text = note.read_text(encoding="utf-8")

        required_terms = (
            "GameplayPolicyEvent",
            "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
            "structure-observer-intake",
            "minimal-second-source-intake",
            "promotion_gate.ready=true",
            "copied Obelisk-owned POD",
            "no UE internals in the ABI",
            "Inventory-backed policy signals are now promoted only through `GameplayPolicyEvent`",
            "pinCode",
            "FName/GObjects",
            "docs/public_gameplay_events.json",
            "`minimal-second-source-intake` is not a standalone public gameplay API",
            "No public Inventory SDK",
            "`InventoryPolicyEvent` ABI",
        )

        for term in required_terms:
            self.assertIn(term, text)

    def test_public_gameplay_event_manifest_allows_minimal_intake_only_for_gameplay_policy_inventory(self) -> None:
        manifest = json.loads(PUBLIC_GAMEPLAY_EVENTS_MANIFEST.read_text(encoding="utf-8"))
        promoted_events = manifest.get("promoted_events")
        self.assertIsInstance(promoted_events, list)

        for event in promoted_events:
            with self.subTest(event=event.get("event_id", "<missing>")):
                self.assertNotEqual(event.get("backing_target_set"), "minimal-second-source-intake")
                if "minimal-second-source-intake" in event.get("target_sets", []):
                    self.assertEqual(event.get("event_id"), "obelisk.gameplay_policy.v1")
                    self.assertEqual(event.get("inventory_backing_target_set"), "minimal-second-source-intake")
                    self.assertIn(
                        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
                        event.get("resource_kinds", []),
                    )
                    self.assertIn(
                        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
                        event.get("event_kind_masks", []),
                    )
                    self.assertIn("not promoted", event.get("inventory_sdk", ""))

    def test_obasevents_documents_binary_scoped_fname_resolution(self) -> None:
        text = (REPO_ROOT / "docs/oBaseEvents.md").read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())

        self.assertIn("validate_fname_index_manifest.py", text)
        self.assertIn("--ark-binary /path/to/offline/ShooterGameServer", text)
        self.assertIn("--ark-binary-sha256", text)
        self.assertIn("--resolve-name ServerChat", text)
        self.assertIn(
            "Candidate-only manifests are rejected for name resolution by default",
            normalized_text,
        )
        self.assertIn(
            "rejects `--ark-binary` paths under protected live-server roots",
            normalized_text,
        )
        self.assertIn("including symlinked live-server paths", normalized_text)
        self.assertIn("copy the binary to an offline artifact location first", normalized_text)
        self.assertIn("--allow-candidate", text)
        self.assertIn("generated_for_ark_binary_sha256", text)

    def test_public_docs_do_not_publish_local_server_paths_or_internal_coordination(self) -> None:
        forbidden = (
            "/servidor/ark",
            "agent handoff",
            "external-agent",
            "queue task",
            "goal tool",
            "CURRENT.md",
        )
        offenders: list[str] = []

        for path in PUBLIC_DOC_FILES:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            for token in forbidden:
                haystack = lowered if token == token.lower() else text
                if token in haystack:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_header_has_no_chat_api_until_promotion(self) -> None:
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        forbidden = [
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "ObeliskChatMessage",
            "ObeliskChatMessageSubscription",
            "ObeliskOnChatMessageCallback",
            "RegisterOnChatMessage",
            "OnChatMessage",
            "UnregisterChatMessage",
        ]

        offenders = [token for token in forbidden if token in header]
        self.assertEqual(offenders, [])

    def test_public_sdk_surface_has_no_structure_api_until_promotion(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
            REPO_ROOT / "plugins",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = (
            "OBELISK_API_CAPABILITY_STRUCTURE_EVENTS",
            "ObeliskStructureEvent",
            "ObeliskStructureEventSubscription",
            "ObeliskOnStructureEventCallback",
            "RegisterOnStructureEvent",
            "RegisterOnStructureEvents",
            "OnStructureEvent",
            "OnStructureEvents",
            "UnregisterStructureEvent",
            "UnregisterStructureEvents",
            "StructureEventView",
            "StructureScalarValue",
            "StructureEventCallback",
            "StructureEventSubscription",
            "StructureEventDispatcher",
            "StructureReflection",
            "ProcessEventStructureReflection",
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_sdk_surface_has_no_inventory_policy_api_until_promotion(self) -> None:
        scanned_roots = [
            REPO_ROOT / "include" / "obelisk",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
            REPO_ROOT / "plugins",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = (
            "OBELISK_API_CAPABILITY_INVENTORY_POLICY_EVENTS",
            "ObeliskInventoryPolicyEvent",
            "ObeliskInventoryPolicyEventSubscription",
            "ObeliskOnInventoryPolicyEventCallback",
            "RegisterInventoryPolicyEvent",
            "RegisterOnInventoryPolicyEvent",
            "OnInventoryPolicyEvent",
            "UnregisterInventoryPolicyEvent",
            "InventoryPolicyEventView",
            "InventoryPolicyScalarValue",
            "InventoryPolicyEventCallback",
            "InventoryPolicyEventSubscription",
            "InventoryPolicyEventDispatcher",
            "ProcessEventInventoryReflection",
        )
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_sdk_consumer_does_not_depend_on_experimental_chat(self) -> None:
        sdk_dir = REPO_ROOT / "tests/sdk_consumer"
        offenders: list[str] = []
        for path in sdk_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in ("RegisterOnChatMessage", "ObeliskChatMessage", "OBELISK_API_CAPABILITY_CHAT_EVENTS"):
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_examples_do_not_use_call_process_event_escape_hatch(self) -> None:
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
        ]
        allowed_fixture_files = {
            REPO_ROOT / "tests" / "sdk_consumer" / "SdkConsumerFixture.cpp",
        }
        forbidden = (
            "OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT",
            ".CallProcessEvent",
            "->CallProcessEvent",
        )
        offenders: list[str] = []
        for root in scanned_roots:
            for path in root.rglob("*"):
                if path in allowed_fixture_files:
                    continue
                if not path.is_file() or path.suffix not in {".cpp", ".h", ".hpp", ".c"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_unpromoted_gameplay_token_list_covers_documented_examples(self) -> None:
        tokens = set(unpromoted_gameplay_tokens())

        for token in (
            "ObeliskCommand",
            "RegisterOnTimer",
            "OBELISK_API_CAPABILITY_PERMISSION_EVENTS",
            "ObeliskPlayers",
            "OBELISK_API_CAPABILITY_BUFF_EVENTS",
            "ObeliskBuff",
            "RegisterOnBuff",
            "UnregisterCommands",
        ):
            self.assertIn(token, tokens)

    def test_public_sdk_headers_have_no_gameplay_module_api_until_promotion(self) -> None:
        offenders: list[str] = []
        forbidden = unpromoted_gameplay_tokens()
        for path in (REPO_ROOT / "include" / "obelisk").rglob("*"):
            if not path.is_file() or path.suffix not in {".h", ".hpp"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_public_docs_and_examples_do_not_advertise_unpromoted_gameplay_api(self) -> None:
        scanned_roots = [
            REPO_ROOT / "plugins",
            REPO_ROOT / "tests" / "sdk_consumer",
            REPO_ROOT / "tests" / "sdk_installed_consumer",
        ]
        scanned_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "docs" / "PLUGIN_ARCHITECTURE.md",
            REPO_ROOT / "docs" / "oBaseEvents.md",
        ]
        forbidden = unpromoted_gameplay_tokens()
        offenders: list[str] = []

        for root in scanned_roots:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix in {".c", ".cpp", ".h", ".hpp", ".md", ".txt"}:
                    scanned_files.append(path)

        for path in scanned_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {token}")

        self.assertEqual(offenders, [])

    def test_chat_abi_preflight_documents_future_shapes(self) -> None:
        note = (REPO_ROOT / "docs/research/2026-05-27-chat-sdk-abi-preflight.md").read_text(
            encoding="utf-8"
        )

        for token in (
            "ObeliskStringView",
            "ObeliskChatMessage",
            "ObeliskChatMessageSubscription",
            "OBELISK_API_CAPABILITY_CHAT_EVENTS",
            "RegisterOnChatMessage",
            "Evidence-pack mode",
        ):
            self.assertIn(token, note)


if __name__ == "__main__":
    unittest.main()
