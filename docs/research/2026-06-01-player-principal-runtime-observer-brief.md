# Player Principal Runtime Observer Brief

Date: 2026-06-01

## Scope

This is a design and runbook brief for the private hook-side player/principal lifecycle
observer now present in the current tree. The observer is default-off,
observer-debug/env/marker/SHA/log-budget gated, redacted, dispatch-limit `0`, and
plugin-invisible. This brief does not authorize server access, marker/env changes,
wrapper changes, restarts, activation, runtime capture, runtime validation,
Discord/community notices, GitHub actions, public SDK work, mutation, return override, or
release claims.

The observer's only first job is to prove that the already-reviewed lifecycle layout
anchors can be observed through the normal `ProcessEvent` hook with copied, redacted,
bounded records. It must not expose player identity. It must not create a plugin-facing
player API.

## Evidence Baseline

Current planning-only evidence:

- target set: `players-lifecycle-anchor-candidates`;
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`;
- layout comparison: six lifecycle-anchor planning targets accepted across two offline
  roots, with promotion still blocked as `planning_only`;
- principal policy: candidate-only process-local opaque principal policy exists, but
  runtime evidence and public ABI review remain missing;
- runtime readiness: false.

The first runtime observer must consume only the two exact lifecycle anchors below. Other
player/admin/login/chat targets remain out of scope.

## Exact Runtime Targets

The only first-window targets are:

- `ShooterGameMode.HandleNewPlayer`
- `ShooterGameMode.OnLogout`

Accepted shapes are exact:

- `ShooterGameMode.HandleNewPlayer`: `ParmsSize=26`, `NumParms=5`,
  `NewPlayer:ObjectProperty@0/8`, `PlayerData:ObjectProperty@8/8`,
  `PlayerCharacter:ObjectProperty@16/8`, `bIsFromLogin:BoolProperty@24/1`,
  `ReturnValue:BoolProperty@25/1`.
- `ShooterGameMode.OnLogout`: `ParmsSize=8`, `NumParms=1`,
  `Exiting:ObjectProperty@0/8`.

`HandleNewPlayer` is a candidate `session_start` observation only when the call is seen
after the original `ProcessEvent` returns and the copied bool bytes are canonical
`bIsFromLogin=1` and `ReturnValue=1`. Any other canonical bool combination is
`session_start_rejected` with `principal_action=none`, not a principal start. A
non-canonical bool byte rejects the record.

`OnLogout` is a candidate `session_end` observation only after exact shape recognition.
The observer logs an invalidation-shaped event, but it does not prove active-candidate
state, complete logout ordering, reconnect behavior, transfer behavior, or public
principal invalidation semantics.

## Runtime Gates

These names are implemented for the private default-off observer, but using them still
requires a separate approved runtime window.

Environment:

- `OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1`
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=<64hex>`
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=<positive uint64>`
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0`
- `OBELISK_WRAPPER_PROFILE=observer-debug`
- `OBELISK_PE_TRACE_LIMIT=0`

Instance markers:

- `allow-observer-debug-window`
- `allow-experimental-observers`
- `enable-player-principal-lifecycle-observer`

The observer must also require stable baseline markers for the same instance:
`enable-process-event-hook` and `disable-plugins`.

The dispatch limit is deliberately fixed at `0` for the first observer. Any non-zero
dispatch limit must fail closed until a separate dispatcher, owner-token cleanup, ABI, and
plugin privacy review exists.

Stable posture must reject these env names and the
`enable-player-principal-lifecycle-observer` marker outside an approved observer-debug
window. That posture remains required before any runtime evidence can be accepted.

## Budget Model

Default budget is zero. Missing, malformed, zero, or overflowing log budget disables the
observer and must avoid metadata reads, parameter reads, sequence reservation, and copied
output.

For the first approved runtime window, use a maximum log budget of `10`. Do not increase
the budget in place. Copy logs and analyze the bounded window first.

Budget reservation order:

1. static gate and marker checks;
2. supported binary SHA check;
3. exact cheap target prefilter for `HandleNewPlayer` or `OnLogout`;
4. positive budget reservation;
5. exact reflected metadata and parameter shape validation;
6. copied redacted log emission only if validation succeeds.

Disabled gates, unsupported SHA, non-target names, and exhausted budgets are no-copy,
no-retain paths.

## Log Grammar

Enable line:

```text
PlayerPrincipalLifecycleObserver enabled binary_sha256=<64hex> target_set=players-lifecycle-anchor-candidates limit=<uint64> dispatch_limit=0 delivery_claim=none principal_claim=none.
```

Observation line:

```text
PlayerPrincipalLifecycleObserver event sequence=<uint64> role=<session_start|session_end|session_start_rejected> target=<Outer.Function> post_original=true copied_bool_fields=<csv-or-empty> copied_bool_values=<csv-or-empty> redacted_count=<uint> redacted_fields=<csv-or-empty> principal_action=<candidate_created|candidate_invalidated|none> principal_id_logged=false principal_generation_logged=false delivery_claim=none.
```

Allowed copied bool fields:

- `ShooterGameMode.HandleNewPlayer.bIsFromLogin`
- `ShooterGameMode.HandleNewPlayer.ReturnValue`

Allowed redacted fields:

