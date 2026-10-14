#!/usr/bin/env python3
"""Tests for check_player_identity_static_lifecycle_orientation.py."""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_static_lifecycle_orientation.py"
REGISTRAR_CALL_VMA = 0x1CCC140
CLASS_SLOT_VMA = 0x58F2BD0


SEGMENTS = [
    {"offset": 0x1000, "vaddr": 0x13CB000, "filesz": 0x3000, "memsz": 0x3000, "flags": 0x5},
    {"offset": 0x4000, "vaddr": 0x15CE000, "filesz": 0x5000, "memsz": 0x5000, "flags": 0x5},
    {"offset": 0x9000, "vaddr": 0x3F63000, "filesz": 0x1000, "memsz": 0x1000, "flags": 0x4},
    {"offset": 0xA000, "vaddr": 0x40E0000, "filesz": 0x2000, "memsz": 0x2000, "flags": 0x4},
    {"offset": 0xC000, "vaddr": 0x416F000, "filesz": 0x5000, "memsz": 0x5000, "flags": 0x4},
    {"offset": 0x12000, "vaddr": 0x58446C0, "filesz": 0, "memsz": 0x1E14D0, "flags": 0x6},
]


def vma_to_offset(vma: int, size: int = 1) -> int:
    for segment in SEGMENTS:
        start = segment["vaddr"]
        end = start + segment["filesz"]
        if start <= vma and vma + size <= end:
            return segment["offset"] + (vma - start)
    raise AssertionError(f"test fixture VMA is not file-backed: {hex(vma)}")


def write_vma(data: bytearray, vma: int, payload: bytes) -> None:
    offset = vma_to_offset(vma, len(payload))
    data[offset : offset + len(payload)] = payload


def call_bytes(call_vma: int, target_vma: int) -> bytes:
    return b"\xe8" + struct.pack("<i", target_vma - (call_vma + 5))


def class_load_bytes(load_vma: int) -> bytes:
    return b"\x48\x8b\x3d" + struct.pack("<i", CLASS_SLOT_VMA - (load_vma + 7))


def registration_bytes(registration_vma: int, name_vma: int, thunk_vma: int) -> bytes:
    return (
        b"\xbe"
        + struct.pack("<I", name_vma)
        + b"\xba"
        + struct.pack("<I", thunk_vma)
        + b"\x31\xc9"
        + call_bytes(registration_vma + 12, REGISTRAR_CALL_VMA)
    )


