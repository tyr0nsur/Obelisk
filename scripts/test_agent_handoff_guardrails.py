#!/usr/bin/env python3
"""Guardrails for Obelisk agent handoff files."""

from __future__ import annotations

import unittest
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO_ROOT / "docs" / "agent-handoff"
CURRENT = HANDOFF_DIR / "CURRENT.md"
README = HANDOFF_DIR / "README.md"
COMPACT_CONTEXT = HANDOFF_DIR / "COMPACT_CONTEXT.md"
GITHUB_WORKFLOW_SKILL = REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md"
AGENT_HANDOFF_SKILL = REPO_ROOT / "agent-skills" / "obelisk-agent-handoff" / "SKILL.md"
LIVE_OPS_SKILL = REPO_ROOT / "agent-skills" / "obelisk-live-ops" / "SKILL.md"
REVERSING_RESEARCH_SKILL = REPO_ROOT / "agent-skills" / "obelisk-reversing-research" / "SKILL.md"
MAX_CURRENT_LINES = 240
MAX_SKILL_LINES = 260
SCOPED_GUARDRAIL_FILES = [
    CURRENT,
    COMPACT_CONTEXT,
    REPO_ROOT / "docs" / "research" / "2026-05-30-mission-copied-bool-observer-plan.md",
    REPO_ROOT / "docs" / "research" / "2026-06-04-arkserver2-runtime-sdk-fast-path.md",
    REPO_ROOT / "docs" / "research" / "README.md",
    REPO_ROOT / "scripts" / "test_release_scope_guardrails.py",
    REPO_ROOT / "scripts" / "test_agent_handoff_guardrails.py",
    REPO_ROOT / "scripts" / "test_send_discord_embed.py",
]


def normalized(text: str) -> str:
    return " ".join(text.split())


EXACT_OR_STANDING_SCOPE = (
    "Current-turn exact scope is required for live server/log reads, marker/env changes, "
    "Discord sends, and runtime capture"
)


