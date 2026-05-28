# Passive Chat Reflection Live Observation

## Objective

Record an operator-supplied live log observation from 2026-05-28 as evidence for the
experimental chat reflection path. This note is passive evidence only, not a public SDK
readiness claim.

## Environment

- Runtime load path: Obelisk loaded through `LD_PRELOAD`
- ARK instance: `arkserver` / Ragnarok
- ProcessEvent candidate: `0x1d34e20`
- Hook state: absolute x64 hook installed with `patch_size=18`
- ReflectionScanner: disabled
- Plugin loading: disabled by `OBELISK_DISABLE_PLUGINS=1`
- Experimental chat reflection: enabled for ShooterGameServer SHA256
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`

## Hypothesis

The runtime recognizer is observing the reflected
`ShooterPlayerController.ServerSendChatMessage` shape and decoding bounded parameter
fields without accepting same-family chat candidates whose outer metadata does not match.

## Method

The operator supplied the log signal. No server actions were performed for this note: no
restart, marker edit, scanner enablement, plugin loading, gameplay mutation, or
`/servidor/ark` write is implied.

## Evidence

The supplied signal reports two accepted `ServerSendChatMessage` ProcessEvent
observations. Both decoded the same reflected parameter fields:

- `ChatMessage`: offset `0x0`, size `16`
- `SendMode`: offset `0x10`, size `1`

Observed send modes:

- `0` / `GlobalChat`
- `1` / `GlobalTribeChat`

The same signal includes two rejected candidates with:

- `fname_index=1865`
- reason: `chat UFunction outer FName index mismatch`

No private player chat content is recorded in this note.

## Result

This is runtime observation evidence for the experimental
`ServerSendChatMessage` recognizer on the stated ShooterGameServer hash. It supports the
hypothesis that reflected field offsets and send-mode decoding are plausible for this
binary, and that the outer-FName guard is rejecting at least two tempting non-matching
chat candidates.

This does not promote chat reflection to public SDK readiness. It does not imply plugin
callbacks, plugin loading, chat dispatch, or any gameplay mutation.

## Rejected Paths

- Two chat-shaped candidates with `fname_index=1865` were rejected because the chat
  `UFunction` outer FName index did not match the expected metadata owner.

## Risks

- Evidence is based on an operator-supplied live log excerpt, not a newly captured
  reproducible evidence pack.
- The observation is scoped to the listed binary SHA256 and current runtime gates.
- Caller identity, copied string ownership, callback lifetime, and ABI policy remain
  unresolved.

## Next Steps

1. Treat this as supporting runtime evidence only.
2. Keep SDK dispatch blocked until copied-data ownership, callback lifetime, ABI tests,
   and second-source validation are complete.
3. Preserve rejected-candidate logging for exact-owner guardrail evidence.

## Skill Updates Needed

None. This note records one passive observation and does not change future workflow rules.
