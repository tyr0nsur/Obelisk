# Player Principal Policy Route

Date: 2026-06-01

## Summary

The current v1 SDK route should stay focused on:

1. candidate-only player lifecycle layout evidence;
2. copied opaque principal privacy/invalidation policy;
3. query-only permissions/admin over that principal;
4. command response after identity and permissions can fail closed.

This route is driven by evidence and demand, not by a broad public SDK claim. The current
tree still reports `scripts/check_public_sdk_v1_completion.py --json` as blocked, with
`obelisk.player_identity.v1` unresolved. Do not describe this lane as stable, production
SDK, complete SDK, public identity, public permissions, command replies, runtime lookup,
ResourceHandle, mutation, return override, or cross-instance identity.

## Current Evidence Boundary

The player-identity lane has these planning-only facts:

- `players-identity-lifecycle-intake` fixture coverage is complete for the 12-target set.
- A distinct vanilla-gdb candidate root compares `12/12` accepted in planning-layout mode.
- `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` have corroborated
  layouts across two offline cores and can be consumed as candidate-only lifecycle layout
  anchors.
- Promotion remains blocked because principal privacy, generation, scope, and fail-closed
  invalidation semantics are not accepted.

These facts are enough to stop rerunning the completed admin snapshot and second-source
layout routes. They are not enough to expose a public player API.

The minimum lifecycle wording must stay narrow: `HandleNewPlayer` plus `OnLogout` can
only support an ARK-specific "accepted session observed" candidate lane. They do not
cover rejected admission, complete login ordering, stable player-data identity, respawn,
downloaded/transferred characters, or cross-map/cross-instance identity.

Additional offline candidates to investigate before a stronger lifecycle claim:

- `ShooterGameMode.CheckJoinInProgress`: pre/admission-shaped bool target with
  `bIsFromLogin`, `NewPlayer`, and `ReturnValue`; relevant if the gate claims join
  admission coverage.
- `GameMode.K2_PostLogin`, `ShooterGameMode.OnPostLogin__DelegateSignature`, and
  `ShooterGameMode.OnStartNewPlayer__DelegateSignature`: post-login/order candidates that
  need runtime ordering before any session-start semantic claim.
- `ShooterGameMode.GetPlayerData`, `GetPlayerDataByInt`, and `RemovePlayerData`: useful
  for identity lifetime research, but not public lookup or `ResourceHandle` evidence.
- Transfer/respawn/download targets such as `ServerRequestDownloadPlayerCharacter`,
  `ServerDownloadTransferredPlayer`, `ServerRequestRespawnAtPoint`, and
  `ServerRequestSpawnPointsForDownloadedCharacters`: out of the minimum gate unless the
  claim includes character restoration or transfers.

## Principal Shape Direction

The minimum future plugin-facing subject should be a copied opaque principal, not a UE
object handle. Required properties:

- `principal_kind`, `state`, `scope_flags`, and `generation`;
- an Obelisk-owned opaque id treated as bytes only;
- explicit privacy class and non-persistence boundary;
- no UE pointers, FNames, GObjects, raw params, Steam/EOS IDs, names, IP-like values,
  tribe ids, object references, display names, or transfer payloads as public identity;
- fail-closed behavior for missing, malformed, stale, mismatched-generation, wrong-scope,
  invalidated, duplicate, reconnect, transfer, logout, plugin reload, and restart cases.

Permissions/admin and commands should consume the copied principal that arrived with the
event or command invocation. They must not rediscover the player through UE pointers,
names, platform ids, chat text, or object lookup.

## Demand Signal

Local plugin demand dictionaries point to this P0 order:

- player identity/principal;
- permissions/admin;
- command input and response.

This unlocks or validates the largest set of ArkApi-style plugin concepts: shop, kits,
points, homes/teleport, safe zones, rewards, admin permissions, tribe/admin features,
structure limits, and command no-permission replies. The next useful validator concepts
after principal invalidation are `ArkShop` and `ArkHomes`-style flows because they combine
identity, permissions, economy/config, commands, and visible responses.

This does not authorize copying ArkServerApi/AseApi or NextGenPlugins code, offsets,
layouts, constants, parsers, ABI assumptions, or implementation behavior. They remain
names, demand, conceptual architecture, and migration ergonomics references only.

## Current Offline Policy Artifact

A consume-only policy/lifecycle bundle now exists at:

```text
/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/
```

It contains:

- `players-identity-lifecycle-anchor-candidates.json`
- `players-identity-principal-invalidation-policy.json`

Both manifests are accepted by `scripts/validate_offline_artifact_gate.py` in consume
mode. The principal policy checker accepts the candidate-only policy and keeps these flags
false:

- `promotion_ready`;
- `public_sdk_ready`;
- `runtime_ready`.

It should reject public principal overclaims, lookup claims, ResourceHandle/GObjects/FName
claims, permissions/commands unlock claims, mutation, return override, raw UE exposure,
unredacted identifiers, and cross-instance stability claims.

The lifecycle-anchor checker should remain candidate-only and should not accept new
values in `principal_policy.invalidation_semantics` as a shortcut to promotion. The
higher-level first-evidence readiness gate can now consume the lifecycle layout artifact
and principal policy artifact together, but it still reports
`approved_runtime_evidence_missing` and blocks public SDK promotion until runtime evidence
and public ABI review exist.

The first-evidence readiness report also emits
`first_evidence.runtime_principal_lifecycle_evidence`, a requirements-only block for the
future approved runtime step. That block is not accepted evidence. It keeps the next
runtime request bounded to copied, private lifecycle observations for
`ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`, plus fail-closed stale
or malformed principal checks. Offline layout comparison, lifecycle candidate manifests,
principal policy manifests, raw `ProcessEvent` traces, admin/listing UFunctions, and any
claim based on names, platform ids, UE pointers, `GObjects`, `FNames`, `ResourceHandle`,
lookup, mutation, or return override remain explicitly insufficient.
The requirements block also records that the current report does not authorize runtime
work, server operations, debug attachment, `ptrace`, `gcore`, runtime scanners, restarts,
Discord/community notices, GitHub publication, tags, pushes, or release claims.

`scripts/check_player_identity_runtime_principal_lifecycle_evidence.py` is the current
schema-specific guard for a future private runtime-evidence manifest. It accepts only a
synthetic/redacted shape fixture and reports `approved_runtime_evidence_present=false`;
`validate_offline_artifact_gate.py` can consume that schema, but promote mode remains
blocked. This gives the future runtime window a fail-closed manifest shape without
turning synthetic fixtures, raw logs, protected paths, UE coordinates, player identifiers,
or principal policy documents into public SDK evidence.
