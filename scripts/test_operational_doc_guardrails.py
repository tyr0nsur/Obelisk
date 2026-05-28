#!/usr/bin/env python3
"""Guardrails for operational docs and skills that must not invite unsafe live actions."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / ".github",
    REPO_ROOT / "docs",
    REPO_ROOT / "agent-skills",
]
SKIP_DIRS = {
    REPO_ROOT / "docs" / "research",
}
RESEARCH_ROOT = REPO_ROOT / "docs" / "research"
FORBIDDEN_ACTIVE_LINES = [
    "touch /servidor/ark/obelisk/state/",
    "mkdir -p /servidor/ark/obelisk/state/",
    "rm -f /servidor/ark/obelisk/state/",
    "/servidor/ark/arkserver2 restart",
    "./arkserver2 restart",
    "./arkserver restart",
    "./arkserver start",
]
FORBIDDEN_STALE_PHRASES = [
    "current TheIsland debug baseline",
    "Ragnarok is the current development/test harness",
    "Ragnarok is the current debug/development harness",
    "use `arkserver` / Ragnarok as the Obelisk development/test harness",
    "use `arkserver` / Ragnarok as the Obelisk debug/development harness",
    "Active debug target is now `arkserver` / Ragnarok",
    "Current routine debug uses Ragnarok",
    "Current core/runtime captures should\n  use the operator-approved `arkserver` window",
    "Current default validation uses",
    "default read-only validation target",
    "default validation target is",
    "Current Ragnarok posture enables",
    "current protected Ragnarok performance posture",
    "Under the current RAM\n  constraint",
    "`arkserver` / Ragnarok available for Obelisk tests",
    "`arkserver` / Ragnarok is available as the Obelisk debug/development",
    "`arkserver` / Ragnarok is now available as the Obelisk",
    "keep `arkserver2` stopped for RAM",
    "while RAM is constrained",
]
RESEARCH_RUNBOOK_MARKERS = [
    "Historical/superseded",
    "operator-approved",
    "approved-window",
    "approved debug",
    "does not authorize",
]


def candidate_paths() -> list[Path]:
    paths: list[Path] = []
    for root in CHECK_ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md"}:
                continue
            if any(skip in path.parents for skip in SKIP_DIRS):
                continue
            paths.append(path)
    return sorted(paths)


def is_comment_or_example(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//")


class OperationalDocGuardrailTests(unittest.TestCase):
    def test_no_active_marker_or_restart_commands_outside_research_docs(self) -> None:
        offenders: list[str] = []
        for path in candidate_paths():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if is_comment_or_example(line):
                    continue
                for forbidden in FORBIDDEN_ACTIVE_LINES:
                    if forbidden in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {forbidden}")

        self.assertEqual(offenders, [])

    def test_no_stale_operational_baseline_phrases_outside_research_docs(self) -> None:
        offenders: list[str] = []
        for path in candidate_paths():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for forbidden in FORBIDDEN_STALE_PHRASES:
                    if forbidden in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {forbidden}")

        self.assertEqual(offenders, [])

    def test_research_live_commands_are_marked_historical_or_approved_runbook(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESEARCH_ROOT.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            header = "\n".join(text.splitlines()[:20])
            header_lower = header.lower()
            has_marker = any(marker.lower() in header_lower for marker in RESEARCH_RUNBOOK_MARKERS)
            for number, line in enumerate(text.splitlines(), start=1):
                if is_comment_or_example(line):
                    continue
                if any(forbidden in line for forbidden in FORBIDDEN_ACTIVE_LINES) and not has_marker:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}")

        self.assertEqual(offenders, [])

    def test_operator_cli_scope_stays_read_only_before_stable_lifecycle(self) -> None:
        cli_doc = (REPO_ROOT / "docs" / "OPERATOR_CLI.md").read_text(encoding="utf-8")
        cli_script = (REPO_ROOT / "scripts" / "obelisk.py").read_text(encoding="utf-8")

        self.assertIn("read-only", cli_doc)
        self.assertIn("Post-Stable Lifecycle TODO", cli_doc)
        self.assertIn("Hot Reload Boundary", cli_doc)
        self.assertIn("plugin restart must\nmean an operational restart", cli_doc)
        self.assertIn('description="Read-only Obelisk operator CLI."', cli_script)

        for mutable_command in ("start", "stop", "restart", "enable", "disable", "install", "rollback"):
            self.assertNotIn(f'add_parser("{mutable_command}"', cli_script)

    def test_posture_checker_requires_explicit_target(self) -> None:
        script = (REPO_ROOT / "scripts" / "check_obelisk_server_posture.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("--instance is required", script)
        self.assertIn("--map is required when --pid is not provided", script)
        self.assertNotIn('INSTANCE="arkserver"', script)
        self.assertNotIn('MAP="Ragnarok"', script)
        self.assertNotIn("Default: arkserver", script)
        self.assertNotIn("Default: Ragnarok", script)

    def test_active_docs_use_expect_stable_as_canonical_posture_check(self) -> None:
        offenders: list[str] = []
        for path in candidate_paths():
            relative = path.relative_to(REPO_ROOT)
            if relative.parts[0] == "scripts":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if "--expect-stable --forbid-chat-reflection" in line:
                    offenders.append(f"{relative}:{number}")

        self.assertEqual(offenders, [])

    def test_observer_debug_profile_is_documented_with_window_marker(self) -> None:
        install_doc = (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        status_doc = (REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for text in (install_doc, status_doc, live_ops_skill):
            self.assertIn("OBELISK_WRAPPER_PROFILE=observer-debug", text)
            self.assertIn("allow-observer-debug-window", text)

    def test_skills_reference_canonical_public_api_header(self) -> None:
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "agent-skills").rglob("SKILL.md")):
            text = path.read_text(encoding="utf-8")
            if "api/ObeliskApi.h" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
