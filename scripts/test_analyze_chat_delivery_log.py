#!/usr/bin/env python3
"""Tests for analyze_chat_delivery_log.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_chat_delivery_log as analyzer


SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def write_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class AnalyzeChatDeliveryLogTests(unittest.TestCase):
    def test_accepts_minimal_copied_delivery_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertTrue(result["promotion_gate"]["ready"])
        self.assertEqual([], result["promotion_gate"]["blockers"])
        self.assertEqual(1, result["accepted_delivery_event_count"])
        self.assertEqual([0], result["accepted_send_modes"])
        self.assertFalse(result["delivery_mode_coverage"]["complete"])
        self.assertEqual([0], result["delivery_mode_coverage"]["covered_send_modes"])
        self.assertEqual([1, 2, 3], result["delivery_mode_coverage"]["uncovered_send_modes"])
        self.assertEqual("copied_plugin_delivery_events_only", result["delivery_mode_coverage"]["basis"])
        self.assertEqual("copied_plugin_delivery", result["send_mode_evidence"][0]["delivery_evidence_status"])
        self.assertEqual("not_observed", result["send_mode_evidence"][1]["delivery_evidence_status"])
        self.assertEqual("not_observed", result["send_mode_evidence"][2]["delivery_evidence_status"])
        self.assertEqual("not_observed", result["send_mode_evidence"][3]["delivery_evidence_status"])
        self.assertEqual(0, result["delivery_metadata_event_count"])
        self.assertIsNone(result["delivery_events"][0]["mode_count"])
        self.assertIsNone(result["delivery_events"][0]["first_observed"])
        self.assertIn("absence of a send mode is inconclusive", result["mode_coverage_note"])

    def test_accepts_optional_mode_count_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5. mode_count=1 first_observed=true.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=2 send_mode=0 flags=0x1 message_size=7. mode_count=2 first_observed=false.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=2)

        self.assertTrue(result["promotion_gate"]["ready"])
        self.assertEqual(2, result["accepted_delivery_event_count"])
        self.assertEqual(2, result["delivery_metadata_event_count"])
        self.assertEqual(1, result["delivery_events"][0]["mode_count"])
        self.assertIs(True, result["delivery_events"][0]["first_observed"])
        self.assertEqual(2, result["delivery_events"][1]["mode_count"])
        self.assertIs(False, result["delivery_events"][1]["first_observed"])

    def test_blocks_inconsistent_mode_count_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5. mode_count=0 first_observed=true.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=2 send_mode=0 flags=0x1 message_size=7. mode_count=2 first_observed=true.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        reasons = {blocker["reason"] for blocker in result["promotion_gate"]["blockers"]}
        self.assertIn("delivery_event_zero_mode_count", reasons)
        self.assertIn("delivery_event_first_observed_mode_count_mismatch", reasons)
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_malformed_mode_count_metadata_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5. mode_count=1 first_observed=yes.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("malformed_delivery_log_line", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertEqual(0, result["delivery_event_count"])
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_reports_observed_modes_and_can_require_mode_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=2 send_mode=3 flags=0x1 message_size=7.",
                    ]
                ),
            )

            result = analyzer.parse_log(
                log,
                expected_sha256=SHA,
                min_events=2,
                required_send_modes={0, 3},
            )

        self.assertTrue(result["promotion_gate"]["ready"])
        self.assertEqual([0, 3], result["accepted_send_modes"])
        self.assertEqual([], result["missing_required_send_modes"])

    def test_reports_route_observer_events_without_delivery_credit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-route.log"
            write_log(
                log,
                "[info] ChatRouteObserver event sequence=1 send_mode=3 send_mode_name=AllianceChat post_original=true delivery_claim=none.\n",
            )

            result = analyzer.parse_log(
                log,
                expected_sha256=None,
                min_events=1,
                required_route_send_modes={3},
            )

        self.assertEqual(0, result["accepted_delivery_event_count"])
        self.assertEqual([], result["accepted_send_modes"])
        self.assertEqual(1, result["route_event_count"])
        self.assertEqual(1, result["accepted_route_event_count"])
        self.assertEqual([3], result["accepted_route_send_modes"])
        self.assertEqual([], result["missing_required_route_send_modes"])
        self.assertIs(True, result["route_events"][0]["post_original"])
        self.assertEqual("none", result["route_events"][0]["delivery_claim"])
        self.assertIn("internal route evidence only", result["route_coverage_note"])

    def test_require_send_modes_remains_delivery_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-route-and-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] ChatRouteObserver event sequence=2 send_mode=3 send_mode_name=AllianceChat post_original=true delivery_claim=none.",
                    ]
                ),
            )

            result = analyzer.parse_log(
                log,
                expected_sha256=SHA,
                min_events=1,
                required_send_modes={3},
                required_route_send_modes={3},
            )

        self.assertEqual([0], result["accepted_send_modes"])
        self.assertEqual([3], result["accepted_route_send_modes"])
        self.assertEqual([3], result["missing_required_send_modes"])
        self.assertEqual([], result["missing_required_route_send_modes"])
        self.assertIn("missing_required_chat_send_modes", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertNotIn(
            "missing_required_chat_route_send_modes",
            {b["reason"] for b in result["promotion_gate"]["blockers"]},
        )

    def test_route_only_tribe_local_alliance_do_not_satisfy_delivery_mode_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-route-and-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] ChatRouteObserver event sequence=2 send_mode=1 send_mode_name=GlobalTribeChat post_original=true delivery_claim=none.",
                        "[info] ChatRouteObserver event sequence=3 send_mode=2 send_mode_name=LocalChat post_original=true delivery_claim=none.",
                        "[info] ChatRouteObserver event sequence=4 send_mode=3 send_mode_name=AllianceChat post_original=true delivery_claim=none.",
                    ]
                ),
            )

            result = analyzer.parse_log(
                log,
                expected_sha256=SHA,
                min_events=1,
                required_send_modes={0, 1, 2, 3},
                required_route_send_modes={1, 2, 3},
            )

        self.assertEqual([0], result["accepted_send_modes"])
        self.assertEqual([1, 2, 3], result["accepted_route_send_modes"])
        self.assertEqual([1, 2, 3], result["missing_required_send_modes"])
        self.assertEqual([], result["missing_required_route_send_modes"])
        self.assertFalse(result["delivery_mode_coverage"]["complete"])
        self.assertEqual([1, 2, 3], result["delivery_mode_coverage"]["uncovered_send_modes"])
        self.assertEqual(
            {
                0: "copied_plugin_delivery",
                1: "route_only_no_plugin_delivery",
                2: "route_only_no_plugin_delivery",
                3: "route_only_no_plugin_delivery",
            },
            {event["send_mode"]: event["delivery_evidence_status"] for event in result["send_mode_evidence"]},
        )
        self.assertIn("missing_required_chat_send_modes", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertNotIn(
            "missing_required_chat_route_send_modes",
            {b["reason"] for b in result["promotion_gate"]["blockers"]},
        )
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_missing_required_route_send_mode_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-route.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] ChatRouteObserver event sequence=2 send_mode=0 send_mode_name=GlobalChat post_original=true delivery_claim=none.",
                    ]
                ),
            )

            result = analyzer.parse_log(
                log,
                expected_sha256=SHA,
                min_events=1,
                required_route_send_modes={0, 1, 2, 3},
            )

        self.assertEqual([0], result["accepted_route_send_modes"])
        self.assertEqual([1, 2, 3], result["missing_required_route_send_modes"])
        self.assertIn("missing_required_chat_route_send_modes", {b["reason"] for b in result["promotion_gate"]["blockers"]})

    def test_blocks_missing_required_send_mode_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1, required_send_modes={0, 1, 2, 3})

        self.assertEqual([0], result["accepted_send_modes"])
        self.assertEqual([1, 2, 3], result["missing_required_send_modes"])
        self.assertIn("missing_required_chat_send_modes", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_when_producer_or_registration_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.\n",
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        reasons = {blocker["reason"] for blocker in result["promotion_gate"]["blockers"]}
        self.assertIn("missing_chat_event_producer_gate", reasons)
        self.assertIn("missing_ochatlogger_registration", reasons)
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_malformed_delivery_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=0 send_mode=9 flags=0x0 message_size=0.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        reasons = {blocker["reason"] for blocker in result["promotion_gate"]["blockers"]}
        self.assertIn("delivery_event_zero_sequence", reasons)
        self.assertIn("delivery_event_send_mode_out_of_range", reasons)
        self.assertIn("delivery_event_missing_copied_payload_flag", reasons)
        self.assertIn("delivery_event_zero_message_size", reasons)
        self.assertIn("insufficient_accepted_chat_delivery_events", reasons)

    def test_blocks_raw_chat_text_log_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] [Plugin] [oChatLogger] raw_chat=<redacted>",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("chat_privacy_data_logged", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_privacy_suffix_on_valid_delivery_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5. message=<redacted>",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("chat_privacy_data_logged", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_privacy_suffix_on_route_lines(self) -> None:
        suffixes = ["message=<redacted>", "params=0x0", "function=0x0"]
        for suffix in suffixes:
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                log = Path(tmp) / "chat-route.log"
                write_log(
                    log,
                    "\n".join(
                        [
                            f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                            "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                            "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                            f"[info] ChatRouteObserver event sequence=2 send_mode=0 send_mode_name=GlobalChat post_original=true delivery_claim=none. {suffix}",
                        ]
                    ),
                )

                result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

            self.assertIn("chat_privacy_data_logged", {b["reason"] for b in result["promotion_gate"]["blockers"]})
            self.assertIn("malformed_route_observer_log_line", {b["reason"] for b in result["promotion_gate"]["blockers"]})
            self.assertEqual(0, result["accepted_route_event_count"])
            self.assertFalse(result["promotion_gate"]["ready"])

    def test_blocks_identity_log_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] [Plugin] [oChatLogger] sender=<redacted> steam_id=<redacted>",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("chat_privacy_data_logged", {b["reason"] for b in result["promotion_gate"]["blockers"]})

    def test_blocks_privacy_leak_outside_ochatlogger_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] [ChatEventDispatcher] player_name=<redacted> text=<redacted>",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("chat_privacy_data_logged", {b["reason"] for b in result["promotion_gate"]["blockers"]})
        self.assertFalse(result["promotion_gate"]["ready"])

    def test_allows_message_size_without_raw_message_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        "[info] [ChatEventDispatcher] copied metadata message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertTrue(result["promotion_gate"]["ready"])

    def test_blocks_delivery_before_required_gate_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertIn("chat_delivery_event_before_required_gate", {b["reason"] for b in result["promotion_gate"]["blockers"]})

    def test_accepts_registration_before_lazy_producer_gate_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        self.assertTrue(result["promotion_gate"]["ready"])
        self.assertEqual(1, result["accepted_delivery_event_count"])

    def test_blocks_unexpected_controlled_message_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1, expected_message_size=6)

        self.assertIn("delivery_event_unexpected_message_size", {b["reason"] for b in result["promotion_gate"]["blockers"]})

    def test_can_require_approved_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1, require_workspace=True)

        self.assertIn("log_not_under_approved_offline_workspace", {b["reason"] for b in result["promotion_gate"]["blockers"]})

    def test_blocks_protected_path_without_reading_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            protected.mkdir()
            log = protected / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            with mock.patch.object(analyzer, "SERVER_ROOT", protected):
                result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1)

        reasons = {blocker["reason"] for blocker in result["promotion_gate"]["blockers"]}
        self.assertIn("log_path_under_live_server_root", reasons)
        self.assertEqual(0, result["accepted_delivery_event_count"])
        self.assertEqual(0, result["source"]["line_count"])

    def test_allow_server_path_reads_protected_path_for_operator_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "server"
            protected.mkdir()
            log = protected / "chat-delivery.log"
            write_log(
                log,
                "\n".join(
                    [
                        f"[info] Chat message event producer enabled for ShooterGameServer SHA256 {SHA}.",
                        "[info] [Plugin] [oChatLogger] Registered ChatMessageEvent callback.",
                        "[info] [Plugin] [oChatLogger] ChatMessageEvent received sequence=1 send_mode=0 flags=0x1 message_size=5.",
                    ]
                ),
            )

            with mock.patch.object(analyzer, "SERVER_ROOT", protected):
                result = analyzer.parse_log(log, expected_sha256=SHA, min_events=1, allow_server_path=True)

        self.assertEqual(1, result["accepted_delivery_event_count"])
        self.assertGreater(result["source"]["line_count"], 0)

    def test_cli_fail_on_quality_blockers_returns_three(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(log, "")

            with redirect_stdout(StringIO()):
                code = analyzer.main([str(log), "--expected-sha256", SHA, "--fail-on-quality-blockers"])

        self.assertEqual(3, code)

    def test_cli_rejects_invalid_expected_message_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(log, "")

            with redirect_stderr(StringIO()):
                code = analyzer.main([str(log), "--expected-message-size", "0"])

        self.assertEqual(2, code)

    def test_cli_rejects_invalid_required_send_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(log, "")

            with redirect_stderr(StringIO()):
                code = analyzer.main([str(log), "--require-send-modes", "0,4"])

        self.assertEqual(2, code)

    def test_cli_rejects_invalid_required_route_send_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "chat-delivery.log"
            write_log(log, "")

            with redirect_stderr(StringIO()):
                code = analyzer.main([str(log), "--require-route-send-modes", "0,4"])

        self.assertEqual(2, code)


if __name__ == "__main__":
    unittest.main()
