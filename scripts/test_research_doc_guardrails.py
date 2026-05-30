#!/usr/bin/env python3
"""Guardrails for Obelisk research docs that encode live-server safety rules."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ResearchDocGuardrailTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
