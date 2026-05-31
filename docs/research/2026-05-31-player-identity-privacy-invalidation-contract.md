# Player Identity Privacy Invalidation Contract

Date: 2026-05-31

## Scope

This note records the candidate privacy and invalidation contract that any future
`obelisk.player_identity.v1` design must satisfy before commands, permissions, economy,
moderation, or player-scoped storage can depend on it.

It is documentation-only. It does not add a public SDK, ABI header, runtime observer,
server test, login/logout target, lookup API, persistence layer, permission system,
command router, mutation path, return override, or `ResourceHandle`.

## Principal Model

A principal must be an Obelisk-owned copied value, not a UE object coordinate.

Required shape for any future principal payload:

- `principal_id`: opaque fixed-size bytes or integer owned by Obelisk.
- `generation`: monotonic Obelisk-owned generation for the process-local principal slot.
- `state`: copied lifecycle state such as `unknown`, `candidate`, `active`, or
  `invalidated`.
- `privacy_class`: copied policy label; no platform id, player name, IP, tribe id,
  transfer id, object pointer, FName index, GObjects index, raw params, or UE pointer.

The principal must not be derived from a raw pointer value, object-array index, FName
index, `PlayerDataID`, Steam/EOS/platform id, player name, IP address, or transfer
payload. A future private correlation layer may use stricter evidence internally, but the
copied plugin-facing value stays opaque.

## Generation Rules

`principal_id + generation` is the minimum validity key. `principal_id` alone is not a
stable authority token.

Generation must change whenever the same opaque slot could refer to a different live
player context or an old context is no longer valid. At minimum, future evidence and tests
must prove fail-closed behavior for:

- session start after previous invalidation;
- disconnect/logout;
- reconnect;
- transfer/download lifecycle edge;
- controller or player-state replacement;
- duplicate or conflicting identity evidence;
- failed validation or unsupported artifact;
- server process restart;
- plugin reload where cached callback data might outlive the owner.

Consumers must treat any missing principal, missing generation, mismatched generation, or
`invalidated` state as no identity. Stale values must not fall back to pointer lookup,
name matching, or platform-id guessing.

## Lifecycle Invalidation

Invalidation is a contract boundary, not a best-effort log event. A future implementation
must make stale principals unusable before any command, permission, or storage decision can
observe them as active.

Required invalidation behavior:

- callbacks expose only copied principal fields valid for that callback scope;
- post-callback UE lookup is not implied;
- cached plugin values require explicit generation checks before use;
- invalidation clears copied output for rejected or stale evidence;
- disabled capability, unsupported binary/artifact, missing lifecycle anchor, missing
  owner token, and malformed copied fields fail closed;
- logs and audit records must redact principal-adjacent private values by default.

Accepted login/logout or connect/disconnect target names are still missing. Layout
acceptance for such targets would not by itself promote this contract; privacy,
invalidation, callback ownership, and negative tests remain separate gates.

## Multi-Instance Limits

The default scope is one ARK server process. A principal from one process is not comparable
with a principal from another process unless a later explicit cross-instance contract says
so.

Required default limits:

- no cluster-stable identity claim;
- no persistence claim across restart;
- no shared permissions, cooldowns, economy balances, storage ownership, or moderation
  state across instances;
- no promise that the same player receives the same `principal_id` on another map,
  server, restart, or transfer;
- no use of platform ids, player names, transfer ids, or saved payload fields as a public
  substitute for cross-instance identity.

Any later multi-instance design must be a separate privacy-reviewed surface with storage,
operator, redaction, abuse-control, and consistency rules. It cannot be inferred from this
process-local principal contract.

## Non-Claims

This note does not claim:

- `obelisk.player_identity.v1` exists;
- any public SDK or runtime surface is ready;
- login/logout lifecycle anchors are accepted;
- `ServerListPlayers`, `ServerKickPlayer`, chat, tribe, mission, transfer, or admin
  functions provide public identity;
- commands, replies, permissions, economy, persistence, moderation, or player lookup are
  available;
- `ResourceHandle`, object identity, raw UE pointers, raw params, FName/GObjects indices,
  `PlayerDataID`, Steam/EOS/platform ids, names, IPs, tribe ids, transfer ids, or saved
  payload fields may be exposed;
- mutation, return override, server observation, scanners, ptrace, `gcore`, restarts, or
  live-server access are authorized.
