# Chat Message Second-Source Readiness

## Objective

Record the second-source readiness result for the minimal copied `ChatMessageEvent`
candidate without exposing local workspace paths in public manifests.

## Result

The `chat-message-intake` target set is accepted for layout evidence only:

- gate mode: `second_source_promotion`
- target set: `chat-message-intake`
- target:
  `obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerSendChatMessage`
- compared targets: `1`
- accepted targets: `1`
- rejected, inconclusive, or missing targets: `0`
- promotion gate: `ready=true`
- blockers: none

The compared fixture is:
`tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json`.

## Scope

This promotes only the copied chat notification layout evidence used by the
`ChatMessageEvent` RC candidate. It does not promote a command SDK, sender identity,
player identity, chat send/moderation authority, UE lookup, mutation, return override,
raw `FString` storage, raw parameter buffers, FName/GObjects indices, or UE pointers.

Actual plugin-facing delivery from a real chat message was validated during an approved
`arkserver` / Ragnarok beta-test window:

- copied evidence root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260529T125701Z`
- analyzer: `scripts/analyze_chat_delivery_log.py`
- accepted delivery events: `1`
- expected message size: `4`
- producer SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- promotion gate: `ready=true`
- blockers: none
- privacy leak lines: `0`

The same beta window later produced a stronger copied-log validation:

- copied evidence root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260529T131635Z`
- accepted delivery events: `5`
- observed sequence range: `1..5`
- observed message sizes: `4`, `14`, `16`, `11`, `4`
- send mode: `0`
- copied payload flag: `0x1`
- promotion gate: `ready=true`
- blockers: none
- privacy leak lines: `0`

The same day later produced copied plugin-facing delivery evidence for every known chat
send mode after deploying the updated `oChatLogger` and restarting `arkserver` with a
larger dispatch budget:

- copied evidence root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260529T183451Z-arkserver-chat-after-player-tests`
- copied log SHA256:
  `08e3f98b69fc82457345b83f25ab46121c2fa64f46be7ef6bb3136dfbe439a3f`
- analyzer summary SHA256:
  `8c8f5e47fbd0e745f654dddb05ac4e44d8c4df7ae0b249a888dfc4e585e812fe`
- accepted delivery events: `18`
- accepted send modes: `0`, `1`, `2`, `3`
- copied payload flag: `0x1`
- delivery metadata suffix: `mode_count` / `first_observed` present on every event
- promotion gate: `ready=true`
- blockers: none
- privacy leak lines: `0`

This is copied plugin-delivery evidence for `GlobalChat`, `GlobalTribeChat`,
`LocalChat`, and `AllianceChat`; route-observer evidence was not used. The validated
command was:

```bash
python3 scripts/analyze_chat_delivery_log.py \
  /servidor/ark/workspace-offline/live-validation-logs/20260529T183451Z-arkserver-chat-after-player-tests/Obelisk.log \
  --expected-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --require-workspace \
  --require-send-modes 0,1,2,3 \
  --fail-on-quality-blockers \
  --json
```

The result does not by itself replace the fuller beta-window manifest gate, because that
gate also records notice, rollback, post-check, and controlled-send context. For API
readiness, the important accepted fact is narrower: the copied `ChatMessageEvent` delivery
path can deliver all four known `send_mode` values to a plugin without raw text, player
identity, UE pointers, or route-observer claims.

## Runtime Delivery Boundary

The delivery evidence above is not a broad runtime-safety or chat-authority proof. It only
shows that the gated copied notification producer delivered bounded plugin-facing events
during an approved beta window. It does not prove that future chat command routing,
moderation, sender identity, route classification, mutation, blocking, or send authority is
safe or promoted.

This validates the copied plugin-facing notification path for the RC candidate. It does
not validate sender/player identity, command routing, chat moderation/blocking, chat send
authority, mutation, return override, UE lookup, raw `FString` storage, raw parameter
buffers, FName/GObjects indices, or UE pointer exposure.
