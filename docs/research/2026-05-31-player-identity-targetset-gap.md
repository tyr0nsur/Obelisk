# Player Identity Target-Set Gap

## Objective

Identify the exact target-set, test, and tooling changes needed before Obelisk can build
a candidate-only first player identity evidence pack from the current
`players-identity-lifecycle-intake` planning lane.

This note is documentation-only. It does not promote identity, add public SDK, read dumps,
touch servers, run scanners, use ptrace or `gcore`, change fixtures, change target sets, or
authorize runtime observation.

## Current Target Set

`scripts/reflection_target_sets.py` already defines `players-identity-lifecycle-intake`
as a `planning_only` target set in the `players_identity` lane. It must stay
`planning_only`; do not move it into `RELEASE_READINESS_TARGET_SETS`.

Current closed targets:

| Target | Current evidence | First-pack role | Field policy |
| --- | --- | --- | --- |
| `ShooterPlayerController.ServerListPlayers` | Inventory candidate only: `Params=0`, `ParmsSize=0`; no committed sanitized snapshot. | Admin/session pressure only. | No copied fields; not login proof. |
| `ShooterPlayerController.ServerKickPlayer` | Inventory candidate only: `Params=2`, `ParmsSize=32`; no committed sanitized snapshot. | Admin/authority pressure only. | All fields redacted until an exact snapshot proves shape; no command or permission claim. |
| `ShooterPlayerController.ServerSendChatMessage` | Committed snapshot: `ChatMessage StrProperty@0x0 size=16`, `SendMode ByteProperty@0x10 size=1`, `ParmsSize=17`. | Chat privacy precedent. | Text/mode evidence only; no sender identity. |
| `ShooterPlayerController.ServerRequestTribeLog` | Committed zero-param snapshot, `ParmsSize=0`. | Tribe-control pressure. | No copied identity fields. |
| `ShooterPlayerController.AllowTribeGroupPermission` | Committed snapshot: enum-like byte, object ref, bool return, `ParmsSize=17`. | Permission-risk shape. | Enum/object redacted; return bool candidate-only. |
| `ShooterPlayerController.IsInTribe` | Committed snapshot: `ReturnValue BoolProperty@0x0`, `ParmsSize=1`. | Membership-risk shape. | Bool candidate-only; no player/tribe identity claim. |
| `ShooterPlayerController.ClientReceiveMyTribeOnlineList` | Committed snapshot: `OnlinePlayerIDs ArrayProperty@0x0`, inner `UInt32Property`, `ParmsSize=16`. | Identity-risk array shape. | Array and elements recognition-only/redacted. |
| `ShooterPlayerController.ClientReceiveActiveMissionTags` | Committed snapshot: `MissionTags ArrayProperty@0x0`, inner `NameProperty`, `ParmsSize=16`. | Mission/tribe context risk. | Array and `FName` values recognition-only/redacted. |
| `ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters` | Committed snapshot: `PlayerDataID UInt64Property@0x0`, `IgnoreBedID IntProperty@0x8`, `ParmsSize=12`. | Transfer/lifecycle-edge risk. | `PlayerDataID` and bed/spawn values private-redacted/forbidden for public identity. |
| `MissionType.AddPlayerToMission` | Committed snapshot: player object, `bForceAdd`, `ReturnValue`, `ParmsSize=10`. | Mission lifecycle precedent. | Object redacted; bools candidate-only. |
| `MissionType.BPAllowPlayerToLeaveMission` | Committed snapshot: player object, `ReturnValue`, `ParmsSize=9`. | Mission lifecycle precedent. | Object redacted; bool candidate-only. |
| `MissionType.BPOnPlayerRemovedFromMission` | Committed snapshot: player/controller objects, two bools, `ParmsSize=18`. | Mission removal precedent. | Objects redacted; bools candidate-only. |

## Exact Blockers

