#!/usr/bin/env python3
"""Guardrails for Obelisk research docs that encode live-server safety rules."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_resource_handle_revalidation as resourcehandle_evaluator  # noqa: E402
import build_player_identity_runtime_principal_lifecycle_evidence_bundle as identity_bundle_builder  # noqa: E402
from check_public_sdk_v1_completion import release_statement_forbidden_broad_claims  # noqa: E402


def normalized(text: str) -> str:
    return " ".join(text.split())


CURRENT_TURN_EXACT_SCOPE = (
    "Current-turn exact scope is required for live server/log reads, marker/env changes, "
    "Discord sends, and runtime capture"
)


class ResearchDocGuardrailTests(unittest.TestCase):
    def test_sdk_priority_map_retired_lifecycle_blocker_is_historical_only(self) -> None:
        priority_map = (
            REPO_ROOT / "docs/research/2026-06-02-sdk-complete-priority-map.md"
        ).read_text(encoding="utf-8")
        compact_priority_map = normalized(priority_map)
        retired_blocker = "lifecycle_anchor_first_evidence_provenance_unbound"

        self.assertIn(
            "Read every later `lifecycle_anchor_first_evidence_provenance_unbound` line "
            "as historical status only",
            compact_priority_map,
        )
        self.assertIn("The active default blocker is\n`approved_runtime_evidence_missing`", priority_map)
        self.assertNotIn("Current route posture changes accordingly", priority_map)

        for paragraph in priority_map.split("\n\n"):
            if retired_blocker not in paragraph:
                continue
            compact = normalized(paragraph).lower()
            with self.subTest(paragraph=normalized(paragraph)[:120]):
                self.assertRegex(compact, r"\b(?:historical|then-current|stale)\b")

    def test_player_identity_post_window_replay_is_mandatory_for_promotion_route_docs(self) -> None:
        checklist = (
            REPO_ROOT
            / "docs/research/2026-06-01-player-identity-runtime-capture-readiness-checklist.md"
        ).read_text(encoding="utf-8")
        route_audit = (
            REPO_ROOT / "docs/research/2026-06-01-player-identity-lifecycle-route-audit.md"
        ).read_text(encoding="utf-8")
        runtime_plan = (
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-capture-plan.md"
        ).read_text(encoding="utf-8")

        offline_bundle = checklist.split("## Offline Bundle Commands", 1)[1].split(
            "## Fail-Closed No-Go Conditions", 1
        )[0]
        manifest_validation = offline_bundle.split("Validate the completed manifest", 1)[1].split(
            "Build the consume-only evidence bundle", 1
        )[0]

        self.assertIn("--post-window-replay", manifest_validation)
        self.assertIn("post-window replay or promotion-route\nconsumption", offline_bundle)
        self.assertIn(
            "using `--post-window-replay` for any post-window replay or promotion-route\n"
            "  consumption",
            route_audit,
        )
        self.assertIn("--post-window-replay", runtime_plan)

    def test_player_identity_approved_window_docs_do_not_use_rehearsal_preflight_flags(self) -> None:
        checklist = (
            REPO_ROOT
            / "docs/research/2026-06-01-player-identity-runtime-capture-readiness-checklist.md"
        ).read_text(encoding="utf-8")
        runtime_plan = (
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-capture-plan.md"
        ).read_text(encoding="utf-8")

        rehearsal_section = checklist.split("## Offline Rehearsal Preflight", 1)[1].split(
            "## Expected Log Cases", 1
        )[0]
        self.assertIn("--offline-only", rehearsal_section)
        self.assertIn("--allow-stopped", rehearsal_section)
        self.assertIn(
            "must not be saved as `preflight-pre.json`, `preflight-post.json`",
            normalized(rehearsal_section),
        )

        approved_sections = {
            "runtime-capture-readiness-checklist-offline-bundle": checklist.split(
                "## Offline Bundle Commands", 1
            )[1],
            "runtime-capture-plan-approved-window": runtime_plan.split(
                "## Exact Approved-Window Preflight", 1
            )[1],
        }
        for name, section in approved_sections.items():
            bash_commands = re.findall(r"```bash\n(.*?)```", section, flags=re.DOTALL)
            self.assertTrue(bash_commands)
            for command in bash_commands:
                with self.subTest(section=name, command=command.splitlines()[0]):
                    self.assertNotIn("--offline-only", command)
                    self.assertNotIn("--allow-stopped", command)

    def test_stale_player_identity_offline_pack_gap_notes_are_marked_superseded(self) -> None:
        curation = (
            REPO_ROOT / "docs/research/2026-05-31-offline-artifact-curation.md"
        ).read_text(encoding="utf-8")
        inventory_audit = (
            REPO_ROOT / "docs/research/2026-05-31-offline-artifact-inventory-audit.md"
        ).read_text(encoding="utf-8")
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")

        for path, text in (
            ("2026-05-31-offline-artifact-curation.md", curation),
            ("2026-05-31-offline-artifact-inventory-audit.md", inventory_audit),
        ):
            compact = normalized(text)
            with self.subTest(path=path):
                self.assertIn("Historical status, superseded", compact)
                self.assertIn("approved_runtime_evidence_missing", compact)
                self.assertIn("source-bound planning manifests", compact)

        curation_status = curation.split("## Player Identity Status", 1)[1]
        self.assertNotIn("known snapshot gaps remain", curation_status)
        readme_compact = normalized(readme)
        self.assertIn("Historical/superseded for player identity", readme_compact)
        self.assertIn("current identity blocker is `approved_runtime_evidence_missing`", readme_compact)

    def test_static_demand_shortest_offline_identity_path_is_marked_superseded(self) -> None:
        static_demand = (
            REPO_ROOT / "docs/research/2026-05-31-v1-sdk-round-identity-static-demand-audit.md"
        ).read_text(encoding="utf-8")
        section = static_demand.split("## Shortest Offline Identity Path", 1)[1].split(
            "## Demand Dictionary", 1
        )[0]
        compact = normalized(section)

        self.assertIn("Historical/superseded for player identity", compact)
        self.assertIn("do not execute this section for the current blocker", compact)
        self.assertIn("approved_runtime_evidence_missing", compact)
        self.assertIn("ShooterGameMode.HandleNewPlayer", compact)
        self.assertIn("ShooterGameMode.OnLogout", compact)
        self.assertIn("candidate/internal planning guidance only", compact)

    def test_player_identity_offline_pack_safe_next_step_points_to_runtime_evidence(self) -> None:
        offline_pack = (
            REPO_ROOT / "docs/research/2026-05-31-player-identity-offline-pack-preflight.md"
        ).read_text(encoding="utf-8")
        section = offline_pack.split("## Safe Next Step", 1)[1]
        current_step = section.split("## Recovery-Only Staged Input Recipe", 1)[0]
        recovery_recipe = section.split("## Recovery-Only Staged Input Recipe", 1)[1].split(
            "## Boundary", 1
        )[0]
        compact = normalized(section)
        current_step_compact = normalized(current_step)
        recovery_compact = normalized(recovery_recipe)

        self.assertIn("consume-only for the current route", compact)
        self.assertIn("approved copied runtime principal lifecycle evidence", compact)
        self.assertIn("reviewed public identity contract gate", compact)
        self.assertIn("principal privacy/invalidation policy", compact)
        self.assertIn("or lifecycle layout alone", compact)
        self.assertIn("ShooterGameMode.HandleNewPlayer", current_step_compact)
        self.assertIn("ShooterGameMode.OnLogout", current_step_compact)
        self.assertIn("Recovery-Only Staged Input Recipe", section)
        self.assertIn("historical recovery guidance only", recovery_compact)
        self.assertIn("binary hash changes", recovery_compact)
        self.assertIn("contradicts the source-bound planning manifests", recovery_compact)
        self.assertIn("approved copied runtime principal lifecycle evidence", recovery_compact)
        self.assertNotIn("build_core_dump_evidence_pack.py", current_step)
        self.assertNotIn("build_reflection_inventory_pack.py", current_step)
        self.assertNotIn(
            "The next useful action is to finish the principal privacy and invalidation policy",
            section,
        )

    def test_player_identity_admin_targets_are_not_lifecycle_anchors(self) -> None:
        notes = {
            "offline_pack": REPO_ROOT
            / "docs/research/2026-05-31-player-identity-offline-pack-preflight.md",
            "targetset_gap": REPO_ROOT / "docs/research/2026-05-31-player-identity-targetset-gap.md",
            "readme": REPO_ROOT / "docs/research/README.md",
        }

        for name, path in notes.items():
            compact = normalized(path.read_text(encoding="utf-8"))
            with self.subTest(note=name):
                self.assertIn("ShooterPlayerController.ServerListPlayers", compact)
                self.assertIn("ShooterPlayerController.ServerKickPlayer", compact)
                self.assertIn("ShooterGameMode.HandleNewPlayer", compact)
                self.assertIn("ShooterGameMode.OnLogout", compact)

        offline_pack = normalized(notes["offline_pack"].read_text(encoding="utf-8"))
        self.assertIn("does not make them lifecycle anchors", offline_pack)

        targetset_gap = normalized(notes["targetset_gap"].read_text(encoding="utf-8"))
        self.assertIn("Admin/session pressure only", targetset_gap)
        self.assertIn("Admin/authority pressure only", targetset_gap)
        self.assertIn("not identity lifecycle proof", targetset_gap)

        readme_route = notes["readme"].read_text(encoding="utf-8").split(
            "| Players identity lifecycle |", 1
        )[1].split("\n", 1)[0]
        self.assertIn("admin targets, not lifecycle anchors", normalized(readme_route))

    def test_player_identity_runtime_observer_brief_bundle_command_matches_builder_cli(self) -> None:
        documented_flags = self._documented_identity_bundle_flags(
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-observer-brief.md",
            "## Post-Window Offline Acceptance",
            "## Non-Claims",
        )
        self._assert_identity_bundle_flags_match_builder_cli(documented_flags)

    def test_player_identity_offline_to_runtime_plan_bundle_command_matches_builder_cli(self) -> None:
        documented_flags = self._documented_identity_bundle_flags(
            REPO_ROOT / "docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md",
            "Validate the copied window manifest",
            "## Runtime Handoff",
        )
        self._assert_identity_bundle_flags_match_builder_cli(documented_flags)

    def test_player_principal_observer_brief_requires_exact_checkjoin_rejected_start(self) -> None:
        observer_brief = (
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-observer-brief.md"
        ).read_text(encoding="utf-8")
        compact = normalized(observer_brief)

        self.assertIn("ShooterGameMode.CheckJoinInProgress(1,0)", observer_brief)
        self.assertIn(
            "CheckJoinInProgress` is the only approved `session_start_rejected` source",
            compact,
        )
        self.assertIn(
            "`HandleNewPlayer` bool combinations are diagnostic only and are not approved "
            "`session_start_rejected` evidence",
            compact,
        )
        self.assertIn("`bIsFromLogin=1` and `ReturnValue=0`", compact)
        self.assertNotIn("canonical rejected anchor `bIsFromLogin=0` and `ReturnValue=1`", observer_brief)
        self.assertNotIn("`HandleNewPlayer` is an approved `session_start_rejected` source", compact)

    def test_player_lifecycle_six_candidate_evidence_is_labeled_scratch_not_durable(self) -> None:
        fixture_gap = (
            REPO_ROOT / "docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md"
        ).read_text(encoding="utf-8")
        runtime_plan = (
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-capture-plan.md"
        ).read_text(encoding="utf-8")
        observer_brief = (
            REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-observer-brief.md"
        ).read_text(encoding="utf-8")

        self.assertIn("committed base fixtures for all six", fixture_gap)
        self.assertIn("limited to `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`", fixture_gap)
        self.assertIn("scratch triage under `/tmp/obelisk-lifecycle-snapshot-probe/`", fixture_gap)
        self.assertIn("second_source_accepted=6", fixture_gap)
        self.assertIn("not durable source-bound second-source lifecycle-anchor evidence for all six", fixture_gap)
        self.assertIn("six committed base fixtures", runtime_plan)
        self.assertIn("limited to\n  `HandleNewPlayer` and `OnLogout`", runtime_plan)
        self.assertIn("scratch triage unless materialized into an approved offline artifact/root", runtime_plan)
        self.assertIn("six committed base fixtures", observer_brief)
        self.assertIn("lifecycle-anchor evidence is currently limited to\n  `HandleNewPlayer` and `OnLogout`", observer_brief)
        self.assertIn("`ShooterGameMode.CheckJoinInProgress(1,0)` is the only approved", observer_brief)
        self.assertIn("scratch triage unless\n  materialized into an approved offline artifact/root", observer_brief)
        self.assertNotIn(
            "`players-lifecycle-anchor-candidates` has accepted planning-layout evidence for six",
            runtime_plan,
        )
        self.assertNotIn(
            "six lifecycle-anchor planning targets accepted across two offline\n  roots",
            observer_brief,
        )

    def test_june4_fast_path_keeps_passive_snapshot_as_non_evidence(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        current = (REPO_ROOT / "docs/agent-handoff/CURRENT.md").read_text(encoding="utf-8")
        compact = (
            REPO_ROOT / "docs/agent-handoff/COMPACT_CONTEXT.md"
        ).read_text(encoding="utf-8")

        fast_compact = normalized(fast_path)
        current_compact = normalized(current)
        compact_compact = normalized(compact)

        for label, text in (
            ("fast-path", fast_compact),
            ("current", current_compact),
            ("compact", compact_compact),
        ):
            with self.subTest(doc=label, invariant="active two-map passive wait"):
                self.assertIn("arkserver` / `Ragnarok", text)
                if label == "current":
                    self.assertIn("Genesis2 still lacks `session_end`", text)
                else:
                    self.assertIn("arkserver3` / `Genesis2", text)
                self.assertRegex(text, r"passive (?:wait|monitor)")
                self.assertTrue(
                    "arkserver2` / `TheIsland` is off" in text
                    or "`arkserver2` / `TheIsland` explicitly approved" in text
                    or "TheIsland `arkserver2`" in text,
                    f"{label}: expected either historical off-state or current TheIsland binding",
                )
                self.assertIn("Never keep three ARK servers running", text)
            with self.subTest(doc=label, invariant="no chained restarts"):
                self.assertRegex(text, r"(?i)do not (?:chain )?restarts? while waiting|avoid repeated restarts")
            with self.subTest(doc=label, invariant="runtime evidence blocker"):
                self.assertIn("approved_runtime_evidence_missing", text)
            with self.subTest(doc=label, invariant="passive snapshot non-evidence"):
                self.assertIn("ready=false", text)
                self.assertTrue(
                    "approved_runtime_evidence=false" in text
                    or "approved runtime evidence false" in text,
                    f"{label}: passive snapshot must preserve approved runtime evidence false",
                )
            with self.subTest(doc=label, invariant="latest snapshot identity"):
                self.assertIn(
                    "/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json",
                    text,
                )
                self.assertIn("captured_at_utc=2026-06-04T08:51:19Z", text)
                self.assertIn("3261082", text)
                self.assertRegex(text, r"diagnostic(?:_candidate_count|_candidates)=17")
                self.assertIn("HandleNewPlayer=7", text)
                self.assertIn("OnLogout=5", text)
                self.assertIn("CheckJoinInProgress=2", text)
                self.assertIn("K2_PostLogin=3", text)
                self.assertIn("HandleNewPlayer=4", text)
                self.assertIn("OnLogout=3", text)
                self.assertRegex(text, r"accepted(?:_count)?=0")
                self.assertRegex(text, r"rejected(?:_count)?=0")
                self.assertIn("passive_snapshot_non_evidence", text)
                self.assertIn("approved-evidence checker rejects", text)

        self.assertIn("All six previously open delegated agents were closed", fast_path)
        self.assertIn("all six spawned agents were closed", current_compact)
        self.assertIn("all six previously open agents were closed", compact_compact)
        self.assertIn("no active sub-agent was left open", fast_compact)
        self.assertIn("Six-Agent Integration", fast_path)
        self.assertIn("All six agents from the current round were closed", fast_path)
        self.assertIn("All six agents from the prior round were closed", fast_path)
        self.assertIn("no new sub-agent work is opened by this note", fast_compact)
        self.assertIn("offline/local hardening", fast_path)
        self.assertIn("No live-server write", fast_compact)
        self.assertIn("marker/env mutation", fast_compact)
        self.assertIn("not approved runtime evidence", fast_compact)
        self.assertIn("The route remains `approved_runtime_evidence_missing`", fast_path)
        self.assertIn("stable_claim_allowed=false", fast_path)
        self.assertIn("SDK remains `0/12`, P0 `0/4`", fast_path)
        self.assertIn(
            "until real copied `PlayerPrincipalLifecycleObserver event` lines are accepted by the evidence checkers",
            fast_compact,
        )
        self.assertIn(
            "no accepted `PlayerPrincipalLifecycleObserver event`, `session_start`, `session_start_rejected`, or `session_end` lines",
            fast_compact,
        )
        self.assertIn("PlayerPrincipalLifecycleObserver event", compact_compact)
        for event_name in ("session_start", "session_start_rejected", "session_end"):
            with self.subTest(event=event_name):
                self.assertIn(event_name, fast_compact)
                self.assertIn(event_name, current_compact)
                self.assertIn(event_name, compact_compact)

        self.assertIn("Operator instruction captured on `2026-06-04`", fast_path)
        self.assertIn("scoped passive server tests", fast_compact)
        self.assertIn("offline development continues in parallel", fast_compact)
        self.assertIn("This does not authorize repeated restarts while waiting", fast_compact)
        self.assertIn("publication, or SDK readiness claims", fast_compact)
        self.assertIn(
            "Historical correction recorded later on 2026-06-04: routing had moved from TheIsland to the two-server Ragnarok+Genesis2 posture",
            fast_compact,
        )
        self.assertIn("then-active two-server pair", fast_compact)
        self.assertIn("never keep three ark servers running", fast_compact.lower())
        self.assertIn("arkserver3:Genesis2:27017", fast_compact)
        self.assertIn("/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log", fast_compact)
        self.assertIn("79.116.87.223:27017", fast_compact)
        self.assertIn("public GameDig query", fast_compact)
        self.assertIn("map `Gen2`", fast_compact)
        self.assertIn("connect=79.116.87.223:7783", fast_compact)
        self.assertIn("the earlier public-query/NAT blocker is resolved", fast_compact)
        self.assertIn("process_control=none", fast_compact)
        self.assertIn("Monitor ticks, copied passive snapshots", fast_compact)
        self.assertIn("`--latest-diff` output", fast_compact)
        self.assertIn("FName-drift diffs", fast_compact)
        self.assertIn("diagnostic-only; they are not runtime evidence", fast_compact)
        self.assertIn("passive_activity_triage", fast_compact)
        self.assertIn("classification only", fast_compact)
        self.assertIn("non-claim wording must not describe it as public/runtime readiness", fast_compact)
        self.assertIn(
            "the copied approved sibling-set bundle with real `PlayerPrincipalLifecycleObserver event` lines for `session_start`, `session_start_rejected`, and `session_end`",
            fast_compact,
        )
        self.assertRegex(
            fast_compact,
            r"do not chain restarts while waiting|not approval for .* chained restarts while waiting",
        )
        self.assertIn("not approval for new marker/env changes, deploys, restarts", fast_compact)
        self.assertIn(
            "Any future active server operation must get a fresh current-turn approval",
            fast_path,
        )
        self.assertIn("exact instance or instances, marker/env gates", fast_compact)
        self.assertIn("process-control window, evidence paths", fast_compact)
        self.assertIn("no-public-readiness/no-publication boundaries", fast_compact)
        self.assertIn(
            "Passive wait docs, monitor output, passive snapshots, and diagnostic summaries cannot be reused as that approval",
            fast_compact,
        )
        latest_theisland_statement = normalized(
            """
            Durable statement for future agents: the `2026-06-04T11:30:21Z` TheIsland
            passive detection at
            `/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260604T113021Z-arkserver2-3261082`
            is useful diagnostic material only, not accepted evidence; it is missing
            `session_start`, `session_start_rejected`, and `session_end`, the remaining
            diagnostic mismatch is `lifecycle_property_FName_mismatch`, and that
            historical TheIsland passive route is no longer active routing.
            `arkserver2` / `TheIsland` was later recorded as off while `arkserver` / `Ragnarok`
            and `arkserver3` / `Genesis2:27017` were the then-active passive pair.
            """
        )
        self.assertIn(latest_theisland_statement, fast_compact)
        for forbidden in (
            "Current correction: active routing",
            "Current run directory",
            "current top-level runtime facts",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, fast_path)
        self.assertIn("organic `arkserver2` / `TheIsland` player presence at `2026-06-04T11:30:21Z`", fast_compact)
        self.assertIn("latest passive snapshot path", fast_compact)
        self.assertIn("passive-detect-20260604T113021Z-arkserver2-3261082", fast_compact)
        self.assertIn("TheIsland's remaining diagnostic mismatch is `lifecycle_property_FName_mismatch`", fast_path)

    def test_june4_fast_path_index_entry_is_historical_non_authorizing(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")

        entries = [
            line
            for line in readme.splitlines()
            if "2026-06-04-arkserver2-runtime-sdk-fast-path.md" in line
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        entry_compact = normalized(entry)
        scope_compact = normalized(
            fast_path.split("## Scope", 1)[1].split(
                "## 2026-06-04 Offline Completion Checker", 1
            )[0]
        )

        for phrase in (
            "historical `arkserver2` / `TheIsland` debug-target approval",
            "superseded by Ragnarok+Genesis2 passive-route facts",
            "non-authorizing research chronology only",
            "not public SDK readiness",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, entry_compact)

        self.assertNotIn(
            "operator-approved `arkserver2` / `TheIsland` debug target and fastest safe route",
            entry,
        )
        self.assertIn(
            "Interpret every old `active`, `current`, or `then-current` server/map phrase",
            scope_compact,
        )
        self.assertIn("timestamped historical context, not standing authorization", scope_compact)
        self.assertIn("current-turn live reads", scope_compact)
        self.assertIn("marker/env changes", scope_compact)
        self.assertIn("process control", scope_compact)
        self.assertIn("runtime capture", scope_compact)
        self.assertIn("publication, or SDK/P0 progress", scope_compact)

    def test_june4_snapshot_on_detect_and_scoped_statement_are_non_claims(self) -> None:
        fast_path = normalized(
            (REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md").read_text(
                encoding="utf-8"
            )
        )
        current = normalized((REPO_ROOT / "docs/agent-handoff/CURRENT.md").read_text(encoding="utf-8"))

        for label, text in (("fast-path", fast_path), ("current", current)):
            with self.subTest(doc=label, invariant="snapshot trigger"):
                self.assertIn("scripts/monitor_ark_player_presence_passive.sh", text)
                self.assertIn("/tmp/obelisk-passive-evidence-snapshots", text)
                self.assertIn("/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log", text)
                self.assertIn("players=1+", text)
                if label == "fast-path":
                    self.assertIn("--snapshot-output-root", text)
                    self.assertIn("--snapshot-monitor-log", text)
                else:
                    self.assertRegex(text, r"snapshot(?:s)? under|--snapshot-output-root")
            with self.subTest(doc=label, invariant="snapshot remains non-evidence"):
                self.assertIn("ready=false", text)
                self.assertTrue(
                    "approved_runtime_evidence=false" in text
                    or "approved runtime evidence false" in text,
                    f"{label}: snapshot must preserve approved runtime evidence false",
                )
                self.assertIn("approved_runtime_evidence_missing", text)

        self.assertIn(
            "only calls `scripts/capture_player_principal_passive_snapshot.py` after `players=1+` is detected",
            fast_path,
        )
        self.assertIn("Until that happens, no new snapshot directory is created", fast_path)
        self.assertTrue(
            "review the snapshot before any marker/server change" in current
            or "snapshots after `players=1+` are review-only until a future scoped marker/server change"
            in current,
            "CURRENT.md must keep passive snapshots review-only before marker/server changes",
        )

        scoped_statement = REPO_ROOT / "docs" / "SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md"
        self.assertTrue(
            scoped_statement.exists(),
            "durable scoped statement must remain present as non-claim bookkeeping",
        )

        statement = scoped_statement.read_text(encoding="utf-8")
        self.assertEqual(release_statement_forbidden_broad_claims(statement), [])
        self.assertIn("non-claim bookkeeping only", statement)
        self.assertIn("Scoped outcome rows: 8; non-claim bookkeeping only", statement)
        self.assertIn("release_statement_missing_non_promoted_blocker_outcomes", statement)
        self.assertIn("do not authorize stable/full/production SDK wording", statement)
        self.assertNotRegex(statement.lower(), r"\b(?:runtime|public sdk|sdk)\s+ready\b")
        self.assertNotRegex(statement, r"readiness(?:_claim)?(?:_allowed)?=(?:true|TRUE)")

        outcome_lines = [
            line
            for line in statement.splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(len(outcome_lines), 8)
        for line in outcome_lines:
            with self.subTest(line=line):
                self.assertRegex(line, r": (?:post-v1|excluded) - (?:no |mission excluded,)")
                self.assertNotIn("stable_claim_allowed=true", line)
                self.assertNotIn("complete_sdk_claim_allowed=true", line)

        forbidden_unlocks = (
            "stable_claim_allowed=true",
            "complete_sdk_claim_allowed=true",
            "public_sdk_ready=true",
            "sdk_ready=true",
            "sdk_claim_ready=true",
            "runtime_ready=true",
            "current_route_blocker=identity_public_contract_gate_missing",
            "sdk_progress=12/12",
            "p0_progress=4/4",
            "SDK `12/12`",
            "P0 `4/4`",
        )
        for phrase in forbidden_unlocks:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, statement)

    def test_june4_fast_path_keeps_current_head_artifacts_as_non_approval(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        guardrail = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )

        for phrase in (
            "Current-head offline fixes",
            "continuous-development cadence",
            "closed sub-agent or all-six-agents-closed notes",
            "package-shape/install success",
            "package installs",
            "exact-version `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks",
            "`source_overclaim_total_flag_count=0`",
            "passing local tests",
            "local validation results",
            "the latest validation pass",
            "six-agent closure notes",
            "`.codex` cleanup",
            "scoped release statements",
            "request/preflight artifacts",
            "passive monitor ticks",
            "passive monitor output",
            "organic player presence",
            "diagnostic candidate lines",
            "`fastest_next_sdk_unblock` objects",
            "generated repo temp dirs",
            "passive snapshots",
            "Mission copied-bool fixture-boundary reports",
            "internal Mission copied-bool summaries",
            "Inventory copied-signal stability reports",
            "Transfer `bAccept` readiness reports",
            "Transfer ScriptStruct readiness",
            "Buff fixture manifest/source binding",
            "Dino scalar readiness",
            "route post-evidence P0 lock simulation",
            "Mission/Transfer/Dino/Tribe umbrella accounting",
        ):
            with self.subTest(artifact=phrase):
                self.assertIn(phrase, guardrail)

        self.assertIn("review/planning artifacts only", guardrail)
        self.assertIn("candidate-only/non-authorizing", guardrail)
        self.assertIn(
            "cannot be read as SDK completion, runtime readiness, live ops approval, P0 progress",
            guardrail,
        )
        self.assertIn("SDK/P0/runtime progress", guardrail)
        self.assertIn("stable readiness", guardrail)
        self.assertIn("public/stable progress", guardrail)
        self.assertIn(
            "They do not authorize live ops, server/log reads, deploy/restart/marker/env changes, server-operation approval, approved runtime evidence, runtime readiness, public SDK readiness, or complete SDK progress",
            guardrail,
        )
        self.assertIn("offline evidence-only and planning-only", guardrail)
        self.assertIn("public Mission SDK", guardrail)
        self.assertIn("v1 completion", guardrail)
        self.assertIn("transfer authority", guardrail)
        self.assertIn("reward/mutation authority", guardrail)
        self.assertIn("server authorization", guardrail)
        self.assertIn(
            "Sub-agent closure, repeated local hardening rounds, install/package shape success, exact-version `COMPONENTS SDK` package-shape validation, zero `source_overclaim_total_flag_count`, the latest validation pass, `.codex` cleanup, and local validation results are process/accounting hygiene only",
            guardrail,
        )
        self.assertIn("they do not move SDK, P0, or v1 counters", guardrail)
        self.assertIn("cannot substitute for accepted runtime evidence or current-turn operator approval", guardrail)
        self.assertIn("cleanup/test artifacts only", guardrail)
        self.assertIn("not handoff evidence", guardrail)
        self.assertIn("tests/core/PlayerIdentityPromotion*", guardrail)
        self.assertIn("tests/sdk_consumer/player_identity_promotion*", guardrail)
        self.assertIn("fresh current-turn operator approval for the exact active operation", guardrail)
        self.assertIn("accepted copied `PlayerPrincipalLifecycleObserver event` lines", guardrail)
        for event_name in ("session_start", "session_start_rejected", "session_end"):
            with self.subTest(event=event_name):
                self.assertIn(event_name, guardrail)
        self.assertIn("approved_runtime_evidence_missing", guardrail)
        self.assertIn("complete_sdk_ready=false", guardrail)
        self.assertIn("complete_sdk_progress_ratio=0/12", guardrail)
        self.assertIn("stable_claim_allowed=false", guardrail)

    def test_player_backed_notice_must_be_sent_before_evidence_window(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")

        fast_guardrail = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## 2026-06-04 20:30 Second Supervised Integration", 1
            )[0]
        )
        evidence_siblings = normalized(
            fast_path.split("## Required Evidence Siblings", 1)[1].split("## Non-Claims", 1)[0]
        )
        readme_compact = normalized(readme)

        for label, text in (
            ("fast-path", fast_guardrail),
            ("README", readme_compact),
        ):
            with self.subTest(doc=label, invariant="notice action"):
                self.assertIn("beta testers Discord", text)
                self.assertIn("approved dry-run-checked notice", text)
                self.assertIn("player_notice_action", text)
                self.assertIn("notice dry-run output", text)
                self.assertIn("sent-notice attestation", text)
                self.assertRegex(text, r"sent before .*")
                self.assertIn("documented but not sent", text)
            with self.subTest(doc=label, invariant="not documentation-only"):
                self.assertIn("executable", text)
                self.assertRegex(text, r"not (?:a )?passive")
                self.assertIn("evidence intake", text)
            with self.subTest(doc=label, invariant="notice action non-authorization"):
                self.assertIn("communication", text)
                self.assertRegex(text, r"not .*runtime evidence")
                self.assertIn("live-ops approval", text)
                self.assertRegex(text, r"SDK(?:/P0)? progress")
                self.assertIn("public readiness", text)
                self.assertIn("public SDK readiness", text)

        self.assertIn("executable required action, not a passive note", fast_guardrail)
        self.assertIn("request the missing notice/send scope", fast_guardrail)
        self.assertIn(CURRENT_TURN_EXACT_SCOPE, readme_compact)
        self.assertIn(
            "That standing authority survives compaction until revoked, but it is authorization only",
            readme_compact,
        )
        self.assertIn("copied-log analysis", readme_compact)
        self.assertIn("They do not count as runtime evidence", readme_compact)
        self.assertIn("not enough for the window or its evidence intake", readme_compact)
        self.assertIn("sent-notice attestation", evidence_siblings)
        for phrase in (
            "approved notice path",
            "dry-run result",
            "send action",
            "send timestamp",
            "reviewer/operator scope",
            "blocks approved evidence intake",
            "secret-free metadata only",
            "webhook token",
            "secret environment assignment",
            "secret-bearing dry-run output",
            "communication proof only",
            "live-ops approval",
            "SDK progress",
            "public readiness",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, evidence_siblings)

    def test_approved_evidence_bundles_stay_non_authorizing_non_claims(self) -> None:
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")

        fast_guardrail = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )
        readme_compact = normalized(readme)

        for label, text in (
            ("fast-path", fast_guardrail),
            ("README", readme_compact),
        ):
            with self.subTest(doc=label, invariant="consume-only"):
                self.assertIn("Approved evidence intake", text)
                self.assertIn("consume-only and non-authorizing", text)
                self.assertIn("checker-accepted approved runtime bundle", text)
                self.assertIn("approved_runtime_evidence_missing", text)
            with self.subTest(doc=label, invariant="non-claim"):
                self.assertIn("SDK/P0 progress", text)
                self.assertIn("public SDK readiness", text)
                self.assertIn("runtime readiness", text)
                self.assertIn("publication", text)
                self.assertIn("complete/stable SDK", text)

    def test_research_index_keeps_package_shape_and_local_validation_as_non_claims(self) -> None:
        readme = normalized((REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8"))

        for phrase in (
            "Request packs",
            "package-shape/install success",
            "exact-version `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks",
            "package installs",
            "support-tier labels",
            "prior approvals",
            "historical live approvals/map names",
            "historical approvals/map names",
            "passing local tests",
            "local validation results",
            "the latest validation pass",
            "six-agent closure notes",
            "`.codex` cleanup",
            "scoped release statements",
            "release-readiness passes",
            "copied evidence bundle shape",
            "closure requests",
            "evidence-closure reports",
            "Discord notice drafts",
            "CMake/header checks",
            "public reachability",
            "passive observation",
            "passive monitor output",
            "passive monitors",
            "passive summaries",
            "passive snapshots",
            "passive triplets",
            "diagnostic candidate lines",
            "diagnostic logs",
            "status reports",
            "status-helper route reports",
            "`progress_normalization_trace`",
            "source_overclaim diagnostics",
            "`source_overclaim_total_flag_count=0`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

        for phrase in (
            "Notice actions have the same boundary",
            "they are not evidence-window approval",
            "unless both `docs/agent-handoff/CURRENT.md` and",
            "record an active standing launch authority",
            "Historical TheIsland/Ragnarok/Genesis2 material",
            "prior approvals",
            "authorization only",
            "closed-agent accounting and `.codex` cleanup are process hygiene only",
            "Plugin Hub publication",
            "approved in-game evidence",
            "accounting or diagnostic artifacts only",
            "They do not move SDK, P0, or v1 counters",
            "cannot be reused as complete SDK readiness",
            "SDK evidence",
            "approved in-game evidence",
            "SDK/P0 progress",
            "public SDK readiness",
            "runtime readiness",
            "live-op authorization",
            "Discord authorization",
            "publication authority",
            "Plugin Hub readiness",
            "package-shape/public package readiness",
            "live-ops approval",
            "stable SDK claim",
            "stable SDK claims",
            "Ragnarok role-complete passive triplet",
            "is diagnostic-only/passive and is not the accepted copied approved sibling-set bundle",
            "Genesis2 still lacks `session_end`",
            "SDK `0/12`",
            "P0 `0/4`",
            "stable_claim_allowed=false",
            "approved_runtime_evidence_missing",
        ):
            with self.subTest(boundary=phrase):
                self.assertIn(phrase, readme)

        for positive_claim in (
            "package_shape_counts_toward_sdk=true",
            "local_validation_counts_toward_p0=true",
            "passive_monitor_counts_toward_sdk=true",
            "diagnostic_candidates_count_as_runtime_evidence=true",
            "bundle_shape_counts_toward_complete_sdk=true",
            "public_reachability_authorizes_live_ops=true",
            "closure_request_authorizes_runtime_capture=true",
            "notice_action_counts_toward_sdk_progress=true",
            "diagnostic_logs_count_as_runtime_evidence=true",
            "passive_triplet_counts_as_approved_evidence=true",
            "status_report_counts_toward_p0=true",
            "progress_normalization_trace_counts_toward_p0=true",
            "source_overclaim_diagnostics_count_as_runtime_evidence=true",
            "source_overclaim_total_flag_count_zero_counts_as_stable_sdk=true",
            "latest_validation_pass_counts_toward_p0=true",
            "six_agent_closure_authorizes_live_ops=true",
            "codex_cleanup_counts_as_sdk_evidence=true",
            "exact_components_sdk_package_shape_counts_as_plugin_hub_readiness=true",
            "release_readiness_pass_authorizes_runtime=true",
            "package_installs_authorize_public_package_readiness=true",
            "historical_approvals_map_names_authorize_live_ops=true",
            "historical_live_approvals_map_names_authorize_live_ops=true",
            "passive_monitors_approve_plugin_hub_readiness=true",
        ):
            with self.subTest(claim=positive_claim):
                self.assertNotIn(positive_claim, readme.lower())

    def test_compaction_invariants_preserve_no_evidence_notice_passive_and_server_auth(self) -> None:
        fast_path = normalized(
            (REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md").read_text(
                encoding="utf-8"
            )
        )
        readme = normalized((REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8"))

        for label, text in (
            ("fast-path", fast_path),
            ("README", readme),
        ):
            with self.subTest(doc=label, invariant="compaction sentence"):
                self.assertIn("Compaction invariant for future agents", text)
                self.assertIn("no complete approved in-game evidence exists yet", text)
                self.assertIn("communication artifacts, not evidence", text)
                self.assertIn("passive diagnostics are diagnostic-only/non-evidence", text)
                if label == "README":
                    self.assertIn("closed-agent accounting and `.codex` cleanup are process hygiene only", text)
                self.assertRegex(text, r"no standby sub-agent remains")
                self.assertRegex(text, r"no current-turn server authorization")
                if label == "README":
                    self.assertIn("live reads of server state or logs", text)
                    self.assertIn("marker/env changes", text)
                    self.assertIn("Discord sends", text)
                    self.assertIn("runtime capture", text)
            with self.subTest(doc=label, invariant="route locked"):
                self.assertIn("approved_runtime_evidence_missing", text)
                self.assertIn("stable_claim_allowed=false", text)
            with self.subTest(doc=label, invariant="no positive flags"):
                self.assertNotIn("complete_approved_in_game_evidence=true", text)
                self.assertNotIn("beta_notice_is_evidence=true", text)
                self.assertNotIn("passive_diagnostics_are_evidence=true", text)
                self.assertNotIn("standby_sub_agent_open=true", text)
                self.assertNotIn("current_turn_server_authorization=true", text)

    def test_checkjoin_gap_round_preserves_authority_and_non_evidence_boundaries(self) -> None:
        current_text = (REPO_ROOT / "docs/agent-handoff/CURRENT.md").read_text(encoding="utf-8")
        compact_text = (REPO_ROOT / "docs/agent-handoff/COMPACT_CONTEXT.md").read_text(encoding="utf-8")
        note_text = (
            REPO_ROOT / "docs/research/2026-06-07-checkjoin-runtime-evidence-gap.md"
        ).read_text(encoding="utf-8")

        for header, text in (
            ("## Active Objective", current_text),
            ("## Live Authority And Safety", current_text),
            ("## 2026-06-08 Event-Split Offline Integration Round", compact_text),
            ("## Event-Split And Post-Runtime Contract Prep", note_text),
        ):
            with self.subTest(header=header):
                self.assertIn(header, text)

        active_objective = normalized(
            current_text.split("## Active Objective", 1)[1].split("## Live Authority And Safety", 1)[0]
        )
        live_authority = normalized(
            current_text.split("## Live Authority And Safety", 1)[1].split("## Latest Development State", 1)[0]
        )
        compact_resume = normalized(
            compact_text.split("## Resume Protocol", 1)[1].split("## Standing Live-Ops Authorization", 1)[0]
        )
        compact_event_round = normalized(
            compact_text.split("## 2026-06-08 Event-Split Offline Integration Round", 1)[1].split(
                "## Canonical References",
                1,
            )[0]
        )
        note_scope = normalized(note_text.split("## Scope", 1)[1].split("## Audited Inputs", 1)[0])
        event_split = normalized(
            note_text.split("## Event-Split And Post-Runtime Contract Prep", 1)[1]
        )
        note_compact = normalized(note_text)

        for phrase in (
            "route samples",
            "beta notices",
            "package-shape installs",
            "status reports remain non-evidence and non-progress",
        ):
            with self.subTest(section="active objective", phrase=phrase):
                self.assertIn(phrase, active_objective)
        self.assertIn("Technical progress alone is not runtime evidence or readiness", live_authority)
        self.assertIn("standing authority is preserved as authorization only, not evidence or readiness", live_authority)
        self.assertIn("preserve the standing launch authority and safety limits", compact_resume)
        self.assertIn("do not convert that authority into runtime evidence, SDK/P0 progress", compact_resume)

        self.assertIn("non-authorizing research facts only", note_scope)
        self.assertIn("does not claim approved runtime evidence, runtime readiness", note_scope)
        self.assertIn("progress against SDK/P0 counters", note_scope)

        for phrase in (
            "ready_log_evidence_split",
            "obelisk.player-principal-lifecycle-ready-log-copy-evidence-split.v1",
            "player_principal_lifecycle_event_split_summary",
            "diagnostic and routing aids only",
            "approved_runtime_evidence=false",
            "runtime_evidence_ready=false",
            "public_sdk_ready=false",
            "SDK/P0 progress `0`",
            "do not authorize runtime work",
            "diagnostic lines or start/end-only material still cannot be bundled/promoted",
            "post_runtime_contract_gap_diagnostic",
            "once the approved runtime principal lifecycle bundle exists",
            "fail-closed",
        ):
            with self.subTest(section="event split", phrase=phrase):
                self.assertIn(phrase, event_split)

        for phrase in (
            "diagnostic_route_sample_non_evidence",
            "does not read params, copy player identity, dispatch events, satisfy lifecycle roles, or count toward runtime evidence",
            "The new route-sample action preserves `approved_runtime_evidence=false`, `runtime_ready=false`, `public_sdk_ready=false`, and SDK/P0 progress `0`",
            "as package-shape/install evidence only",
            "notice artifacts, status reports, and planning-source artifacts do not clear it",
            "Do not treat them as approved runtime evidence, second-source evidence, public SDK readiness",
        ):
            with self.subTest(section="checkjoin note", phrase=phrase):
                self.assertIn(phrase, note_compact)

        for phrase in (
            "All six agents completed or were closed by lead; no standby sub-agent remains",
            "No live/server/RCON/Discord/deploy/marker/env/GitHub/release operation occurred",
            "keeping every split path non-evidence",
            "without granting runtime authorization or progress",
        ):
            with self.subTest(section="compact event round", phrase=phrase):
                self.assertIn(phrase, compact_event_round)

        combined = normalized(f"{current_text}\n{compact_text}\n{note_text}").lower()
        for positive_claim in (
            "event_split_counts_toward_sdk=true",
            "post_runtime_diagnostic_counts_toward_p0=true",
            "route_samples_count_as_runtime_evidence=true",
            "beta_notices_count_as_progress=true",
            "package_shape_counts_toward_sdk=true",
            "agent_closure_counts_as_evidence=true",
            "standing_authority_counts_as_readiness=true",
        ):
            with self.subTest(claim=positive_claim):
                self.assertNotIn(positive_claim, combined)

    def test_side_lane_accounting_stays_candidate_only_and_non_authorizing(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")
        readme_compact = normalized(readme)
        fast_compact = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )

        for label, text in (
            ("README", readme_compact),
            ("fast-path", fast_compact),
        ):
            with self.subTest(doc=label, invariant="named side lanes"):
                self.assertIn("Inventory copied-signal stability", text)
                self.assertIn("Mission copied-bool fixture-boundary", text)
                self.assertIn("Transfer `bAccept`", text)
                self.assertIn("Transfer ScriptStruct readiness", text)
                self.assertIn("Buff fixture manifest/source binding", text)
                self.assertIn("Dino scalar readiness", text)
                self.assertIn("route post-evidence P0 lock simulation", text)
                self.assertIn("Mission/Transfer/Dino/Tribe umbrella accounting", text)
            with self.subTest(doc=label, invariant="non-authorizing boundary"):
                self.assertIn("candidate-only/non-authorizing", text)
                self.assertIn("SDK completion", text)
                self.assertIn("SDK/P0/runtime progress", text)
                self.assertIn("runtime readiness", text)
                self.assertIn("live ops approval", text)
                self.assertIn("P0 progress", text)
                self.assertIn("approved runtime evidence", text)
                self.assertIn("public SDK readiness", text)
                self.assertIn("stable readiness", text)
                self.assertIn("server/log reads", text)

        latest_round = normalized(
            fast_path.split("## 2026-06-05 Transfer/Buff/Dino Side-Lane Guardrail Round", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )
        for phrase in (
            "Transfer ScriptStruct, Buff manifest/source binding, Dino scalar, and accounting-integration results",
            "candidate-only/non-authorizing",
            "do not authorize live ops, server/log reads",
            "SDK/P0/runtime/public/stable progress",
            "Transfer/Buff/Dino SDK readiness",
            "runtime readiness",
            "public SDK readiness",
            "P0 progress",
            "stable SDK status",
        ):
            with self.subTest(doc="latest-round", phrase=phrase):
                self.assertIn(phrase, latest_round)

        for positive_claim in (
            "inventory_copied_signal_stability_counts_toward_p0=true",
            "mission_fixture_boundary_counts_toward_sdk=true",
            "transfer_baccept_runtime_ready=true",
            "transfer_scriptstruct_counts_toward_sdk=true",
            "buff_fixture_source_binding_counts_toward_p0=true",
            "dino_scalar_counts_toward_p0=true",
            "dino_scalar_public_sdk_ready=true",
            "post_evidence_p0_lock_simulation_counts_toward_runtime=true",
            "mission_transfer_dino_tribe_umbrella_p0_progress=true",
            "side_lane_live_ops_approved=true",
            "side_lane_server_log_reads_authorized=true",
        ):
            with self.subTest(claim=positive_claim):
                self.assertNotIn(positive_claim, f"{readme_compact} {fast_compact}".lower())

    def _documented_identity_bundle_flags(
        self, path: Path, section_start: str, section_end: str
    ) -> set[str]:
        text = path.read_text(encoding="utf-8")
        section = text.split(section_start, 1)[1].split(section_end, 1)[0]
        commands = re.findall(r"```bash\n(.*?)```", section, flags=re.DOTALL)
        bundle_commands = [
            command
            for command in commands
            if "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py" in command
        ]
        self.assertEqual(len(bundle_commands), 1)
        bundle_command = bundle_commands[0].split(
            "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", 1
        )[1].split("\n\n", 1)[0]
        return set(re.findall(r"(?m)(?<!<)--[a-z0-9-]+", bundle_command))

    def _assert_identity_bundle_flags_match_builder_cli(self, documented_flags: set[str]) -> None:
        parser = identity_bundle_builder.parse_args
        parser_source = (REPO_ROOT / "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py").read_text(
            encoding="utf-8"
        )
        supported_flags = set(re.findall(r'add_argument\("([^"]+)"', parser_source))

        self.assertIs(parser, identity_bundle_builder.parse_args)
        self.assertTrue(documented_flags)
        self.assertEqual(documented_flags - supported_flags, set())
        self.assertIn("--copied-log", documented_flags)
        self.assertIn("--window-manifest", documented_flags)
        self.assertIn("--output-dir", documented_flags)
        self.assertIn("--obelisk-commit", documented_flags)
        self.assertIn("--reviewed-by", documented_flags)
        self.assertIn("--review-note", documented_flags)
        self.assertNotIn("--post-window-replay", documented_flags)
        self.assertNotIn("--json", documented_flags)

    def test_resourcehandle_research_and_handoff_do_not_claim_readiness(self) -> None:
        scanned_paths = [
            REPO_ROOT / "docs" / "agent-handoff" / "CURRENT.md",
            *sorted((REPO_ROOT / "docs" / "research").glob("*resource*handle*.md")),
            *sorted((REPO_ROOT / "docs" / "research").glob("*uobject*flag*.md")),
        ]
        forbidden_literals = (
            "public_resource_handle_ready=true",
            "resource_handle_ready=true",
            "post_callback_resource_handle_ready=true",
            "uobject_flags_validity_semantics_proven=true",
        )
        forbidden_positive_claims = (
            r"\b(?:public|promoted|supported|available|included)\s+ResourceHandle\s+(?:SDKs?|APIs?|surfaces?|lookup|contract)\b",
            r"\bResourceHandle\s+(?:SDKs?|APIs?|surfaces?|lookup|contract)\s+(?:is|are)\s+(?:public|promoted|supported|available|included|ready)\b",
            r"\b(?:ship|ships|shipped|promote|promotes|promoted|expose|exposes|exposed|publish|publishes|published|support|supports|supported)\s+(?:a\s+)?(?:public\s+)?ResourceHandle\s+(?:SDKs?|APIs?|surfaces?|lookup|contract)\b",
        )
        negated_claim_context = re.compile(
            r"\b(?:does\s+not|do\s+not|must\s+not|not|no|never|without|blocked|blocks|excludes?|outside|candidate-only|internal|until|separate)\b",
            re.IGNORECASE,
        )

        offenders: list[str] = []
        for path in scanned_paths:
            text = path.read_text(encoding="utf-8")
            compact = " ".join(text.split())
            for literal in forbidden_literals:
                if literal in compact:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {literal}")
            for pattern in forbidden_positive_claims:
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    context = text[max(0, match.start() - 100):match.start()]
                    if not negated_claim_context.search(context):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {pattern}")

        self.assertEqual(offenders, [])

    def test_resourcehandle_current_checkpoint_preserves_no_scan_blockers(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md"
        text = note.read_text(encoding="utf-8")
        section = text.split("## Current No-Scan Checkpoint", 1)[1].split(
            "## Next Repo-Local Improvement", 1
        )[0]

        for phrase in (
            "Do not rerun or request broad FName, GObjects, core, UFunction,",
            "ReflectionScanner, serial-sweep, or scanner-like discovery",
            "unless the\nbinary hash changes or new contradictory artifact evidence invalidates",
            "New repo-local work should consume the existing artifacts and produce only\n"
            "redacted schema/gate planning artifacts.",
            "resourcehandle-identity-complete-failclosed-20260530T165521Z/resourcehandle-revalidation.json",
            "resourcehandle-post-callback-contract-20260530T171910Z/post-callback-contract.json",
            "resourcehandle-serial-policy-20260530T190642Z/serial-policy.json",
            "preserve these exact blocker labels",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

        current_promote_blockers = [
            line.strip("- `")
            for line in section.split("Current strict promote blockers:", 1)[1]
            .split("Still-required ResourceHandle promotion blockers:", 1)[0]
            .splitlines()
            if line.startswith("- `")
        ]
        self.assertEqual(
            current_promote_blockers,
            [
                "promote_mode_serial_policy_candidate_only",
                "promote_mode_manifest_has_non_claims",
            ],
        )

        required_resourcehandle_blockers = [
            line.strip("- `")
            for line in section.split("Still-required ResourceHandle promotion blockers:", 1)[1]
            .split("Historical evaluator blockers", 1)[0]
            .splitlines()
            if line.startswith("- `")
        ]
        self.assertEqual(
            required_resourcehandle_blockers,
            [
                "public_resourcehandle_policy_missing",
                "no_public_resource_handle_contract",
                "no_rejected_runtime_object_samples",
                "no_serial_reuse_or_wraparound_policy",
                "post_callback_lifetime_policy_unproven",
                "no_version_matched_source_decompiler_correlation_for_public_lifecycle_names",
            ],
        )

        historical_blockers = [
            line.strip("- `")
            for line in section.split("Historical evaluator blockers to retain as provenance", 1)[1]
            .split("Blocker interpretation checkpoint:", 1)[0]
            .splitlines()
            if line.startswith("- `")
        ]
        self.assertEqual(
            historical_blockers,
            [
                "no_post_callback_lifetime_contract",
                "uobject_flags_validity_semantics_unproven",
            ],
        )

        interpretation = section.split("Blocker interpretation checkpoint:", 1)[1]
        for phrase in (
            "Offline/core scans cannot satisfy this.",
            "Unknown wraparound remains rejection unless separately planned.",
            "Do not treat negative rejection as public handle support.",
            "More flag sweeps do not clear this.",
            "public API exposure as a non-claim",
            "Do not convert any row in this table into a request for broad FName, GObjects, core,",
            "If a future note\ncannot name which blocker it narrows and which canonical input it consumes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, interpretation)

    def test_resourcehandle_blocker_interpretation_matches_evaluator_blockers(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md"
        text = note.read_text(encoding="utf-8")
        section = text.split("## Current No-Scan Checkpoint", 1)[1].split(
            "## Next Repo-Local Improvement", 1
        )[0]

        expected_evaluator_blockers = set(resourcehandle_evaluator.RESOURCE_HANDLE_LIFETIME_BLOCKERS)
        expected_evaluator_blockers.add(resourcehandle_evaluator.BLOCKER_UOBJECT_FLAGS)

        still_required_blockers = [
            line.strip("- `")
            for line in section.split("Still-required ResourceHandle promotion blockers:", 1)[1]
            .split("Historical evaluator blockers", 1)[0]
            .splitlines()
            if line.startswith("- `")
        ]
        historical_blockers = [
            line.strip("- `")
            for line in section.split("Historical evaluator blockers to retain as provenance", 1)[1]
            .split("Blocker interpretation checkpoint:", 1)[0]
            .splitlines()
            if line.startswith("- `")
        ]

        interpretation = section.split("Blocker interpretation checkpoint:", 1)[1].split(
            "Do not convert any row in this table", 1
        )[0]
        table_blockers: list[str] = []
        for line in interpretation.splitlines():
            if not line.startswith("| `"):
                continue
            first_cell = line.split("|", 2)[1]
            table_blockers.extend(re.findall(r"`([^`]+)`", first_cell))

        documented_blockers = still_required_blockers + historical_blockers
        self.assertEqual(set(documented_blockers), expected_evaluator_blockers)
        self.assertEqual(set(table_blockers), expected_evaluator_blockers)
        self.assertEqual(len(table_blockers), len(expected_evaluator_blockers))

        payload = resourcehandle_evaluator.build_evaluation(
            [
                {
                    "schema": resourcehandle_evaluator.GOBJECTS_RECONCILIATION_SCHEMA,
                    "samples": [
                        {
                            "status": "candidate-uobject",
                            "item_dword_0x8": 17,
                            "membership": {"passes": True},
                        }
                    ],
                    "summary": {
                        "sample_count": 1,
                        "accepted_count": 1,
                        "rejected_count": 0,
                        "membership_pass_count": 1,
                    },
                }
            ],
            {
                "schema": resourcehandle_evaluator.STATIC_GLOBAL_EVIDENCE_SCHEMA,
                "candidates": [
                    {
                        "kind": "gobjects",
                        "static_contract": {
                            "satisfied": True,
                            "blockers": [],
                            "coherent_window": {"redacted_fixture": True},
                        },
                    }
                ],
            },
        )
        self.assertTrue(expected_evaluator_blockers.issubset(set(payload["blockers"])))

    def test_no_obsolete_theisland_second_core_runbook_references(self) -> None:
        forbidden = [
            "theisland-second-core",
            "TheIsland second core",
            "run the existing isolated capture runbook only against\n",
            "0x12d1400 group is the best next decompiler target",
        ]
        offenders: list[str] = []
        for path in (REPO_ROOT / "docs").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")

        self.assertEqual(offenders, [])

    def test_second_core_runbook_prefers_dedicated_debug_instance(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-isolated-second-core-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Preferred target:", text)
        self.assertIn("arkserver-obelisk-debug", text)
        self.assertIn("Fallback target:", text)
        self.assertIn("arkserver2", text)
        self.assertIn("Protected target:", text)
        self.assertIn("arkserver` / Ragnarok", text)

    def test_second_core_runbook_does_not_reuse_primary_fname_root_slot(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-isolated-second-core-runbook.md"
        text = runbook.read_text(encoding="utf-8")
        offline_follow_up = text.split("## Offline Follow-Up", 1)[1]

        self.assertIn("--scan-only", offline_follow_up)
        self.assertIn("--json-plan", offline_follow_up)
        self.assertIn("--verified-fname-root-slot <verified-slot-from-this-artifact>", offline_follow_up)
        self.assertIn("--gobjects-candidate 0x595b7e0", offline_follow_up)
        self.assertIn("not copied from the\n  primary-core-only `0x5956f30` slot", offline_follow_up)
        self.assertNotIn("static_fname_root_slot=0x5956f30", offline_follow_up)
        self.assertNotIn("--binary /servidor/ark", offline_follow_up)
        self.assertNotIn("/servidor/ark/obelisk/dumps", offline_follow_up)

    def test_historical_core_dump_runbook_is_not_ragnarok_executable(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-arkserver-core-dump-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Historical runbook", text)
        self.assertIn("arkserver-obelisk-debug", text)
        self.assertNotIn("/servidor/ark/arkserver restart", text)
        self.assertNotIn("state/instances/arkserver/allow-ptrace", text)
        self.assertNotIn("ShooterGameServer Ragnarok", text)

    def test_runtime_debug_control_prefers_dedicated_debug_instance(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-runtime-debug-control.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("arkserver-obelisk-debug", text)
        self.assertNotIn("/servidor/ark/arkserver restart", text)
        self.assertNotIn("state/instances/arkserver/enable-debug-control", text)

    def test_reflectionscanner_runbook_separates_debug_and_theisland_fallback(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Preferred dedicated-debug profile", text)
        self.assertIn("Fallback TheIsland profile", text)
        self.assertIn("only with explicit operator approval", text)
        self.assertNotIn("touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/disable-plugins\n./arkserver2 restart", text)

    def test_static_fname_capture_is_historical_not_ragnarok_retry(self) -> None:
        notes = [
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-live-capture.md",
            REPO_ROOT / "docs/research/2026-05-27-live-fname-reject-capture.md",
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-sampling.md",
        ]

        for note in notes:
            text = note.read_text(encoding="utf-8")
            self.assertIn("Historical", text, str(note))
            self.assertIn("arkserver-obelisk-debug", text, str(note))
            self.assertNotIn("/servidor/ark/arkserver start", text, str(note))

    def test_historical_fname_gobjects_routes_do_not_reopen_current_hash_discovery(self) -> None:
        route_docs = [
            REPO_ROOT / "docs/research/2026-05-27-arkserver-core-fname-evidence.md",
            REPO_ROOT / "docs/research/2026-05-27-fname-indirect-table-probe.md",
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-candidate.md",
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-live-capture.md",
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-probe.md",
            REPO_ROOT / "docs/research/2026-05-27-static-fname-root-sampling.md",
            REPO_ROOT / "docs/research/2026-05-27-core-gobjects-candidate.md",
            REPO_ROOT / "docs/research/2026-05-27-core-gobjects-next-development.md",
            REPO_ROOT / "docs/research/2026-05-27-gobjects-static-anchor-classification.md",
            REPO_ROOT / "docs/research/2026-05-29-static-gobjects-decompiler-tool-check.md",
            REPO_ROOT / "docs/research/2026-05-29-static-gobjects-field-window-audit.md",
            REPO_ROOT / "docs/research/2026-05-29-static-gobjects-same-fuobjectarray.md",
        ]
        stale_current_hash_instructions = (
            "Build and deploy the corrected ReflectionScanner.",
            "Run a short scanner capture with",
            "Use this FName resolver evidence as the base for `GObjects` discovery.",
            "Run `ReflectionScanner` only on an isolated/debug instance with plugins disabled.",
            "Run an isolated capture with `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`.",
            "Capture a short debug run with:",
            "Add a bounded table-content sampler",
            "Run this only on an isolated/debug ARK instance.",
            "Capture copied logs with `OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1`.",
            "Repeat the core/object enumeration against a second isolated capture",
            "repeat the classified static/context checks on a second isolated core or future binary.",
            "Repeat the same classification after a second isolated core or binary update",
            "Install or provide one bounded decompiler-capable tool path",
            "Run an independent static or isolated-core reconciliation",
            "second isolated runtime/core evidence pack with distinct artifact identity is still needed",
        )

        for path in route_docs:
            text = path.read_text(encoding="utf-8")
            compact = normalized(text)
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertIn("Current No-Repeat Checkpoint", text)
                self.assertIn("new binary hash", compact)
                self.assertIn("contradictory artifact evidence", compact)
                for phrase in stale_current_hash_instructions:
                    self.assertNotIn(phrase, compact)

        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        player_identity_route = readme.split("| Players identity lifecycle |", 1)[1].split(
            "\n", 1
        )[0]
        self.assertIn("approved_runtime_evidence_missing", player_identity_route)
        self.assertIn("Do not rerun broad FName/GObjects/core discovery", player_identity_route)

    def test_module_readiness_uses_current_debug_target_language(self) -> None:
        notes = [
            REPO_ROOT / "docs/research/2026-05-27-module-readiness-matrix.md",
            REPO_ROOT / "docs/research/2026-05-27-mission-tribe-function-snapshot-fixtures.md",
            REPO_ROOT / "docs/research/2026-05-27-structure-function-snapshot-fixtures.md",
            REPO_ROOT / "docs/research/2026-05-27-primaldinocharacter-function-inventory.md",
            REPO_ROOT / "docs/research/2026-05-27-primalbuff-snapshot-fixtures.md",
            REPO_ROOT / "docs/research/2026-05-27-chat-reflection-stack-cycle-guard.md",
            REPO_ROOT / "docs/research/2026-05-27-structure-runtime-observation-plan.md",
            REPO_ROOT / "docs/research/2026-05-28-inventory-observation-gate-plan.md",
            REPO_ROOT / "docs/research/2026-05-27-transfer-upload-download-fixture-triage.md",
            REPO_ROOT / "docs/research/2026-05-27-tribe-control-observation-fixture.md",
            REPO_ROOT / "docs/research/2026-05-27-inventory-controller-snapshot-fixtures.md",
            REPO_ROOT / "docs/research/2026-05-27-primalitem-function-inventory.md",
            REPO_ROOT / "docs/research/2026-05-27-real-core-ufunction-snapshot-fixtures.md",
        ]
        forbidden = [
            "TheIsland/debug",
            "TheIsland A/B",
            "gated to TheIsland",
            "Use only TheIsland",
            "TheIsland/debug-instance",
        ]

        offenders: list[str] = []
        for note in notes:
            text = note.read_text(encoding="utf-8")
            for phrase in forbidden:
                if phrase in text:
                    offenders.append(f"{note.relative_to(REPO_ROOT)}: {phrase}")

        self.assertEqual(offenders, [])

    def test_module_route_keeps_general_lanes_and_layout_boundary(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        roadmap = (
            REPO_ROOT / "docs/research/2026-05-29-module-surface-roadmap.md"
        ).read_text(encoding="utf-8")
        readiness = (
            REPO_ROOT / "docs/research/2026-05-27-module-readiness-matrix.md"
        ).read_text(encoding="utf-8")
        taxonomy = (
            REPO_ROOT / "docs/research/2026-05-27-sdk-module-taxonomy.md"
        ).read_text(encoding="utf-8")

        lane_names = (
            "Inventory lane",
            "Structures lane",
            "Items lane",
            "Mission lane",
            "Transfer lane",
            "Buff lane",
            "Dino lane",
            "Tribe lane",
            "Admin/permissions lane",
        )
        readme_compact = normalized(readme)
        for lane in lane_names:
            with self.subTest(file="docs/research/README.md", lane=lane):
                self.assertIn(lane, readme_compact)

        roadmap_compact = normalized(roadmap)
        for phrase in (
            "Recommended lane order",
            "Next v1 Round Recommendation",
            "hub foundation",
            "gameplay policy backing",
            "internal recognizer planning",
            "No-repeat rules for this round",
            "Promotion gate for every module lane",
            "exact layout target set",
            "do not turn target-set labels into public SDK names",
            "Do not rerun broad FName, GObjects, UFunction, ReflectionScanner, core, or serial-sweep discovery",
            "Do not route work back to chat as the roadmap center",
            "structures lane",
            "inventory lane",
            "items lane",
            "mission lane",
            "transfer lane",
            "buff lane",
            "dino lane",
            "tribe lane",
            "admin/permissions lane",
        ):
            with self.subTest(file="docs/research/2026-05-29-module-surface-roadmap.md", phrase=phrase):
                self.assertIn(phrase, roadmap_compact)

        for phrase in (
            "Next v1 research round",
            "hub foundation first",
            "`GameplayPolicyEvent` backing evidence",
            "mission copied-bool internal planning",
            "Do not repeat broad discovery on the current binary",
            "do not promote new SDK modules",
            "do not recenter the roadmap on chat",
        ):
            with self.subTest(file="docs/research/README.md", phrase=phrase):
                self.assertIn(phrase, readme_compact)

        for path, text in (
            ("docs/research/2026-05-27-module-readiness-matrix.md", readiness),
            ("docs/research/2026-05-27-sdk-module-taxonomy.md", taxonomy),
        ):
            compact = normalized(text)
            compact_lower = compact.lower()
            for phrase in (
                "not the product center",
            ):
                with self.subTest(file=path, phrase=phrase):
                    self.assertIn(phrase, compact_lower)
            for phrase in (
                "Inventory, structures, items, mission, transfer, buff, dino, tribe, and admin/permissions",
                "independent promotion gates",
            ):
                with self.subTest(file=path, phrase=phrase):
                    self.assertIn(phrase, compact)

    def test_static_reversing_artifacts_do_not_read_as_current_runtime_or_sdk_readiness(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        direct_route = (
            REPO_ROOT / "docs/research/2026-06-03-direct-route-approved-runtime-binding.md"
        ).read_text(encoding="utf-8")
        rc_gate = (
            REPO_ROOT / "docs/research/2026-05-30-rc-second-source-release-gate-check.md"
        ).read_text(encoding="utf-8")
        head_refresh = (
            REPO_ROOT / "docs/research/2026-05-30-head-rc-second-source-refresh-gap.md"
        ).read_text(encoding="utf-8")
        minimal = (
            REPO_ROOT / "docs/research/2026-05-29-minimal-second-source-readiness.md"
        ).read_text(encoding="utf-8")
        capability_map = (
            REPO_ROOT / "docs/research/2026-05-30-v1-core-capability-map.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("broader production-ready Obelisk core", capability_map)
        self.assertIn("broader evidence-gated Obelisk core", capability_map)

        self.assertIn("not a current evidence artifact", normalized(direct_route))
        self.assertIn("does not record a current approved runtime target", normalized(direct_route))

        readme_compact = normalized(readme)
        self.assertIn("Historical module runtime hit", readme_compact)
        self.assertIn("not current approved runtime evidence", readme_compact)

        for path, text in (
            ("2026-05-30-rc-second-source-release-gate-check.md", rc_gate),
            ("2026-05-30-head-rc-second-source-refresh-gap.md", head_refresh),
            ("2026-05-29-minimal-second-source-readiness.md", minimal),
        ):
            compact = normalized(text)
            with self.subTest(path=path):
                self.assertRegex(compact, r"promotion_gate(?:\.| )ready=true")
                self.assertIn("not current approved runtime evidence", compact)
                self.assertIn("public SDK promotion", compact)
                self.assertIn("stable production readiness", compact)

        self.assertIn("historical RC layout-gate output", normalized(rc_gate))
        self.assertIn("RC UFunction layout-gate output", normalized(head_refresh))
        self.assertIn("named-target-set layout readiness only", normalized(minimal))
        self.assertIn("promotion_gate.promotion_ready=false", minimal)

    def test_inventory_mission_route_lock_stays_internal_and_non_promoting(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        next_candidate = (
            REPO_ROOT / "docs/research/2026-05-29-next-internal-module-candidate.md"
        ).read_text(encoding="utf-8")
        mission = (
            REPO_ROOT / "docs/research/2026-05-29-mission-reflection-internal-readiness.md"
        ).read_text(encoding="utf-8")
        primalitem = (
            REPO_ROOT / "docs/research/2026-05-27-primalitem-function-inventory.md"
        ).read_text(encoding="utf-8")

        readme_compact = normalized(readme)
        for phrase in (
            "offline hardening target is boundary preservation",
            "Inventory may use only the already promoted copied/redacted `GameplayPolicyEvent` lane",
            "Mission remains internal/test-only copied-bool planning",
            "Neither lane is a public Inventory SDK, public Mission SDK, new capability family",
            "identity/lookup contract, mutation path, return override, or server-observation approval",
        ):
            with self.subTest(file="docs/research/README.md", phrase=phrase):
                self.assertIn(phrase, readme_compact)

        next_compact = normalized(next_candidate)
        for phrase in (
            "2026-05-31 Inventory/Mission Offline Hardening Audit",
            "do not treat the older `sdk.inventory` recommendation as a new SDK or runtime-observer request",
            "Mission remains internal/test-only",
            "must not be routed into `ProcessEventHook.cpp`, a dispatcher, public Mission SDK",
            "the next useful offline hardening for v1.0 is docs/guardrail hardening",
            "The next real gate is a separate runtime-observation and lifecycle review",
        ):
            with self.subTest(
                file="docs/research/2026-05-29-next-internal-module-candidate.md",
                phrase=phrase,
            ):
                self.assertIn(phrase, next_compact)

        mission_compact = normalized(mission)
        for phrase in (
            "2026-05-31 Offline Audit Checkpoint",
            "exactly five copied canonical one-byte bool fields",
            "Do not reopen this lane as Mission SDK design",
            "does not authorize edits to `ProcessEventHook.cpp`",
            "public Mission capability bits, plugin callbacks",
        ):
            with self.subTest(
                file="docs/research/2026-05-29-mission-reflection-internal-readiness.md",
                phrase=phrase,
            ):
                self.assertIn(phrase, mission_compact)

        primalitem_compact = normalized(primalitem)
        for phrase in (
            "The original next-step list is historical discovery guidance",
            "`PrimalItem.CanUse` and `PrimalItem.AllowRemoteAddToInventory` are part of the compact inventory backing",
            "`AllowEquipItem`, `CanRepair`, and `UseItemOntoItem` are handled by the separate return-only item policy slice",
            "Do not use this older inventory survey to justify a public Items SDK, public Inventory SDK",
            "The next offline hardening is to preserve those exclusions in route and docs guardrails",
        ):
            with self.subTest(
                file="docs/research/2026-05-27-primalitem-function-inventory.md",
                phrase=phrase,
            ):
                self.assertIn(phrase, primalitem_compact)

    def test_mission_copied_bool_fixture_boundary_reports_are_non_claims(self) -> None:
        mission_plan = (
            REPO_ROOT / "docs/research/2026-05-30-mission-copied-bool-observer-plan.md"
        ).read_text(encoding="utf-8")
        fast_path = (
            REPO_ROOT / "docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md"
        ).read_text(encoding="utf-8")

        mission_boundary = normalized(
            mission_plan.split("## Fixture-Boundary / Internal Report Boundary", 1)[1].split(
                "## Future-Agent Bridge Lane", 1
            )[0]
        )
        fast_guardrail = normalized(
            fast_path.split("## Durable Guardrail", 1)[1].split(
                "## Required Evidence Siblings", 1
            )[0]
        )

        for label, text in (
            ("mission-plan", mission_boundary),
            ("fast-path", fast_guardrail),
        ):
            with self.subTest(doc=label, invariant="fixture-boundary scope"):
                self.assertIn("Mission copied-bool", text)
                self.assertIn("offline evidence-only and planning-only", text)
            for phrase in (
                "public Mission SDK",
                "runtime readiness",
                "v1 completion",
                "transfer authority",
                "reward/mutation authority",
                "server authorization",
                "operator approval",
                "live-observation approval",
            ):
                with self.subTest(doc=label, phrase=phrase):
                    self.assertIn(phrase, text)

        for phrase in (
            "excluded demand signals",
            "must not be turned into callback authority",
            "copied payload authority",
            "transfer or reward authority",
            "server-side authorization",
            "SDK completion evidence",
            "the latest validation pass",
            "six-agent closure notes",
            "`.codex` cleanup",
        ):
            with self.subTest(file="mission-plan", phrase=phrase):
                self.assertIn(phrase, mission_boundary)

        forbidden_positive_flags = (
            "mission_sdk_ready=true",
            "public_mission_sdk_ready=true",
            "mission_runtime_ready=true",
            "mission_v1_completion_ready=true",
            "mission_transfer_authority=true",
            "mission_reward_authority=true",
            "mission_mutation_authority=true",
            "server_authorization=true",
        )
        combined = f"{mission_boundary} {fast_guardrail}".lower()
        for flag in forbidden_positive_flags:
            with self.subTest(flag=flag):
                self.assertNotIn(flag, combined)

    def test_second_source_intake_runbook_keeps_planner_phases_explicit(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-28-second-source-core-intake-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Full-intake planning is offline and does not touch any live server", text)
        self.assertIn("abort broad\nFName-table scans and plan the full sequence with direct root validation", text)
        self.assertIn("scripts/scan_core_fname_tables.py", text)
        self.assertIn("--root-slot <verified-slot>", text)
        self.assertIn("--require-exact-root", text)
        self.assertIn("fname-root-validation/core.fname-root-validation.json", text)
        self.assertIn("--scan-only", text)
        self.assertIn("only while deriving and reviewing an artifact-specific FName root for a\nnew binary hash", text)
        self.assertIn("cannot be\nmistaken for GObjects sampling or snapshot comparison", text)
        self.assertIn("--json-plan", text)
        self.assertIn("obelisk.second-source-core-intake-plan.v1", text)
        self.assertIn("stores both argv and shell-rendered commands", text)
        self.assertIn("incompatible with\n`--execute`", text)
        self.assertIn("--fail-on-readiness-gaps", text)
        self.assertIn("promotion_gate.ready=true", text)
        self.assertIn("reject direct or symlink-resolved live-server roots under\n`/servidor/ark`", text)
        self.assertIn("store large raw captures under\n`/servidor/ark/obelisk/dumps`", text)
        self.assertIn("promotion tooling must consume\nhardlinked or copied offline artifacts from the workspace", text)
        self.assertIn("`/servidor/ark/workspace-offline`", text)
        self.assertIn("contains UFunction snapshot\ntargets before expensive", text)
        self.assertIn("`--verified-fname-root-slot` and `--gobjects-candidate` take raw non-negative addresses", text)
        self.assertIn("not `LABEL=ADDR`", text)
        self.assertIn("`--fname-index` takes either `LABEL=INDEX` or a raw\nnon-negative index", text)
        self.assertIn("`--gobjects-sample-index` takes a non-negative integer", text)

    def test_structure_build_policy_triage_stays_second_wave_offline_only(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-30-structure-build-policy-triage.md"
        text = note.read_text(encoding="utf-8")

        required = (
            "`APrimalStructure.IsAllowedToBuild` is a valid post-RC research target",
            "Treat it as a second-wave structure build-policy candidate",
            "Do not add it to `structure-observer-intake`",
            "Those lanes do not promote public `StructureEvents`, build-policy SDK",
            "Return override/build denial is a separate mutation/authority feature and remains\n  blocked.",
            "Do not infer allow/deny constants\n  from ArkApi code.",
            "do not\npass an evidence-pack manifest to `--core`",
            "The inspector now rejects evidence-pack\nmanifests passed as `--core`",
            "use the snapshot regeneration\nconsumer for that manifest",
            "This triage does not promote a public Structure SDK, build-policy API",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_gameplay_policy_backing_docs_preserve_copied_data_boundaries(self) -> None:
        readiness = (
            REPO_ROOT / "docs/research/2026-05-29-public-gameplay-event-readiness-audit.md"
        ).read_text(encoding="utf-8")
        minimal = (
            REPO_ROOT / "docs/research/2026-05-29-minimal-second-source-readiness.md"
        ).read_text(encoding="utf-8")
        item_strict = (
            REPO_ROOT / "docs/research/2026-05-30-item-compact-redacted-signatures-strict.md"
        ).read_text(encoding="utf-8")
        structure_build = (
            REPO_ROOT / "docs/research/2026-05-30-structure-build-policy-triage.md"
        ).read_text(encoding="utf-8")
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")

        readiness_compact = normalized(readiness)
        for phrase in (
            '"item_return_backing_target_set": "item-return-only-policy-slice"',
            "structures: `structure-observer-intake`",
            "compact inventory checks: `minimal-second-source-intake`",
            "return-only item checks: `item-return-only-policy-slice`",
            "`INVENTORY_ALLOW_EQUIP_ITEM_CHECK` | `ReturnValue` bool only",
            "`INVENTORY_CAN_REPAIR_CHECK` | `ReturnValue` bool only",
            "`INVENTORY_USE_ITEM_ONTO_ITEM_CHECK` | `ReturnValue` bool only",
            "only copied canonical bool/int32 scalars may cross into `field_mask`, `bool_values`, and `int32_values`",
            "`item-return-only-policy-slice` is not a standalone public item API",
            "It does not promote item identity, item lookup, object handles, item mutation, repair semantics, equip authority, item-to-item payloads, or return override.",
        ):
            with self.subTest(file="public-gameplay-event-readiness", phrase=phrase):
                self.assertIn(phrase, readiness_compact)

        minimal_compact = normalized(minimal)
        for phrase in (
            "This note backs only the compact inventory and structure part of `GameplayPolicyEvent`",
            "It does not back the return-only item event kinds",
            "The only reusable boundary from this note is copied scalar evidence for `GameplayPolicyEvent`.",
        ):
            with self.subTest(file="minimal-second-source", phrase=phrase):
                self.assertIn(phrase, minimal_compact)

        item_compact = normalized(item_strict)
        for phrase in (
            "This strict `item-compact-intake` artifact is a review aid for item recognizer shape.",
            "The public `GameplayPolicyEvent` item backing is the narrower `item-return-only-policy-slice`",
            "`PrimalItem.AllowEquipItem.ReturnValue`",
            "`PrimalItem.CanRepair.ReturnValue`",
            "`PrimalItem.UseItemOntoItem.ReturnValue`",
            "`CraftBlueprint`, `CanRepair.bIgnoreInventoryRequirement`, destination inventory refs, destination item refs, `AdditionalData`, item identity, lookup, mutation, and return override remain redacted or blocked.",
        ):
            with self.subTest(file="item-compact-strict", phrase=phrase):
                self.assertIn(phrase, item_compact)

        structure_compact = normalized(structure_build)
        for phrase in (
            "For current `GameplayPolicyEvent` backing, structures remain limited to the copied fields already covered by `structure-observer-intake`",
            "Build placement policy is not part of that backing lane.",
            "It is not a `GameplayPolicyEvent` extension, dispatcher, or public SDK step",
        ):
            with self.subTest(file="structure-build-policy", phrase=phrase):
                self.assertIn(phrase, structure_compact)

        readme_compact = normalized(readme)
        for phrase in (
            "`GameplayPolicyEvent` backing currently means exactly three copied-data lanes",
            "`structure-observer-intake`, `minimal-second-source-intake`, and `item-return-only-policy-slice`",
            "Preserve the boundary as copied `field_mask`, `bool_values`, and `int32_values` only.",
            "Do not widen this phrase into public Inventory SDK, Items SDK, `StructureEvents`, build-policy API, identity/lookup, `ResourceHandle`, mutation, return override, runtime observation, or raw UE parameter access.",
        ):
            with self.subTest(file="research-readme", phrase=phrase):
                self.assertIn(phrase, readme_compact)

    def test_gap_matrix_minimal_second_source_compare_is_promotion_gate(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-28-second-source-reversing-gap-matrix.md"
        text = note.read_text(encoding="utf-8")
        section = text.split("When a second sanitized snapshot root exists, compare only this intake first:", 1)[1]
        command = section.split("```", 2)[1]

        self.assertIn("--target-set minimal-second-source-intake", command)
        self.assertIn("--readiness-report", command)
        self.assertIn("--fail-on-readiness-gaps", command)
        self.assertIn("--json", command)

    def test_static_binary_skill_documents_verified_static_artifact_provenance(self) -> None:
        skill = REPO_ROOT / "agent-skills/obelisk-static-binary-analysis/SKILL.md"
        text = skill.read_text(encoding="utf-8")

        self.assertIn("<artifact>.provenance.json", text)
        self.assertIn("verified=true", text)
        self.assertIn("matching `binary_sha256`", text)
        self.assertIn("matching\n  `artifact_sha256`", text)
        self.assertIn("resolving sidecars are fail-closed evidence blockers", text)
        self.assertIn("build_static_global_promotion_evidence.py", text)
        self.assertIn("writes verified sidecars", text)

    def test_optional_static_tools_remain_optional_and_offline_only(self) -> None:
        skill = (REPO_ROOT / "agent-skills/obelisk-static-binary-analysis/SKILL.md").read_text(
            encoding="utf-8"
        )
        packs = (REPO_ROOT / "docs/OFFLINE_ARTIFACT_PACKS.md").read_text(encoding="utf-8")
        research = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        combined = "\n".join((skill, packs, research))

        self.assertIn("optional evidence enrichment", skill)
        self.assertIn("not required to run pack normalization, consume gates, or repository tests", packs)
        self.assertIn("tests must not require those tools", research)
        self.assertIn("record `command -v`", combined)
        self.assertIn("version output when available", combined)
        self.assertIn("Direct or symlink-resolved reads from a protected server root", packs)
        self.assertIn("direct or symlink-resolved protected live-server paths", research)
        self.assertIn("`<offline-artifact-root>`", research)
        self.assertNotIn("/servidor/ark", research)

    def test_fname_manifest_plan_keeps_indices_binary_scoped(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-28-fname-index-manifest-plan.md"
        text = note.read_text(encoding="utf-8")

        self.assertIn("obelisk.fname-index-manifest.v1", text)
        self.assertIn("ark_binary_sha256", text)
        self.assertIn("strict lowercase SHA256 hex", text)
        self.assertIn("Hash mismatch must fail closed", text)
        self.assertIn("Raw\nindices", text)
        self.assertIn("runtime `int32_t` ABI", text)
        self.assertIn("number` values other than `0` are rejected", text)
        self.assertIn("candidate-only", text)
        self.assertIn("accepted", text)
        self.assertIn("obelisk.fname-index-promotion-evidence.v1", text)
        self.assertIn("docs/research/YYYY-MM-DD-*.md", text)
        self.assertIn("evidence-pack `manifest.json` path", text)
        self.assertIn("Acceptance Criteria For `accepted`", text)
        self.assertIn("artifact_kind", text)
        self.assertIn("artifact_sha256", text)
        self.assertIn("capture_id", text)
        self.assertIn("evidence_pack_id", text)
        self.assertIn("Static\nevidence alone must not turn `promotion_gate.ready` true", text)
        self.assertIn("must\nnot point under `/servidor/ark`", text)
        self.assertIn("--require-accepted", text)
        self.assertIn("`--ark-binary <ShooterGameServer>`", text)
        self.assertIn("`--resolve-name` must always include an expected\n   binary hash", text)
        self.assertIn("Candidate-only manifests must use `--allow-candidate` explicitly", text)
        self.assertIn("Non-JSON resolver output must print that field", text)
        self.assertIn("preferably computed from an offline binary path", text)
        self.assertIn("Do not expose a public plugin ABI callback-by-name", text)
        self.assertIn("operator-side name-to-index workflow", text)

    def test_player_principal_capture_plan_uses_window_manifest_template(self) -> None:
        note = REPO_ROOT / "docs/research/2026-06-01-player-principal-runtime-capture-plan.md"
        text = note.read_text(encoding="utf-8")
        log_copying = text.split("## Log Copying", 1)[1].split("## Manifest And Checker", 1)[0]

        self.assertIn("prepare_player_principal_lifecycle_window_request.py", text)
        self.assertIn("check_player_principal_lifecycle_window_request.py", text)
        self.assertIn("prepared_at_utc", text)
        self.assertIn("approval_recorded_at_utc", text)
        self.assertIn("--map <map> \\\n  --mode stable", text)
        self.assertIn("--target-map <map>", text)
        self.assertIn("--mode observer-window", text)
        self.assertIn("--env-file /servidor/ark/workspace-offline/live-validation-logs/<run-id>/observer-window.env", text)
        self.assertIn("--window-manifest /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env", text)
        self.assertIn("--copied-log /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log", text)
        self.assertIn("--evidence-dir /servidor/ark/workspace-offline/live-validation-logs/<run-id>", text)
        self.assertIn(
            "check_player_identity_runtime_principal_lifecycle_window_manifest.py",
            log_copying,
        )
        self.assertIn("--emit-template", log_copying)
        self.assertIn("stale or extra keys must fail closed", log_copying)
        for stale_key in (
            "copy_method=",
            "ark_binary_sha256=",
            "post_check=passed|failed",
            "rollback_completed=true|false",
            "users_policy=<no_regular_users|operator_approved_beta_users|unknown>",
        ):
            with self.subTest(stale_key=stale_key):
                self.assertNotIn(stale_key, log_copying)

    def test_chat_command_readiness_stays_plugin_local_docs_tests_only(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-31-chat-command-readiness.md"
        text = note.read_text(encoding="utf-8")
        compact = normalized(text)

        for phrase in (
            "The current surface is enough for plugin-local command parsing tests.",
            "The narrowest next hardening step before beta-player testing is docs/tests, not runtime code and not an approved live test.",
            "This is not enough for a public command SDK, player-facing authority, or beta-player command behavior.",
            "plugin may subscribe to copied `ChatMessageEvent`, validate ABI/size/flags/send-mode, copy callback-scope message bytes into plugin-owned memory",
            "route to local handlers with `principal=unknown`",
            "`scripts/test_chat_command_parser_contract.py` covers copied-text parsing, non-command no-match behavior, malformed event rejection, prefix-at-byte-zero matching, command name byte limits, ASCII safe command-name characters, no lowercasing, and a result type containing only `name`.",
            "`plugins/oBaseEvents/oBaseEvents.cpp` contains a disabled-by-default helper",
            "`plugins/oChatLogger` and `plugins/oChatAudit` remain experimental copied-data examples",
            "Not accepted for beta-player command behavior:",
            "Any command that needs a real sender, player, admin, tribe, connection, platform ID, map authority, or persistent identity.",
            "Any first-party `oCommand*` plugin, runtime command router, new `ObeliskApi` function, capability bit, event struct, command registry, or installed helper target.",
            "Do docs/tests next.",
            "this note does not create that approval",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, compact)

    def test_arkapi_aseapi_nextgen_references_remain_names_demand_only(self) -> None:
        readme = (REPO_ROOT / "docs/research/README.md").read_text(encoding="utf-8")
        p0_snapshot = (
            REPO_ROOT / "docs/research/2026-06-03-p0-runtime-evidence-gate-snapshot.md"
        ).read_text(encoding="utf-8")
        reference_notes = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((REPO_ROOT / "docs/research").glob("*.md"))
            if any(
                token in path.name.lower()
                for token in ("arkserverapi", "aseapi", "nextgen")
            )
        }
        self.assertEqual(
            set(reference_notes),
            {
                "2026-05-30-aseapi-reference-scan.md",
                "2026-05-30-nextgenplugins-reference-inventory.md",
                "2026-06-01-aseapi-name-demand-map.md",
                "2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md",
            },
        )

        readme_compact = normalized(readme)
        for phrase in (
            "ArkApi/AseApi material remains a names/demand reference only, not an architecture, ergonomics, behavior, or implementation reference.",
            "ArkServerApi/AseApi/NextGenPlugins material is never authority for porting targets, API ergonomics, wrapper semantics, command parser behavior, timer behavior, return semantics, return override semantics, support-tier classification, offsets, layouts, ABI, schemas, constants, or source code.",
            "ArkApi/AseApi/NextGenPlugins demand can keep a blocked idea visible, but it cannot change the support tier without a named promotion gate.",
            "old `lifecycle_anchor_first_evidence_provenance_unbound` validation lines are historical only and the active default blocker is `approved_runtime_evidence_missing`.",
            "Allows ArkServerApi/AseApi as names/demand evidence only while banning copied architecture, ergonomics, behavior, offsets, vtables, MSVC ABI, Windows libs, direct UE pointer APIs, and direct memory access patterns.",
            "Records the local ArkApi plugin-source clone as a future Plugin Hub demand signal only, not as runtime evidence or portable implementation source.",
            "Maps high-demand dictionary-only plugin capability families to candidate Obelisk surfaces and likely UE4 names without promoting SDK, runtime, mutation, or Plugin Hub work.",
            "Condenses dictionary-only demand into blocker ordering without promoting compatibility, public SDK completion, runtime observers, command replies, storage, mutation, or porting work.",
        ):
            with self.subTest(file="docs/research/README.md", phrase=phrase):
                self.assertIn(phrase, readme_compact)

        p0_compact = normalized(p0_snapshot)
        for phrase in (
            "source-boundary wording in the README and the four reference notes",
            "ArkServerApi/AseApi/NextGenPlugins notes remain names/demand dictionaries only.",
            "do not restart broad FName, GObjects, core, serial, ReflectionScanner, or decompiler discovery unless a new binary hash or contradictory artifact evidence invalidates the accepted inputs.",
            "Historical FName/GObjects/core/admin/lifecycle-layout notes are evidence trails only",
        ):
            with self.subTest(file="p0-runtime-evidence-gate-snapshot", phrase=phrase):
                self.assertIn(phrase, p0_compact)
        self.assertNotIn("the three reference notes", p0_compact)

        authority_boundary = (
            "never authority for porting targets, API ergonomics, wrapper semantics, "
            "command parser behavior, timer behavior, return semantics, return override "
            "semantics, support-tier classification, offsets, layouts, ABI, schemas, "
            "constants, or source code"
        )
        for path, text in reference_notes.items():
            with self.subTest(file=path, phrase="authority boundary"):
                self.assertIn(authority_boundary, normalized(text))

        aseapi_compact = normalized(reference_notes["2026-05-30-aseapi-reference-scan.md"])
        for phrase in (
            "Useful, but only as a names and demand dictionary for evidence promotion.",
            "It is not a behavior map, compatibility target, architecture guide, ergonomics guide, implementation guide, or evidence source for public Obelisk SDK surfaces.",
            "Do not use AseApi for:",
            "Memory offsets, vtable definitions, direct `GetNativePointerField` accessors, direct `NativeCall` wrappers, or copied C++ struct layouts.",
            "Behavior parity, control flow, command parsers, schemas, constants, return semantics, or source-level implementation patterns.",
            "Every AseApi-derived name must be revalidated through Obelisk before it can become an Obelisk target:",
        ):
            with self.subTest(file="aseapi-reference-scan", phrase=phrase):
                self.assertIn(phrase, aseapi_compact)

        nextgen_compact = normalized(reference_notes["2026-05-30-nextgenplugins-reference-inventory.md"])
        for phrase in (
            "Use this material only as names and demand evidence.",
            "do not copy Windows ArkApi code, offsets, MSVC ABI assumptions, vtables, memory layouts, direct UE pointer API patterns, constants, schemas, control flow, command parsers, or implementation details into Obelisk.",
            "It is not a source-mining checklist",
            "These revisions are provenance for demand analysis only; they are not runtime evidence and do not authorize copied implementation, offsets, layouts, ABI assumptions, or ArkApi compatibility claims.",
            "Use this clone as names/demand evidence only, not as architecture guidance or source code to port.",
            "Do not trust `DECLARE_HOOK` declarations as Linux ABI, direct UE pointer wrappers as safe public API shape, or ArkApi return constants as accepted Linux ARK behavior.",
        ):
            with self.subTest(file="nextgenplugins-reference-inventory", phrase=phrase):
                self.assertIn(phrase, nextgen_compact)

        demand_compact = normalized(reference_notes["2026-06-01-aseapi-name-demand-map.md"])
        for phrase in (
            "Status: dictionary/demand synthesis only; no promotion evidence",
            "No runtime probing, server access, scanner run, debugger, offset derivation, ABI change, source porting, command parser inspection, schema extraction, or implementation copying was performed.",
            "AseApi and NextGenPlugins names below are dictionary/demand signals only.",
            "must not be used as architecture, behavior, ergonomics, implementation, source, offset, vtable, layout, ABI, wrapper, constant, schema, command parser, return semantic, or algorithm sources.",
            "Do not cite AseApi or NextGenPlugins line numbers, signatures, structs, command names, schemas, constants, parser behavior, return values, or hook wrappers as Obelisk evidence.",
        ):
            with self.subTest(file="aseapi-name-demand-map", phrase=phrase):
                self.assertIn(phrase, demand_compact)

        demand_chain_compact = normalized(
            reference_notes["2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md"]
        )
        for phrase in (
            "Status: demand synthesis, not promotion evidence",
            "The chain explains ordering only.",
            "ArkApi, AseApi, and local NextGenPlugins material may inform names and demand grouping only.",
            "Do not use it as architecture or ergonomics guidance, and do not copy or port:",
            "source code, control flow, command parsers, schemas, constants, return semantics, or plugin behavior;",
            "direct native-call wrappers, pointer accessors, or Windows/MSVC ABI assumptions;",
            "This note is also not evidence for ArkApi/AseApi compatibility, public v1 completion",
        ):
            with self.subTest(file="v1-sdk-demand-chain-from-aseapi-nextgen", phrase=phrase):
                self.assertIn(phrase, demand_chain_compact)

    def test_sdk_complete_priority_map_historical_blockers_are_not_active_route(self) -> None:
        priority_map = (
            REPO_ROOT / "docs/research/2026-06-02-sdk-complete-priority-map.md"
        ).read_text(encoding="utf-8")
        boundary = priority_map.split("## Current Route Boundary", 1)[1].split(
            "## Reorganization Checkpoint", 1
        )[0]
        boundary_compact = normalized(boundary)

        for phrase in (
            "Read every later `lifecycle_anchor_first_evidence_provenance_unbound` line as historical status only",
            "must not be routed as an active blocker",
            "The active default blocker is `approved_runtime_evidence_missing`",
            "Only after accepted approved runtime principal lifecycle evidence",
            "identity_public_contract_gate_missing",
            "permissions/admin, command response, commands/replies, and v1 completion flags still false",
            "Do not use historical validation lines in this ledger to rerun broad FName/GObjects/core/admin/lifecycle-layout discovery",
            "start servers, change markers/env, run ReflectionScanner, ptrace/gcore, broad tracing",
            "ArkServerApi/AseApi/NextGenPlugins remain names/demand signals only",
            "not authority for offsets, layouts, ABI, command parser behavior, return semantics, architecture, ergonomics, source code, or implementation copying",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, boundary_compact)


if __name__ == "__main__":
    unittest.main()
