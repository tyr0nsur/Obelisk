#!/usr/bin/env python3
"""Guardrails for pre-release versioning language."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class VersioningGuardrailTests(unittest.TestCase):
    def test_public_docs_link_versioning_policy(self) -> None:
        for relative in ("README.md", "docs/STATUS.md", "docs/RELEASE.md"):
            with self.subTest(path=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("docs/VERSIONING.md" if relative == "README.md" else "VERSIONING.md", text)

    def test_versioning_policy_keeps_current_line_dev(self) -> None:
        text = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("0.1.0-dev", text)
        self.assertIn("no `v0.1.0` release is", text)
        self.assertIn("numeric package", text)
        self.assertIn("not a release claim", text)

    def test_cmake_package_version_is_documented_as_compatibility_floor(self) -> None:
        cmake = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        versioning = (REPO_ROOT / "docs/VERSIONING.md").read_text(encoding="utf-8")
        config_template = (REPO_ROOT / "cmake/ObeliskConfig.cmake.in").read_text(encoding="utf-8")
        install_layout_test = (REPO_ROOT / "scripts/test_install_obelisk_layout.sh").read_text(
            encoding="utf-8"
        )

        self.assertRegex(cmake, re.compile(r"project\(Obelisk VERSION 0\.1\.0 LANGUAGES CXX\)"))
        self.assertIn("project(Obelisk VERSION 0.1.0)", versioning)
        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", versioning)
        self.assertIn("find_package(Obelisk 0.1.0 CONFIG REQUIRED)", install_layout_test)
        for token in (
            "Obelisk_DEVELOPMENT_LINE",
            "Obelisk_RELEASE_CHANNEL",
            "Obelisk_API_ABI_VERSION",
            "Obelisk_PLUGIN_METADATA_ABI_VERSION",
            "Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION",
        ):
            with self.subTest(token=token):
                self.assertIn(token, config_template)
                self.assertIn(token, install_layout_test)
                self.assertIn(token, versioning)

    def test_official_examples_use_development_version_until_stable_tag(self) -> None:
        obase = (REPO_ROOT / "plugins/oBaseEvents/oBaseEvents.cpp").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn('out->version = "0.1.0-dev";', obase)
        self.assertNotIn('out->version = "0.1.0";', obase)
        self.assertIn('out->version = "0.1.0-dev";', readme)

    def test_release_doc_does_not_claim_current_stable_release(self) -> None:
        text = (REPO_ROOT / "docs/RELEASE.md").read_text(encoding="utf-8")

        self.assertIn("not ready for a production-stable release", text)
        self.assertRegex(text, re.compile(r"git tag -a v0\.1\.0", re.M))


if __name__ == "__main__":
    unittest.main()