- The target set is incomplete as a fixture-backed pack: `build_redacted_ufunction_signatures.py
  --target-set players-identity-lifecycle-intake` currently fails with missing
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`.
- No exact session-start/login/connect target and no exact session-end/logout/disconnect
  target are accepted. The current seed set is pressure/risk classification, not identity
  lifecycle proof.
- The generic redacted UFunction signature report is not strict enough for player identity:
  identity-like scalar names such as `PlayerDataID` must be forced redacted for this pack,
  not reported as copied scalar candidates.
- No distinct second-source sanitized root covers the full 12-target planning set.
- No privacy policy accepts a copied public principal, hashed principal, persistent ID, or
  process-local ID.
- No lifecycle invalidation evidence proves cleanup for disconnect, transfer, reconnect,
  duplicate identity, stale controller/state object, failed validation, or server restart.
- `ResourceHandle`, public GObjects, object identity, lookup, mutation, return override,
  command routing, per-player permissions, and economy remain blocked.

## Required Target-Set Changes

No promotion change is needed. The required target-set work is coverage/completeness only:

1. Keep `players-identity-lifecycle-intake` exactly `planning_only`.
2. Add committed sanitized snapshots for the two existing missing targets before building
   a full target-set pack:
   - `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_players/ShooterPlayerController.ServerListPlayers.snapshot.json`
   - `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_players/ShooterPlayerController.ServerKickPlayer.snapshot.json`
3. Add matching `tests/fixtures/ufunction_snapshots/manifest.json` entries under a players
   fixture namespace such as `sdk_players`.
4. Update `docs/research/2026-05-27-module-readiness-matrix.md` for any new manifest
   module name so `scripts/test_ufunction_snapshot_fixtures.py` remains satisfied.
5. Do not add inferred login/logout names. If future offline inventory names exact
   lifecycle anchors, add them in a separate docs-only review first and keep them
   candidate-only.

## Required Tooling Changes

The first pack should be generated by a candidate-only identity-specific wrapper or mode,
not by public SDK tooling. Minimal shape:

- Input: `--target-set players-identity-lifecycle-intake`, sanitized snapshot root, and
  optional distinct second-source root.
- Output schema: candidate-only, for example
  `obelisk.players-identity-first-evidence.v1`.
- Required fields: artifact identity, binary SHA, Obelisk commit, target-set revision,
  target coverage, per-target exact shape, per-field classification, blockers, and
  non-claims.
- Required status: `promotion_ready=false`, `public_sdk_ready=false`,
  `readiness_classification=planning_only`.
- Field classifier: force player IDs, Steam/EOS/platform IDs, names, IPs, tribe IDs,
  transfer IDs, bed/spawn IDs, online-list values, mission tags, object refs, arrays,
  strings, `FName`/GObjects indices, raw params, and UE pointers to
  private-redacted/recognition-only/forbidden unless a later privacy policy narrows one
  copied form.
- Bool rule: any copied bool candidate must use canonical bytes only, `0` or `1`, and
  non-canonical values must reject and clear output.
- Second source: if supplied, compare layouts only and still report no promotion because
  the target set is planning-only.

Useful existing commands for a future approved offline pass, in the required order:

First produce or approve a complete `obelisk.core-dump-evidence-pack.v1` manifest from a
non-protected offline core. This note intentionally does not prescribe a server, dump
path, runtime action, or direct-core planning mode. Do not satisfy this lane from
ScriptStruct inventory, standalone snapshots, redacted signatures, static thunks, direct
`--core` plus manual `--gobjects`/`--fname-root-slot`, or a two-function-only inventory.

Then build the complete UFunction reflection inventory pack from that evidence-pack
manifest. The inventory must include function rows, stay tied to the complete core
evidence pack through `inputs.evidence_pack_manifest`, and report coverage for the full
12-target `players-identity-lifecycle-intake` set:

```bash
python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest <approved-complete-core-evidence-pack>/manifest.json \
  --include-functions \
  --target-set players-identity-lifecycle-intake \
  --output-dir <ignored-non-protected-output>/players-identity-reflection-inventory
```

Only after that inventory exists, plan exact focal snapshots for the two currently missing
admin/session targets. Do not plan the whole target set at this step; the full 12-target
coverage belongs to the inventory pack and later first-evidence validation, while snapshot
generation is currently missing only these two targets. The focal planner rejects broad
player-identity snapshot plans; this first missing-target pass must use exact `--target`
entries:

```bash
python3 scripts/plan_ufunction_focal_snapshots.py \
  --inventory-pack <approved-reflection-inventory-pack>/manifest.json \
  --target ShooterPlayerController.ServerListPlayers \
  --target ShooterPlayerController.ServerKickPlayer \
  --evidence-obelisk-commit <reviewed-obelisk-id> \
  --json-out <ignored-non-protected-output>/players-identity-admin-focal-plan.json
```

This emits candidate-only `inspect_core_ufunctions.py --snapshot-json` commands for those
two targets. It does not reread the core, execute commands, add fixtures, promote
identity, or authorize server work.

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <distinct-sanitized-second-source-root> \
  --target-set players-identity-lifecycle-intake \
  --readiness-report \
  --json
```

The expected comparison result may have `layout_ready=true` only after all 12 targets are
comparable, but `promotion_gate.ready=false` must remain blocked by
`target_set_not_release_readiness`.

## Required Tests And Gates

- Target-set listing test: assert `players-identity-lifecycle-intake` remains
  `planning_only`, `release_readiness=false`, `promotion_ready=false`, and
  `public_sdk_ready=false`.
- Fixture coverage test: after adding the two snapshots, assert the UFunction manifest
  covers all 12 player identity targets.
- Redacted pack test: build the candidate-only first evidence pack from the fixture root
  and assert full target coverage, no unexpected targets, complete artifact identity, and
  no public SDK fields.
- Missing-target negative test: removing either admin/session snapshot must fail closed.
- Identity scalar negative test: `PlayerDataID`, online player arrays, mission tags,
  object refs, chat strings, and any future `SteamID`/`EOSID`/`PlatformID` fields must not
  appear as copied public fields.
- Bool canonicality test: mission and tribe bool candidates accept only `0`/`1` and clear
  copied output on forged non-canonical bytes.
- Second-source gate test: full 12-target comparison can report layout comparison, but
  promotion remains blocked because the target set is planning-only.
- Public guardrail test: release/readiness validation must not accept this target set as a
  release target or public SDK evidence.
- Lifecycle blocker test: the pack must explicitly report missing accepted login/logout
  anchors until exact offline evidence adds them.

## Non-Claims

- This note does not promote `players-identity-lifecycle-intake`.
- This note does not claim an accepted player login/logout/session lifecycle target exists.
- This note does not add public player identity, command, permission, economy, admin,
  tribe, mission, transfer, lookup, persistence, database, chat-reply, moderation,
  mutation, or return-override APIs.
- This note does not promote `ServerListPlayers`, `ServerKickPlayer`,
  `ServerSendChatMessage`, tribe functions, transfer functions, or mission functions as
  public identity anchors.
- This note does not promote `ResourceHandle`, public GObjects, object identity, UE
  pointers, raw params, `FName`/GObjects indices, or pointer-derived handles.
- This note does not authorize runtime observation, server access, scanners, ptrace,
  `gcore`, broad tracing, marker changes, restarts, Discord updates, commits, tags, or
  pushes.
