# Player Identity Lifecycle Plan

## Current Supersession

Historical seed plan. Later player-identity evidence closed the 12-target fixture/admin
coverage route and accepted `ShooterGameMode.HandleNewPlayer` plus
`ShooterGameMode.OnLogout` as candidate-only lifecycle layout anchors. Do not use this
note to restart broad FName/GObjects/core discovery, admin snapshots, second-source
layout, or lifecycle layout work for the current binary. The active P0 blocker is
approved copied runtime principal lifecycle evidence under a current-turn
operator-approved live-ops window, followed by the locked planning-only
`identity_public_contract_gate_missing` review.

## Objective

Define the next small offline plan for `players_identity_lifecycle` using only existing
docs and target names already recorded in Obelisk research. This note is
candidate-only planning for a future target set; it does not run scans, read dumps, touch
servers, regenerate snapshots, or widen public SDK scope.

## Evidence Boundary

Allowed inputs for this pass:

- `docs/research/2026-05-30-v1-core-capability-map.md`
- `docs/research/2026-05-27-shooterplayercontroller-function-inventory.md`
- `docs/research/2026-05-27-mission-tribe-function-snapshot-fixtures.md`
- `docs/research/2026-05-27-array-payload-snapshot-gates.md`
- `docs/research/2026-05-27-transfer-upload-download-fixture-triage.md`
- accepted target-set names already documented in `scripts/reflection_target_sets.py`

Explicitly out of scope:

- no new core reads, dump reads, broad UFunction scans, scanners, ptrace, `gcore`, or
  runtime observation;
- no `/servidor/ark` reads/writes from this plan;
- no ResourceHandle, no lookup, no SDK, no runtime, no UE pointer exposure, no mutation,
  and no return override;
- no player, tribe, transfer, mission, chat, admin, or command public API promotion.

## Current Status

`players_identity_lifecycle` is not ready for a public surface. Existing evidence is useful
only as candidate metadata and privacy-risk classification:

- `ShooterPlayerController` has many session, admin, tribe, inventory, transfer, and chat
  names, but those names do not prove stable identity, connection lifecycle, authority, or
  safe lookup semantics.
- `ShooterPlayerState` appears in transfer target evidence, but current scalar IDs are
  redacted planning inputs, not player identifiers.
- Mission and tribe fixtures already show player/controller object refs, membership, and
  online-list shapes. Those fields are identity-sensitive and must stay recognition-only
  unless a separate promotion gate defines copied identity, privacy, and lifecycle policy.
- The current copied `ChatMessageEvent` intentionally excludes sender/player identity.
  That remains the precedent for this family: copied/redacted fields only.

## Closed Seed Set

The first offline `players_identity_lifecycle` target-set proposal should stay closed to
these already-known names. Additions require a separate docs-only review before any
fixture, scan, or runtime work.

| Seed group | Existing known names | Candidate use | Redaction rule |
| --- | --- | --- | --- |
| Controller session/admin pressure | `ShooterPlayerController.ServerListPlayers`, `ShooterPlayerController.ServerKickPlayer` | Demand signal for permission and authority planning only. | No copied fields; documentation-only until permissions and abuse controls exist. |
| Chat sender precedent | `ShooterPlayerController.ServerSendChatMessage` | Privacy precedent because the public event copies text/mode but not sender identity. | Sender, controller, player id, Steam/EOS/platform ids, and caller object remain redacted. |
| Tribe identity-risk shapes | `ShooterPlayerController.ServerRequestTribeLog`, `ShooterPlayerController.AllowTribeGroupPermission`, `ShooterPlayerController.IsInTribe`, `ShooterPlayerController.ClientReceiveMyTribeOnlineList`, `ShooterPlayerController.ClientReceiveActiveMissionTags` | Existing compact/array metadata that can inform identity and group-membership risk. | Copy no player ids, tribe ids, online-list values, names, tags, strings, or object refs. Bool returns remain candidate-only. |
| Transfer/lifecycle edge | `ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters` | Existing PlayerState transfer scalar shape for lifecycle-edge planning. | `PlayerDataID`, bed ids, transfer ids, and spawn/region choices remain redacted. |
| Mission player lifecycle precedent | `MissionType.AddPlayerToMission`, `MissionType.BPAllowPlayerToLeaveMission`, `MissionType.BPOnPlayerRemovedFromMission` | Existing add/leave/remove lifecycle names with copied bool precedent. | Player/controller object refs and mission identity remain recognition-only; only canonical bool ranges are future copied-field candidates. |

The v1 map mentions `ShooterPlayerController`/`PlayerState` login and lifecycle names as
the desired family. Current docs do not establish an exact accepted login/logout target.
Do not invent one in this plan. If a future offline inventory note names exact
login/logout targets, add them as candidate-only seeds first and keep the same redaction
and non-promotion rules.

## Copied/Redacted Field Policy

The only acceptable first payload design is copied/redacted fields, and even that is
future work after second-source layout evidence:

- Possible copied values: canonical bool bytes from known lifecycle-style functions, event
  kind enums owned by Obelisk, and local sequence numbers assigned by Obelisk.
- Redacted values: player ids, Steam/EOS/platform ids, names, IPs, tribe ids, online-list
  values, transfer ids, bed/spawn ids, mission tags, object refs, arrays, strings,
  `FName`/GObjects indices, raw params, and UE pointers.
- Recognition-only metadata may confirm exact `Outer.Function`, property names/classes,
  offsets, sizes, and array inner summaries. It must not be copied into plugin payloads as
  identity.
- Bool copying must use the existing canonical rule: accept only bytes `0` or `1`; reject
  non-canonical bytes instead of normalizing arbitrary nonzero values.

## Guarded Next Step

This pass can support a closed offline planning target-set named
`players-identity-lifecycle-intake`, using only the names in the closed seed set above.
That target-set is a guidance index for future review, not a release/readiness target,
not a public target-set, and not evidence that fixtures or second-source layouts exist
for every seed.

When offline artifact work is approved separately, the first review of
`players-identity-lifecycle-intake` should only answer:

1. Which of the closed seed names have existing sanitized fixtures or accepted
   second-source layout evidence?
2. Which fields are copied-scalar candidates and which are redacted identity/lifecycle
   risks?
3. Which exact login/logout names, if any, are already documented by accepted offline
   evidence rather than inferred from naming demand?

The output remains a review note or target-set definition only. It must keep
`promotion_gate.ready=false`, `promotion_ready=false`, no ResourceHandle, no lookup,
no SDK, no runtime, no mutation, and no return override until a separate promotion gate
proves stable copied identity, privacy policy, lifecycle cleanup, and fail-closed lookup
semantics.
