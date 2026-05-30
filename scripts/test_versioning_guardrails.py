#!/usr/bin/env python3
"""Guardrails for pre-release versioning language."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def cmake_set_value(cmake_text: str, variable: str) -> str:
    match = re.search(rf"set\({re.escape(variable)}\s+\"?(?P<value>[^\")]+)\"?\)", cmake_text)
    if not match:
        raise AssertionError(f"missing CMake variable {variable}")
    return match.group("value")


def header_define_value(header_text: str, macro: str) -> str:
    match = re.search(rf"^#define\s+{re.escape(macro)}\s+(?P<value>\d+)u?$", header_text, re.M)
    if not match:
        raise AssertionError(f"missing public SDK macro {macro}")
    return match.group("value")


class VersioningGuardrailTests(unittest.TestCase):
    def test_public_docs_link_versioning_policy(self) -> None:
        for relative in ("README.md", "docs/STATUS.md", "docs/RELEASE.md"):
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("docs/VERSIONING.md" if relative == "README.md" else "VERSIONING.md", text)

    def test_versioning_policy_keeps_current_line_dev(self) -> None:
        text = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("0.1.0-rc.1", text)
        self.assertIn("no `v0.1.0` release is", text)
        self.assertIn("numeric package", text)
        self.assertIn("not a release claim", text)

    def test_cmake_package_version_is_documented_as_compatibility_floor(self) -> None:
        cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        versioning = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")
        config_template = (REPO_ROOT / "cmake/ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        installed_consumer_cmake = (
            REPO_ROOT / "tests/sdk_installed_consumer/CMakeLists.txt"
        ).read_text(encoding="utf-8")

        self.assertRegex(cmake, re.compile(r"project\(Obelisk VERSION 0\.1\.0 LANGUAGES C CXX\)"))
        self.assertIn("project(Obelisk VERSION 0.1.0)", versioning)
        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", versioning)
        self.assertIn(
            "find_package(Obelisk 0.1.0 CONFIG REQUIRED)",
            installed_consumer_cmake,
        )
        for token in (
            "Obelisk_DEVELOPMENT_LINE",
            "Obelisk_RELEASE_CHANNEL",
            "Obelisk_API_ABI_VERSION",
            "Obelisk_PLUGIN_METADATA_ABI_VERSION",
            "Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION",
        ):
            with self.subTest(token=token):
                self.assertIn(token, config_template)
                self.assertIn(token, installed_consumer_cmake)
                self.assertIn(token, versioning)

    def test_official_examples_use_release_candidate_version_until_stable_tag(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        plugin_sources = [
            REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp",
            REPO_ROOT / "tests/sdk_consumer/MinimalPlugin.cpp",
            REPO_ROOT / "tests/sdk_consumer/MinimalNoShutdownPlugin.cpp",
            REPO_ROOT / "tests/sdk_consumer/CAbiPlugin.c",
            REPO_ROOT / "tests/sdk_installed_consumer/consumer_plugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/no_shutdown_plugin.cpp",
            REPO_ROOT / "tests/sdk_installed_consumer/c_abi_plugin.c",
        ]

        self.assertIn('out->version = "0.1.0-rc.1";', readme)
        for path in plugin_sources:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn('out->version = "0.1.0-rc.1";', text)
                self.assertNotIn('out->version = "0.1.0";', text)

    def test_post_rc_timer_example_does_not_claim_rc_or_stable_version(self) -> None:
        text = (REPO_ROOT / "plugins/oProcessTimer/oProcessTimer.cpp").read_text(encoding="utf-8")

        self.assertIn('out->version = "0.2.0-dev";', text)
        self.assertNotIn('out->version = "0.1.0";', text)
        self.assertNotIn('out->version = "0.1.0-rc.1";', text)

    def test_cmake_exported_abi_versions_match_public_sdk_header(self) -> None:
        cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        config_template = (REPO_ROOT / "cmake/ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        versioning = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("freezes the current append-only `ObeliskApi` ABI v1", versioning)

        for variable, macro, exported in (
            ("OBELISK_API_ABI_VERSION", "OBELISK_API_ABI_VERSION", "Obelisk_API_ABI_VERSION"),
            (
                "OBELISK_PLUGIN_METADATA_ABI_VERSION",
                "OBELISK_PLUGIN_METADATA_ABI_VERSION",
                "Obelisk_PLUGIN_METADATA_ABI_VERSION",
            ),
            (
                "OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION",
                "OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION",
                "Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION",
            ),
        ):
            with self.subTest(variable=variable):
                self.assertEqual(cmake_set_value(cmake, variable), header_define_value(header, macro))
                self.assertIn(f"set({exported} @{variable}@)", config_template)

    def test_release_doc_does_not_claim_current_stable_release(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        self.assertIn("not ready for a production-stable release", text)
        self.assertIn("git tag -a <stable-tag>", text)
        self.assertIn("Only after explicit release-manager approval", text)


if __name__ == "__main__":
    unittest.main()
