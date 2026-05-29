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

Actual plugin-facing delivery from a real chat message remains pending in an isolated
`arkserver2` validation window before any public milestone claim.