def make_fake_binary(path: Path, *, tamper_vma: int | None = None, tamper_byte: bytes = b"\x00") -> str:
    size = 0x14000
    data = bytearray(size)
    phoff = 64
    phentsize = 56
    phnum = len(SEGMENTS)
    data[:64] = struct.pack(
        "<16sHHIQQQIHHHHHH",
        b"\x7fELF\x02\x01\x01" + b"\x00" * 9,
        2,
        62,
        1,
        0x81DC59,
        phoff,
        0,
        0,
        64,
        phentsize,
        phnum,
        0,
        0,
        0,
    )
    for index, segment in enumerate(SEGMENTS):
        data[phoff + index * phentsize : phoff + (index + 1) * phentsize] = struct.pack(
            "<IIQQQQQQ",
            1,
            segment["flags"],
            segment["offset"],
            segment["vaddr"],
            segment["vaddr"],
            segment["filesz"],
            segment["memsz"],
            0x1000,
        )

    write_vma(data, 0x3F63B7C, "/Script/ShooterGame".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x40E0B24, "ShooterGameMode".encode("utf-32-le") + b"\x00\x00\x00\x00")
    write_vma(data, 0x416FF3A, b"CheckJoinInProgress\x00")
    write_vma(data, 0x4170122, b"HandleNewPlayer\x00")
    write_vma(data, 0x417024F, b"OnLogout\x00")
    write_vma(data, 0x13CBC88, class_load_bytes(0x13CBC88))
    write_vma(data, 0x13CBC8F, registration_bytes(0x13CBC8F, 0x416FF3A, 0x15CE900))
    write_vma(data, 0x13CC203, class_load_bytes(0x13CC203))
    write_vma(data, 0x13CC20A, registration_bytes(0x13CC20A, 0x4170122, 0x15D04C0))
    write_vma(data, 0x13CC559, class_load_bytes(0x13CC559))
    write_vma(data, 0x13CC560, registration_bytes(0x13CC560, 0x417024F, 0x15D1500))
    write_vma(data, 0x15CE900, b"\x55\x48\x89\xe5")
    write_vma(data, 0x15D04C0, b"\x55\x48\x89\xe5")
    write_vma(data, 0x15D1500, b"\x55\x48\x89\xe5")

    if tamper_vma is not None:
        write_vma(data, tamper_vma, tamper_byte)

    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class CheckPlayerIdentityStaticLifecycleOrientationTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_synthetic_binary_is_valid_candidate_only_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary)

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.player-identity-static-lifecycle-orientation-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertFalse(payload["accepted_lifecycle_anchors"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["approved_runtime_lifecycle_evidence"])
        self.assertFalse(payload["approved_runtime_evidence_present"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["counts_as_approved_runtime_lifecycle_evidence"])
        self.assertFalse(payload["counts_as_approved_runtime_evidence"])
        self.assertFalse(payload["counts_as_runtime_lifecycle_evidence"])
        self.assertFalse(payload["counts_as_runtime_evidence"])
        self.assertFalse(payload["counts_as_sdk_progress"])
        self.assertFalse(payload["counts_as_p0_progress"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["public_readiness_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(
            {target["target"] for target in payload["checked_targets"]},
            {
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.OnLogout",
            },
        )
        self.assertEqual(
            {
                "ShooterGameMode.CheckJoinInProgress": "session_start_rejected",
                "ShooterGameMode.HandleNewPlayer": "session_start",
                "ShooterGameMode.OnLogout": "session_end",
            },
            {target["target"]: target["role_hint"] for target in payload["checked_targets"]},
        )
        targets = {target["target"]: target for target in payload["checked_targets"]}
        for target in targets.values():
            self.assertEqual(target["source_policy_scope"], "source_names_only_not_runtime_evidence")
            self.assertEqual(
                target["runtime_evidence_status"],
                "approved_source_names_only_runtime_evidence_missing",
            )
            self.assertEqual(target["accepted_target_name_scope"], "source_name_only_not_runtime_evidence")
            self.assertEqual(target["anchor_binding_label_scope"], "source_name_only_not_runtime_evidence")
            self.assertFalse(target["accepted_target_name_counts_as_runtime_proof"])
            self.assertFalse(target["anchor_binding_label_counts_as_runtime_proof"])
            self.assertFalse(target["counts_as_approved_runtime_lifecycle_evidence"])
            self.assertFalse(target["counts_as_runtime_lifecycle_evidence"])
            self.assertFalse(target["counts_as_sdk_progress"])
            self.assertFalse(target["runtime_ready"])
            self.assertFalse(target["public_sdk_ready"])
            self.assertFalse(target["promotion_ready"])
        self.assertEqual(
            targets["ShooterGameMode.CheckJoinInProgress"]["required_runtime_shape"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        self.assertFalse(targets["ShooterGameMode.CheckJoinInProgress"]["static_lifecycle_anchor_source_name"])
        self.assertTrue(targets["ShooterGameMode.CheckJoinInProgress"]["rejected_start_triplet_source_name"])
        self.assertEqual(
            targets["ShooterGameMode.CheckJoinInProgress"]["anchor_binding_status"],
            "observer_only_rejected_start_source_not_anchor",
        )
        self.assertEqual(
            targets["ShooterGameMode.CheckJoinInProgress"]["required_copied_bool_fields"],
            ["bIsFromLogin", "ReturnValue"],
        )
        self.assertEqual(
            targets["ShooterGameMode.CheckJoinInProgress"]["required_copied_bool_values"],
            ["1", "0"],
        )
        self.assertFalse(
            targets["ShooterGameMode.CheckJoinInProgress"]["bare_source_alias_counts_as_runtime_evidence"]
        )
        self.assertFalse(
            targets["ShooterGameMode.CheckJoinInProgress"]["static_evidence_can_replace_runtime_triplet"]
        )
        self.assertEqual(
            targets["ShooterGameMode.HandleNewPlayer"]["required_runtime_shape"],
            "ShooterGameMode.HandleNewPlayer(1,1)",
        )
        self.assertTrue(targets["ShooterGameMode.HandleNewPlayer"]["static_lifecycle_anchor_source_name"])
        self.assertFalse(targets["ShooterGameMode.HandleNewPlayer"]["rejected_start_triplet_source_name"])
        self.assertEqual(
            targets["ShooterGameMode.HandleNewPlayer"]["anchor_binding_status"],
            "static_anchor_source_name_only_not_runtime_evidence",
        )
        self.assertEqual(
            targets["ShooterGameMode.OnLogout"]["required_runtime_shape"],
            "ShooterGameMode.OnLogout(matched)",
        )
        triplet_requirement = payload["approved_runtime_triplet_requirement"]
        self.assertFalse(triplet_requirement["approved_runtime_evidence_present"])
        self.assertFalse(triplet_requirement["approved_runtime_evidence_ready"])
        self.assertFalse(triplet_requirement["static_evidence_can_replace_runtime_triplet"])
        self.assertEqual(
            [
                "ShooterGameMode.HandleNewPlayer(1,1)",
                "ShooterGameMode.CheckJoinInProgress(1,0)",
                "ShooterGameMode.OnLogout(matched)",
            ],
            [entry["required_runtime_shape"] for entry in triplet_requirement["required_exact_triplet"]],
        )
        source_policy = payload["lifecycle_source_policy"]
        self.assertEqual(source_policy["policy_scope"], "source_names_only_not_runtime_evidence")
        self.assertEqual(
            source_policy["runtime_triplet_evidence_status"],
            "approved_source_names_only_runtime_evidence_missing",
        )
        self.assertFalse(source_policy["approved_runtime_evidence_present"])
        self.assertFalse(source_policy["runtime_ready"])
        self.assertFalse(source_policy["public_sdk_ready"])
        self.assertFalse(source_policy["promotion_ready"])
        self.assertEqual(
            source_policy["static_lifecycle_anchor_sources"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        self.assertEqual(
            source_policy["observer_rejected_start_sources"],
            ["ShooterGameMode.CheckJoinInProgress"],
        )
        self.assertEqual(source_policy["all_six_planning_gap_evidence_status"], "non_evidence")
        all_six_policy = payload["all_six_planning_gap_policy"]
        self.assertEqual(all_six_policy["all_six_planning_gap_evidence_status"], "non_evidence")
        self.assertFalse(all_six_policy["planning_gap_records_count_as_runtime_proof"])
        self.assertFalse(all_six_policy["accepted_targets_fields_count_as_runtime_proof"])
        self.assertFalse(all_six_policy["approved_runtime_evidence_present"])
        self.assertFalse(all_six_policy["runtime_ready"])
        self.assertFalse(all_six_policy["public_sdk_ready"])
        self.assertFalse(all_six_policy["promotion_ready"])
        self.assertEqual(
            {target["target_set_status"] for target in payload["checked_targets"]},
            {"known_lifecycle_orientation_not_in_closed_target_set"},
        )
        self.assertIn(
            "known_lifecycle_orientation_targets_not_in_closed_target_set",
            payload["promotion_blockers"],
        )
        self.assertIn(
            "check_join_in_progress_diagnostic_wording_is_not_approved_runtime_lifecycle_evidence",
            payload["promotion_blockers"],
        )
        self.assertIn(
            "fname_drift_notes_are_not_approved_runtime_lifecycle_evidence",
            payload["promotion_blockers"],
        )
        self.assertIn(
            "diagnostic_reflection_notes_do_not_count_toward_sdk_or_p0_progress",
            payload["promotion_blockers"],
        )
        self.assertIn(
            "diagnostic_reflection_notes_do_not_clear_public_readiness",
            payload["promotion_blockers"],
        )
        contract = payload["static_candidate_orientation_contract"]
        self.assertEqual(contract["status"], "candidate_blocked")
        self.assertFalse(contract["promotion_ready"])
        self.assertIn(
            "check_join_in_progress_diagnostic_wording_is_not_approved_runtime_lifecycle_evidence",
            contract["blockers"],
        )
        self.assertIn(
            "fname_drift_notes_are_not_approved_runtime_lifecycle_evidence",
            contract["blockers"],
        )
        self.assertIn("does not prove accepted session-start", " ".join(payload["non_claims"]))
        self.assertIn("CheckJoinInProgress is rejected-start orientation only", " ".join(payload["non_claims"]))
        self.assertIn("CheckJoinInProgressDiagnostic wording", " ".join(payload["non_claims"]))
        self.assertIn("FName drift notes", " ".join(payload["non_claims"]))
        self.assertIn("does not promote public identity", " ".join(payload["non_claims"]))

    def test_diagnostic_and_fname_notes_are_zero_credit_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary)

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, "--json")

        payload = json.loads(result.stdout)
        guardrails = {guardrail["source_phrase"]: guardrail for guardrail in payload["diagnostic_reflection_note_guardrails"]}

        self.assertEqual(
            {"CheckJoinInProgressDiagnostic", "FName drift notes"},
            set(guardrails),
        )
        for guardrail in guardrails.values():
            self.assertIn(
                guardrail["classification"],
                {"diagnostic_reflection_note_only", "reflection_drift_note_only"},
            )
            for flag in (
                "approved_runtime_lifecycle_evidence",
                "approved_runtime_evidence_present",
                "approved_runtime_evidence_ready",
                "counts_as_approved_runtime_lifecycle_evidence",
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_lifecycle_evidence",
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "counts_toward_complete_sdk_claim",
                "counts_toward_p0_dependency_chain",
                "counts_toward_p0_dependency_chain_claim",
                "public_readiness_ready",
                "promotion_ready",
                "public_sdk_ready",
                "runtime_ready",
            ):
                self.assertFalse(guardrail[flag], flag)

    def test_registration_pattern_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x13CC20F, tamper_byte=b"\x51")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("registration_thunk_immediate_mismatch", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_ascii_name_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            digest = make_fake_binary(binary, tamper_vma=0x417024F, tamper_byte=b"X")

            result = self.run_checker(str(binary), "--expected-binary-sha256", digest, check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("lifecycle_ascii_name_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_sha_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "ShooterGameServer"
            make_fake_binary(binary)

            result = self.run_checker(
                str(binary),
                "--expected-binary-sha256",
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("binary_sha256_mismatch", {blocker["reason"] for blocker in payload["blockers"]})


if __name__ == "__main__":
    unittest.main()