class AgentHandoffGuardrailsTests(unittest.TestCase):
    def test_current_stays_concise_routing_table(self) -> None:
        text = CURRENT.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        self.assertLessEqual(
            line_count,
            MAX_CURRENT_LINES,
            "CURRENT.md should remain a concise routing table; move detail to docs/research/ "
            "or docs/agent-handoff/HISTORY-*.md",
        )
        self.assertIn("active routing table", text)
        self.assertIn("Priority Next Steps", text)
        self.assertIn("Agent Protocol", text)
        self.assertNotIn(
            "latest pushed checkpoint",
            text,
            "CURRENT.md should not duplicate the moving HEAD hash; use git log instead",
        )
        try:
            priority = text.split("## Priority Next Steps", 1)[1].split("## Agent Protocol", 1)[0]
        except IndexError:
            self.fail("CURRENT.md must include Priority Next Steps before Agent Protocol")
        priority_items = [line.strip() for line in priority.splitlines() if line.startswith("- ")]
        self.assertEqual(
            len(priority_items),
            len(set(priority_items)),
            "Priority Next Steps should not contain duplicate top-level routing items",
        )

    def test_handoff_history_files_are_archives(self) -> None:
        history_files = sorted(HANDOFF_DIR.glob("HISTORY-*.md"))
        self.assertTrue(history_files, "expected at least one archived handoff history file")
        for path in history_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("preserves the full `docs/agent-handoff/CURRENT.md` content", text)
            self.assertIn("before", text)

    def test_docs_point_agents_to_current_not_history(self) -> None:
        readme = README.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        self.assertIn("Do not use history files as the active source of truth", readme)
        self.assertIn("Current routing table only", compact)

    def test_direct_subagent_handoff_keeps_lead_integration_boundary(self) -> None:
        readme = README.read_text(encoding="utf-8")
        current = CURRENT.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        workflow_skill = GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8")
        handoff_skill = AGENT_HANDOFF_SKILL.read_text(encoding="utf-8")

        retired_terms = (
            "EXTERNAL" + "_AGENT" + "_QUEUE",
            "agent" + "_task" + "_queue",
            ".obelisk" + "-agent" + "-queue",
            "external " + "queue",
            "external " + "coordinator",
            "stale" + "-after",
        )
        for text in (readme, current, compact, workflow_skill):
            for term in retired_terms:
                self.assertNotIn(term, text)

        for text in (current, compact):
            self.assertIn("scoped", text)
            self.assertIn("safety", text)
            self.assertIn("baseline", text)
            self.assertIn("allowed paths", text)
            self.assertIn("required skills", text)
            self.assertIn("expert role", text)
            self.assertIn("expected decision", text)
            self.assertIn("sub-agent", text)
        for text in (current, compact):
            lowered = text.lower()
            self.assertIn("only the skills", lowered)
            self.assertIn("sub-agents", lowered)
            self.assertIn("expert", lowered)
        self.assertIn("GitHub work may be delegated only for an evidenced, stable milestone", current)
        self.assertNotIn("forbids GitHub pushes", current)
        self.assertNotIn("Do not push unless the operator reopens pushing", current)
        self.assertIn("Standing operator authorization, 2026-06-06 local", " ".join(current.split()))
        self.assertIn("persistent authority to run any runtime tests", " ".join(current.split()))
        self.assertIn("recorded standing launch authority applies", " ".join(current.split()))
        self.assertIn("Technical progress alone is not runtime evidence or readiness", " ".join(current.split()))
        self.assertIn("Standing Live-Ops Authorization", compact)
        self.assertIn("until explicitly revoked", compact)
        self.assertIn("Memory-loss/compaction recovery flow", current)
        self.assertIn(
            "Treat memory loss, context compaction, reboot, or a resumed Codex session as a recovery event",
            normalized(compact),
        )
        self.assertIn("not as revocation", compact)
        self.assertIn("do not convert that authority into runtime evidence", normalized(compact))
        self.assertIn("server-safety decisions", current)
        self.assertIn("all six spawned agents were closed", current)
        self.assertIn("no active sub-agent is left open", normalized(compact))
        self.assertIn("delegated results become active routing only after lead integration", normalized(current))
        self.assertRegex(normalized(compact), r"six-agent round")
        self.assertIn("all six spawned agents were closed", normalized(compact))
        self.assertIn("This round did not touch live servers", compact)
        normalized_workflow = normalized(workflow_skill)
        self.assertRegex(normalized_workflow, r"Follow explicit .* routing only")
        for text in (current, compact, workflow_skill):
            self.assertNotIn("two on Obelisk engineering/audit/development", text)
            self.assertNotIn("four on research/knowledge/reversing/dump", text)
            self.assertNotIn("six-agent split", text)
            self.assertNotIn("local critical-path task", text)
            self.assertNotIn("parallel sub-agents", text)
            self.assertIsNone(re.search(r"\b\d+\s+tests passed\b", text))

        self.assertRegex(normalized_workflow, r"(documented|recorded) next actions")
        self.assertNotIn("queued next tasks", workflow_skill)
        self.assertIn(
            "record the expert role/scope, owned paths, result, validation/risk, and closed-or-polling status",
            normalized_workflow,
        )
        self.assertIn(
            "Record each delegated agent's scope, result, validation, remaining risk, and closure status",
            normalized(handoff_skill),
        )
        self.assertIn("close completed or obsolete standby agents", normalized(handoff_skill))
        self.assertIn("Treat memory loss, reboot, or context compaction as a recovery event", handoff_skill)
        self.assertIn(
            "not as revocation of any standing authority recorded in both files",
            normalized(handoff_skill),
        )

    def test_discord_policy_stays_embed_helper_and_approval_scoped(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        workflow_skill = GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8")

        for path, text in (
            ("docs/agent-handoff/CURRENT.md", current),
            ("agent-skills/obelisk-github-research-workflow/SKILL.md", workflow_skill),
        ):
            with self.subTest(file=path, item="webhook variables only"):
                self.assertIn("OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL", text)
                self.assertIn("OBELISK_BETA_TEST_WEBHOOK_URL", text)
                self.assertNotIn("discord.com/" + "api/webhooks", text)
                self.assertNotIn("discordapp.com/" + "api/webhooks", text)
            with self.subTest(file=path, item="approval scope"):
                self.assertIn("approved", text)
                self.assertIn("public", text)
                self.assertIn("modder-facing", text)
                self.assertIn("milestones", text)
                self.assertIn("beta-test", text)
            with self.subTest(file=path, item="embed shape"):
                lowered = text.lower()
                self.assertIn("embed", lowered)
                self.assertIn("routine validation", lowered)
                self.assertIn("speculative", lowered)

        normalized_workflow = normalized(workflow_skill)
        self.assertIn("Do not draft or send Discord updates unless explicitly approved", workflow_skill)
        self.assertIn("Do not draft or send community announcements unless explicitly delegated", workflow_skill)
        self.assertIn("Always dry-run before any approved send", current)
        self.assertIn("prefer the guarded helper instead of hand-written", workflow_skill)
        self.assertIn("python3 scripts/send_discord_embed.py --channel community", workflow_skill)
        self.assertIn("scripts/discord_beta_bridge.py --send-beta-notice", workflow_skill)
        self.assertIn("OBELISK_BETA_TEST_WEBHOOK_URL` is deprecated for real", workflow_skill)
        self.assertIn("--confirm-approved-send", workflow_skill)
        self.assertIn("--approval-scope community", workflow_skill)
        self.assertNotIn("--approval-scope beta-test", workflow_skill)
        self.assertRegex(normalized_workflow, r"send_discord_embed\.py --channel community.*dry-run")
        self.assertRegex(normalized_workflow, r"discord_beta_bridge\.py --send-beta-notice.*dry-run")
        self.assertRegex(normalized_workflow, r"approved .* current turn|current-turn approval")

    def test_scoped_guardrail_files_do_not_store_secret_webhook_urls(self) -> None:
        forbidden_literals = [
            "discord.com/" + "api/webhooks",
            "discordapp.com/" + "api/webhooks",
            "https://" + "discord.com",
            "https://" + "discordapp.com",
            "OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL" + "=",
            "OBELISK_BETA_TEST_WEBHOOK_URL" + "=",
        ]

        for path in SCOPED_GUARDRAIL_FILES:
            text = path.read_text(encoding="utf-8")
            for literal in forbidden_literals:
                with self.subTest(file=str(path.relative_to(REPO_ROOT)), literal=literal):
                    self.assertNotIn(literal, text)

    def test_scoped_guardrail_files_do_not_authorize_real_servers_or_discord(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        mission_plan = (REPO_ROOT / "docs" / "research" / "2026-05-30-mission-copied-bool-observer-plan.md").read_text(
            encoding="utf-8"
        )
        send_discord_tests = (REPO_ROOT / "scripts" / "test_send_discord_embed.py").read_text(encoding="utf-8")

        self.assertIn("Standing operator authorization, 2026-06-06 local", " ".join(current.split()))
        self.assertIn("persistent authority to run any runtime tests", " ".join(current.split()))
        self.assertIn("never keep three ark servers running", " ".join(current.split()).lower())
        self.assertIn("no `/servidor/ark` writes", " ".join(current.split()))
        self.assertIn("write under protected live paths", " ".join(current.split()))
        self.assertIn("no Discord for internal rounds or agent status", " ".join(current.split()))
        self.assertIn("Standing Live-Ops Authorization", compact)
        self.assertIn("until explicitly revoked", compact)
        self.assertIn("Player-backed runtime evidence should use the scoped runtime window", compact)
        self.assertIn("dry-run-checked beta tester notice path before activation", compact)
        self.assertIn("No run is approved by this note", mission_plan)
        self.assertIn("This plan is not approval to add or enable gates", mission_plan)
        self.assertNotIn("arkserver " + "ventana aprobada", send_discord_tests)

    def test_preflight_and_planning_acceptance_are_not_runtime_approval_or_readiness(self) -> None:
        files = {
            "CURRENT.md": normalized(CURRENT.read_text(encoding="utf-8")),
            "COMPACT_CONTEXT.md": normalized(COMPACT_CONTEXT.read_text(encoding="utf-8")),
            "obelisk-github-research-workflow": normalized(GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8")),
            "obelisk-live-ops": normalized(LIVE_OPS_SKILL.read_text(encoding="utf-8")),
        }
        for label, text in files.items():
            with self.subTest(file=label):
                self.assertRegex(text.lower(), r"request[- ]?pack|preflight")
                self.assertRegex(text.lower(), r"not .*approval|do not authorize|does not authorize|not runtime approval")
                self.assertIn("public SDK readiness", text)
                self.assertIn("runtime readiness", text)

        compact = files["COMPACT_CONTEXT.md"]
        workflow = files["obelisk-github-research-workflow"]
        for text in (compact, workflow):
            self.assertIn("planning_layout_gate.ready=true", text)
            self.assertIn("reply/send-chat ABI", text)
            self.assertIn("command router", text)

    def test_handoff_skill_keeps_authorization_and_evidence_status_separate(self) -> None:
        skill = normalized(AGENT_HANDOFF_SKILL.read_text(encoding="utf-8"))

        for phrase in (
            "Authorization and evidence status are separate facts",
            "request packs",
                "`progress_normalization_trace`",
                "source_overclaim diagnostics",
                "`source_overclaim_total_flag_count=0`",
                "status reports",
                "release-readiness passes",
                "the latest validation pass",
                "closed sub-agent/all-six-agents-closed notes",
                "`.codex` cleanup",
                "passive observation",
                "passive player summaries",
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
                "support-tier or package-shape labels",
                "Plugin Hub planning",
                "prior approvals",
                "historical live approvals/map names",
                "historical approvals/map names",
            "historical server names such as TheIsland, Ragnarok, and Genesis2",
            "non-authorizing/non-evidence",
            "current-turn exact approval or accepted checker evidence",
            "durable standing launch authorization recorded in both",
            "that standing authorization remains transferable until revoked",
            "live/log/process/posture/marker/env/start/stop/restart/beta-notice/evidence/debug",
            "current-turn live-op scope",
            "runtime evidence",
            "SDK evidence",
            "approved in-game evidence",
                "SDK/P0 progress",
                "live-op authorization",
                "Discord authorization",
                "publication",
                "public readiness",
                "package-shape/public package readiness",
                "stable claims",
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, skill)

    def test_standing_authorization_compaction_keeps_strict_status_blocked(self) -> None:
        current_text = CURRENT.read_text(encoding="utf-8")
        compact_text = COMPACT_CONTEXT.read_text(encoding="utf-8")
        handoff_skill = normalized(AGENT_HANDOFF_SKILL.read_text(encoding="utf-8"))

        current_active = normalized(
            current_text.split("## Active Objective", 1)[1].split("## Live Authority And Safety", 1)[0]
        )
        current_authority = normalized(
            current_text.split("## Live Authority And Safety", 1)[1].split("## Latest Development State", 1)[0]
        )
        compact_resume = normalized(
            compact_text.split("## Resume Protocol", 1)[1].split("## Standing Live-Ops Authorization", 1)[0]
        )
        compact_standing = normalized(
            compact_text.split("## Standing Live-Ops Authorization", 1)[1].split(
                "## Latest Local Checkpoint",
                1,
            )[0]
        )
        compact_stable = normalized(
            compact_text.split("## Stable Baseline", 1)[1].split("## Canonical References", 1)[0]
        )

        for phrase in (
            "Strict current accounting is fail-closed",
            "route `approved_runtime_evidence_missing`",
            "next `approved_runtime_principal_lifecycle_evidence_bundle`",
            "after-runtime blocker `identity_public_contract_gate_missing`",
            "SDK `0/12`, P0 `0/4`",
            "runtime readiness false",
        ):
            with self.subTest(section="current active objective", phrase=phrase):
                self.assertIn(phrase, current_active)

        for phrase in (
            "standing authority is preserved as authorization only, not evidence or readiness",
            "Technical progress alone is not runtime evidence or readiness",
            "Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness",
            "do not authorize runtime work, runtime capture, public SDK readiness, or runtime readiness",
        ):
            with self.subTest(section="current live authority", phrase=phrase):
                self.assertIn(phrase, current_authority)

        for phrase in (
            "Reconfirm strict status with `scripts/report_obelisk_sdk_status.py --compact`",
            "preserve the standing launch authority and safety limits",
            "do not convert that authority into runtime evidence, SDK/P0 progress, readiness",
        ):
            with self.subTest(section="compact resume", phrase=phrase):
                self.assertIn(phrase, compact_resume)

        for phrase in (
            "applies across all future turns and compactions until explicitly revoked",
            "Player-backed runtime evidence should use the scoped runtime window",
            "do not publish, tag, push, activate Plugin Hub, or make SDK/stable/public-readiness claims",
        ):
            with self.subTest(section="compact standing authorization", phrase=phrase):
                self.assertIn(phrase, compact_standing)

        for phrase in (
            "default no-runtime route is now blocked at `approved_runtime_evidence_missing`",
            "keeps all public/runtime/promotion/SDK readiness flags false",
            "With accepted approved runtime evidence it may advance only to `identity_public_contract_gate_missing`",
            "Official complete-SDK progress remains `0%` (`0/12` complete-SDK rows and `0/4` P0 promoted rows)",
        ):
            with self.subTest(section="compact stable baseline", phrase=phrase):
                self.assertIn(phrase, compact_stable)

        for phrase in (
            "durable standing launch authorization recorded in both",
            "that standing authorization remains transferable until revoked",
            "It still supplies no runtime evidence, SDK/P0 progress, publication, or SDK/stable/public-readiness claim",
            "Reconfirm current SDK/evidence status before acting",
            "never translate that authority into evidence, readiness, publication permission, or broad Discord permission",
        ):
            with self.subTest(section="handoff skill", phrase=phrase):
                self.assertIn(phrase, handoff_skill)

        combined_authority_sections = normalized(
            "\n".join((current_authority, compact_resume, compact_standing, handoff_skill))
        ).lower()
        for positive_claim in (
            "standing_authority_counts_as_evidence=true",
            "standing_authority_counts_as_readiness=true",
            "standing_authority_counts_as_progress=true",
            "standing_authority_clears_approved_runtime_evidence_missing=true",
            "standing_authority_advances_sdk=true",
        ):
            with self.subTest(claim=positive_claim):
                self.assertNotIn(positive_claim, combined_authority_sections)

    def test_github_workflow_skill_keeps_aliases_non_authorizing(self) -> None:
        skill = normalized(GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8"))

        for phrase in (
            "planning/compatibility inputs, not public readiness or release authorization",
            "support-tier activation",
            "public package readiness",
            "stable SDK evidence",
            "`progress_normalization_trace`",
            "source_overclaim diagnostics",
            "`source_overclaim_total_flag_count=0`",
            "the latest release-readiness pass",
            "release-readiness passes",
            "the latest validation pass",
            "closed-agent/all-six-agent closure notes",
            "`.codex` cleanup",
            "install/package or package-shape success",
            "package-shape installs",
            "package installs",
            "`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`",
            "beta notice drafts/actions",
            "passive monitor ticks/output",
            "passive monitors",
            "passive player summaries/snapshots",
            "public reachability",
            "Plugin Hub planning",
            "side-lane candidate accounting",
            "support-tier labels",
            "prior approvals",
            "historical live approvals/map names",
            "historical approvals/map names",
            "historical TheIsland/Ragnarok/Genesis2 names",
            "live authorization",
            "runtime evidence",
            "approved in-game evidence",
            "SDK/P0 progress",
            "live-op authorization",
            "Discord authorization",
            "publication authority",
            "public SDK readiness",
            "stable SDK readiness",
            "stable SDK claim",
            "Plugin Hub readiness",
            "current-turn exact approval",
            "accepted checker evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_call_process_event_handoff_stays_owner_scoped_init_window_only(self) -> None:
        for path in (CURRENT, COMPACT_CONTEXT):
            text = normalized(path.read_text(encoding="utf-8"))
            with self.subTest(file=str(path.relative_to(REPO_ROOT))):
                self.assertIn("CallProcessEvent", text)
                self.assertIn("init-window debug escape hatch", text)
                self.assertRegex(
                    text,
                    r"(current plugin owner is inside|calling plugin is currently inside) `?ObeliskPlugin_Init`?",
                )
                self.assertIn("OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT", text)
                self.assertIn("Post-init calls through captured API tables", text)
                self.assertRegex(text, r"future .* owner[- ]token ABI|future replacement must carry an owner token")
                self.assertNotRegex(text, r"\bglobal CallProcessEvent\b")
                self.assertNotRegex(text, r"\bCallProcessEvent (?:is |remains |stays )?(?:global|ownerless|unowned)\b")
                self.assertNotRegex(text, r"\bCallProcessEvent\b.{0,80}\b(?:not owner[- ]scoped|no owner scope)\b")
                self.assertNotRegex(text, r"\bpost-init CallProcessEvent\b.{0,80}\b(?:supported|allowed|callable)\b")

    def test_resourcehandle_followup_does_not_restart_broad_scans(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        reversing_skill = normalized(REVERSING_RESEARCH_SKILL.read_text(encoding="utf-8"))

        for text in (current, compact, reversing_skill):
            self.assertIn("ResourceHandle", text)
            self.assertRegex(text, r"broad (FName, GObjects, or core scans|FName, GObjects, or core scan)")
        self.assertIn("rejected runtime object samples", reversing_skill)
        self.assertIn("runtime serial reuse/wraparound semantics", reversing_skill)

    def test_release_handoff_routing_stays_post_f33dc34_aligned(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        status = normalized((REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))
        compatibility = normalized((REPO_ROOT / "docs" / "SDK_V1_COMPATIBILITY.md").read_text(encoding="utf-8"))

        # These files retain the broader historical release contract. The root
        # README describes the operator-requested native prototype, whose gameplay
        # acceptance is independent of the complete-SDK promotion counters.
        for text in (current, compact, compatibility, status):
            self.assertIn("Plugin Hub", text)
        for text in (current, compatibility, status):
            self.assertRegex(text, r"v1(?:\.0)? .*complete|complete .*v1")
            self.assertRegex(text, r"blocked|not .*claim|not .*authorize")

        self.assertIn("post-SDK-complete planning only", current)
        self.assertIn("post-SDK-complete planning only", status)
        self.assertIn("The P0 chain must be promoted before", compatibility)
        self.assertIn("archived boundaries only until SDK completion", compact)
        self.assertNotIn("Plugin Hub seed review requires", compact)

        for text in (current, compatibility, status):
            self.assertIn("approved copied runtime principal lifecycle evidence", text)
        self.assertIn("approved copied runtime principal lifecycle evidence", compact)
        self.assertNotIn("Current identity next step is accepted login/logout", current)
        self.assertNotIn("stays blocked on lifecycle-anchor evidence unless", current)

        self.assertIn("rejected runtime object samples", current)
        self.assertIn("runtime serial reuse/wraparound semantics", current)
        self.assertIn("runtime object negative samples", compatibility)
        self.assertIn("runtime serial reuse/wraparound semantics", compatibility)
        self.assertIn("rejected object samples plus runtime serial reuse/wraparound semantics", status)

    def test_status_matrix_keeps_current_v1_completion_snapshot(self) -> None:
        status = normalized((REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))

        self.assertIn("Current completion snapshot for agents and contributors", status)
        self.assertIn("P0 dependency chain: `0/4` promoted", status)
        self.assertIn("v1 demand-family promotion gate: `0/12` promoted", status)
        self.assertIn(
            "Scoped non-P0 release-statement bookkeeping: the default checker uses",
            status,
        )
        self.assertIn("records `8/8` reviewed scoped outcomes", status)
        self.assertIn("still leaves P0 `0/4`, the v1 demand-family gate `0/12`, and `stable_claim_allowed=false`", status)
        self.assertIn("approved_runtime_evidence_missing", status)
        self.assertIn("identity_public_contract_gate_missing", status)
        self.assertIn("does not unlock public identity, permissions/admin, command response, command replies", status)
        self.assertIn("stable SDK claim", status)

    def test_current_handoff_keeps_passive_wait_non_evidence_and_sdk_locked(self) -> None:
        current_text = CURRENT.read_text(encoding="utf-8")
        current = normalized(current_text)
        earlier_round = normalized(
            current_text.split("- Earlier 2026-06-04/05 supervised offline rounds", 1)[1].split(
                "- Historical TheIsland evidence round", 1
            )[0]
        )
        historical_round = normalized(
            current_text.split("- Historical lead round, 2026-06-05 local `08:06 CEST`", 1)[1].split(
                "- Historical passive snapshot anchor", 1
            )[0]
        )
        p0_runtime_step = normalized(
            current_text.split("- P0 runtime evidence:", 1)[1].split(
                "- P0 public contract:", 1
            )[0]
        )

        self.assertIn("COMPACT_CONTEXT.md", earlier_round)
        self.assertIn("non-authorizing", earlier_round)
        self.assertIn("route `approved_runtime_evidence_missing`", earlier_round)
        self.assertIn("SDK `0/12`, P0 `0/4`", earlier_round)
        self.assertIn("all six spawned agents were closed", historical_round)
        self.assertIn("Carver/Erdos/Planck/Halley/Laplace completed", historical_round)
        self.assertIn("Boyle was shut down after timeout", historical_round)
        self.assertIn("no standby sub-agent remains", historical_round)
        self.assertIn("timestamped copied lifecycle log lines", historical_round)
        self.assertIn("public/P0 gates reject reviewed/current identity contract aliases", historical_round)
        self.assertIn("lifecycle runtime rejects unknown invalidation reason bits", historical_round)
        self.assertIn("RC assembly is minimal/structure/chat only", historical_round)
        self.assertIn("stale `--item-return-root` rejected", historical_round)
        self.assertIn("side-lane/offline gates reject readiness/counting/accounting aliases", historical_round)
        self.assertIn("completion scanner no longer flags its own negative/non-claim disclaimers", historical_round)
        self.assertIn("evidence/window suite 411 OK", historical_round)
        self.assertIn("public contract/header/route suite 427 OK", historical_round)
        self.assertIn("reflection/side-lane focal 518 OK", historical_round)
        self.assertIn("worker rerun 705 OK", historical_round)
        self.assertIn("release-options/posture/wrapper/install tests passed", historical_round)
        self.assertIn("release scope 63 OK", historical_round)
        self.assertIn("C++ lifecycle build plus CTest 4/4 passed", historical_round)
        self.assertIn("runtime guardrail 20 OK", historical_round)
        self.assertIn("public SDK completion suite 301 OK", historical_round)
        self.assertIn("blocker `approved_runtime_evidence_missing`", historical_round)
        self.assertIn("SDK `0/12`, P0 `0/4`", historical_round)
        self.assertIn("Ragnarok remains diagnostic/non-evidence", historical_round)
        self.assertIn("Genesis2 still lacks `session_end`", historical_round)
        self.assertIn("no complete in-game evidence is approved yet", historical_round)
        self.assertIn("No live server/log/`/servidor/ark`", historical_round)
        self.assertIn(
            "/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json",
            current,
        )
        self.assertIn("captured_at_utc=2026-06-04T08:51:19Z", current)
        self.assertIn("script PID `3261082`", current)
        self.assertIn("/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log", current)
        self.assertIn("snapshots under `/tmp/obelisk-passive-evidence-snapshots`", current)
        self.assertIn("Ragnarok `accepted=0`, `rejected=0`, `diagnostic_candidates=17`", current)
        self.assertIn("target_counts `HandleNewPlayer=7`, `OnLogout=5`, `CheckJoinInProgress=2`, `K2_PostLogin=3`", current)
        self.assertIn("mismatches `HandleNewPlayer=4`, `OnLogout=3`", current)
        self.assertIn("TheIsland `accepted=0`, `rejected=0`, `diagnostic_candidates=0`", current)
        self.assertIn("passive_snapshot_non_evidence", current)
        self.assertIn("approved-evidence checker rejects it", current)

        self.assertIn("recorded 2026-06-06 standing launch authority", p0_runtime_step)
        self.assertIn("exact scoped current-turn approval", p0_runtime_step)
        self.assertIn("Plain offline sub-agents without that delegated scope must not continue passive observation", p0_runtime_step)
        self.assertIn("read live logs", p0_runtime_step)
        self.assertIn("touch `/servidor/ark`", p0_runtime_step)
        self.assertIn("any server/log read, marker/env change, or runtime capture", p0_runtime_step)
        self.assertIn("copied `Obelisk.log`", p0_runtime_step)
        self.assertIn("Preserve the historical TheIsland copied `Obelisk.log` and existing request files", p0_runtime_step)
        for sibling in (
            "window-request.json",
            "observer-window.env",
            "operator-approval-request.md",
            "operator-approval-receipt.json",
            "preflight-pre.json",
        ):
            with self.subTest(existing_sibling=sibling):
                self.assertIn(sibling, p0_runtime_step)
        self.assertIn("do not call it approved", p0_runtime_step)
        for missing_sibling in (
            "preflight-post.json",
            "window-manifest.env",
            "approved-runtime-principal-lifecycle-evidence.json",
        ):
            with self.subTest(missing_sibling=missing_sibling):
                self.assertIn(missing_sibling, p0_runtime_step)
        self.assertIn("Diagnostic candidate lines, passive player presence, and public-query results are non-evidence", p0_runtime_step)
        self.assertIn("Accepted evidence now requires real `session_start`", p0_runtime_step)
        self.assertIn("session_start_rejected", p0_runtime_step)
        self.assertIn("session_end", p0_runtime_step)
        self.assertIn("apply_status", p0_runtime_step)
        self.assertIn("correlation_status", p0_runtime_step)

        standing_authorization = normalized(
            current_text.split("- Standing operator authorization, 2026-06-06 local:", 1)[1].split(
                "- Standing-authority checkpoint, 2026-06-06 local:",
                1,
            )[0]
        )
        launch_override = normalized(
            current_text.split("- Default live-ops rule:", 1)[1].split(
                "- Request-pack/preflight",
                1,
            )[0]
        )

        self.assertIn("applies across future turns and compactions until explicitly revoked", standing_authorization)
        self.assertIn("persistent authority to run any runtime tests", standing_authorization)
        self.assertIn("safe ARK instance starts/stops/restarts", standing_authorization)
        self.assertIn("beta-tester Discord notices", standing_authorization)
        self.assertIn("`arkserver2` / `TheIsland` explicitly approved", standing_authorization)
        self.assertIn("never keep three ARK servers running", standing_authorization)
        self.assertIn("avoid raw player text/secrets", standing_authorization)
        self.assertIn("do not claim SDK/stable/public readiness", standing_authorization)
        self.assertIn("active and persistent for necessary ObeliskSDK runtime evidence/debug work", launch_override)
        self.assertIn("Prior passive evidence remains non-evidence until checkers accept a copied bundle", launch_override)

        live_ops = normalized(LIVE_OPS_SKILL.read_text(encoding="utf-8"))
        self.assertIn(EXACT_OR_STANDING_SCOPE, live_ops)
        self.assertIn("Passive/read-only observation and beta tester notices are not exceptions", live_ops)
        self.assertIn("recorded standing launch authorization", live_ops)
        self.assertIn("do not treat compaction or a resumed turn as revocation", live_ops)
        self.assertIn("use it for the named runtime/beta evidence window", live_ops)
        self.assertIn("Discord sends, runtime capture", live_ops)
        self.assertIn("do not restart merely to broaden logging while players are active", normalized(current_text).lower())
        self.assertIn("do not restart merely to broaden observer coverage", live_ops)
        self.assertIn(
            "do not restart merely to broaden observer coverage",
            normalized(COMPACT_CONTEXT.read_text(encoding="utf-8")).lower(),
        )

        forbidden_active_restart_guidance = (
            "restart both",
            "restart `arkserver`",
            "restart `arkserver2`",
            "restart `arkserver3`",
            "start `arkserver`",
            "start `arkserver3`",
            "trigger a restart",
            "request a restart",
            "schedule a restart",
        )
        for phrase in forbidden_active_restart_guidance:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, p0_runtime_step.lower())

    def test_docs_guard_non_authorizing_paths_from_runtime_capture_or_sdk_evidence(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        readme = normalized((REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        status = normalized((REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))
        compatibility = normalized((REPO_ROOT / "docs" / "SDK_V1_COMPATIBILITY.md").read_text(encoding="utf-8"))

        for label, text in (
            ("CURRENT.md", current),
            ("SDK_V1_COMPATIBILITY.md", compatibility),
            ("STATUS.md", status),
        ):
            with self.subTest(file=label, invariant="blocked snapshot"):
                self.assertIn("approved_runtime_evidence_missing", text)
                self.assertIn("0/12", text)
                self.assertIn("0/4", text)
                self.assertIn("stable_claim_allowed=false", text)

        self.assertIn(
            "Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness, planning acceptance, or route acceptance do not authorize runtime work",
            current,
        )
        self.assertIn("runtime capture", current)
        self.assertIn("public SDK readiness", current)
        self.assertIn("Prior passive evidence remains non-evidence until checkers accept a copied bundle", current)
        self.assertIn("Operator instruction, 2026-06-04, is superseded by the 2026-06-06 persistent launch authority", current)
        self.assertIn("Diagnostic/passive material remains non-evidence", current)
        self.assertIn("Genesis2 public query now works, but public reachability still does not change SDK route or readiness", current)
        self.assertIn("Preserve the historical TheIsland copied `Obelisk.log`", current)
        self.assertIn("but do not call it approved", current)

        self.assertIn(
            "Status tooling explicitly marks Ragnarok role-complete passive triplets and historical TheIsland closure as non-authorizing/non-evidence",
            compact,
        )
        self.assertIn("Ragnarok role-complete passive triplet", compact)
        self.assertIn("Genesis2 still lacks `session_end`", compact)
        self.assertIn("historical TheIsland sidecar closure and then-active Genesis2 passive wait as non-authorizing paths", compact)
        self.assertIn(
            "the historical TheIsland candidate's missing `window-manifest.env`, `preflight-post.json`, and `approved-bundle/approved-runtime-principal-lifecycle-evidence.json` without writing under `/servidor/ark` or granting authorization",
            compact,
        )

        for label, text in (
            ("CURRENT.md", current),
            ("COMPACT_CONTEXT.md", compact),
            ("README.md", readme),
            ("STATUS.md", status),
            ("SDK_V1_COMPATIBILITY.md", compatibility),
        ):
            with self.subTest(file=label, invariant="no positive authorization fields"):
                self.assertNotIn("runtime_capture_authorized=true", text)
                self.assertNotIn("approved_runtime_evidence=true", text)
                self.assertNotIn("public_sdk_ready=true", text)
                self.assertNotIn("stable_claim_allowed=true", text)

    def test_compact_active_overrides_preserve_latest_live_ops_round_rules(self) -> None:
        compact_text = COMPACT_CONTEXT.read_text(encoding="utf-8")
        active_overrides = normalized(
            compact_text.split("## Active Overrides", 1)[1].split("## Stable Baseline", 1)[0]
        )

        for phrase in (
            "standing launch authorization",
            "superseded",
            "live-log reads/tails",
            "passive observation",
            "Passive logs, passive monitor output, public-query results, and diagnostic/status snapshots are not SDK evidence or readiness",
            "never use passive-log material to clear `approved_runtime_evidence_missing`",
            "Never keep three ARK servers running",
            "server concurrency stays two or fewer",
            "Delegated sub-agents must be closed or explicitly marked obsolete before another round",
            "Closed-agent and all-six-closed notes are process hygiene only",
            "not live-ops approval, accepted runtime evidence, SDK progress, or public readiness",
            "Generated repo temp dirs",
            "tests/core/PlayerIdentityPromotion*",
            "tests/sdk_consumer/player_identity_promotion*",
            "not handoff evidence, runtime evidence, SDK progress, or readiness",
            "exact notice path must be dry-run checked and sent before activation",
            "documented-but-unsent notice is incomplete",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, active_overrides)

    def test_handoff_skill_blocks_concurrent_public_sdk_completion_suite(self) -> None:
        skill = normalized(AGENT_HANDOFF_SKILL.read_text(encoding="utf-8"))

        for phrase in (
            "full `scripts.test_check_public_sdk_v1_completion` suite",
            "concurrently",
            "`tests/core`",
            "`tests/sdk_consumer`",
            "repo-local temp dirs",
            "coordinate a serial lead-run",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_handoff_skill_serializes_principal_lifecycle_bundle_and_checker_suites(self) -> None:
        skill = normalized(AGENT_HANDOFF_SKILL.read_text(encoding="utf-8"))

        for phrase in (
            "`scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`",
            "`scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`",
            "concurrently",
            "fixture cleanup surfaces",
            "run them serially",
            "false integration failures",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_fast_path_keeps_agent_closure_as_non_approval(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        guardrail = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )

        self.assertIn("closed sub-agent or all-six-agents-closed notes", guardrail)
        self.assertIn("six-agent closure notes", guardrail)
        self.assertIn("the latest validation pass", guardrail)
        self.assertIn("`.codex` cleanup", guardrail)
        self.assertIn("Sub-agent closure", guardrail)
        self.assertIn("repeated local hardening rounds", guardrail)
        self.assertIn("process/accounting hygiene only", guardrail)
        self.assertIn("server-operation approval", guardrail)
        self.assertIn("they do not move SDK, P0, or v1 counters", guardrail)
        self.assertIn(
            "cannot substitute for accepted runtime evidence or current-turn operator approval",
            guardrail,
        )
        self.assertIn("Compaction invariant for future agents", guardrail)
        self.assertIn("no complete approved in-game evidence exists yet", guardrail)
        self.assertIn("communication artifacts, not evidence", guardrail)
        self.assertIn("passive diagnostics are diagnostic-only/non-evidence", guardrail)
        self.assertIn("no standby sub-agent remains", guardrail)
        self.assertIn("no current-turn server authorization", guardrail)

    def test_player_identity_focal_plans_require_exact_targets(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        obsolete_plan = (
            "scripts/plan_ufunction_focal_snapshots.py "
            "--target-set players-identity-lifecycle-intake"
        )

        for text in (current, compact):
            self.assertIn("12-target `players-identity-lifecycle-intake`", text)
            self.assertIn("ShooterPlayerController.ServerListPlayers", text)
            self.assertIn("ShooterPlayerController.ServerKickPlayer", text)
            self.assertIn("exact", text)
            self.assertNotIn(obsolete_plan, text)

    def test_compact_context_preserves_p0_promoted_only_sdk_chain(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))

        for label, text in (("CURRENT.md", current), ("COMPACT_CONTEXT.md", compact)):
            with self.subTest(file=label):
                self.assertIn("v1_required_dependency_chain", text)
                self.assertIn("promoted-only", text)
                self.assertIn("complete SDK claim", text)
                self.assertIn("scoped non-complete", text)
                self.assertIn("obelisk.command_chat_response_path.v1", text)

        self.assertNotIn("named post-v1 `obelisk.command_chat_response_path.v1`", compact)
        self.assertNotIn("post-v1 `obelisk.command_chat_response_path.v1` planning dependency", compact)

    def test_learning_skill_keeps_adopted_knowledge_compact(self) -> None:
        skill = (REPO_ROOT / "agent-skills/obelisk-continuous-learning/SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertLessEqual(len(skill.splitlines()), MAX_SKILL_LINES)
        self.assertIn("Adopted knowledge should not remain only in chat or an agent result", skill)
        self.assertIn("smallest durable place", skill)
        self.assertIn("skill rule when it changes repeatable behavior", skill)
        self.assertIn("research note when it records evidence", skill)
        self.assertIn("active handoff only when it changes the next turn's routing", skill)
        self.assertIn("Keep the promoted form concise", skill)
        self.assertIn("Avoid copying full agent transcripts", skill)


if __name__ == "__main__":
    unittest.main()
