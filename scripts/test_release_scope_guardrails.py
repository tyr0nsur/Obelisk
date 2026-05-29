#!/usr/bin/env python3
"""Guardrails that keep the first stable release scope coherent."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class ReleaseScopeGuardrailTests(unittest.TestCase):
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
            "Filtered, non-mutating `ProcessEvent` callback infrastructure as the stable runtime",
            "Target-specific gameplay/module surfaces remain experimental",
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
        ]
        required_changelog_items = [
            "Linux `LD_PRELOAD` runtime bootstrap",
            "Absolute x86_64 `UObject::ProcessEvent` hook",
            "C plugin ABI",
            "Public plugin C ABI v1 is the intended first-stable compatibility contract",
            "Central install layout",
            "LinuxGSM wrapper templates",
            "`oBaseEvents` as the first official plugin example",
            "Runtime default-deny gates for global ProcessEvent callbacks",
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
            "timer SDKs, including richer chat APIs and command APIs beyond `ChatMessageEvent`",
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
            "Filtered, non-mutating `ProcessEvent` callback infrastructure as the stable runtime",
            "Target-specific gameplay/module surfaces remain experimental",
            "Gameplay mutation, return overrides, arbitrary UE4 function calls, and public",
            "`CallProcessEvent`-based plugin behavior",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)

        for item in [
            "Current safe interaction shape",
            "observe a narrow `ProcessEvent` target by exact `FName` index",
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

    def test_chat_message_event_release_docs_keep_rc_boundary_explicit(self) -> None:
        release = read("docs/RELEASE.md")
        status = read("docs/STATUS.md")

        required_release_items = [
            "`ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI",
            "copied UTF-8 message\n  text, send mode, copied-payload flag, and process-local sequence only",
            "not a command SDK,\n  chat send/moderation API, sender identity API, UE lookup path, mutation surface, or\n  return-override authority",
            "accepted `chat-message-intake` second-source comparison",
            "The runtime producer\nexists behind observer-debug gates, SHA, marker, and positive dispatch budget",
            "isolated\n`arkserver2` delivery validation is still required",
        ]
        required_status_items = [
            "ChatMessageEvent | v0.1-rc SDK ABI surface",
            "Minimal copied UTF-8 chat notification contract for plugins that parse text locally",
            "sender/player identity, resource identity, raw `FString`, raw params, FName/GObjects indices, UE pointers, chat send/moderation/blocking, command routing, mutation, and return overrides remain blocked",
            "The target layout now has accepted second-source evidence",
            "isolated debug-server delivery validation is still pending",
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
        for item in forbidden_claims:
            for path, text in (("docs/RELEASE.md", release), ("docs/STATUS.md", status)):
                with self.subTest(file=path, item=item):
                    self.assertNotIn(item, text)

    def test_release_readiness_is_the_documented_release_gate(self) -> None:
        release = read("docs/RELEASE.md")
        pr_template = read(".github/pull_request_template.md")
        ci = read(".github/workflows/ci.yml")
        script = read("scripts/check_release_readiness.sh")
        build_skill = read("agent-skills/obelisk-build-system/SKILL.md")
        workflow_skill = read("agent-skills/obelisk-github-research-workflow/SKILL.md")

        self.assertIn("scripts/check_release_readiness.sh", release)
        self.assertIn("`oPolicyAudit`", release)
        self.assertIn("Verify the ABI v1 freeze artifacts before tagging", release)
        self.assertIn("Obelisk freezes the\n   current append-only `ObeliskApi` ABI v1", release)
        self.assertIn("Any ABI v2 must use an explicit migration plan", release)
        self.assertIn("installed SDK consumer validation, and the `oBaseEvents` release\n   example", release)
        self.assertIn("first-stable plugin scope excludes background-work plugins", release)
        self.assertIn("idempotent shutdown through `ObeliskPlugin_Shutdown`", release)
        self.assertIn("owner-token callback handles unregistered before unload", release)
        self.assertIn("threads\n   joined, sockets/files closed", release)
        self.assertIn("scripts/check_release_readiness.sh", pr_template)
        self.assertIn("scripts/check_release_readiness.sh", ci)
        self.assertIn("scripts/check_release_readiness.sh", build_skill)
        self.assertIn("scripts/check_release_readiness.sh", workflow_skill)
        self.assertIn("canonical local and CI gate", build_skill)
        self.assertIn("single core-first release gate", workflow_skill)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", pr_template)
        self.assertIn("observational only", pr_template)
        self.assertIn("not release readiness or second-source promotion evidence", pr_template)
        self.assertIn("Core-first release readiness", ci)
        self.assertIn("first-stable core release gate", ci)
        self.assertNotIn("scripts/install_obelisk.sh --dry-run /tmp/obelisk-ci-install", ci)
        self.assertNotIn("scripts/test_install_obelisk_layout.sh /tmp/obelisk-ci-layout", ci)
        self.assertIn("Reflection base readiness", ci)
        self.assertIn("--fail-on-base-readiness-gaps", ci)
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
        self.assertIn("gameplay/module second-source promotion gate was not run", script)
        self.assertIn("scripts/install_obelisk_plugin.sh --dry-run", script)
        self.assertIn("${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so", script)
        self.assertNotIn("oPolicyAudit.so", script)
        self.assertIn("--require-second-source-readiness", release)
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
        self.assertIn("default second-source gate is intentionally scoped to the core-first UFunction intake", release)
        self.assertIn("`minimal-second-source-intake`", release)
        self.assertIn("Mission target sets such as `mission-compact-intake` are", release)
        self.assertIn("not part of the default gate", release)
        self.assertIn("scalar-candidate summaries are review aids only, not RC\nscope", release)
        self.assertIn("Explicit\n`--ufunction-second-source-target-set` values replace that default", release)
        self.assertIn("--ufunction-second-source-target-set minimal-second-source-intake", release)
        self.assertIn("ScriptStruct promotion, including transfer structs, is not part of the default gate", release)
        self.assertIn("ScriptStruct promotion requires explicit opt-in", script)
        self.assertIn("--scriptstruct-second-source-root requires at least one --scriptstruct-second-source-target-set", script)
        self.assertNotIn('SCRIPTSTRUCT_SECOND_SOURCE_TARGET_SETS=("transfer-scriptstruct")', script)
        self.assertIn("name every promoted target set", pr_template)
        self.assertIn(
            "pass `--scriptstruct-second-source-root` only when a ScriptStruct target set is explicitly named",
            pr_template,
        )
        self.assertIn("--second-source-report-dir", release)
        self.assertIn("--second-source-report-dir", pr_template)
        self.assertIn("--second-source-report-dir", script)
        self.assertIn("--fail-on-readiness-gaps", script)
        self.assertIn("gate_mode=second_source_promotion", release)
        self.assertIn("promotion_gate.ready=true", release)
        self.assertIn("gate_mode=informational_gap_report", release)
        self.assertIn("not_second_source_promotion_gate", release)
        self.assertIn("gate_mode=base_fixture_readiness", release)
        self.assertIn("required positional install roots even when `OBELISK_ROOT` is set", release)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", release)
        self.assertIn("not a release gate", release)
        self.assertIn("not\nsecond-source promotion evidence", release)
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
                r"endif\(\)",
                re.M,
            ),
        )
        for text in (architecture, status, release, plugins_readme):
            self.assertIn("oPolicyAudit", text)
            self.assertIn("oChatLogger", text)
            self.assertIn("OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON", text)
        self.assertIn("Experimental Examples", plugins_readme)
        self.assertIn("Excluded unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`", architecture)
        self.assertIn("not published by `scripts/check_release_readiness.sh`", status)
        self.assertNotIn("OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON", script)
        self.assertNotIn("oPolicyAudit.so", script)

    def test_lead_commit_policy_prefers_useful_checkpoints(self) -> None:
        workflow_skill = read("agent-skills/obelisk-github-research-workflow/SKILL.md")
        handoff_skill = read("agent-skills/obelisk-agent-handoff/SKILL.md")
        learning_skill = read("agent-skills/obelisk-continuous-learning/SKILL.md")

        self.assertIn("Batch small internal documentation, skill, handoff, and guardrail cleanups", workflow_skill)
        self.assertIn("Do not commit\n  and push after every routine round", workflow_skill)
        self.assertIn("useful to contributors", workflow_skill)
        self.assertIn("stable integration point", workflow_skill)
        self.assertIn("Community/Discord updates are lead-only", workflow_skill)
        self.assertIn("explicitly delegates that scope", workflow_skill)
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
        self.assertIn("Mission target sets such as `mission-compact-intake` are", release)
        self.assertIn("not part of the default gate", release)
        self.assertIn("scalar-candidate summaries are review aids only, not RC\nscope", release)
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
