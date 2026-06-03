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


def normalized(text: str) -> str:
    return " ".join(text.split())


class ResearchDocGuardrailTests(unittest.TestCase):
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
        self.assertIn("limited to\n  `HandleNewPlayer` and `OnLogout`", observer_brief)
        self.assertIn("scratch triage unless\n  materialized into an approved offline artifact/root", observer_brief)
        self.assertNotIn(
            "`players-lifecycle-anchor-candidates` has accepted planning-layout evidence for six",
            runtime_plan,
        )
        self.assertNotIn(
            "six lifecycle-anchor planning targets accepted across two offline\n  roots",
            observer_brief,
        )

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
        self.assertIn("direct or symlink-resolved protected `/servidor/ark` paths", research)

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


if __name__ == "__main__":
    unittest.main()
