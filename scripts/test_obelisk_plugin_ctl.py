#!/usr/bin/env python3
"""Local client protocol tests; no ARK installation or live endpoint is used."""

from __future__ import annotations

import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

import obelisk_plugin_ctl as client


class PluginControlClientTests(unittest.TestCase):
    def roundtrip(self, responder, action="pause", plugin_id="oPing"):
        with tempfile.TemporaryDirectory(prefix="obelisk-control-client-") as directory:
            path = str(Path(directory) / "operator.sock")
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(path)
            listener.listen(1)
            seen = []

            def serve():
                try:
                    with listener.accept()[0] as channel:
                        channel.settimeout(2)
                        payload = bytearray()
                        while b"\n" not in payload:
                            payload.extend(channel.recv(4096))
                        request = json.loads(payload)
                        seen.append(request)
                        response = responder(request)
                        if response is not None:
                            channel.sendall(json.dumps(response).encode() + b"\n")
                finally:
                    listener.close()

            worker = threading.Thread(target=serve)
            worker.start()
            try:
                result = client.request(path, action, plugin_id, 50)
                return result, seen
            finally:
                worker.join(timeout=3)
                self.assertFalse(worker.is_alive(), "mock local endpoint did not terminate")

    def test_action_identity_and_queue_timeout_are_forwarded(self):
        response, requests = self.roundtrip(lambda request: {"ok": True, "request_id": request["request_id"], "started": True})
        self.assertTrue(response["ok"])
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["action"], "pause")
        self.assertEqual(requests[0]["plugin_id"], "oPing")
        self.assertEqual(requests[0]["timeout_ms"], 50)
        self.assertRegex(requests[0]["request_id"], r"\A[a-f0-9]{32}\Z")

    def test_in_progress_is_preserved_and_never_retried(self):
        response, requests = self.roundtrip(lambda request: {
            "ok": False, "error": "in_progress", "started": True, "request_id": request["request_id"]})
        self.assertEqual(response["error"], "in_progress")
        self.assertTrue(response["started"])
        self.assertEqual(len(requests), 1)

    def test_no_response_and_mismatched_response_are_unknown_outcomes(self):
        with self.assertRaisesRegex(RuntimeError, "outcome is unknown"):
            self.roundtrip(lambda request: None)
        with self.assertRaisesRegex(RuntimeError, "outcome is unknown"):
            self.roundtrip(lambda request: {"ok": True, "request_id": "another_request"})

    def test_invalid_or_player_authority_inputs_are_rejected_before_connect(self):
        for action, plugin, timeout in (
            ("reload", "../oPing", 50), ("kick-player", "oPing", 50),
            ("start", None, 50), ("pause", "oPing", 0), ("pause", "oPing", 5001),
        ):
            with self.subTest(action=action, plugin=plugin, timeout=timeout):
                with self.assertRaises(ValueError):
                    client.request("/nonexistent-operator.sock", action, plugin, timeout)
        with self.assertRaises(ValueError):
            client.request("relative.sock", "status")


if __name__ == "__main__":
    unittest.main()