- `ShooterGameMode.HandleNewPlayer.NewPlayer`
- `ShooterGameMode.HandleNewPlayer.PlayerData`
- `ShooterGameMode.HandleNewPlayer.PlayerCharacter`
- `ShooterGameMode.OnLogout.Exiting`

`principal_action=candidate_created` is allowed only for post-original
`HandleNewPlayer` with canonical `bIsFromLogin=1` and `ReturnValue=1`.
`principal_action=none` is required for every `session_start_rejected` combination such
as `0,1`, `1,0`, or `0,0`. `principal_action=candidate_invalidated` is allowed for exact
`OnLogout`, but it remains private evidence and must not be consumed by public plugins.

Do not log player names, Steam/EOS/platform ids, IP-like values, tribe ids, transfer ids,
saved player data ids, controller identity, player-state identity, character identity,
object names, class names, UE pointers, raw params, raw buffers, FName indices, GObjects
indices, `ResourceHandle`, map location, command text, chat text, permissions, admin
state, plugin subscriber state, or hashes of redacted identity values.

## Fail-Closed Cases

The observer must fail closed for:

- missing `observer-debug` profile;
- missing `allow-observer-debug-window` marker;
- missing `allow-experimental-observers` marker;
- missing `enable-player-principal-lifecycle-observer` marker;
- missing stable baseline markers;
- plugin loading enabled in the first window;
- missing or unsupported binary SHA;
- missing, zero, malformed, or overflowing log budget;
- non-zero dispatch budget;
- non-target `ProcessEvent` name;
- missing target metadata;
- `Outer.Function` mismatch;
- `ParmsSize`, `NumParms`, property order, property class, offset, size, or bool-tail
  mismatch;
- null or unreadable params for a target that needs copied bool validation;
- non-canonical bool bytes other than `0` or `1`;
- any object field not classified as redacted;
- duplicate start, logout without active private candidate, reconnect, transfer, controller
  replacement, player-state replacement, restart, plugin reload, or stale generation case
  remains an interpretation/evidence blocker until explicitly modeled;
- any attempt to derive principal identity from a pointer, object index, FName/GObjects
  value, platform id, name, text, saved player data field, transfer payload, or command
  payload.

Every rejection path must clear copied output. Rejected metadata may increment aggregate
internal counters later, but it must not emit redacted values, pointer-derived values, raw
buffers, or per-player identifiers.

## Runtime Runbook Requirements

No run is approved by this note. A later run request must name:

- exact instance id, map, ARK binary path, and SHA256;
- exact Obelisk build that contains the observer;
- exact env and marker changes;
- log budget and expected maximum event lines;
- whether player-facing action is required, with privacy bounds;
- copied-log destination outside live server logs;
- rollback owner;
- stable-posture verification command and expected shutdown/posture state.

The window must keep `OBELISK_PE_TRACE_LIMIT=0`, plugins disabled, scanner/native-exec
off, ptrace/gcore off, broad tracing off, and all unrelated observer families off.

## Rollback And Posture

Rollback must be defined before activation:

- remove or unset all `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_*` env values;
- remove `OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER`;
- remove `enable-player-principal-lifecycle-observer`;
- remove `allow-observer-debug-window` and `allow-experimental-observers` unless another
  current-turn approved window still owns them;
- restore stable wrapper/profile posture;
- keep `enable-process-event-hook` and `disable-plugins` as the stable baseline markers;
- restart only the explicitly approved instance if the approved window requires restart;
- copy logs to the approved offline evidence path before cleanup;
- run stable posture verification for the same approved instance and map;
- record whether any observer env or marker survived rollback.

If stable posture cannot prove that the observer env and marker are gone, the runtime
evidence remains operationally blocked even if the bounded observer lines look correct.

## Local Validation Floor

Before an approved runtime window or before accepting runtime evidence, local-only tests
should prove:

- gate-denied paths do not read metadata or params and do not reserve budget;
- unsupported SHA, zero budget, non-target name, wrong shape, and non-canonical bools
  clear copied output;
- exact `HandleNewPlayer` and `OnLogout` fixture shapes are the only accepted targets;
- object fields are redacted and never copied, logged, hashed, or converted into identity;
- stable posture rejects the observer env and marker names;
- dispatch remains disabled and non-zero dispatch budget fails closed.

This validation floor is not approval to run a server.

## Non-Claims

This brief does not claim:

- public `obelisk.player_identity.v1` readiness;
- public Player SDK, Principal SDK, Permissions SDK, command replies, economy, storage, or
  moderation readiness;
- authenticated sender identity for chat or commands;
- stable player identity, platform identity, saved-player identity, persistent identity,
  transfer identity, or cross-instance identity;
- lookup, `ResourceHandle`, UE pointer validity, object-array validity, FName/GObjects
  stability, post-callback object lifetime, or public handles;
- complete login/logout ordering, admission coverage, reconnect coverage, respawn
  coverage, transfer/download coverage, controller replacement coverage, or cluster
  semantics;
- plugin callbacks, dispatcher delivery, callback ABI, owner-token lifecycle, public
  capability bits, or installed SDK consumer support;
- mutation, return override, kicking/banning, permission checks, admin authority, chat
  sends, or manual `ProcessEvent` calls;
- approved runtime observer run, server access, restarts, marker changes, scanners,
  ptrace, `gcore`, broad `ProcessEvent` tracing, Discord/community notices, GitHub
  publication, tags, pushes, release readiness, or production validation.
