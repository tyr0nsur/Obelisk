#!/usr/bin/env python3
"""Guardrails that keep the first stable release scope coherent."""

from __future__ import annotations

import json
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFLECTION_TARGET_SET_VARS = runpy.run_path(str(REPO_ROOT / "scripts" / "reflection_target_sets.py"))
TARGET_SETS = REFLECTION_TARGET_SET_VARS["TARGET_SETS"]
PLANNING_ONLY_TARGET_SETS = REFLECTION_TARGET_SET_VARS["PLANNING_ONLY_TARGET_SETS"]
RELEASE_READINESS_TARGET_SETS = REFLECTION_TARGET_SET_VARS["RELEASE_READINESS_TARGET_SETS"]
PUBLIC_RC_UFUNCTION_TARGET_SETS = [
    "minimal-second-source-intake",
    "structure-observer-intake",
    "item-return-only-policy-slice",
    "chat-message-intake",
]


def read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.split())


def normalized_contains(text: str, expected: str) -> bool:
    return normalized(expected) in normalized(text)


def sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?|\n])\s+", text) if part.strip()]


def paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def cmake_targets(cmake: str) -> list[tuple[str, str, str]]:
    return [
        (match.group("kind"), match.group("name"), match.group("body"))
        for match in re.finditer(
            r"add_(?P<kind>library|executable)\((?P<name>[A-Za-z0-9_]+)(?P<body>.*?)\n\)",
            cmake,
            re.S,
        )
    ]


def shell_array_values(script: str, name: str) -> list[str]:
    match = re.search(rf"{re.escape(name)}=\(\n(?P<body>.*?)\n\)", script, re.S)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group("body"))


def target_set_args(text: str) -> list[str]:
    return re.findall(r"--target-set\s+([A-Za-z0-9_-]+)", text)


def ufunction_target_set_args(text: str) -> list[str]:
    return re.findall(r"--ufunction-second-source-target-set\s+([A-Za-z0-9_-]+)", text)


