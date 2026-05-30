# Chat Route Observer Plan

## Objective

Define the smallest internal observer needed to investigate chat mode coverage without
expanding the public `ChatMessageEvent` ABI or logging player text/identity.

## Design

Keep a default-off internal route observer, separate from `enable-chat-reflection` and from
`enable-chat-events`, that runs only after the original `ProcessEvent` returns. It should
record route/mode coverage for exact `ServerSendChatMessage` matches and never dispatch a
plugin callback.

Allowed log schema:

```text
Chat route observer enabled for ShooterGameServer SHA256 <64hex>.
ChatRouteObserver event sequence=<uint64> send_mode=<0..3> send_mode_name=<GlobalChat|GlobalTribeChat|LocalChat|AllianceChat> post_original=true delivery_claim=none.
```

Allowed fields are only sequence, copied send mode, send-mode name, post-original marker,
and `delivery_claim=none`.

Do not log message text, message size, sender/player/tribe/platform IDs, UE pointers,
function pointers, FName/GObjects indices, raw params, FString storage, object names, or
raw buffers.

## Gates

Use a separate internal gate so route evidence cannot be confused with plugin-facing
delivery:

```text
OBELISK_ENABLE_CHAT_ROUTE_OBSERVER=1
OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=<supported sha>
OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=<n>
OBELISK_WRAPPER_PROFILE=observer-debug
state/instances/<id>/allow-observer-debug-window
state/instances/<id>/allow-experimental-observers
state/instances/<id>/enable-chat-route-observer
```

Do not set `OBELISK_API_CAPABILITY_CHAT_EVENTS`, require plugin subscribers, or change
`ObeliskApi`.

Current tooling status: the hook-side route observer, LinuxGSM wrapper, stable posture
checker, and CLI summaries now own the `enable-chat-route-observer` marker and
`OBELISK_CHAT_ROUTE_OBSERVER_*` env family. Stable launches scrub the env family and fail
closed on the marker. `observer-debug` exports the route observer only with the
observer-window markers, exact supported binary SHA, and a positive limit. Do not activate
this route observer in an operational window without a scoped run plan, copied-log
evidence capture, rollback, and post-window stable posture check.

## Implementation Notes

- Hook near the current post-original chat delivery path in `hooks/ProcessEventHook.cpp`.
- Apply the cheap chat FName prefilter before any reflected reads.
- Accept only exact `ChatFunction::ServerSendChatMessage` with send modes `0..3`.
- Reserve the route observer sequence only after exact reflection and known send-mode
  validation. Rejected functions or unknown send modes must not consume the bounded
  observation budget, otherwise a noisy route window can silently miss real modes.
- Do not call text/FString decoding helpers.
- `scripts/analyze_chat_delivery_log.py` reports separate route fields such as
  `accepted_route_send_modes` and `missing_required_route_send_modes`.
- Use `--require-route-send-modes` only for internal route-coverage claims. Keep
  `--require-send-modes` scoped to plugin-facing `ChatMessageEvent` delivery.

## 2026-05-29 Runtime Hardening

`hooks/ProcessEventHook.cpp` now reserves `ChatRouteObserver` sequence numbers after
`TryBuildChatRouteObservation()` succeeds. Local validation:

```bash
cmake --build build --target process_event_chat_reflection_tests chat_reflection_benchmark -j"$(nproc)"
./build/process_event_chat_reflection_tests
./build/chat_reflection_benchmark 20000 > /tmp/obelisk-chat-reflection-benchmark.txt
python3 scripts/check_chat_reflection_benchmark.py /tmp/obelisk-chat-reflection-benchmark.txt
python3 -m unittest scripts/test_analyze_chat_delivery_log.py scripts/test_research_doc_guardrails.py scripts/test_secret_guardrails.py
python3 scripts/test_public_sdk_guardrails.py
git diff --check -- hooks/ProcessEventHook.cpp docs/README.md
```

All listed commands passed locally.

## 2026-05-29 Operational Guardrails

`packaging/linuxgsm/ObeliskRun.sh`, `scripts/check_obelisk_server_posture.sh`, and
`scripts/obelisk.py` now treat `enable-chat-route-observer` as an experimental observer
marker. Local validation:

```bash
bash -n packaging/linuxgsm/ObeliskRun.sh scripts/check_obelisk_server_posture.sh scripts/test_linuxgsm_wrapper_markers.sh scripts/test_check_obelisk_server_posture.sh
python3 -m py_compile scripts/obelisk.py scripts/test_obelisk_cli.py
scripts/test_linuxgsm_wrapper_markers.sh
scripts/test_check_obelisk_server_posture.sh
python3 -m unittest scripts/test_obelisk_cli.py
```

This closes the prior wrapper/posture/CLI tooling gap. It does not make route observations
public delivery evidence.

## Non-Claims

Route observations are mode-route evidence only. They are not plugin-facing
`ChatMessageEvent` delivery evidence, do not validate commands, do not validate text
delivery, and must not update public manifest delivery coverage until copied plugin logs
are accepted by the delivery analyzer for that controlled mode window.
