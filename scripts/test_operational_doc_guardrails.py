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
    "development instances need to be restored quickly",
]
RESEARCH_RUNBOOK_MARKERS = [
    "Historical/superseded",
    "operator-approved",
    "approved-window",
    "approved debug",
    "does not authorize",
]
CURRENT_TURN_EXACT_SCOPE = (
    "Current-turn exact scope is required for live server/log reads, marker/env changes, "
    "Discord sends, and runtime capture"
)


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
        normalized_cli_doc = " ".join(cli_doc.split())

        self.assertIn("read-only", cli_doc)
        self.assertIn("Post-Stable Lifecycle TODO", cli_doc)
        self.assertIn("Hot Reload Boundary", cli_doc)
        self.assertIn("multi-instance inventory and posture inspection", cli_doc)
        self.assertIn(
            "No current command starts, stops, restarts, installs, enables, disables, rolls back, or reloads anything",
            normalized_cli_doc,
        )
        self.assertIn("roadmap boundary, not accepted syntax", cli_doc)
        self.assertIn("plugin restart must\nmean an operational restart", cli_doc)
        self.assertIn('description="Read-only Obelisk operator CLI."', cli_script)
        self.assertIn("Current commands only inspect install, plugin, and per-instance marker state.", cli_script)
        self.assertIn(
            "Lifecycle commands such as start, stop, restart, and plugin restart are",
            cli_script,
        )

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

    def test_release_status_runtime_approval_words_are_current_turn_scoped(self) -> None:
        status_doc = (REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        release_doc = (REPO_ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8")
        combined = " ".join((status_doc + "\n" + release_doc).split())

        for phrase in (
            "current-turn approved adapter-validation window",
            "current-turn operator-approved live-ops brief",
            "current-turn approved debug-server experiment",
            "explicit current-turn operator approval",
            "current-turn specifically approved debug/development run window",
            "current-turn approved debug target",
            "current-turn approved runtime experiment",
            "same current-turn approved validation adapter target",
            "capture whose live collection was separately scoped and approved at the time",
        ):
            with self.subTest(required=phrase):
                self.assertIn(phrase, combined)

        for phrase in (
            "requires a current approved adapter-validation window",
            "approved copied-log plugin-facing delivery validation",
            "an approved observer capture",
            "followed an approved runtime experiment",
            "same approved validation adapter target",
            "after any approved debug-server experiment",
            "use only a specifically approved debug/development run window",
            "on an approved debug target",
        ):
            with self.subTest(forbidden=phrase):
                self.assertNotIn(phrase, combined)

    def test_observer_debug_profile_is_documented_with_window_marker(self) -> None:
        install_doc = (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        status_doc = (REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for text in (install_doc, status_doc, live_ops_skill):
            self.assertIn("OBELISK_WRAPPER_PROFILE=observer-debug", text)
            self.assertIn("allow-observer-debug-window", text)

    def test_live_ops_skill_caps_concurrent_ark_servers(self) -> None:
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized_live_ops_skill = " ".join(live_ops_skill.split())

        self.assertIn(
            "never keep three ARK servers running at the same time",
            normalized_live_ops_skill,
        )
        self.assertIn("Never run more than two ARK servers at once", live_ops_skill)
        self.assertIn("ARK server concurrency at two or fewer", normalized_live_ops_skill)

    def test_live_ops_skill_keeps_workspace_offline_and_cron_scoped(self) -> None:
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized_live_ops_skill = " ".join(live_ops_skill.split())

        self.assertIn("`/servidor/ark/workspace-offline`", live_ops_skill)
        self.assertIn(
            "allowed only when a current-turn operator-approved offline artifact scope explicitly permits under-`/servidor/ark` writes",
            normalized_live_ops_skill,
        )
        self.assertIn("not standing approval to read or write `/servidor/ark`", normalized_live_ops_skill)
        self.assertIn(
            "Unattended cron-style work may collect read-only snapshots only when the operator has explicitly approved that recurring read-only snapshot scope",
            normalized_live_ops_skill,
        )

    def test_live_ops_and_publication_actions_require_current_exact_scope(self) -> None:
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        workflow_skill = (
            REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md"
        ).read_text(encoding="utf-8")
        normalized_live_ops_skill = " ".join(live_ops_skill.split())
        normalized_workflow_skill = " ".join(workflow_skill.split())

        self.assertIn("live log reads/tails", normalized_live_ops_skill)
        self.assertIn("live reads of server state or logs", normalized_live_ops_skill)
        self.assertIn("RCON/admin-console commands", normalized_live_ops_skill)
        self.assertIn(
            "require explicit current-turn operator approval for the exact scoped run",
            normalized_live_ops_skill,
        )
        self.assertIn(CURRENT_TURN_EXACT_SCOPE, normalized_live_ops_skill)
        self.assertIn("passive/read-only observation", normalized_live_ops_skill)
        self.assertIn("beta tester notices are not exceptions", normalized_live_ops_skill)
        self.assertIn(
            "do not authorize markers, env changes, runtime observation, live reads of server state or logs, live log reads/tails, RCON/admin-console actions, starts, stops, restarts, Discord",
            normalized_live_ops_skill,
        )
        self.assertIn("Discord sends, runtime capture", normalized_live_ops_skill)
        for phrase in (
            "Request packs, preflight outputs, accepted planning artifacts, status reports",
            "`progress_normalization_trace`",
            "source_overclaim diagnostics",
            "`source_overclaim_total_flag_count=0`",
            "the latest release-readiness pass",
            "release-readiness passes",
            "the latest validation pass",
            "closed-agent/all-six-agent closure notes",
            "`.codex` cleanup",
            "passive observation",
            "passive summaries/snapshots",
            "passive monitor ticks/output",
            "passive monitors",
            "public reachability",
            "beta tester notices",
            "Discord notice drafts",
            "package-shape installs",
            "package installs",
            "`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`",
            "install/package success",
            "package-shape install success",
            "Plugin Hub planning/readiness",
            "support-tier or package-shape labels",
            "prior approvals",
            "historical live approvals/map names",
            "historical approvals/map names",
            "historical server/map names",
            "support a request or chronology only",
            "current-turn live-op scope",
            "runtime evidence",
            "SDK evidence",
            "approved in-game evidence",
            "SDK/P0 counter progress",
            "live-op authorization",
            "Discord authorization",
            "publication",
            "publication authority",
            "Plugin Hub readiness",
            "public package readiness",
            "support-tier activation",
            "stable SDK readiness",
            "stable SDK claims",
            "stable claims",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_live_ops_skill)
        self.assertIn(
            "update GitHub state unless the lead explicitly delegates that action for one turn",
            normalized_workflow_skill,
        )
        self.assertIn(
            "may push only when publication is explicitly authorized for the current scope",
            normalized_workflow_skill,
        )
        self.assertIn(
            "If current user direction or handoff state says GitHub publication is closed",
            normalized_workflow_skill,
        )

    def test_genesis2_ports_and_public_query_guardrails_are_durable(self) -> None:
        restore_doc = (REPO_ROOT / "docs" / "SERVER_RESTORE.md").read_text(encoding="utf-8")
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        for text in (restore_doc, live_ops_skill):
            normalized_text = " ".join(text.split())
            with self.subTest(document=text[:40]):
                self.assertIn("arkserver3", text)
                self.assertIn("Genesis2", text)
                self.assertIn("7783", text)
                self.assertIn("7784", text)
                self.assertIn("27017", text)
                self.assertIn("27022", text)
                self.assertIn("public Steam/GameDig query from outside the LAN", text)
                self.assertIn("local health does not prove public reachability", normalized_text)
                self.assertIn(
                    "treat missing forwarding for UDP `7783`/`7784`/`27017` as the likely network-scope cause",
                    normalized_text,
                )
                self.assertIn("operator/network evidence", normalized_text)
                self.assertIn(
                    "does not authorize starts, stops, restarts, router/NAT/firewall edits, port forwarding, or any other network changes without current-turn approval",
                    normalized_text,
                )

    def test_live_ops_skill_keeps_observer_and_passive_wait_lessons(self) -> None:
        live_ops_skill = (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized_live_ops_skill = " ".join(live_ops_skill.split())

        self.assertIn("stable wrapper start must fail closed when any observer marker exists", normalized_live_ops_skill)
        self.assertIn("OBELISK_WRAPPER_PROFILE=observer-debug", live_ops_skill)
        self.assertIn("observer env/SHA/budget variables required by the exact observer marker", normalized_live_ops_skill)
        self.assertIn("same instance", live_ops_skill)
        self.assertIn("servername", live_ops_skill)
        self.assertIn("GameUserSettings.ini", live_ops_skill)
        self.assertIn("do not use that label to identify which instance", normalized_live_ops_skill)
        self.assertIn("do not call LinuxGSM `monitor`", live_ops_skill)
        self.assertIn("do not start/stop/restart again just because no player has joined yet", normalized_live_ops_skill)
        self.assertIn(
            "A passive window may wait for organic player logs while offline development continues",
            normalized_live_ops_skill,
        )
        self.assertIn(
            "Candidate-only diagnostic lines must remain non-evidence until the approved checkers accept a copied evidence bundle",
            normalized_live_ops_skill,
        )
        self.assertIn("Passive-wait approval is wait-only", live_ops_skill)
        self.assertIn(
            "passive monitor ticks, player-presence detections, snapshots, and diagnostic summaries do not authorize deployment, marker/env changes, starts/stops/restarts, runtime capture, publication, or readiness claims",
            normalized_live_ops_skill,
        )
        self.assertIn(
            "Any active follow-up must request fresh current-turn exact scope",
            normalized_live_ops_skill,
        )
        self.assertIn(
            "Approval must name the target instance, marker/env gates, start/stop/restart window, rollback plan, evidence paths",
            normalized_live_ops_skill,
        )

    def test_install_doc_guards_player_principal_diagnostic_candidates_as_non_claim(self) -> None:
        install_doc = (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")

        self.assertIn("OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1", install_doc)
        self.assertIn("candidate-only FName target evidence", install_doc)
        self.assertIn("must not read params, log identity, dispatch\ncallbacks", install_doc)
        self.assertIn("promote runtime/public SDK readiness", install_doc)
        self.assertIn("It also exports non-claim package metadata", install_doc)
        self.assertIn("Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED=FALSE", install_doc)
        self.assertIn("Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED=FALSE", install_doc)
        self.assertIn("Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED=FALSE", install_doc)
        self.assertNotIn("Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED=TRUE", install_doc)
        self.assertNotIn("Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED=TRUE", install_doc)
        self.assertNotIn("Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED=TRUE", install_doc)

    def test_install_doc_keeps_plugin_hub_dry_run_and_package_shape_non_authorizing(self) -> None:
        install_doc = (REPO_ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        normalized_install_doc = " ".join(install_doc.split())

        for phrase in (
            "Plugin Hub seed work is parked until the complete SDK blocker chain is resolved",
            "does not validate Plugin Hub scope, ArkApi compatibility, public SDK promotion, or release readiness",
            "run the plugin installer with `--dry-run` as an offline/package-shape check before any current-turn approved copy into a shared `plugins/` root",
            "A dry-run, package-shape install, or copied `.so` remains non-authorizing/non-evidence",
            "does not create Plugin Hub readiness/publication, public SDK promotion, support-tier activation, release readiness, or runtime readiness",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_install_doc)

    def test_june4_fast_path_artifacts_do_not_authorize_server_operations(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        guardrail = " ".join(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0].split()
        )

        for phrase in (
            "continuous-development cadence",
            "closed sub-agent or all-six-agents-closed notes",
            "package-shape/install success",
            "package installs",
            "exact-version `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks",
            "`source_overclaim_total_flag_count=0`",
            "the latest validation pass",
            "six-agent closure notes",
            "`.codex` cleanup",
            "passing local tests",
            "local validation results",
            "closure requests",
            "evidence-closure reports",
            "public reachability",
            "generated repo temp dirs",
            "passive monitor output",
            "passive triplets",
            "status reports",
        ):
            with self.subTest(artifact=phrase):
                self.assertIn(phrase, guardrail)

        self.assertIn("No current-turn exact live-op or Discord scope exists", guardrail)
        self.assertIn("Historical TheIsland, Ragnarok, and Genesis2 material", guardrail)
        self.assertIn("Plugin Hub publication", guardrail)
        self.assertIn("stable v1 wording", guardrail)
        self.assertIn("approved in-game evidence", guardrail)
        self.assertIn("server-operation approval", guardrail)
        self.assertIn("current-turn operator approval", guardrail)
        self.assertIn("accepted runtime evidence", guardrail)
        self.assertRegex(
            guardrail,
            r"do not authorize .*deploy/restart/marker/env changes",
        )
        self.assertIn("they do not move SDK, P0, or v1 counters", guardrail)
        self.assertIn("cleanup/test artifacts only", guardrail)
        self.assertIn("not handoff evidence", guardrail)
        self.assertIn("Compaction invariant for future agents", guardrail)
        self.assertIn("no current-turn server authorization", guardrail)
        self.assertIn("no complete approved in-game evidence exists yet", guardrail)
        self.assertIn("passive diagnostics are diagnostic-only/non-evidence", guardrail)

    def test_player_backed_evidence_notice_is_executable_not_documented_only(self) -> None:
        live_ops_skill = " ".join(
            (REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md")
            .read_text(encoding="utf-8")
            .split()
        )
        fast_path = " ".join(
            (REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md")
            .read_text(encoding="utf-8")
            .split()
        )
        readme = " ".join((REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8").split())

        for label, text in (
            ("live-ops-skill", live_ops_skill),
            ("fast-path", fast_path),
            ("research-readme", readme),
        ):
            with self.subTest(doc=label, invariant="approved notice must be sent"):
                self.assertIn("beta testers Discord", text)
                self.assertIn("dry-run-checked notice", text)
                self.assertRegex(
                    text,
                    r"(?:send .*dry-run-checked notice before|dry-run-checked notice .* sent before)",
                )

        self.assertIn("approved notice path is an action, not passive documentation", live_ops_skill)
        self.assertIn("request the missing notice scope", live_ops_skill)
        self.assertIn("executable required action, not a passive note", fast_path)
        self.assertIn("documented but not sent is incomplete", fast_path)
        self.assertIn("documented but not sent are not enough", readme)

    def test_player_notice_action_is_secret_free_and_non_authorizing(self) -> None:
        fast_path_text = (
            REPO_ROOT / "docs" / "research" / "2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        fast_path = " ".join(fast_path_text.split())
        fast_guardrail = " ".join(
            fast_path_text.split("## Durable Guardrail", 1)[1].split(
                "## 2026-06-04 20:30 Second Supervised Integration", 1
            )[0].split()
        )
        evidence_siblings = " ".join(
            fast_path_text.split("## Required Evidence Siblings", 1)[1].split(
                "## Non-Claims", 1
            )[0].split()
        )
        readme = " ".join((REPO_ROOT / "docs" / "research" / "README.md").read_text(
            encoding="utf-8"
        ).split())

        for label, text in (
            ("fast-path", fast_guardrail),
            ("research-readme", readme),
        ):
            with self.subTest(doc=label, invariant="notice artifacts named"):
                self.assertIn("player_notice_action", text)
                self.assertIn("notice dry-run output", text)
                self.assertIn("sent-notice attestation", text)
            with self.subTest(doc=label, invariant="non-authorizing"):
                self.assertIn("communication", text)
                self.assertRegex(text, r"not .*runtime evidence")
                self.assertIn("live-ops approval", text)
                self.assertIn("SDK", text)
                self.assertIn("public readiness", text)
                self.assertIn("public SDK readiness", text)
                self.assertIn("runtime readiness", text)
                self.assertIn("publication", text)

        for label, text in (
            ("fast-path", fast_path),
            ("research-readme", readme),
            ("evidence-siblings", evidence_siblings),
        ):
            with self.subTest(doc=label, invariant="secret-free attestation"):
                self.assertIn("Discord webhook URLs", text)
                self.assertIn("webhook tokens", text)
                self.assertIn("secret environment assignment", text)
                self.assertIn("secret-bearing dry-run output", text)
                self.assertIn("non-secret notice path/channel", text)

        self.assertIn("The sent-notice attestation must be secret-free metadata only", evidence_siblings)
        self.assertIn("dry-run result, send action, and `player_notice_action` value", evidence_siblings)
        self.assertIn("not runtime evidence", evidence_siblings)
        self.assertIn("not runtime evidence, live-ops approval, SDK progress", evidence_siblings)

    def test_server_restore_runtime_checks_stay_inside_approved_window(self) -> None:
        restore_doc = (REPO_ROOT / "docs" / "SERVER_RESTORE.md").read_text(encoding="utf-8")
        normalized_restore_doc = " ".join(restore_doc.split())

        self.assertIn(
            "before any `/servidor/ark` read/write, stop/start/restart, backup, restore, runtime observation, or live log read",
            normalized_restore_doc,
        )
        self.assertIn(CURRENT_TURN_EXACT_SCOPE, normalized_restore_doc)
        self.assertIn("passive/read-only observations and beta tester notices are not exceptions", normalized_restore_doc)
        self.assertIn(
            "Historical approvals, release-readiness/package-shape/install success, Plugin Hub or support-tier labels, public reachability, passive monitor output, passive monitors, `progress_normalization_trace`, source_overclaim diagnostics, `source_overclaim_total_flag_count=0`, the latest validation pass, six-agent closure notes, `.codex` cleanup, exact-version `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks, package installs, historical live approvals/map names, historical approvals/map names, and beta notices are chronology only",
            normalized_restore_doc,
        )
        for phrase in (
            "`progress_normalization_trace`",
            "source_overclaim diagnostics",
            "`source_overclaim_total_flag_count=0`",
            "the latest validation pass",
            "six-agent closure notes",
            "`.codex` cleanup",
            "`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`",
            "package installs",
            "historical live approvals/map names",
            "historical approvals/map names",
            "passive monitors",
            "Discord authorization",
            "Plugin Hub readiness",
            "support-tier activation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_restore_doc)
        self.assertIn(
            "They do not create live-op authorization, Discord authorization, runtime evidence/readiness, SDK/P0 progress, public SDK readiness, publication authority, Plugin Hub readiness, support-tier activation, package-shape/public package readiness, stable SDK readiness, or stable SDK claims",
            normalized_restore_doc,
        )
        self.assertIn("Historical Ragnarok gameplay config note, not current authorization", restore_doc)
        self.assertIn("Treat every live read of server state or logs as scoped operator work", restore_doc)
        self.assertIn("After starting inside the same approved maintenance window:", restore_doc)
        self.assertIn(
            "These are live runtime/log observations, not offline receipts or copied-log review",
            normalized_restore_doc,
        )
        self.assertIn(
            "Skip them unless the current approval names the target instances, restart window, marker/env gates when applicable, evidence paths, rollback, shutdown/posture expectation, and any notice/send path required for player-facing validation",
            normalized_restore_doc,
        )

    def test_server_restore_motd_normalizer_stays_offline_and_guarded(self) -> None:
        restore_doc = (REPO_ROOT / "docs" / "SERVER_RESTORE.md").read_text(encoding="utf-8")
        normalized_restore_doc = " ".join(restore_doc.split())

        for phrase in (
            "Use `scripts/normalize_ark_motd_ini.py` on an offline staged copy before copying `GameUserSettings.ini` back to `/servidor/ark`",
            'staged_ini="/tmp/ark-GameUserSettings.ini"',
            'python3 scripts/normalize_ark_motd_ini.py "$staged_ini" --check --json',
            'python3 scripts/normalize_ark_motd_ini.py "$staged_ini" --write --json',
            "The normalizer rejects direct or symlink-resolved paths under `/servidor/ark` unless `--allow-protected-path` is passed",
            "That flag is for an already approved maintenance workflow only",
            "it does not authorize live config reads/writes, server starts, restarts, runtime observation, or validation",
            "leaves unrelated INI sections, keys, comments, and blank lines unchanged",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_restore_doc)

    def test_skills_reference_canonical_public_api_header(self) -> None:
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "agent-skills").rglob("SKILL.md")):
            text = path.read_text(encoding="utf-8")
            if "api/ObeliskApi.h" in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(offenders, [])

    def test_gitignore_blocks_local_runtime_and_dump_artifacts(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        required_patterns = {
            "build/",
            "/local/",
            "*.log",
            "*.so",
            "__pycache__/",
            "*.core",
            "core.*",
            "*.dump",
            "*.dmp",
            "dumps/",
        }

        self.assertTrue(required_patterns.issubset(set(gitignore)))


if __name__ == "__main__":
    unittest.main()