class ReleaseScopeGuardrailTests(unittest.TestCase):
    def assertNormalizedIn(self, expected: str, text: str, msg: str | None = None) -> None:
        self.assertTrue(normalized_contains(text, expected), msg or expected)

    def assertRcPublicScopeClaim(self, path: str, text: str) -> None:
        compact = normalized(text)
        match = re.search(
            r"RC public scope remains limited to (?P<claim>[^.]*DescribeGameplayPolicyEventKind)",
            compact,
        )
        self.assertIsNotNone(match, f"{path}: missing limited RC public scope claim")
        claim = match.group("claim") if match else ""

        allowed_surfaces = [
            "GameplayPolicyEvent",
            "minimal copied `ChatMessageEvent`",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
        ]
        forbidden_scope_additions = re.compile(
            r"\b(?:Inventory|StructureEvents|Mission|Transfer|Dino|Buff|Tribe|Player|"
            r"Admin|Command|Permission|gameplay/module timer)\b",
            re.IGNORECASE,
        )
        with self.subTest(file=path, claim="RC public scope"):
            for surface in allowed_surfaces:
                self.assertIn(surface, claim)
            self.assertIsNone(forbidden_scope_additions.search(claim), claim)

    def assertCurrentTurnReleaseAuthorization(self, path: str, text: str) -> None:
        compact = normalized(text)
        self.assertRegex(
            compact,
            re.compile(
                r"\bNo\b[^.]*\btag or release-ref push\b[^.]*\b(?:release-manager|lead)\b"
                r"[^.]*\bauthorization\b[^.]*\bcurrent[- ]turn\b",
                re.IGNORECASE,
            ),
            f"{path}: tag/release-ref authorization must be explicit and current-turn scoped",
        )

    def test_first_stable_included_scope_is_documented_as_baseline(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        changelog = read("CHANGELOG.md")

        required_release_items = [
            "Runtime bootstrap",
            "ProcessEvent hook",
            "C plugin ABI, after an explicit first-stable ABI freeze decision",
            "Central install script and LinuxGSM wrappers",
            "`oBaseEvents`",
            "`OBELISK_INSTANCE_ID` logs and state markers",
            "Filtered raw `ProcessEvent` callback infrastructure as debug-gated runtime plumbing",
            "Stable plugin paths should use copied Obelisk-owned events",
            "Target-specific gameplay/module\n  surfaces remain experimental",
            "Dispatcher callback cleanup that is safe across the current callback families",
            "unregister/owner cleanup initiated from gameplay callbacks avoids dispatcher cleanup\n  waits",
            "non-callback owner/plugin cleanup\n  still waits for in-flight dispatch and deferred `DestroyUserData` cleanup",
        ]
        required_status_items = [
            "`LD_PRELOAD` bootstrap | Stable baseline",
            "ProcessEvent hook | Stable baseline",
            "Plugin C ABI loading | Stable baseline",
            "Central install root | Stable baseline",
            "ARK/LinuxGSM validation adapter | Stable baseline",
            "`oBaseEvents` | Release example",
            "`oPolicyAudit` | Experimental",
            "Per-instance runtime flags | Stable baseline",
            "Plugin callback ownership | Stable baseline",
            "Unregister/owner cleanup initiated from gameplay callbacks avoids dispatcher cleanup waits",
            "non-callback owner/plugin cleanup still waits for in-flight dispatch and deferred `DestroyUserData` cleanup",
        ]
        required_changelog_items = [
            "Linux `LD_PRELOAD` runtime bootstrap",
            "Absolute x86_64 `UObject::ProcessEvent` hook",
            "C plugin ABI",
            "Public plugin C ABI v1 is the intended first-stable compatibility contract",
            "Central install layout",
            "LinuxGSM wrapper templates",
            "`oBaseEvents` as the first official plugin example",
            "Runtime default-deny gates for filtered/global ProcessEvent callbacks",
            "Fail-closed ProcessEvent hook removal",
            "safe `instance_allowlist` validation",
            "Multi-instance shared-root posture",
            "shared target-set snapshot comparison/regeneration",
        ]

        for item in required_release_items:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)
        for item in required_status_items:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)
        for item in required_changelog_items:
            with self.subTest(file="CHANGELOG.md", item=item):
                self.assertIn(item, changelog)

    def test_first_stable_exclusions_stay_excluded(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        changelog = read("CHANGELOG.md")

        for item in [
            "Stable gameplay module interception APIs",
            "Full UE4 reflection",
            "Higher-level gameplay SDK APIs outside `GameplayPolicyEvent` and the minimal",
            "Gameplay mutation, return overrides, arbitrary UE4 function calls, and public",
            "`CallProcessEvent`-based plugin behavior",
            "Experimental first-party plugins such as `oPolicyAudit`",
            "`OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`",
            "Plugins with background workers, sockets, HTTP listeners/clients, long-lived file\n  readers",
            "background-work\n  promotion gate",
            "Production HTTP plugins",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)

        for item in [
            "GNames/FNamePool resolution | Not ready",
            "GObjects/GUObjectArray enumeration | Not ready",
            "General reflected UFunction parameter decoding | Not ready",
            "Higher-level SDK APIs | Not ready",
            "Internal copied inventory policy events | Internal bridge",
            "`oPolicyAudit` | Experimental",
            "Operator CLI | Experimental",
            "ReflectionScanner | Experimental",
        ]:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)

        for item in [
            "GNames/GObjects-backed reflection layer",
            "gameplay/module timer SDKs, including richer chat APIs and command APIs beyond",
            "Mutable operator lifecycle commands",
            "Production-ready HTTP plugins",
        ]:
            with self.subTest(file="CHANGELOG.md", item=item):
                self.assertIn(item, changelog)

    def test_game_interaction_boundary_stays_non_mutating(self) -> None:
        readme = read("README.md")
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")

        for item in [
            "Filtered raw `ProcessEvent` callback infrastructure as debug-gated runtime plumbing",
            "Stable plugin paths should use copied Obelisk-owned events",
            "Target-specific gameplay/module\n  surfaces remain experimental",
            "Gameplay mutation, return overrides, arbitrary UE4 function calls, and public",
            "`CallProcessEvent`-based plugin behavior",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)

        for item in [
            "Current safe interaction shape",
            "observe selected UE4 `ProcessEvent` calls through debug-gated filtered callbacks",
            "keep callbacks filtered, non-blocking, and instance-gated",
            "record metadata or plugin-local state only",
            "Blocked from stable plugin APIs until promoted with evidence",
            "mutating UE4 parameter buffers or return values",
            "calling arbitrary UE4 functions or replaying events through `CallProcessEvent`",
            "exposing borrowed `UObject`, `FString`, `UFunction`, or raw parameter memory",
        ]:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)

        for item in [
            "`CallProcessEvent` is a low-level trampoline escape hatch",
            "Stable plugin APIs should prefer higher-level Obelisk module surfaces as they are promoted",
        ]:
            with self.subTest(file="README.md", item=item):
                self.assertIn(item, readme)

    def test_resource_programming_scope_stays_category_only_in_release_docs(self) -> None:
        release = read("docs/RELEASE.md")
        compact_release = normalized(release)

        for item in [
            "`DescribeResourceKind` as metadata-only resource category descriptors",
            "not `ResourceHandle`, resource lookup, object identity, or cross-event correlation",
            "`GameplayPolicyEvent` as the promoted v0.1 gameplay policy callback family",
            "copied POD scalar payloads and no identity, no lookup, no mutation, and no return override authority",
            "it does not by itself promote a public Inventory SDK",
            "It also does not prove resource cross-event correlation",
            "must not unlock `ResourceHandle`, object lookup, GObjects promotion",
            "ResourceHandle semantic work must remain blocked",
            "In v0.1, `resource_kind` is a category only, not a game object identity",
            "must not be treated as \"this same structure/item\", a lookup handle, a persistent ID",
            "Do not add `GetResource`, `ResolveResource`, `ResourceHandle`, pointer-derived IDs",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(normalized(item), compact_release)

    def test_chat_message_event_release_docs_keep_rc_boundary_explicit(self) -> None:
        readme = read("README.md")
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")

        required_release_items = [
            "`ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI",
            "copied UTF-8 message\n  text, send mode, copied-payload flag, and process-local sequence only",
            "not a command SDK,\n  chat send/moderation API, sender identity API, UE lookup path, mutation surface, or\n  return-override authority",
            "accepted `chat-message-intake` second-source comparison",
            "The runtime producer\nexists behind the `enable-chat-events` marker/env path",
            "accepted copied-log validation\n  with 18 accepted delivery events covering send modes `0,1,2,3` through the",
            "further beta\nobservation is regression/revalidation only unless a new promotion gate is defined",
            "Do not count `enable-chat-reflection` observer evidence for\nthat claim",
        ]
        required_status_items = [
            "ChatMessageEvent | v0.1-rc SDK ABI surface",
            "Minimal copied UTF-8 chat notification contract for plugins that parse text locally",
            "sender/player identity, resource identity, raw `FString`, raw params, FName/GObjects indices, UE pointers, chat send/moderation/blocking, command routing, mutation, and return overrides remain blocked",
            "The target layout has accepted second-source evidence",
            "the `enable-chat-events` producer path has approved copied-log plugin-facing delivery validation with 18 accepted events covering all four known send modes (`0..3`) and no privacy blockers",
            "Historical `enable-chat-reflection` observer logs still do not satisfy delivery evidence",
        ]
        forbidden_claims = [
            "ChatMessageEvent | Promoted v0.1 SDK surface",
            "ChatMessageEvent | Stable baseline",
            "ChatMessageEvent` as a promoted v0.1 chat plugin event ABI",
            "ChatMessageEvent` as a stable chat plugin event ABI",
            "promotes a command SDK",
            "promotes sender/player identity",
            "promotes chat send/moderation",
            "live debug delivery validated",
            "end-to-end public milestone claim",
        ]

        for item in required_release_items:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)
        for item in required_status_items:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)
        for item in [
            "v0.1-rc public C ABI slices:",
            "Minimal v0.1-rc `ChatMessageEvent` callback ABI",
            "This remains a copied notification contract only",
        ]:
            with self.subTest(file="README.md", item=item):
                self.assertIn(item, readme)
        self.assertLess(
            readme.index("v0.1-rc public C ABI slices:"),
            readme.index("Minimal v0.1-rc `ChatMessageEvent` callback ABI"),
        )
        for item in forbidden_claims:
            for path, text in (("docs/RELEASE.md", release), ("docs/STATUS.md", status), ("README.md", readme)):
                with self.subTest(file=path, item=item):
                    self.assertNotIn(item, text)

    def test_chat_message_event_docs_do_not_make_generic_stable_or_promoted_claims(self) -> None:
        claim_words = re.compile(
            r"\b(?:stable(?:\s+baseline|\s+api|\s+sdk|\s+surface)?|promoted(?:\s+v0\.1\s+sdk\s+surface)?|"
            r"production-ready)\b",
            re.IGNORECASE,
        )
        allowed_context = re.compile(
            r"\b(?:minimal|v0\.1-rc|rc\b|not|no|outside|beyond|blocked|excluded|separate|separately|"
            r"GameplayPolicyEvent|DescribeResourceKind|DescribeGameplayPolicyEventKind)\b",
            re.IGNORECASE,
        )
        offenders: list[str] = []

        for path in [
            "README.md",
            "CHANGELOG.md",
            "docs/RELEASE.md",
            "docs/STATUS.md",
            "docs/public_gameplay_events.json",
            ".github/pull_request_template.md",
        ]:
            for sentence in sentences(read(path)):
                if "ChatMessageEvent" not in sentence or not claim_words.search(sentence):
                    continue
                if allowed_context.search(sentence):
                    continue
                offenders.append(f"{path}: {normalized(sentence)}")

        self.assertEqual(offenders, [])

    def test_chat_milestone_does_not_weaken_inventory_resource_or_ue_blocks(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        changelog = read("CHANGELOG.md")
        pr_template = read(".github/pull_request_template.md")

        for path, text in (
            ("docs/RELEASE.md", release),
            ("docs/STATUS.md", status),
            ("CHANGELOG.md", changelog),
        ):
            with self.subTest(file=path, item="ResourceHandle"):
                self.assertIn("ResourceHandle", text)
            with self.subTest(file=path, item="Inventory SDK"):
                self.assertIn("Inventory SDK", text)
            with self.subTest(file=path, item="mutation"):
                self.assertIn("mutation", text)
            with self.subTest(file=path, item="return override"):
                self.assertIn("return", text)
                self.assertIn("override", text)

        for item in [
            "public Inventory SDK",
            "It is not a `ResourceHandle`, object identity, lookup API, persistent handle",
            "resource identity, raw `FString`, raw params, FName/GObjects indices, UE pointers",
            "Inventory-backed signals use the same `GameplayPolicyEvent` family, not a separate Inventory SDK",
            "Outside the promoted `GameplayPolicyEvent` surface and the minimal `ChatMessageEvent` RC notification surface",
        ]:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)

        for item in [
            "public Inventory SDK",
            "`ResourceHandle`, object identity, GObjects lookup, mutation, or return overrides",
            "raw `FString`, `UObject`, `UFunction`, FName/GObjects\nindices, raw params, mutation, or return overrides",
            "ResourceHandle`, GNames/GObjects promotion, public Inventory SDK",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)

        for item in [
            "does not promote public\n  Inventory/Structure SDKs, `ResourceHandle`, GObjects lookup, mutation, or return\n  overrides",
            "raw `FString`, raw params, UE pointers, mutation, or return-override surface",
            "`ResourceHandle`, public `StructureEvents`, public Inventory SDK",
            "GNames/GObjects-backed reflection layer",
        ]:
            with self.subTest(file="CHANGELOG.md", item=item):
                self.assertIn(item, changelog)

        for item in [
            "does not expose public Inventory SDKs, `ResourceHandle`, resource/object identity",
            "UE pointers, raw `FString`, raw params, FName/GObjects indices",
            "without a separately named promotion gate",
        ]:
            with self.subTest(file=".github/pull_request_template.md", item=item):
                self.assertIn(item, pr_template)

    def test_rc_checkpoint_slicing_plan_matches_current_public_scope(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")

        for item in [
            "GameplayPolicyEvent",
            "ChatMessageEvent",
            "DescribeResourceKind",
            "DescribeGameplayPolicyEventKind",
            "minimal copied `ChatMessageEvent`",
            "metadata-only `DescribeGameplayPolicyEventKind`",
            "richer chat APIs beyond the minimal copied `ChatMessageEvent`",
            "no module SDK, UE lookup, mutation, identity, or return override",
        ]:
            with self.subTest(item=item):
                self.assertIn(item, plan)

        for stale in [
            "only `GameplayPolicyEvent` and\n`DescribeResourceKind`",
            "only `GameplayPolicyEvent` and `DescribeResourceKind`",
            "public mission, tribe, buff, dino, transfer, chat, player",
        ]:
            with self.subTest(stale=stale):
                self.assertNotIn(stale, plan)

    def test_dispatcher_cleanup_rule_stays_callback_safe_without_overclaiming(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        hardening = read("docs/research/2026-05-29-dispatcher-hook-safety-hardening.md")
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")

        for path, text in (
            ("docs/RELEASE.md", release),
            ("docs/STATUS.md", status),
            ("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md", plan),
        ):
            lower_text = text.lower()
            with self.subTest(file=path, item="callback-initiated cleanup avoids waits"):
                self.assertIn("unregister/owner cleanup", lower_text)
                self.assertIn("gameplay callbacks avoids dispatcher cleanup", lower_text)
                self.assertIn("callback-to-callback deadlocks", lower_text)
            with self.subTest(file=path, item="non-callback cleanup waits"):
                self.assertIn("non-callback owner/plugin cleanup", lower_text)
                self.assertIn("in-flight dispatch", lower_text)
                self.assertIn("deferred `destroyuserdata` cleanup", lower_text)

        self.assertIn("cross-family callback cleanup suppression was restored", hardening)
        self.assertIn("unregister/owner cleanup initiated from any gameplay callback family must not wait", hardening)
        self.assertIn("non-callback owner/plugin cleanup still waits", hardening)
        self.assertIn("does not promote Inventory, StructureEvents, Mission, Dino, Tribe, Transfer", hardening)

    def test_plugin_cleanup_failure_retry_policy_stays_documented(self) -> None:
        status = read("docs/STATUS.md")
        current = read("docs/agent-handoff/CURRENT.md")
        compact = read("docs/agent-handoff/COMPACT_CONTEXT.md")
        architecture = read("docs/PLUGIN_ARCHITECTURE.md")

        required = [
            "skips `dlclose`",
            "retains the plugin",
            "retry",
            "does not repeat plugin shutdown",
        ]
        for path, text in (
            ("docs/STATUS.md", status),
            ("docs/agent-handoff/CURRENT.md", current),
            ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
        ):
            for item in required:
                with self.subTest(file=path, item=item):
                    self.assertIn(item, text)

        for item in [
            "must keep the plugin\nlibrary mapped and retry cleanup later",
            "must not call shutdown a\nsecond time on that retry",
        ]:
            with self.subTest(file="docs/PLUGIN_ARCHITECTURE.md", item=item):
                self.assertIn(item, architecture)

        for stale in [
            "Runtime lifecycle debt remains open",
            "should prevent `dlclose`",
            "a later\n  no-ABI-change patch",
        ]:
            for path, text in (
                ("docs/agent-handoff/CURRENT.md", current),
                ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
            ):
                with self.subTest(file=path, stale=stale):
                    self.assertNotIn(stale, text)

    def test_release_readiness_is_the_documented_release_gate(self) -> None:
        readme = read("README.md")
        release = read("docs/RELEASE.md")
        pr_template = read(".github/pull_request_template.md")
        ci = read(".github/workflows/ci.yml")
        script = read("scripts/check_release_readiness.sh")
        status = read("docs/STATUS.md")
        changelog = read("CHANGELOG.md")
        build_skill = read("agent-skills/obelisk-build-system/SKILL.md")
        workflow_skill = read("agent-skills/obelisk-github-research-workflow/SKILL.md")

        self.assertIn("scripts/check_release_readiness.sh", readme)
        self.assertIn("canonical release gate", readme)
        self.assertIn("Quick contributor loop", readme)
        self.assertIn("scripts/check_release_readiness.sh", release)
        self.assertIn("--ufunction-second-source-root <second-source-ufunction-snapshots>", release)
        self.assertIn("refreshed root recorded in", release)
        self.assertNormalizedIn("do not reuse it as the final root for any later candidate", release)
        self.assertIn("including current bool-tail metadata", release)
        self.assertIn("--second-source-report-dir /tmp/obelisk-rc-second-source", release)
        self.assertIn("`oPolicyAudit`", release)
        self.assertIn("Verify the ABI v1 freeze artifacts before tagging", release)
        self.assertNormalizedIn("Obelisk freezes the current append-only `ObeliskApi` ABI v1", release)
        self.assertIn("Any ABI v2 must use an explicit migration plan", release)
        self.assertNormalizedIn("installed SDK consumer validation, and the `oBaseEvents` release example", release)
        self.assertIn("Owner-token public registrations must keep using the plugin owner's init-time", release)
        self.assertIn("first-stable plugin scope excludes background-work plugins", release)
        self.assertIn("idempotent shutdown through `ObeliskPlugin_Shutdown`", release)
        self.assertIn("owner-token callback handles unregistered before unload", release)
        self.assertNormalizedIn("threads joined, sockets/files closed", release)
        self.assertIn("scripts/check_release_readiness.sh", pr_template)
        self.assertIn("scripts/check_release_readiness.sh", ci)
        self.assertIn("scripts/check_release_readiness.sh", build_skill)
        self.assertIn("scripts/check_release_readiness.sh", workflow_skill)
        self.assertIn("canonical local and CI gate", build_skill)
        self.assertIn("single release-readiness entry point", workflow_skill)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", pr_template)
        self.assertIn("observational only", pr_template)
        self.assertIn("not release readiness or second-source promotion evidence", pr_template)
        self.assertIn("If this PR claims runtime `ChatMessageEvent` delivery", pr_template)
        self.assertIn("enable-chat-events", pr_template)
        self.assertIn("approved operator-selected beta-test window", pr_template)
        self.assertIn("operator-approved notice", pr_template)
        self.assertIn("enable-chat-reflection", pr_template)
        self.assertIn("historical `enable-chat-reflection` observer logs", pr_template)
        self.assertIn("not counted as delivery evidence", pr_template)
        self.assertIn("Core-first release readiness", ci)
        self.assertIn("first-stable core release gate", ci)
        self.assertIn("production libobelisk.so test-only symbol checks", ci)
        self.assertNotIn("scripts/install_obelisk.sh --dry-run /tmp/obelisk-ci-install", ci)
        self.assertNotIn("scripts/test_install_obelisk_layout.sh /tmp/obelisk-ci-layout", ci)
        self.assertIn("Reflection base readiness", ci)
        self.assertIn("--fail-on-base-readiness-gaps", ci)
        for target_set in PUBLIC_RC_UFUNCTION_TARGET_SETS:
            self.assertIn(f"--target-set {target_set}", ci)
        self.assertEqual(re.findall(r"--target-set ([A-Za-z0-9_-]+)", ci), PUBLIC_RC_UFUNCTION_TARGET_SETS)
        self.assertIn("Check committed public RC UFunction target sets", ci)
        self.assertNotIn("tests/fixtures/scriptstruct_snapshots", ci)
        self.assertNotIn("Check committed ScriptStruct promotion target sets", ci)
        self.assertIn("all 12 public\n  RC snapshots across the four public target sets", changelog)
        self.assertNotIn("all nine public\n  RC targets", changelog)
        self.assertRegex(
            ci,
            re.compile(
                r"run:\s*\|\s*\n(?:\s+.*\n)*?\s+python3 scripts/compare_reflection_snapshots\.py"
                r"(?:\s+.*\n)*?\s+--fail-on-base-readiness-gaps",
                re.M,
            ),
        )
        self.assertIn("--require-second-source-readiness", ci)
        self.assertIn("Release readiness requires a clean worktree", script)
        self.assertIn("first-stable core release gate", script)
        self.assertIn("production libobelisk.so symbol surface checks", script)
        self.assertIn("check_production_runtime_symbols", script)
        self.assertIn("Production libobelisk.so exposes test-only/internal symbols", script)
        self.assertIn("gameplay/module second-source promotion gate was not run", script)
        self.assertIn("pre-build readiness metadata preflight", script)
        self.assertIn("current BoolProperty tail metadata", script)
        self.assertIn("test-only/internal symbol patterns", release)
        self.assertIn("Production `libobelisk.so` remains free of test-only/internal symbols", pr_template)
        self.assertIn("canonical release gate rejecting production `libobelisk.so`", status)
        self.assertNormalizedIn("fail before the build/test/install steps", release)
        self.assertIn("preflights the configured UFunction root before build/test/install work", status)
        self.assertIn("unambiguous public RC target coverage", changelog)
        self.assertIn("scripts/install_obelisk_plugin.sh --dry-run", script)
        self.assertIn("${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so", script)
        self.assertIn("${BUILD_DIR}/plugins/oProcessTimer/oProcessTimer.so", script)
        self.assertIn("${BUILD_DIR}/plugins/oDescriptorCatalog/oDescriptorCatalog.so", script)
        self.assertNotIn("oPolicyAudit.so", script)
        rc_smoke = read("scripts/check_rc_layout_evidence_smoke.sh")
        release_second_source_command = re.search(
            r"scripts/check_release_readiness\.sh \\\n(?P<body>.*?--second-source-report-dir /tmp/obelisk-rc-second-source)",
            release,
            re.S,
        )
        self.assertIsNotNone(release_second_source_command)
        if release_second_source_command is not None:
            self.assertEqual(
                ufunction_target_set_args(release_second_source_command.group("body")),
                PUBLIC_RC_UFUNCTION_TARGET_SETS,
            )
        self.assertEqual(
            shell_array_values(script, "PUBLIC_RC_UFUNCTION_SECOND_SOURCE_TARGET_SETS"),
            PUBLIC_RC_UFUNCTION_TARGET_SETS,
        )
        self.assertEqual(target_set_args(rc_smoke), PUBLIC_RC_UFUNCTION_TARGET_SETS)
        self.assertIn("freshly assembled for the intended HEAD", rc_smoke)
        self.assertNormalizedIn("including current bool-tail metadata", rc_smoke)
        self.assertIn("do not reuse a historical published-RC root", rc_smoke)
        self.assertIn("v0.1.0-rc.2", rc_smoke)
        self.assertIn("--require-second-source-readiness", release)
        self.assertNormalizedIn("an existing local or unpublished RC tag is not proof", release)
        self.assertIn("may point behind the current validated head", normalized(release))
        self.assertIn("tag was checked against the intended release ref", normalized(status))
        self.assertIn("exact tag/ref verification", normalized(status))
        self.assertIn("--require-second-source-readiness", pr_template)
        self.assertIn("--require-second-source-readiness", script)
        self.assertIn("--ufunction-second-source-root", release)
        self.assertIn("--ufunction-second-source-root", pr_template)
        self.assertIn("--ufunction-second-source-root", script)
        self.assertIn("--scriptstruct-second-source-root", release)
        self.assertIn("--scriptstruct-second-source-root", pr_template)
        self.assertIn("--scriptstruct-second-source-root", script)
        self.assertIn("--ufunction-second-source-target-set", release)
        self.assertIn("--ufunction-second-source-target-set", pr_template)
        self.assertIn("--ufunction-second-source-target-set", script)
        self.assertIn("--scriptstruct-second-source-target-set", release)
        self.assertIn("--scriptstruct-second-source-target-set", pr_template)
        self.assertIn("--scriptstruct-second-source-target-set", script)
        self.assertIn("default second-source gate is intentionally scoped to the public RC UFunction target", release)
        self.assertIn("`minimal-second-source-intake`", release)
        self.assertIn("`structure-observer-intake`", release)
        self.assertIn("`item-return-only-policy-slice`", release)
        self.assertIn("`chat-message-intake`", release)
        self.assertIn("accepted default intake is layout-only evidence", release)
        self.assertIn("promotion_gate.ready_scope=layout_only", release)
        self.assertIn("promotion_gate.promotion_ready=false", release)
        self.assertIn("does not by itself promote a public Inventory SDK", release)
        self.assertNormalizedIn(
            "redacted signature manifests accepted in offline-artifact consume mode remain candidate-only",
            release,
        )
        self.assertIn("transfer-ufunction-intake", release)
        self.assertIn("transfer-scriptstruct", release)
        self.assertIn("is layout-only offline evidence", release)
        self.assertNormalizedIn("does not promote a public Transfer SDK", release)
        self.assertIn("UObject flag transition matrices and static flag-policy reports", release)
        self.assertNormalizedIn("pass the offline artifact gate in consume mode are candidate evidence only", release)
        self.assertNormalizedIn("does not prove lifecycle/validity semantics", release)
        self.assertIn("does not satisfy promote-mode artifact gates", release)
        self.assertIn("must not unlock `ResourceHandle`, object lookup, GObjects promotion", release)
        self.assertIn("does not prove resource cross-event correlation", release)
        self.assertIn("ResourceHandle semantic work must remain blocked", release)
        self.assertIn("helper predicate", release)
        self.assertIn("caller mode", release)
        self.assertIn("mutation windows", release)
        self.assertIn("Strict serial reuse/wraparound policy artifacts", release)
        self.assertNormalizedIn("internal candidate-only contracts", release)
        self.assertNormalizedIn("does not prove runtime reuse semantics", release)
        self.assertNormalizedIn("public lookup safety, persistent handles, identity, mutation", release)
        self.assertIn("refreshed default `minimal-second-source-intake` evidence remains layout-only", status)
        self.assertIn("promotion_ready=false", status)
        self.assertIn("accepted transfer evidence for `transfer-ufunction-intake` and `transfer-scriptstruct`", status)
        self.assertIn("does not promote a public Transfer SDK", status)
        self.assertIn("UObject flag validity policy | Not ready", status)
        self.assertIn("Static flag-policy reports, transition matrices, and strict serial-policy artifacts", status)
        self.assertIn("do not prove lifecycle/validity or serial reuse semantics", status)
        self.assertIn("do not unlock `ResourceHandle`, object lookup, GObjects promotion", status)
        self.assertIn("capability-snapshot tests for owner-token public registrations", status)
        self.assertIn("Current ResourceHandle semantic work remains blocked", status)
        self.assertIn("strict serial reuse/wraparound policy", status)
        self.assertIn("internal candidate-only contracts", status)
        self.assertIn("cross-event correlation", status)
        self.assertIn("refreshed default `minimal-second-source-intake`", changelog)
        self.assertIn("does not promote public\n  Inventory/Structure SDKs", changelog)
        self.assertIn("Mission target sets such as `mission-compact-intake` are", normalized(release))
        self.assertIn(
            "Transfer target sets such as `transfer-ufunction-intake` are also not part of the default gate",
            normalized(release),
        )
        self.assertIn(
            "Planning/guidance-only target sets such as `players-identity-lifecycle-intake` and",
            release,
        )
        self.assertIn("`mission-copied-bool-policy-slice`", release)
        self.assertIn("NextGen/Plugin Hub planning target sets", release)
        self.assertIn("rejected by `scripts/check_release_readiness.sh`", release)
        self.assertIn("not part of the default gate", release)
        self.assertIn("scalar-candidate summaries are review aids only, not RC scope", normalized(release))
        self.assertIn("remaining item producer/runtime validation", normalized(release))
        self.assertIn("Mission copied-bool observer, and Transfer `bAccept` lanes stay internal", normalized(release))
        self.assertIn("three item return-only checks are public only as copied `GameplayPolicyEvent`", normalized(release))
        self.assertIn("do not create an Inventory SDK, Items SDK", normalized(release))
        self.assertNormalizedIn(
            "Explicit `--ufunction-second-source-target-set` values add promoted release-readiness module target sets",
            release,
        )
        self.assertIn("they do not replace or omit the public RC gate", release)
        self.assertIn("--ufunction-second-source-target-set minimal-second-source-intake", release)
        self.assertIn(
            "ScriptStruct target sets such as `transfer-scriptstruct` are internal/layout-only",
            normalized(release),
        )
        self.assertIn("ScriptStruct promotion requires explicit opt-in", script)
        self.assertIn("--scriptstruct-second-source-root requires at least one --scriptstruct-second-source-target-set", script)
        self.assertNotIn('SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=("transfer-scriptstruct")', script)
        self.assertIn("target_set_readiness_classification", script)
        self.assertIn("release_readiness", script)
        self.assertIn("reject_non_release_second_source_target_set", script)
        self.assertIn("add_scriptstruct_second_source_target_set", script)
        self.assertIn("planning/guidance-only", script)
        self.assertIn("internal/layout-only", script)
        self.assertIn("name every promoted target set", pr_template)
        self.assertIn(
            "pass `--scriptstruct-second-source-root` only when a ScriptStruct target set is explicitly named",
            pr_template,
        )
        self.assertIn("--second-source-report-dir", release)
        self.assertIn("--second-source-report-dir", pr_template)
        self.assertIn("--second-source-report-dir", script)
        self.assertIn("validate_second_source_report_dir", script)
        self.assertIn("git check-ignore", script)
        self.assertIn("Second-source report dir inside the repository must be ignored", script)
        self.assertNormalizedIn("unignored in-repo report paths are rejected before the release build starts", release)
        self.assertIn("--fail-on-readiness-gaps", script)
        self.assertIn("gate_mode=second_source_promotion", release)
        self.assertIn("promotion_gate.ready=true", release)
        self.assertIn("gate_mode=informational_gap_report", release)
        self.assertIn("not_second_source_promotion_gate", release)
        self.assertIn("gate_mode=base_fixture_readiness", release)
        self.assertIn("required positional install roots even when `OBELISK_ROOT` is set", release)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", release)
        self.assertIn("not a release gate", release)
        self.assertNormalizedIn("not second-source promotion evidence", release)
        self.assertIn("Module-level field aggregates are not promotable layouts", release)
        self.assertIn("not used as promotion evidence", release)
        self.assertIn("per target set/function", release)
        self.assertIn("per-function analyzer fixture coverage", pr_template)
        self.assertIn("approved sanitized observer capture/research-note coverage", pr_template)
        self.assertIn("module-level field aggregates are not used as promotion evidence", pr_template)
        self.assertIn("readiness_gate=none", release)
        self.assertIn("runtime_observer_observational_only", release)
        self.assertNotIn("--map Ragnarok --instance arkserver", release)
        self.assertIn("--map <map> --instance <instance-id>", release)

    def test_release_gate_rejects_guidance_only_target_sets_before_build(self) -> None:
        blocked_cases = [
            ("--ufunction-second-source-target-set", "players-identity-lifecycle-intake", "UFunction"),
            ("--ufunction-second-source-target-set", "command-chat-response-route-planning", "UFunction"),
            ("--ufunction-second-source-target-set", "mission-copied-bool-policy-slice", "UFunction"),
            ("--ufunction-second-source-target-set", "structure-aggregate-census-planning", "UFunction"),
            ("--ufunction-second-source-target-set", "nextgen-plugin-hub-planning", "UFunction"),
            ("--scriptstruct-second-source-target-set", "structure-aggregate-census-planning", "ScriptStruct"),
            ("--scriptstruct-second-source-target-set", "plugin-hub-planning", "ScriptStruct"),
        ]

        for option, target_set, label in blocked_cases:
            with self.subTest(target_set=target_set):
                result = subprocess.run(
                    [
                        str(REPO_ROOT / "scripts/check_release_readiness.sh"),
                        "--require-second-source-readiness",
                        option,
                        target_set,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
                self.assertIn(f"{target_set} is planning/guidance-only", result.stderr)
                self.assertIn(f"release readiness {label} target set", result.stderr)
                self.assertIn("Promote a separate release/public target set", result.stderr)
                self.assertNotIn("cmake -S", result.stdout)

    def test_release_gate_rejects_internal_layout_only_target_sets_before_build(self) -> None:
        blocked_cases = [
            ("--ufunction-second-source-target-set", "buff-compact-intake", "UFunction"),
            ("--ufunction-second-source-target-set", "dino-compact-intake", "UFunction"),
            ("--ufunction-second-source-target-set", "mission-compact-intake", "UFunction"),
            ("--ufunction-second-source-target-set", "transfer-ufunction-intake", "UFunction"),
            ("--ufunction-second-source-target-set", "transfer-baccept-only-policy-slice", "UFunction"),
            ("--scriptstruct-second-source-target-set", "transfer-scriptstruct", "ScriptStruct"),
        ]

        for option, target_set, label in blocked_cases:
            with self.subTest(target_set=target_set):
                result = subprocess.run(
                    [
                        str(REPO_ROOT / "scripts/check_release_readiness.sh"),
                        "--require-second-source-readiness",
                        option,
                        target_set,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
                self.assertIn(f"{target_set} is internal/layout-only", result.stderr)
                self.assertIn(f"release readiness {label} target set", result.stderr)
                self.assertIn("Promote a separate release/public target set", result.stderr)
                self.assertNotIn("cmake -S", result.stdout)

    def test_release_gate_rejects_guidance_only_target_set_patterns_before_build(self) -> None:
        result = subprocess.run(
            [
                str(REPO_ROOT / "scripts/check_release_readiness.sh"),
                "--require-second-source-readiness",
                "--ufunction-second-source-target-set",
                "NextGen-plugin-hub-guidance",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("NextGen-plugin-hub-guidance is planning/guidance-only", result.stderr)
        self.assertIn("Promote a separate release/public target set", result.stderr)
        self.assertNotIn("cmake -S", result.stdout)

    def test_structure_census_aliases_cannot_be_release_readiness_target_sets(self) -> None:
        reserved_aliases = {
            "structure-aggregate",
            "structure-aggregate-census",
            "structure-census",
            "structure-census-planning",
            "structure-counts",
            "structure-proximity",
        }

        self.assertIn("structure-aggregate-census-planning", TARGET_SETS)
        self.assertIn("structure-aggregate-census-planning", PLANNING_ONLY_TARGET_SETS)
        self.assertNotIn("structure-aggregate-census-planning", RELEASE_READINESS_TARGET_SETS)
        for alias in reserved_aliases:
            with self.subTest(alias=alias):
                if alias in TARGET_SETS:
                    self.assertIn(alias, PLANNING_ONLY_TARGET_SETS)
                    self.assertNotIn(alias, RELEASE_READINESS_TARGET_SETS)

    def test_plugin_hub_matrix_keeps_player_identity_lifecycle_intake_planning_only(self) -> None:
        matrix = read("docs/PLUGIN_HUB_CAPABILITY_MATRIX.md")
        compact = normalized(matrix)

        self.assertIn("Player identity lifecycle intake", matrix)
        self.assertIn("`players-identity-lifecycle-intake` research guidance only", matrix)
        self.assertIn("Planning-only", matrix)
        self.assertIn(
            normalized(
                "Stable player identity, lookup, permissions, send-chat, moderation, public SDK, "
                "runtime hooks, or release readiness"
            ),
            compact,
        )
        self.assertLess(
            matrix.index("Players, tribes, dinos, buffs/status, missions, transfers"),
            matrix.index("Player identity lifecycle intake"),
        )

    def test_plugin_hub_seed_path_stays_classified_before_install_or_release_scope(self) -> None:
        contributor_path = read("docs/PLUGIN_HUB_CONTRIBUTOR_PATH.md")
        install = read("docs/INSTALL.md")
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        pr_template = read(".github/pull_request_template.md")

        for path, text in (
            ("docs/INSTALL.md", install),
            ("docs/RELEASE.md", release),
            ("docs/STATUS.md", status),
            (".github/pull_request_template.md", pr_template),
        ):
            compact = normalized(text)
            with self.subTest(file=path, item="foundation and matrix route"):
                self.assertIn("docs/PLUGIN_HUB_FOUNDATION_V1.md", text)
                self.assertIn("docs/PLUGIN_HUB_CAPABILITY_MATRIX.md", text)
            with self.subTest(file=path, item="install does not promote public SDK"):
                self.assertIn("plugin `.so`", compact)
                self.assertRegex(compact, r"(?i)(does not|do not)[^.]*public SDK")

        contributor_compact = normalized(contributor_path)
        for item in (
            "adding a Plugin Hub foundation example without widening the SDK",
            "`release-supported seed`: lifecycle/config/logging, descriptor/catalog reads, or process-local timers",
            "`experimental pattern`: passive copied `ChatMessageEvent` parsing or copied `GameplayPolicyEvent` auditing",
            "`blocked backlog`: anything that needs commands, replies, send-chat, permissions, identity",
            "Do not start from `plugins/` when writing the minimum external package",
            "Plugin Hub foundation examples help contributors learn the current C ABI",
            "They do not declare a complete v1 SDK",
        ):
            with self.subTest(file="docs/PLUGIN_HUB_CONTRIBUTOR_PATH.md", item=item):
                self.assertIn(normalized(item), contributor_compact)

        self.assertNormalizedIn(
            "keep support-tier classification separate from installation",
            install,
        )
        self.assertIn("The plugin installer only publishes an already-built `.so`", install)
        self.assertIn("run the\nplugin installer with `--dry-run`", install)
        self.assertIn("adding a first-party example", release)
        self.assertIn("naming a popular plugin\n  family does not promote public SDK surface", release)
        self.assertNormalizedIn(
            "do not gain new support tier, public SDK scope, or `v1.0` completion weight",
            status,
        )
        self.assertIn("names, demand, conceptual architecture, and migration-ergonomics references only", pr_template)
        self.assertIn("no source/API/ABI/behavior copying", pr_template)

    def test_release_gate_rejects_incomplete_ufunction_metadata_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_root = Path(temp_dir) / "candidate"
            shutil.copytree(REPO_ROOT / "tests/fixtures/ufunction_snapshots", candidate_root)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()

            for snapshot in candidate_root.rglob("*.snapshot.json"):
                payload = json.loads(snapshot.read_text(encoding="utf-8"))
                evidence = payload.setdefault("evidence", {})
                evidence["obelisk_commit"] = head[:12]
                evidence["artifact_sha256"] = "b" * 64
                evidence["capture_id"] = "release-preflight-test-capture"
                evidence["evidence_pack_id"] = "release-preflight-test-pack"
                snapshot.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            malformed = (
                candidate_root
                / "7e7ded49e0c6"
                / "sdk_inventory"
                / "PrimalItem.AllowRemoteAddToInventory.snapshot.json"
            )
            payload = json.loads(malformed.read_text(encoding="utf-8"))
            properties = payload["targets"][0]["property_chain"]["properties"]
            for prop in properties:
                if prop.get("class_name") == "BoolProperty":
                    prop.pop("bool_property_semantics", None)
                    break
            malformed.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    str(REPO_ROOT / "scripts/check_release_readiness.sh"),
                    "--require-second-source-readiness",
                    "--ufunction-second-source-root",
                    str(candidate_root),
                    "--ufunction-second-source-target-set",
                    "minimal-second-source-intake",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn("UFunction second-source root failed pre-build readiness metadata preflight", result.stderr)
        self.assertIn("complete artifact identity", result.stderr)
        self.assertIn("current BoolProperty tail metadata", result.stderr)
        self.assertNotIn("cmake -S", result.stdout)

    def test_release_gate_preflight_blocks_ambiguous_ufunction_target_sets_before_build(self) -> None:
        result = subprocess.run(
            [
                str(REPO_ROOT / "scripts/check_release_readiness.sh"),
                "--allow-dirty",
                "--allow-cross-ref-second-source-root",
                "--require-second-source-readiness",
                "--ufunction-second-source-root",
                str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
                "--ufunction-second-source-target-set",
                "minimal-second-source-intake",
                "--ufunction-second-source-target-set",
                "structure-observer-intake",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("ambiguous_target_set_coverage", result.stderr)
        self.assertIn("PrimalStructure.AllowStructureAccess", result.stderr)
        self.assertNotIn("cmake -S", result.stdout)

    def test_active_handoff_rc_tag_mentions_track_published_baseline(self) -> None:
        for path in ("docs/agent-handoff/CURRENT.md", "docs/agent-handoff/COMPACT_CONTEXT.md"):
            text = read(path)
            compact = normalized(text)
            lower = compact.lower()
            with self.subTest(file=path, item="published baseline"):
                self.assertIn("v0.1.0-rc.2", text)
                self.assertIn("published", lower)
                self.assertRegex(lower, r"(frozen|current published) core-first rc baseline")
            with self.subTest(file=path, item="clean gate and tag verification"):
                self.assertRegex(lower, r"clean (?:release )?gate|without `--allow-dirty`")
                self.assertIn("tag/ref verification", lower)
            with self.subTest(file=path, item="future stale tag guardrail"):
                self.assertIn("stale", lower)

    def test_current_handoff_stays_compact(self) -> None:
        current = read("docs/agent-handoff/CURRENT.md")
        section_headings = re.findall(r"^##\s+", current, re.M)

        self.assertLessEqual(len(section_headings), 8)
        self.assertNotIn("```", current)
        self.assertNotRegex(current, r"(?m)^###\s+")

        compact = normalized(current)
        for expected in [
            "This file is an active routing table only",
            "Durable evidence belongs in `docs/research/`",
            "resume facts in `COMPACT_CONTEXT.md`",
            "use `git log --oneline -1`",
        ]:
            with self.subTest(item=expected):
                self.assertIn(expected, compact)

        for stale_detail in [
            "Include only:",
            "Validate:",
            "checkpoint zero",
            "0-pre/0a/0b slicing sequence",
        ]:
            with self.subTest(stale_detail=stale_detail):
                self.assertNotIn(stale_detail, compact)

    def test_core_timers_stay_distinct_from_gameplay_module_timer_apis(self) -> None:
        docs = {
            "README.md": read("README.md"),
            "docs/ARCHITECTURE.md": read("docs/ARCHITECTURE.md"),
            "CONTRIBUTING.md": read("CONTRIBUTING.md"),
            "docs/agent-handoff/CURRENT.md": read("docs/agent-handoff/CURRENT.md"),
            "docs/agent-handoff/COMPACT_CONTEXT.md": read("docs/agent-handoff/COMPACT_CONTEXT.md"),
            "plugins/README.md": read("plugins/README.md"),
        }
        required = [
            "process-local",
            "core",
            "timer",
            "owner-token",
            "explicit unregister",
            "gameplay/module timer",
            "shared scheduler state",
            "UE identity",
            "persistent handles",
        ]

        for path, text in docs.items():
            compact = normalized(text)
            with self.subTest(file=path):
                for item in required:
                    self.assertIn(item, compact)

        plugins_readme = normalized(read("plugins/README.md"))
        timer_source = read("plugins/oProcessTimer/oProcessTimer.cpp")
        self.assertIn("`oProcessTimer` is part of the first-stable core plugin set for `v0.1.0`", plugins_readme)
        self.assertIn('out->version = "0.1.0";', timer_source)
        self.assertNotIn('out->version = "0.2.0-dev";', timer_source)
        self.assertNotIn('out->version = "0.1.0-rc.1";', timer_source)

    def test_reference_plugins_copy_only_advertised_api_prefix(self) -> None:
        for relative in (
            "plugins/oBaseEvents/oBaseEvents.cpp",
            "plugins/oProcessTimer/oProcessTimer.cpp",
            "plugins/oDescriptorCatalog/oDescriptorCatalog.cpp",
            "plugins/oChatAudit/oChatAudit.cpp",
            "plugins/oPolicyAudit/oPolicyAudit.cpp",
            "plugins/oChatLogger/oChatLogger.c",
        ):
            source = read(relative)
            with self.subTest(file=relative):
                self.assertIn("CopyApiPrefix", source)
                self.assertRegex(source, r"(?:std::)?memcpy\(&g_Api, api, copySize\);")
                self.assertIn("api->struct_size < sizeof(g_Api)", source)
                self.assertNotIn("g_Api = *api;", source)

    def test_core_timer_release_scope_separates_published_rc_from_future_v0_1(self) -> None:
        docs = {
            "docs/agent-handoff/COMPACT_CONTEXT.md": read("docs/agent-handoff/COMPACT_CONTEXT.md"),
            "docs/STATUS.md": read("docs/STATUS.md"),
            "docs/RELEASE.md": read("docs/RELEASE.md"),
            "CHANGELOG.md": read("CHANGELOG.md"),
            "plugins/README.md": read("plugins/README.md"),
            "docs/PLUGIN_ARCHITECTURE.md": read("docs/PLUGIN_ARCHITECTURE.md"),
        }

        for path, text in docs.items():
            compact = normalized(text)
            lower = compact.lower()
            with self.subTest(file=path, item="no post-RC/v1 timer label"):
                self.assertNotIn("post-rc/v1 timers", lower)
                self.assertNotRegex(lower, r"timers? (?:are|as) post-rc/v1")
                self.assertNotRegex(lower, r"timers?.{0,80}not part of (?:the )?v0\.1")

        compact_context = normalized(docs["docs/agent-handoff/COMPACT_CONTEXT.md"])
        release = normalized(docs["docs/RELEASE.md"])
        changelog = normalized(docs["CHANGELOG.md"])

        self.assertIn("First-stable `v0.1.0` timers are the first non-UE-dependent core primitive", compact_context)
        self.assertIn("part of the current `v0.1.0-rc.2` public surface", compact_context)
        self.assertIn("RC public scope remains limited to `GameplayPolicyEvent`, the minimal copied", release)
        self.assertIn("process-local owner-token timer primitive", release)
        self.assertIn("Added owner-token process-local timers", changelog)

    def test_arkapi_reference_is_names_demand_only_not_porting_or_copying(self) -> None:
        docs = {
            "README.md": read("README.md"),
            "docs/ARCHITECTURE.md": read("docs/ARCHITECTURE.md"),
            "CONTRIBUTING.md": read("CONTRIBUTING.md"),
            "docs/agent-handoff/CURRENT.md": read("docs/agent-handoff/CURRENT.md"),
        }
        required = [
            "ArkServerApi/AseApi",
            "names",
            "demand",
            "conceptual architecture",
            "migration",
            "not a behavior map",
            "not a porting",
            "copying source",
            "offsets",
            "layouts",
            "ABI assumptions",
            "wrappers",
            "raw UE pointer APIs",
            "command parsers",
            "return semantics",
            "implementations",
        ]

        for path, text in docs.items():
            compact = normalized(text)
            with self.subTest(file=path):
                for item in required:
                    self.assertIn(item, compact)

    def test_rc_publication_guardrails_are_consistent(self) -> None:
        published_pattern = (
            r"`?v?0\.1\.0-rc\.2`? is (?:the )?(?:current )?published|"
            r"published release-candidate baseline is core-first `v0\.1\.0-rc\.2`|"
            r"published release candidate"
        )

        docs = {
            "docs/RELEASE.md": read("docs/RELEASE.md"),
            "docs/STATUS.md": read("docs/STATUS.md"),
            "CHANGELOG.md": read("CHANGELOG.md"),
            "docs/agent-handoff/CURRENT.md": read("docs/agent-handoff/CURRENT.md"),
            "docs/agent-handoff/COMPACT_CONTEXT.md": read("docs/agent-handoff/COMPACT_CONTEXT.md"),
        }

        for path, text in docs.items():
            compact = normalized(text)
            lower = compact.lower()
            with self.subTest(file=path, item="published rc baseline"):
                self.assertRegex(text, r"0\.1\.0-rc\.2")
            with self.subTest(file=path, item="public api scope"):
                self.assertRcPublicScopeClaim(path, text)

        for path in ("docs/RELEASE.md", "docs/STATUS.md", "docs/agent-handoff/CURRENT.md", "docs/agent-handoff/COMPACT_CONTEXT.md"):
            text = docs[path]
            compact = normalized(text)
            lower = compact.lower()
            with self.subTest(file=path, item="published wording"):
                self.assertRegex(compact, published_pattern)
            with self.subTest(file=path, item="validated publication evidence"):
                self.assertRegex(lower, r"(clean (?:release )?gate|without `--allow-dirty`|release ref passed|passed this gate)")
                self.assertIn("tag/ref verification", lower)

        for path in ("docs/RELEASE.md", "docs/agent-handoff/CURRENT.md", "docs/agent-handoff/COMPACT_CONTEXT.md"):
            text = docs[path]
            compact = normalized(text)
            lower = compact.lower()
            with self.subTest(file=path, item="future unauthorized push guardrail"):
                self.assertCurrentTurnReleaseAuthorization(path, text)
            with self.subTest(file=path, item="future stale tag guardrail"):
                self.assertIn("stale", lower)
                self.assertRegex(lower, r"(not publicable|do not recreate|must not be reused|are not reused or pushed|recreated only after rerunning)")

        pr_template = normalized(read(".github/pull_request_template.md"))
        pr_lower = pr_template.lower()
        self.assertIn("release-candidate publication prs rerun", pr_lower)
        self.assertIn("scripts/check_release_readiness.sh --require-second-source-readiness", pr_template)
        self.assertIn("accepted second-source root", pr_lower)
        self.assertIn("release tags and release-ref pushes have explicit release-manager/lead authorization", pr_lower)
        self.assertIn("exact tag/ref comparison", pr_lower)
        self.assertIn("stale local tags", pr_lower)
        self.assertIn("are not reused or pushed", pr_lower)

    def test_disable_plugins_marker_is_documented_as_wrapper_input_not_runtime_gate(self) -> None:
        readme = read("README.md")
        install = read("docs/INSTALL.md")
        status = read("docs/STATUS.md")

        for path, text in (("README.md", readme), ("docs/INSTALL.md", install), ("docs/STATUS.md", status)):
            with self.subTest(file=path, item="marker named"):
                self.assertIn("disable-plugins", text)
            with self.subTest(file=path, item="runtime env gate"):
                self.assertIn("OBELISK_DISABLE_PLUGINS=1", text)
            with self.subTest(file=path, item="not runtime gate by itself"):
                self.assertRegex(
                    normalized(text),
                    r"disable-plugins.*(?:not an independent runtime gate|not a runtime gate by itself)",
                )

        normalized_readme = normalized(readme)
        normalized_install = normalized(install)
        normalized_status = normalized(status)
        self.assertIn("LinuxGSM wrapper input", normalized_readme)
        self.assertIn("not an independent runtime gate by itself", normalized_readme)
        self.assertIn("wrapper translates it into `OBELISK_DISABLE_PLUGINS=1`", normalized_install)
        self.assertIn("custom launchers must set that environment variable themselves", normalized_install)
        self.assertIn("when the wrapper or launcher sets `OBELISK_DISABLE_PLUGINS=1`", normalized_status)

    def test_rc_final_validation_does_not_use_minimal_only_root_for_all_public_target_sets(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")
        final_validation = re.search(r"## Final RC Validation(?P<body>.*)", plan, re.S)
        self.assertIsNotNone(final_validation)
        final_text = final_validation.group("body")
        release_gate = re.search(
            r"```bash\n(?P<command>scripts/check_release_readiness\.sh \\\n.*?\n)```",
            final_text,
            re.S,
        )
        self.assertIsNotNone(release_gate)
        release_gate_text = release_gate.group("command")

        for target_set in [
            "minimal-second-source-intake",
            "structure-observer-intake",
            "chat-message-intake",
        ]:
            with self.subTest(target_set=target_set):
                self.assertIn(f"--ufunction-second-source-target-set {target_set}", release_gate_text)

        self.assertIn("scripts/assemble_rc_ufunction_second_source_root.py", final_text)
        self.assertIn("--minimal-root", final_text)
        self.assertIn("--structure-root", final_text)
        self.assertIn("--item-return-root", final_text)
        self.assertIn("--chat-root", final_text)
        self.assertIn("/tmp/obelisk-rc-ufunction-second-source-root", final_text)
        self.assertIn("--ufunction-second-source-root /tmp/obelisk-rc-ufunction-second-source-root", release_gate_text)
        self.assertIn("must contain the candidate snapshots for all four", final_text)
        self.assertNotRegex(
            release_gate_text,
            r"--ufunction-second-source-root\s+/servidor/ark/workspace-offline/[^\\\n]*minimal[^\\\n]*/ufunction-snapshots",
        )

    def test_offline_artifact_pack_runbook_stays_container_scoped(self) -> None:
        runbook = read("docs/OFFLINE_ARTIFACT_PACKS.md")
        compact = normalized(runbook)

        required = (
            "This runbook is for contributors who receive or prepare already-captured offline evidence packs",
            "The pack container is evidence packaging, not a promotion result",
            "Child JSON is always scanned for generic hygiene blockers",
            "unknown `obelisk.*` schemas fail closed",
            "Promote mode is not a pack-container approval path",
            "Strict coverage requires `target_set_coverage` to be complete and internally consistent",
            "does not replace per-target readiness reports",
            "Do not claim that a passing pack promotes a public SDK",
            "object identity, lookup, mutation, return overrides, ResourceHandle",
            "Local artifact directories are not current release or v1 identity/structure evidence by location",
            "`obelisk.offline-artifact-gate-result.v1` JSON is gate output, not an authoritative child manifest",
            "convert archival identity/structure packs into current evidence",
            "Label local packs as current-reviewed or archival/rejected",
            "current v1 player identity, structure aggregate/census, release readiness, or SDK completion",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(normalized(item), compact)

        forbidden = (
            "/servidor/ark/",
            "arkserver restart",
            "arkserver2 restart",
            "git push",
            "git tag",
            "discord.com/" + "api/webhooks",
        )
        for item in forbidden:
            with self.subTest(forbidden=item):
                self.assertNotIn(item, runbook)

    def test_structure_build_policy_target_is_not_release_scope(self) -> None:
        forbidden_terms = [
            "PrimalStructure.IsAllowedToBuild",
            "APrimalStructure.IsAllowedToBuild",
        ]
        release_scope_files = [
            "docs/RELEASE.md",
            "docs/STATUS.md",
            "CHANGELOG.md",
            "scripts/check_release_readiness.sh",
            "scripts/check_rc_layout_evidence_smoke.sh",
            "scripts/reflection_target_sets.py",
            "scripts/assemble_rc_ufunction_second_source_root.py",
        ]

        for path in release_scope_files:
            text = read(path)
            for term in forbidden_terms:
                with self.subTest(file=path, term=term):
                    self.assertNotIn(term, text)

        triage = read("docs/research/2026-05-30-structure-build-policy-triage.md")
        for expected in [
            "second-wave structure build-policy candidate",
            "Do not add it to `structure-observer-intake`",
            "No committed sanitized snapshot currently exists",
            "Return override/build denial is a separate mutation/authority feature",
            "This triage does not promote a public Structure SDK",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, triage)

    def test_rc_ufunction_root_helper_is_documented_as_copy_only(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")
        compact = read("docs/agent-handoff/COMPACT_CONTEXT.md")

        final_validation = re.search(r"## Final RC Validation(?P<body>.*)", plan, re.S)
        self.assertIsNotNone(final_validation)
        final_text = final_validation.group("body")

        for path, text in (
            ("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md", final_text),
            ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
        ):
            with self.subTest(file=path, claim="helper"):
                self.assertIn("scripts/assemble_rc_ufunction_second_source_root.py", text)
            with self.subTest(file=path, claim="copy-only snapshots"):
                self.assertRegex(normalized(text), r"copies existing sanitized snapshots(?: only)?")
            with self.subTest(file=path, claim="no evidence regeneration"):
                self.assertRegex(normalized(text), r"does not regenerate evidence|without regenerating snapshots")

    def test_rc_ufunction_root_helper_manifest_redaction_stays_explicit(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")
        helper = read("scripts/assemble_rc_ufunction_second_source_root.py")

        final_validation = re.search(r"## Final RC Validation(?P<body>.*)", plan, re.S)
        self.assertIsNotNone(final_validation)
        final_text = final_validation.group("body")

        for item in [
            "fresh\npath-redacted manifest written by the helper",
            "do not reuse or publish older `/tmp`\nmanifests",
            "absolute source roots",
            "non-redacted input paths",
        ]:
            with self.subTest(item=item):
                self.assertIn(item, final_text)

        self.assertIn("path_redacted", helper)
        self.assertIn("assert_no_manifest_path_leaks(manifest", helper)

    def test_checkpoint_scope_preserves_resource_and_post_rc_ordering(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")
        compact = read("docs/agent-handoff/COMPACT_CONTEXT.md")
        current = read("docs/agent-handoff/CURRENT.md")
        status = read("docs/STATUS.md")

        for path, text in (
            ("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md", plan),
            ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
        ):
            with self.subTest(file=path, item="post-RC recognizer order"):
                if path.endswith("COMPACT_CONTEXT.md"):
                    self.assertIn("Structure aggregate/census planning", normalized(text))
                    self.assertIn("Transfer `bAccept` remains a useful bool-layout fixture", normalized(text))
                else:
                    self.assertIn(
                        "Item return-only policy, Mission copied-bool observer, then Transfer `bAccept`",
                        normalized(text),
                    )
            with self.subTest(file=path, item="no RC public SDK/API promotion"):
                self.assertRegex(normalized(text), r"no RC public SDK/API|not RC public SDK/API|does not change the RC public API")

        for path, text in (
            ("docs/agent-handoff/CURRENT.md", current),
            ("docs/STATUS.md", status),
        ):
            compact_text = normalized(text)
            with self.subTest(file=path, item="item return-only public shape"):
                self.assertIn("three", compact_text)
                self.assertIn("GameplayPolicyEvent", compact_text)
                self.assertIn("ReturnValue", compact_text)
            with self.subTest(file=path, item="no separate item/inventory SDK promotion"):
                self.assertIn("public Inventory SDK", compact_text)
                self.assertIn("Items SDK", compact_text)
                self.assertIn("identity", compact_text)
                self.assertIn("mutation", compact_text)
                self.assertIn("return override", compact_text)

        for path, text in (
            ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
            ("docs/agent-handoff/CURRENT.md", current),
        ):
            with self.subTest(file=path, item="no transfer runtime authorization"):
                self.assertIn("does not authorize Transfer runtime work", normalized(text))

        for path, text in (
            ("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md", plan),
            ("docs/agent-handoff/COMPACT_CONTEXT.md", compact),
            ("docs/agent-handoff/CURRENT.md", current),
        ):
            with self.subTest(file=path, item="ResourceHandle semantic blockers"):
                compact_text = normalized(text)
                self.assertIn("ResourceHandle", compact_text)
                self.assertIn("semantic", compact_text)
                self.assertIn("helper", compact_text)
                self.assertIn("mutation", compact_text)
                self.assertIn("fail-closed", compact_text)

    def test_item_return_only_policy_slice_promotes_only_copied_return_value_events(self) -> None:
        bridge_plan = read("docs/research/2026-05-29-item-return-only-policy-bridge-plan.md")
        slice_note = read("docs/research/2026-05-30-item-return-only-policy-slice.md")
        current = read("docs/agent-handoff/CURRENT.md")
        status = read("docs/STATUS.md")
        release_gate = read("scripts/check_release_readiness.sh")

        for path, text in (
            ("docs/research/2026-05-29-item-return-only-policy-bridge-plan.md", bridge_plan),
            ("docs/research/2026-05-30-item-return-only-policy-slice.md", slice_note),
        ):
            compact = normalized(text)
            with self.subTest(file=path, item="return-only bool shape"):
                self.assertIn("PrimalItem.AllowEquipItem.ReturnValue", text)
                self.assertIn("PrimalItem.CanRepair.ReturnValue", text)
                self.assertIn("PrimalItem.UseItemOntoItem.ReturnValue", text)
            with self.subTest(file=path, item="excluded item fields"):
                self.assertIn("CraftBlueprint", text)
                self.assertIn("bIgnoreInventoryRequirement", text)
                self.assertIn("bConsumeResources", text)
                self.assertIn("toInventory", text)
                self.assertIn("DestinationItem", text)
                self.assertIn("AdditionalData", text)
            with self.subTest(file=path, item="historical notes do not promote broad item SDKs"):
                self.assertIn("does not promote", compact)
                self.assertIn("Items SDK", compact)
                self.assertIn("Inventory SDK", compact)
                self.assertIn("ResourceHandle", compact)
                self.assertIn("identity", compact)
                self.assertIn("mutation", compact)
                self.assertIn("return override", compact)
            with self.subTest(file=path, item="no runtime claim"):
                self.assertRegex(compact, r"(test-only|offline evidence-only|offline review evidence only)")
                self.assertRegex(compact, r"(no hook wiring|runtime hook|Before Runtime Wiring|runtime log claim)")
                self.assertRegex(compact, r"(No SDK/API header|public SDK exposure|public callback)")

        compact_slice = normalized(slice_note)
        with self.subTest(file="docs/research/2026-05-30-item-return-only-policy-slice.md", item="descriptor-only preflight"):
            self.assertIn("Promotion Update", slice_note)
            self.assertIn("append-only public `GameplayPolicyEvent` kinds", compact_slice)
            self.assertIn("Descriptor-Only Preflight", slice_note)
            self.assertIn("inventory_item.allow_equip_check", slice_note)
            self.assertIn("inventory_item.can_repair_check", slice_note)
            self.assertIn("inventory_item.use_onto_item_check", slice_note)
            self.assertIn("promotion_ready=false", compact_slice)
            self.assertIn("OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE` only", slice_note)
            self.assertIn("historical descriptor-only preflight", compact_slice)
            self.assertIn("docs/public_gameplay_events.json", slice_note)
            self.assertIn("include/obelisk/ObeliskApi.h", slice_note)
            self.assertIn("runtime dispatcher tables", compact_slice)
            self.assertIn("public SDK fixtures", slice_note)
            self.assertIn("plugin callbacks", slice_note)
            self.assertIn("OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK", slice_note)
            self.assertIn("OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN", slice_note)

        for path, text in (
            ("docs/agent-handoff/CURRENT.md", current),
            ("docs/STATUS.md", status),
        ):
            compact = normalized(text)
            with self.subTest(file=path, item="three public GameplayPolicyEvent kinds only"):
                self.assertIn("three", compact)
                self.assertIn("GameplayPolicyEvent", compact)
                self.assertIn("ReturnValue", compact)
            with self.subTest(file=path, item="item blockers"):
                self.assertIn("ResourceHandle", compact)
                self.assertIn("public Inventory SDK", compact)
                self.assertIn("Items SDK", compact)
                self.assertIn("identity", compact)
                self.assertIn("mutation", compact)
                self.assertIn("return override", compact)

        with self.subTest(file="scripts/check_release_readiness.sh", item="no-core inventory hygiene checks"):
            self.assertIn("scripts/check_item_return_only_readiness.py --json", release_gate)
            self.assertIn("scripts/check_inventory_action_fixture_boundary.py --json", release_gate)

    def test_installed_sdk_consumer_stays_in_release_gate_not_default_ctest(self) -> None:
        cmake = read("CMakeLists.txt")
        release_gate = read("scripts/check_release_readiness.sh")

        self.assertNotIn("InstallLayoutPublicSdkConsumer", cmake)
        self.assertNotIn("scripts/test_install_obelisk_layout.sh", cmake)
        self.assertIn("scripts/test_install_obelisk_layout.sh", release_gate)
        self.assertIn("LAYOUT_CHECK_ROOT", release_gate)

    def test_installed_sdk_smoke_covers_release_examples_in_release_gate(self) -> None:
        release_gate = read("scripts/check_release_readiness.sh")
        layout_test = read("scripts/test_install_obelisk_layout.sh")
        installed_consumer_cmake = read("tests/sdk_installed_consumer/CMakeLists.txt")
        consumer = read("tests/sdk_installed_consumer/consumer_plugin.cpp")
        fixture = read("tests/sdk_installed_consumer/consumer_fixture.cpp")

        self.assertIn('scripts/test_install_obelisk_layout.sh "${LAYOUT_CHECK_ROOT}"', release_gate)
        self.assertIn('cp -R "${REPO_DIR}/tests/sdk_installed_consumer/." "${WORK_DIR}/"', layout_test)
        self.assertIn('"${WORK_DIR}/build/consumer_fixture"', layout_test)
        self.assertIn('"${PLUGIN_PATH}"', layout_test)
        self.assertIn('installed_headers="$(find "${INSTALL_ROOT}/include" -type f', layout_test)
        self.assertIn('obelisk/ObeliskApi.h', layout_test)
        self.assertIn("SDK install published unexpected public headers", layout_test)
        self.assertIn('OBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT="${REPO_DIR}/plugins"', layout_test)
        self.assertIn('OBELISK_RELEASE_SCOPE_EXTERN_ROOT="${REPO_DIR}/extern"', layout_test)

        external_examples = (
            (
                "minimal",
                "SDK_MINIMAL_EXAMPLE_DIR",
                "SDK_MINIMAL_EXAMPLE_PLUGIN_PATH",
                "examples/sdk_minimal_plugin",
                "obelisk_sdk_minimal_plugin.so",
                '"obelisk_sdk_minimal_plugin"',
            ),
            (
                "descriptor catalog",
                "SDK_DESCRIPTOR_EXAMPLE_DIR",
                "SDK_DESCRIPTOR_EXAMPLE_PLUGIN_PATH",
                "examples/sdk_descriptor_catalog",
                "obelisk_sdk_descriptor_catalog.so",
                '"obelisk_sdk_descriptor_catalog"',
            ),
            (
                "timer",
                "SDK_TIMER_EXAMPLE_DIR",
                "SDK_TIMER_EXAMPLE_PLUGIN_PATH",
                "examples/sdk_timer_plugin",
                "obelisk_sdk_timer_plugin.so",
                '"obelisk_sdk_timer_plugin"',
            ),
        )
        for label, example_dir_var, plugin_path_var, source_dir, plugin_so, plugin_id in external_examples:
            with self.subTest(example=label):
                self.assertIn(f'cp -R "${{REPO_DIR}}/{source_dir}/."', layout_test)
                cmake_match = re.search(
                    rf'cmake -S "\$\{{{example_dir_var}\}}" -B "\$\{{{example_dir_var}\}}/build"'
                    rf'(?P<body>.*?)\ncmake --build "\$\{{{example_dir_var}\}}/build"',
                    layout_test,
                    re.S,
                )
                self.assertIsNotNone(cmake_match)
                cmake_body = cmake_match.group("body") if cmake_match else ""
                self.assertIn('-DCMAKE_PREFIX_PATH="${INSTALL_ROOT}"', cmake_body)
                self.assertIn("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", cmake_body)
                self.assertIn(
                    f'{plugin_path_var}="${{{example_dir_var}}}/build/{plugin_so}"',
                    layout_test,
                )
                self.assertIn(f'require_path "${{{plugin_path_var}}}"', layout_test)
                self.assertIn(
                    f'if ! grep -F "${{INSTALL_ROOT}}/include" "${{{example_dir_var}}}/build/compile_commands.json"',
                    layout_test,
                )
                self.assertIn(
                    f'if grep -F "${{REPO_DIR}}/include" "${{{example_dir_var}}}/build/compile_commands.json"',
                    layout_test,
                )
                self.assertIn(f'"${{{plugin_path_var}}}"', layout_test)
                self.assertIn(plugin_id, layout_test)

        for target in ("release_scope_oBaseEvents", "release_scope_oProcessTimer", "release_scope_oDescriptorCatalog"):
            with self.subTest(file="tests/sdk_installed_consumer/CMakeLists.txt", target=target):
                self.assertIn(target, installed_consumer_cmake)
        for plugin_path in ("oBaseEvents.so", "oProcessTimer.so", "oDescriptorCatalog.so"):
            with self.subTest(file="scripts/test_install_obelisk_layout.sh", plugin_path=plugin_path):
                self.assertIn(plugin_path, layout_test)
        self.assertIn("Obelisk::obelisk_sdk", installed_consumer_cmake)

        self.assertRegex(
            consumer,
            re.compile(
                r"OBELISK_CONCAT\(Register, TimerWithOwnerTokenHandle\)\(\s*"
                r"g_OwnerToken,\s*"
                r"1000,\s*"
                r"1000,\s*"
                r"OBELISK_TIMER_FLAG_REPEATING,\s*"
                r"HandleScheduledCallback,",
                re.S,
            ),
        )
        self.assertIn("InstallLayoutConsumer_ScheduledCallbackSeen", consumer)

        for token in [
            'Require(intervalMs == 1000, "unexpected repeating timer interval");',
            'Require(flags == OBELISK_TIMER_FLAG_REPEATING, "unexpected repeating timer flags");',
            "DispatchValidTimer();",
            'Require(timerSeen(), "expected plugin to observe timer callback");',
        ]:
            with self.subTest(file="tests/sdk_installed_consumer/consumer_fixture.cpp", token=token):
                self.assertIn(token, fixture)

    def test_mission_copied_bool_observer_stays_internal_and_non_authoritative(self) -> None:
        mission_plan = read("docs/research/2026-05-30-mission-copied-bool-observer-plan.md")
        current = read("docs/agent-handoff/CURRENT.md")
        status = read("docs/STATUS.md")

        compact_plan = normalized(mission_plan)
        for item in [
            "MissionType.AddPlayerToMission.bForceAdd",
            "MissionType.AddPlayerToMission.ReturnValue",
            "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
            "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
            "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
        ]:
            with self.subTest(file="docs/research/2026-05-30-mission-copied-bool-observer-plan.md", item=item):
                self.assertIn(item, mission_plan)

        for item in [
            "internal/test-only",
            "no hook wiring",
            "marker/env",
            "public Mission SDK",
            "identity",
            "mutation",
            "return override",
            "ResourceHandle",
            "does not authorize public Mission SDK/API/runtime wiring",
            "must never dispatch plugin callbacks",
            "This plan is not approval to add or enable gates",
            "does not authorize server access, Discord notices, marker/env changes, restarts, or live observation",
            "No run is approved by this note",
        ]:
            with self.subTest(file="docs/research/2026-05-30-mission-copied-bool-observer-plan.md", item=item):
                self.assertIn(normalized(item), compact_plan)

        for path, text in (
            ("docs/agent-handoff/CURRENT.md", current),
            ("docs/STATUS.md", status),
        ):
            compact = normalized(text)
            with self.subTest(file=path, item="mission remains internal after item event promotion"):
                self.assertIn("Mission copied-bool", compact)
                self.assertRegex(compact, r"internal|absent|not ready")
            with self.subTest(file=path, item="mission blockers"):
                self.assertRegex(compact, r"public Mission SDK|missions.*public.*SDK|public module SDK")
                self.assertIn("ResourceHandle", compact)
                self.assertIn("identity", compact)
                self.assertIn("mutation", compact)
                self.assertIn("return override", compact)

    def test_mission_copied_bool_tail_contract_stays_documented_and_candidate_only(self) -> None:
        mission_plan = read("docs/research/2026-05-30-mission-copied-bool-observer-plan.md")
        current = read("docs/agent-handoff/CURRENT.md")

        compact_plan = normalized(mission_plan)
        compact_current = normalized(current)
        bool_tail_contract = (
            r"`bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, "
            r"`field_mask=0xff`, (?:and )?`native_bool=false`"
        )

        for path, compact in (
            ("docs/research/2026-05-30-mission-copied-bool-observer-plan.md", compact_plan),
            ("docs/agent-handoff/CURRENT.md", compact_current),
        ):
            with self.subTest(file=path, item="exact bool-tail evidence"):
                self.assertRegex(compact, bool_tail_contract)
            with self.subTest(file=path, item="consume-only non-promotion"):
                self.assertRegex(compact, r"consume mode accepts?|Consume gate: `accepted`")
                self.assertRegex(compact, r"promote mode blocks?|Promotion ready: `false`")

        for item in [
            "older `/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-policy-slice-20260530T072912Z/` pack is historical",
            "predates the preserved `bool_field_size` and `bool_byte_offset` fields",
            "now fails the consume gate",
        ]:
            with self.subTest(file="docs/research/2026-05-30-mission-copied-bool-observer-plan.md", item=item):
                self.assertIn(normalized(item), compact_plan)

    def test_uobject_flag_policy_current_blockers_stay_explicit(self) -> None:
        current = read("docs/agent-handoff/CURRENT.md")
        status = read("docs/STATUS.md")
        release = read("docs/RELEASE.md")
        research = read("docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md")

        compact_current = normalized(current)
        compact_status = normalized(status)
        compact_release = normalized(release)
        compact_research = normalized(research)

        for item in [
            "ResourceHandle/public GObjects remain blocked",
            "old flag-policy artifact is obsolete",
            "durable rich-provenance refresh is preserved",
            "Consume mode accepts it and promote mode stays blocked",
            "Do not rerun broad FName, GObjects, or core scans for ResourceHandle",
            "post-callback rejection contract is preserved as candidate-only",
            "first strict serial reuse/wraparound policy artifact is preserved",
            "manifest consume mode accepts it and promote mode blocks it as candidate-only",
            "does not unlock runtime negative samples, public lookup, object identity",
            "next strict ResourceHandle blocker is rejected runtime object samples plus runtime serial reuse/wraparound semantics",
            "future-runtime-observation-plan",
            "operator-approved live-ops brief names the exact debug target",
            "Do not replace this with another broad offline FName/GObjects scan",
        ]:
            with self.subTest(file="docs/agent-handoff/CURRENT.md", item=item):
                self.assertIn(normalized(item), compact_current)

        for item in [
            "UObject flag validity policy | Not ready",
            "strict serial-policy artifacts",
            "candidate-only evidence",
            "do not prove lifecycle/validity or serial reuse semantics",
            "do not unlock `ResourceHandle`, object lookup, GObjects promotion",
            "persistent handles, identity, mutation, or return overrides",
        ]:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(normalized(item), compact_status)

        for item in [
            "Strict serial reuse/wraparound policy artifacts are also internal candidate-only contracts",
            "does not prove runtime reuse semantics",
            "public lookup safety",
            "persistent handles, identity, mutation, return overrides, runtime negative samples",
            "public `ResourceHandle`",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(normalized(item), compact_release)

        for item in [
            "old labels",
            "missing provenance",
            "caller",
            "consume",
            "promote",
            "ResourceHandle",
            "Durable Rich-Provenance Refresh",
            "status=accepted_internal_static_evidence",
            "promote_mode_uobject_flag_policy_candidate_only",
            "direct consume gate accepts candidate reports with minimal verified sidecars",
        ]:
            with self.subTest(file="docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md", item=item):
                self.assertIn(normalized(item), compact_research)

    def test_historical_checkpoint_zero_stays_guardrail_only(self) -> None:
        plan = read("docs/research/2026-05-29-rc-checkpoint-slicing-plan.md")
        compact = read("docs/agent-handoff/COMPACT_CONTEXT.md")
        current = read("docs/agent-handoff/CURRENT.md")

        checkpoint_zero_a = re.search(r"### 0a\..*?(?=\n### 0b\.)", plan, re.S)
        checkpoint_zero_b = re.search(r"### 0b\..*?(?=\n### 1\.)", plan, re.S)
        self.assertIsNotNone(checkpoint_zero_a)
        self.assertIsNotNone(checkpoint_zero_b)
        checkpoint_zero_a_text = checkpoint_zero_a.group(0)
        checkpoint_zero_b_text = checkpoint_zero_b.group(0)
        checkpoint_zero_a_include = re.search(
            r"Include only:\n\n(?P<body>.*?)(?=\n\nValidate:)",
            checkpoint_zero_a_text,
            re.S,
        )
        self.assertIsNotNone(checkpoint_zero_a_include)
        checkpoint_zero_a_include_paths = re.findall(
            r"^- `([^`]+)`$",
            checkpoint_zero_a_include.group("body"),
            re.M,
        )
        self.assertEqual(
            [
                "scripts/scan_resource_handle_serials.py",
                "scripts/test_scan_resource_handle_serials.py",
                "scripts/validate_offline_artifact_gate.py",
                "scripts/test_validate_offline_artifact_gate.py",
            ],
            checkpoint_zero_a_include_paths,
        )
        checkpoint_zero_b_include = re.search(
            r"Include:\n\n(?P<body>.*?)(?=\n\nValidate:)",
            checkpoint_zero_b_text,
            re.S,
        )
        self.assertIsNotNone(checkpoint_zero_b_include)
        checkpoint_zero_b_include_text = checkpoint_zero_b_include.group("body")
        checkpoint_zero_b_include_paths = re.findall(
            r"^- `([^`]+)`(?: .*)?$",
            checkpoint_zero_b_include_text,
            re.M,
        )
        self.assertEqual(
            [
                "scripts/check_release_readiness.sh",
                "scripts/test_check_release_readiness_options.sh",
            ],
            checkpoint_zero_b_include_paths,
        )

        for item in [
            "make the local review surface deterministic before slicing runtime/API changes",
            "artifact hygiene only",
            "scripts/validate_offline_artifact_gate.py",
            "scripts/test_validate_offline_artifact_gate.py",
            "broad release/public-scope guardrails that read public API/docs/handoff/skills",
            "runtime/API implementation changes",
            "analyzer output, offline evidence packs, generated snapshots, logs, copied server\n  configs, or other artifacts",
            "any statement that the current dirty worktree passes the release gate",
        ]:
            with self.subTest(item=item):
                self.assertIn(item, checkpoint_zero_a_text)

        for item in [
            "scripts/check_release_readiness.sh",
            "scripts/test_check_release_readiness_options.sh",
            "release-check option/default behavior self-contained",
            "read only\nthe release gate script and its option fixtures",
            "Run the broad\npublic-scope guardrails with the later API/docs checkpoint",
            "option/default and in-repo report-dir ignored-path validation alignment",
            "public docs, public metadata JSON, handoff, skills, research-note changes, or broad\n  public-scope guardrail edits",
            "offline evidence packs, generated snapshots, logs, copied server configs, or other\n  artifacts",
            "any claim that broad guardrail success proves RC readiness",
        ]:
            with self.subTest(item=item):
                self.assertIn(item, checkpoint_zero_b_text)

        self.assertNotIn("minimal docs wording required", checkpoint_zero_b_text)

        for stale_path in [
            "include/obelisk/ObeliskApi.h",
            "src/",
            "plugins/oBaseEvents/oBaseEvents.cpp",
            "docs/public_gameplay_events.json",
            "docs/research/2026-05-29-public-gameplay-event-readiness-audit.md",
        ]:
            with self.subTest(stale_path=stale_path):
                self.assertNotIn(stale_path, checkpoint_zero_a_text)

        for public_or_beta_scope in [
            ".github/",
            "CHANGELOG.md",
            "README.md",
            "agent-skills/",
            "docs/RELEASE.md",
            "docs/STATUS.md",
            "docs/agent-handoff/",
            "docs/public_gameplay_events.json",
            "include/obelisk/ObeliskApi.h",
            "enable-chat-events",
            "beta",
            "oChatLogger",
            "chat route",
        ]:
            with self.subTest(public_or_beta_scope=public_or_beta_scope):
                self.assertNotIn(public_or_beta_scope, checkpoint_zero_a_text)

        for runtime_or_api_path in [
            "include/obelisk/ObeliskApi.h",
            "core/",
            "hooks/",
            "plugins/oBaseEvents/",
            "docs/public_gameplay_events.json",
            "tests/abi/",
            "tests/sdk_consumer/",
            "tests/sdk_installed_consumer/",
        ]:
            with self.subTest(runtime_or_api_path=runtime_or_api_path):
                self.assertNotIn(runtime_or_api_path, checkpoint_zero_b_text)

        for forbidden_checkpoint_zero_b_include in [
            ".github/",
            "CHANGELOG.md",
            "README.md",
            "CONTRIBUTING.md",
            "agent-skills/",
            "docs/RELEASE.md",
            "docs/STATUS.md",
            "docs/VERSIONING.md",
            "docs/ARCHITECTURE.md",
            "docs/INSTALL.md",
            "docs/OPERATOR_CLI.md",
            "docs/oBaseEvents.md",
            "docs/public_gameplay_events.json",
            "docs/research/",
            "include/obelisk/",
            "core/",
            "hooks/",
            "plugins/",
            "tests/abi/",
            "tests/sdk_consumer/",
            "tests/sdk_installed_consumer/",
            "tests/fixtures/",
            "ufunction-snapshots",
            "scriptstruct",
            "snapshot_evidence_pack",
            "/servidor/ark/",
        ]:
            with self.subTest(forbidden_checkpoint_zero_b_include=forbidden_checkpoint_zero_b_include):
                self.assertNotIn(forbidden_checkpoint_zero_b_include, checkpoint_zero_b_include_text)

        compact_text = normalized(compact)
        compact_lower = compact_text.lower()
        self.assertIn("historical recovery context", compact_text)
        self.assertIn("not active routing for the current head", compact_text)
        self.assertIn("use `git log --oneline -1` for the current head", compact_lower)
        self.assertIn("rather than by the old 0-pre/0a/0b slicing sequence", compact_text)
        current_text = normalized(current)
        current_lower = current_text.lower()
        self.assertIn("historical recovery context", current_lower)
        self.assertIn("not active routing", current_text)
        self.assertIn("use `git log --oneline -1`", current_lower)
        self.assertIn("Current post-RC focus:", current_text)
        self.assertNotIn("Current RC focus:", current_text)
        self.assertIn("accepted RC UFunction second-source root", current_text)

    def test_experimental_plugins_stay_out_of_release_scope(self) -> None:
        cmake = read("CMakeLists.txt")
        architecture = read("docs/PLUGIN_ARCHITECTURE.md")
        status = read("docs/STATUS.md")
        release = read("docs/RELEASE.md")
        plugins_readme = read("plugins/README.md")
        script = read("scripts/check_release_readiness.sh")

        self.assertIn(
            'option(OBELISK_BUILD_EXPERIMENTAL_PLUGINS "Build experimental first-party plugins outside the release scope" OFF)',
            cmake,
        )
        self.assertRegex(
            cmake,
            re.compile(
                r"if\(OBELISK_BUILD_EXPERIMENTAL_PLUGINS\)\s+"
                r"add_subdirectory\(plugins/oPolicyAudit\)\s+"
                r"add_subdirectory\(plugins/oChatLogger\)\s+"
                r"add_subdirectory\(plugins/oChatAudit\)\s+"
                r"endif\(\)",
                re.M,
            ),
        )
        for text in (architecture, status, release, plugins_readme):
            self.assertIn("oPolicyAudit", text)
            self.assertIn("oChatLogger", text)
            self.assertIn("oChatAudit", text)
            self.assertIn("OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON", text)
        self.assertIn("Experimental Examples", plugins_readme)
        self.assertIn("Excluded unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`", architecture)
        self.assertIn("not published by `scripts/check_release_readiness.sh`", status)
        self.assertNotIn("OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON", script)
        for experimental_plugin in ("oPolicyAudit", "oChatLogger", "oChatAudit"):
            with self.subTest(experimental_plugin=experimental_plugin):
                self.assertNotIn(f"{experimental_plugin}.so", script)

    def test_post_rc_observers_stay_out_of_runtime_and_public_abi(self) -> None:
        cmake = read("CMakeLists.txt")
        process_event_hook = read("hooks/ProcessEventHook.cpp")
        public_header = read("include/obelisk/ObeliskApi.h")

        obelisk_target = re.search(
            r"add_library\(obelisk SHARED\n(?P<sources>.*?)\n\)",
            cmake,
            re.S,
        )
        self.assertIsNotNone(obelisk_target)
        obelisk_sources = obelisk_target.group("sources")

        for source in [
            "ue/MissionReflection.cpp",
            "ue/TransferReflection.cpp",
            "hooks/ProcessEventMissionReflection.cpp",
            "hooks/ProcessEventTransferReflection.cpp",
        ]:
            with self.subTest(target="obelisk", source=source):
                self.assertNotIn(source, obelisk_sources)

        for token in [
            "ProcessEventMissionReflection",
            "ProcessEventTransferReflection",
        ]:
            with self.subTest(file="hooks/ProcessEventHook.cpp", token=token):
                self.assertNotIn(token, process_event_hook)

        for token in [
            "ObeliskMission",
            "ObeliskItem",
            "ObeliskTransfer",
            "MISSION",
            "ITEM_EVENTS",
            "TRANSFER",
            "RegisterMission",
            "RegisterItem",
            "RegisterTransfer",
        ]:
            with self.subTest(file="include/obelisk/ObeliskApi.h", token=token):
                self.assertNotIn(token, public_header)

    def test_item_return_runtime_producer_remains_private_and_gated(self) -> None:
        process_event_hook = read("hooks/ProcessEventHook.cpp")
        public_header = read("include/obelisk/ObeliskApi.h")

        for token in [
            "ProcessEventItemReflection",
            "ItemReturnEventDispatcher",
            "OBELISK_ENABLE_ITEM_RETURN_EVENTS",
            "enable-item-return-events",
            "OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256",
            "OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT",
            "OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT",
            "MissingObserverDebugProfile",
            "MissingObserverDebugWindow",
            "IsReflectedItemReturnNameIndex",
            "TryReserveObservationBudget",
            "TryBuildCopiedItemReturnObservationForMatchedAttempt",
        ]:
            with self.subTest(file="hooks/ProcessEventHook.cpp", token=token):
                self.assertIn(token, process_event_hook)

        for token in [
            "ObeliskItem",
            "ITEM_EVENTS",
            "RegisterItem",
            "OBELISK_ENABLE_ITEM_RETURN_EVENTS",
            "ItemReturnEventDispatcher",
        ]:
            with self.subTest(file="include/obelisk/ObeliskApi.h", token=token):
                self.assertNotIn(token, public_header)

    def test_mission_observer_has_no_operational_runtime_gate(self) -> None:
        operational_paths = [
            "loader/Bootstrap.cpp",
            "runtime/RuntimeMarkers.cpp",
            "runtime/RuntimeMarkers.h",
            "scripts/check_obelisk_server_posture.sh",
            "scripts/check_release_readiness.sh",
            "scripts/install_obelisk.sh",
            "scripts/obelisk.py",
        ]

        for path in operational_paths:
            text = read(path)
            for token in [
                "OBELISK_ENABLE_MISSION_REFLECTION",
                "enable-mission-reflection",
                "MissionCopiedBoolObserver",
            ]:
                with self.subTest(file=path, token=token):
                    self.assertNotIn(token, text)

    def test_mission_copied_bool_dispatcher_remains_test_only_if_added(self) -> None:
        cmake = read("CMakeLists.txt")
        forbidden_runtime_sources = [
            "core/MissionCopiedBoolEventDispatcher.cpp",
            "tests/core/MissionCopiedBoolEventDispatcherTests.cpp",
        ]
        obelisk_target = re.search(
            r"add_library\(obelisk SHARED\n(?P<sources>.*?)\n\)",
            cmake,
            re.S,
        )
        self.assertIsNotNone(obelisk_target)
        obelisk_sources = obelisk_target.group("sources") if obelisk_target else ""

        for source in forbidden_runtime_sources:
            with self.subTest(target="obelisk", source=source):
                self.assertNotIn(source, obelisk_sources)

        offenders: list[str] = []
        saw_test_target = False
        for kind, name, body in cmake_targets(cmake):
            source_set = set(
                re.findall(r"\b(?:core|hooks|tests|ue)/[A-Za-z0-9_/]+\.cpp\b", body)
            )
            mentions_mission_copied_bool_dispatcher = (
                "mission_copied_bool_event_dispatcher" in name
                or any("MissionCopiedBoolEventDispatcher" in source for source in source_set)
            )
            if not mentions_mission_copied_bool_dispatcher:
                continue

            is_dispatcher_unit_test_target = (
                kind == "executable"
                and name == "mission_copied_bool_event_dispatcher_tests"
                and "tests/core/MissionCopiedBoolEventDispatcherTests.cpp" in source_set
            )
            is_process_event_unit_test_target = (
                kind == "executable"
                and name == "process_event_mission_reflection_tests"
                and "tests/core/ProcessEventMissionReflectionTests.cpp" in source_set
                and "hooks/ProcessEventMissionReflection.cpp" in source_set
            )
            is_benchmark_test_target = (
                kind == "executable"
                and name == "mission_copied_bool_event_dispatcher_benchmark"
                and "tests/perf/MissionCopiedBoolEventDispatcherBenchmark.cpp" in source_set
            )
            if is_dispatcher_unit_test_target:
                saw_test_target = True
            if (
                not is_dispatcher_unit_test_target
                and not is_process_event_unit_test_target
                and not is_benchmark_test_target
            ):
                offenders.append(f"add_{kind}({name}): {sorted(source_set)}")

        if "tests/core/MissionCopiedBoolEventDispatcherTests.cpp" in cmake:
            self.assertTrue(saw_test_target)
            self.assertIn(
                "add_test(NAME MissionCopiedBoolEventDispatcherTests "
                "COMMAND mission_copied_bool_event_dispatcher_tests)",
                cmake,
            )
        self.assertEqual(offenders, [])

        plugin_manager_paths = [
            "core/PluginManager.cpp",
            "core/PluginManager.h",
        ]
        operational_paths = [
            "loader/Bootstrap.cpp",
            "runtime/RuntimeMarkers.cpp",
            "runtime/RuntimeMarkers.h",
            "packaging/linuxgsm/ObeliskRun.sh",
            "packaging/linuxgsm/ObeliskRunDebug.sh",
            "packaging/linuxgsm/arkserver-obelisk-debug.cfg.example",
            "scripts/check_linuxgsm_wrapper_drift.sh",
            "scripts/check_obelisk_server_posture.sh",
            "scripts/install_obelisk.sh",
            "scripts/obelisk.py",
        ]
        forbidden_tokens = [
            "MissionCopiedBoolEventDispatcher",
            "OBELISK_ENABLE_MISSION_COPIED_BOOL",
            "enable-mission-copied-bool",
            "mission-copied-bool-events",
        ]
        for path in plugin_manager_paths + operational_paths:
            text = read(path)
            for token in forbidden_tokens:
                with self.subTest(file=path, token=token):
                    self.assertNotIn(token, text)

    def test_transfer_observer_has_no_operational_runtime_gate(self) -> None:
        operational_paths = [
            "loader/Bootstrap.cpp",
            "runtime/RuntimeMarkers.cpp",
            "runtime/RuntimeMarkers.h",
            "packaging/linuxgsm/ObeliskRun.sh",
            "packaging/linuxgsm/ObeliskRunDebug.sh",
            "packaging/linuxgsm/arkserver-obelisk-debug.cfg.example",
            "scripts/check_linuxgsm_wrapper_drift.sh",
            "scripts/check_obelisk_server_posture.sh",
            "scripts/install_obelisk.sh",
            "scripts/obelisk.py",
        ]

        for path in operational_paths:
            text = read(path)
            for token in [
                "OBELISK_ENABLE_TRANSFER_REFLECTION",
                "OBELISK_ENABLE_TRANSFER_BACCEPT",
                "enable-transfer-reflection",
                "enable-transfer-baccept",
                "OBELISK_ENABLE_TRANSFER_BACCEPT_EVENTS",
                "enable-transfer-baccept-events",
                "TransferBAcceptObserver",
                "TransferBAcceptEventDispatcher",
                "TransferCopiedBoolEventDispatcher",
                "transfer-baccept-events",
            ]:
                with self.subTest(file=path, token=token):
                    self.assertNotIn(token, text)

    def test_transfer_baccept_dispatcher_remains_test_only_if_added(self) -> None:
        cmake = read("CMakeLists.txt")
        forbidden_runtime_sources = [
            "core/TransferBAcceptEventDispatcher.cpp",
            "core/TransferCopiedBoolEventDispatcher.cpp",
            "tests/core/TransferBAcceptEventDispatcherTests.cpp",
            "tests/core/TransferCopiedBoolEventDispatcherTests.cpp",
        ]
        obelisk_target = re.search(
            r"add_library\(obelisk SHARED\n(?P<sources>.*?)\n\)",
            cmake,
            re.S,
        )
        self.assertIsNotNone(obelisk_target)
        obelisk_sources = obelisk_target.group("sources") if obelisk_target else ""

        for source in forbidden_runtime_sources:
            with self.subTest(target="obelisk", source=source):
                self.assertNotIn(source, obelisk_sources)

        offenders: list[str] = []
        saw_test_target = False
        for kind, name, body in cmake_targets(cmake):
            source_set = set(
                re.findall(r"\b(?:core|hooks|tests|ue)/[A-Za-z0-9_/]+\.cpp\b", body)
            )
            mentions_transfer_baccept_dispatcher = (
                "transfer_baccept_event_dispatcher" in name
                or "transfer_copied_bool_event_dispatcher" in name
                or any("TransferBAcceptEventDispatcher" in source for source in source_set)
                or any("TransferCopiedBoolEventDispatcher" in source for source in source_set)
            )
            if not mentions_transfer_baccept_dispatcher:
                continue

            is_test_target = (
                kind == "executable"
                and name in {
                    "transfer_baccept_event_dispatcher_tests",
                    "transfer_copied_bool_event_dispatcher_tests",
                }
                and (
                    "tests/core/TransferBAcceptEventDispatcherTests.cpp" in source_set
                    or "tests/core/TransferCopiedBoolEventDispatcherTests.cpp" in source_set
                )
            )
            if is_test_target:
                saw_test_target = True
            else:
                offenders.append(f"add_{kind}({name}): {sorted(source_set)}")

        if (
            "tests/core/TransferBAcceptEventDispatcherTests.cpp" in cmake
            or "tests/core/TransferCopiedBoolEventDispatcherTests.cpp" in cmake
        ):
            self.assertTrue(saw_test_target)
        self.assertEqual(offenders, [])

        plugin_manager_paths = [
            "core/PluginManager.cpp",
            "core/PluginManager.h",
        ]
        operational_paths = [
            "loader/Bootstrap.cpp",
            "runtime/RuntimeMarkers.cpp",
            "runtime/RuntimeMarkers.h",
            "packaging/linuxgsm/ObeliskRun.sh",
            "packaging/linuxgsm/ObeliskRunDebug.sh",
            "packaging/linuxgsm/arkserver-obelisk-debug.cfg.example",
            "scripts/check_linuxgsm_wrapper_drift.sh",
            "scripts/check_obelisk_server_posture.sh",
            "scripts/install_obelisk.sh",
            "scripts/obelisk.py",
        ]
        forbidden_tokens = [
            "TransferBAcceptEventDispatcher",
            "TransferCopiedBoolEventDispatcher",
            "OBELISK_ENABLE_TRANSFER_BACCEPT_EVENTS",
            "enable-transfer-baccept-events",
            "transfer-baccept-events",
        ]
        for path in plugin_manager_paths + operational_paths:
            text = read(path)
            for token in forbidden_tokens:
                with self.subTest(file=path, token=token):
                    self.assertNotIn(token, text)

    def test_post_rc_hook_recognizers_remain_test_only_targets(self) -> None:
        cmake = read("CMakeLists.txt")
        post_rc_hook_sources = [
            "hooks/ProcessEventMissionReflection.cpp",
            "hooks/ProcessEventTransferReflection.cpp",
        ]
        offenders: list[str] = []

        for kind, name, body in cmake_targets(cmake):
            source_set = set(re.findall(r"\b(?:hooks|tests|ue)/[A-Za-z0-9_/]+\.cpp\b", body))
            for source in post_rc_hook_sources:
                if source not in source_set:
                    continue
                is_test_target = (
                    kind == "executable"
                    and name.endswith("_tests")
                    and any(path.startswith("tests/") for path in source_set)
                )
                if not is_test_target:
                    offenders.append(f"add_{kind}({name}): {source}")

        self.assertEqual(offenders, [])

    def test_lead_commit_policy_prefers_useful_checkpoints(self) -> None:
        workflow_skill = read("agent-skills/obelisk-github-research-workflow/SKILL.md")
        handoff_skill = read("agent-skills/obelisk-agent-handoff/SKILL.md")
        learning_skill = read("agent-skills/obelisk-continuous-learning/SKILL.md")
        normalized_workflow = normalized(workflow_skill)

        self.assertIn("Batch small internal documentation, skill, handoff, and guardrail cleanups", workflow_skill)
        self.assertIn("Do not commit and push after every routine round", normalized_workflow)
        self.assertIn("useful to contributors", workflow_skill)
        self.assertIn("stable integration point", workflow_skill)
        self.assertIn("Do not draft or send Discord updates unless explicitly approved", workflow_skill)
        self.assertIn("Endpoints are operator secrets", workflow_skill)
        self.assertIn("scripts/send_discord_embed.py --dry-run", workflow_skill)
        self.assertIn("--confirm-approved-send", workflow_skill)
        self.assertIn("--approval-scope community", workflow_skill)
        self.assertIn("name every promoted second-source target set explicitly", normalized_workflow)
        self.assertIn("Runtime-observer summaries are review artifacts only", workflow_skill)
        self.assertIn("Module-level field aggregates are not promotable layouts", normalized_workflow)
        self.assertIn("second-source/static evidence before promotion", normalized_workflow)
        self.assertIn("useful stable\n   checkpoint", handoff_skill)
        self.assertIn("intentionally batched for later lead integration", learning_skill)
        self.assertNotIn("Are changes committed and pushed if stable?", learning_skill)

    def test_release_example_does_not_publish_map_scoped_config(self) -> None:
        obase_docs = read("docs/oBaseEvents.md")
        obase_source = read("plugins/oBaseEvents/oBaseEvents.cpp")
        architecture = read("docs/PLUGIN_ARCHITECTURE.md")

        default_config_start = obase_source.index("constexpr const char* kDefaultConfig")
        default_config_end = obase_source.index(")json\";", default_config_start)
        default_config = obase_source[default_config_start:default_config_end]

        self.assertNotIn("map_allowlist", default_config)
        self.assertNotIn('"map_allowlist"', obase_docs)
        self.assertIn("Do not publish map-scoped config fields", architecture)
        self.assertIn("scripts/install_obelisk_plugin.sh", architecture)
        self.assertNotIn("operator copies the `.so`", architecture)

    def test_background_work_plugins_stay_experimental_until_shutdown_gate(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        obase_docs = read("docs/oBaseEvents.md")

        for text in (release, status, obase_docs):
            self.assertIn("background", text)
            self.assertIn("idempotent shutdown", text)
            self.assertIn("owner-token", text)
            self.assertIn("drain", text)
            self.assertIn("join", text)
            self.assertIn("sockets", text)
            self.assertIn("detached workers", text)

        self.assertIn("does not start background workers", obase_docs)
        self.assertIn("open sockets", obase_docs)
        self.assertIn("long-lived file readers", obase_docs)
        self.assertIn("Plugins with background workers", status)
        self.assertIn("are experimental until they pass a promotion gate", status)

    def test_scalar_candidate_tooling_and_mission_route_stay_out_of_rc_scope(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")
        fixture_readme = read("tests/fixtures/ufunction_snapshots/README.md")

        self.assertIn("mission/transfer APIs", release)
        self.assertIn("Mission target sets such as `mission-compact-intake` are", normalized(release))
        self.assertIn("not part of the default gate", release)
        self.assertIn("scalar-candidate summaries are review aids only, not RC scope", normalized(release))
        self.assertIn("missions", status)
        self.assertIn("remain roadmap items", status)

        self.assertIn("scripts/summarize_reflection_scalar_candidates.py", fixture_readme)
        self.assertIn("--target-set mission-compact-intake", fixture_readme)
        self.assertIn("This helper is a review aid only", fixture_readme)
        self.assertIn(
            "does not replace\nsecond-source readiness reports or promote public SDK callbacks",
            fixture_readme,
        )
        self.assertIn("not a release\nreadiness gate, not RC scope", fixture_readme)
        self.assertIn("`mission-compact-intake` example remains\ncandidate-only", fixture_readme)


if __name__ == "__main__":
    unittest.main()
