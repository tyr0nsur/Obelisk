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
            "Higher-level gameplay SDK APIs outside `GameplayPolicyEvent`",
            "Gameplay mutation, return overrides, arbitrary UE4 function calls, and public",
            "`CallProcessEvent`-based plugin behavior",
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
            "Operator CLI | Experimental",
            "ReflectionScanner | Experimental",
        ]:
            with self.subTest(file="docs/STATUS.md", item=item):
                self.assertIn(item, status)

        for item in [
            "GNames/GObjects-backed reflection layer",
            "timer SDKs, including chat/command APIs",
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

    def test_release_readiness_is_the_documented_release_gate(self) -> None:
        release = read("docs/RELEASE.md")
        pr_template = read(".github/pull_request_template.md")
        ci = read(".github/workflows/ci.yml")
        script = read("scripts/check_release_readiness.sh")
        build_skill = read("agent-skills/obelisk-build-system/SKILL.md")
        workflow_skill = read("agent-skills/obelisk-github-research-workflow/SKILL.md")

        self.assertIn("scripts/check_release_readiness.sh", release)
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
        self.assertIn("Explicit\n`--ufunction-second-source-target-set` values replace that default", release)
        self.assertIn("--ufunction-second-source-target-set minimal-second-source-intake", release)
        self.assertIn("ScriptStruct promotion, including transfer structs, is not\npart of the default gate", release)
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


if __name__ == "__main__":
    unittest.main()
