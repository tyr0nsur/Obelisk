# TheIsland Chat Reflection A/B Runbook

> Historical/superseded as of 2026-05-28: do not execute these `arkserver2` /
> TheIsland commands unless the operator explicitly approves a scoped test window.
> Current operator direction protects `arkserver` / Ragnarok while users are active;
> start `arkserver2` only for the approved test and shut it down afterward. Chat remains a
> historical observer family, not the center of the SDK roadmap.
> This document is preserved as evidence of a retired experiment shape. Use the current
> chat mode coverage beta runbook for any future player-facing `ChatMessageEvent`
> validation.

## Objective

Define a controlled `arkserver2` / TheIsland validation run for the experimental chat
reflection path before any public chat SDK promotion.

This runbook is preparation only. It does not authorize unattended execution, marker
changes, text logging, deployment, or restarts.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Debug target: `arkserver2` / TheIsland
- Protected target: `arkserver` / Ragnarok
- Central Obelisk root: `/servidor/ark/obelisk`
- Current public SDK header: `include/obelisk/ObeliskApi.h`
- Related gates:
  - `/servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection`
  - `OBELISK_ENABLE_CHAT_REFLECTION=1`
  - `OBELISK_CHAT_REFLECTION_BINARY_SHA256=<supported ARK SHA256>`
  - `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`

## Hypothesis

On the supported ARK binary hash, `ShooterPlayerController.ServerSendChatMessage` can be
recognized through the gated `ProcessEvent` reflection path with bounded metadata cost.
Decoded text evidence should require an extra explicit text gate and must not dispatch
plugin callbacks or change the public ABI.

## Safety Boundaries

- Do not run this on `arkserver` / Ragnarok while players are testing performance.
- Do not enable plugins for this validation.
- Do not enable `ReflectionScanner`, native exec probes, ptrace, gcore, or broad
  `ProcessEvent` tracing as part of this runbook.
- Do not run text logging unattended. It can capture player chat contents and needs a
  short operator-approved window with non-sensitive test messages.
- Do not treat metadata-only fallback candidates as accepted chat events.
- Do not add `OBELISK_API_CAPABILITY_CHAT_EVENTS` or public SDK chat fields from this
  run alone.

## Prechecks

Before any runtime window, record the exact code and binary context:

```bash
cd /home/flowcommunity-ark/Obelisk
git rev-parse HEAD
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
```

Expected baseline:

- ProcessEvent hook is mapped through the central runtime.
- Plugins are disabled.
- Scanner/native-exec/debug-control env is absent.
- `enable-chat-reflection` is absent before Phase A unless the window is explicitly
  starting from an already-enabled debug posture.

If the stable posture check fails, stop and fix posture before continuing. The
`--forbid-chat-reflection` check is expected to pass only before Phase A and after
rollback; it should fail during Phase B and Phase C while the experimental gate is active.

## Phase A: Reflection Off Baseline

Goal: establish the quiet baseline with chat reflection off.

1. Confirm `enable-process-event-hook` and `disable-plugins` are present for `arkserver2`.
2. Confirm `enable-chat-reflection` is absent.
3. Restart only `arkserver2` if the operator-approved window includes a restart.
4. Send one bounded non-sensitive normal chat message from a TheIsland client.
5. Run a supervisor snapshot and record chat counters, process PID, CPU/RSS if available,
   and log tail.

Expected result:

- No `Reflected chat ProcessEvent` lines.
- No `ServerSendChatMessage` reflection lines.
- No text logging.
- Server remains joinable.

## Phase B: Metadata-Only Reflection On

Goal: prove the recognized chat path without decoding player text.

```bash
touch /servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection
/servidor/ark/arkserver2 restart
```

Then tail bounded evidence:

```bash
tail -Fn 0 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log \
  | rg --line-buffered 'Experimental chat reflection|Reflected chat|Chat reflection rejected|metadata_only=true|ServerSendChatMessage|ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage'
```

Send exactly one bounded non-sensitive normal chat message from a TheIsland client. Then
capture:

```bash
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
tail -n 80 /servidor/ark/obelisk/dumps/supervisor/latest/obelisk-log-tail.txt
```

Acceptance evidence:

- `Experimental chat reflection enabled` appears for the supported binary SHA gate.
- At least one accepted `ServerSendChatMessage` line appears with `metadata_only=false`.
- `send_mode_known=true` and `send_mode_name` is one of `GlobalChat`, `GlobalTribeChat`,
  `LocalChat`, or `AllianceChat`.
- Parameter ranges remain bounded and match the documented `ChatMessage` / `SendMode`
  shape.

Rejected evidence:

- Only `ClientChatMessage`, `ClientServerChatMessage`, or
  `ClientServerChatDirectMessage` lines appear with `metadata_only=true`.
- `send_mode_known=false` appears for the observed `ServerSendChatMessage`.
- Rejection counters rise without accepted hits.
- Log volume grows without a bounded test message.

## Phase C: Text Logging On

Goal: validate the UTF-32 `FString` decoder with copied/sanitized log output.

This phase needs a separate explicit operator approval because it can record chat content.
Use a short non-sensitive test phrase and stop immediately after evidence is captured.

The marker alone does not enable text logging. Add the extra environment gate through the
approved wrapper/env path for `arkserver2` only:

```text
OBELISK_CHAT_REFLECTION_LOG_TEXT=1
```

Then restart only `arkserver2`, send exactly one bounded test message, capture one
supervisor snapshot, and remove the text gate immediately. Do not leave the process
running with text logging enabled after the capture.

Acceptance evidence:

- Text log line appears only for accepted `ServerSendChatMessage`.
- Decoded text matches the deliberate non-sensitive test phrase.
- Send mode remains known and in `0..3`.
- No plugin callback dispatch occurs.

## Rollback

Rollback is per-instance and should not touch Ragnarok:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection
# remove OBELISK_CHAT_REFLECTION_LOG_TEXT=1 from the approved arkserver2 env/wrapper path
/servidor/ark/arkserver2 restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
```

Expected rollback state:

- `chat_reflection_marker=disabled`
- `OBELISK_CHAT_REFLECTION_LOG_TEXT` absent
- ProcessEvent hook still enabled
- plugins still disabled
- scanner/native-exec/debug-control env absent

## Evidence Record

For each phase, record:

- Obelisk commit.
- ARK binary SHA256.
- Instance id and map.
- PID after restart.
- Active markers and relevant env.
- Whether plugins are disabled.
- Snapshot directory name.
- Chat counters from `chat-reflection.txt`.
- Relevant bounded log lines, without publishing private player chat contents.
- CPU/RSS or available process metrics.
- Result: accepted, rejected, or inconclusive.

## Result

This runbook aligns the next runtime chat validation with the current project vision:
Ragnarok remains protected for player performance testing, TheIsland is the debug harness,
chat reflection stays internal and gated, and public SDK chat events remain blocked until
runtime text evidence, benchmark evidence, ownership tests, and ABI gates are complete.

## Next Steps

1. Use this runbook only during an explicit TheIsland debug window.
2. After the window, write a follow-up research note with evidence and rollback result.
3. Keep `ChatEventDispatcher` internal until public SDK promotion gates are satisfied.
4. Rerun `scripts/verify_chat_reflection_constants.py` before accepting constants for any
   new ARK binary hash.
