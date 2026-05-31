#!/usr/bin/env python3
"""Guardrails for pre-release versioning language."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def cmake_derives_abi_version(cmake_text: str, variable: str) -> bool:
    return (
        re.search(rf"^\s*obelisk_read_public_abi_version\({re.escape(variable)}\)\s*$", cmake_text, re.M)
        is not None
    )


def header_define_value(header_text: str, macro: str) -> str:
    match = re.search(rf"^#define\s+{re.escape(macro)}\s+(?P<value>\d+)u?$", header_text, re.M)
    if not match:
        raise AssertionError(f"missing public SDK macro {macro}")
    return match.group("value")


def public_abi_version_macros(header_text: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^\s*#define\s+(OBELISK_[A-Z0-9_]*ABI_VERSION)\s+([0-9]+)u\s*$",
        header_text,
        re.M,
    )


class VersioningGuardrailTests(unittest.TestCase):
    def test_public_docs_link_versioning_policy(self) -> None:
        for relative in ("README.md", "docs/STATUS.md", "docs/RELEASE.md"):
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("docs/VERSIONING.md" if relative == "README.md" else "VERSIONING.md", text)

    def test_versioning_policy_keeps_current_line_dev(self) -> None:
        text = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("0.1.0-rc.2", text)
        self.assertIn("0.1.0-dev", text)
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
        install_doc = (REPO_ROOT / "docs/INSTALL.md").read_text(encoding="utf-8")

        self.assertRegex(cmake, re.compile(r"project\(Obelisk VERSION 0\.1\.0 LANGUAGES C CXX\)"))
        self.assertIn('set(OBELISK_DEVELOPMENT_LINE "0.1.0-dev")', cmake)
        self.assertIn('set(OBELISK_RELEASE_CHANNEL "dev")', cmake)
        self.assertIn("project(Obelisk VERSION 0.1.0)", versioning)
        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", versioning)
        self.assertIn('Obelisk_DEVELOPMENT_LINE STREQUAL "0.1.0-dev"', installed_consumer_cmake)
        self.assertIn('Obelisk_RELEASE_CHANNEL STREQUAL "dev"', installed_consumer_cmake)
        self.assertIn(
            "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)",
            installed_consumer_cmake,
        )
        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", install_doc)
        self.assertIn("numeric package version is the SDK compatibility floor", install_doc)
        self.assertIn("not a claim that a stable `v0.1.0` tag exists", install_doc)
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

        self.assertIn('out->version = "0.1.0-rc.2";', readme)
        for path in plugin_sources:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn('out->version = "0.1.0-rc.2";', text)
                self.assertNotIn('out->version = "0.1.0";', text)

    def test_timer_example_claims_first_stable_core_version_only(self) -> None:
        text = (REPO_ROOT / "plugins/oProcessTimer/oProcessTimer.cpp").read_text(encoding="utf-8")

        self.assertIn('out->version = "0.1.0";', text)
        self.assertNotIn('out->version = "0.2.0-dev";', text)
        self.assertNotIn('out->version = "0.1.0-rc.2";', text)

    def test_cmake_exported_abi_versions_match_public_sdk_header(self) -> None:
        cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        header = (REPO_ROOT / "include/obelisk/ObeliskApi.h").read_text(encoding="utf-8")
        config_template = (REPO_ROOT / "cmake/ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        versioning = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("freezes the current append-only `ObeliskApi` ABI v1", versioning)

        header_abi_macros = public_abi_version_macros(header)
        self.assertGreater(len(header_abi_macros), 0)

        for macro, _version in header_abi_macros:
            exported = macro.replace("OBELISK_", "Obelisk_", 1)
            with self.subTest(variable=macro):
                self.assertTrue(cmake_derives_abi_version(cmake, macro))
                self.assertIsNotNone(header_define_value(header, macro))
                self.assertIn(f"set({exported} @{macro}@)", config_template)
                self.assertIn(exported, versioning)

    def test_release_doc_does_not_claim_current_stable_release(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        self.assertIn("not ready for a production-stable release", text)
        self.assertIn("git tag -a <stable-tag>", text)
        self.assertIn("Only after explicit release-manager approval", text)


if __name__ == "__main__":
    unittest.main()
