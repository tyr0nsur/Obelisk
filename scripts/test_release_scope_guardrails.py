#!/usr/bin/env python3
"""Guardrails that keep the first stable release scope coherent."""

from __future__ import annotations

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
            "C plugin ABI",
            "Central install script and LinuxGSM wrappers",
            "`oBaseEvents`",
            "`OBELISK_INSTANCE_ID` logs and state markers",
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
            "Central install layout",
            "LinuxGSM wrapper templates",
            "`oBaseEvents` as the first official plugin example",
            "Multi-instance shared-root posture",
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
            "Higher-level gameplay SDK APIs",
            "Production HTTP plugins",
        ]:
            with self.subTest(file="docs/RELEASE.md", item=item):
                self.assertIn(item, release)

        for item in [
            "GNames/FNamePool resolution | Not ready",
            "GObjects/GUObjectArray enumeration | Not ready",
            "General reflected UFunction parameter decoding | Not ready",
            "Higher-level SDK APIs | Not ready",
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

    def test_release_readiness_is_the_documented_release_gate(self) -> None:
        release = read("docs/RELEASE.md")
        pr_template = read(".github/pull_request_template.md")
        ci = read(".github/workflows/ci.yml")
        script = read("scripts/check_release_readiness.sh")

        self.assertIn("scripts/check_release_readiness.sh", release)
        self.assertIn("scripts/check_release_readiness.sh", pr_template)
        self.assertIn("scripts/check_release_readiness.sh", ci)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", pr_template)
        self.assertIn("observational only", pr_template)
        self.assertIn("not release readiness or second-source promotion evidence", pr_template)
        self.assertIn("Core-first release readiness", ci)
        self.assertIn("first-stable core release gate", ci)
        self.assertIn("--require-second-source-readiness", ci)
        self.assertIn("Release readiness requires a clean worktree", script)
        self.assertIn("first-stable core release gate", script)
        self.assertIn("gameplay/module second-source promotion gate was not run", script)
        self.assertIn("scripts/install_obelisk_plugin.sh --dry-run", script)
        self.assertIn("--require-second-source-readiness", release)
        self.assertIn("--require-second-source-readiness", pr_template)
        self.assertIn("--require-second-source-readiness", script)
        self.assertIn("--fail-on-readiness-gaps", script)
        self.assertIn("analyze_runtime_observer_log.py --fail-on-quality-blockers", release)
        self.assertIn("not a release gate", release)
        self.assertIn("not\nsecond-source promotion evidence", release)
        self.assertIn("readiness_gate=none", release)
        self.assertIn("runtime_observer_observational_only", release)
        self.assertNotIn("--map Ragnarok --instance arkserver", release)
        self.assertIn("--map <map> --instance <instance-id>", release)

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


if __name__ == "__main__":
    unittest.main()
