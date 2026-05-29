# Next Target Set Discovery

Post-RC research/layout note only. This is not active RC routing and does not promote a
public Mission, Tribe, Transfer, or broader module SDK.

## Objective

Pick the next high-value `UFunction` target family beyond chat for generic Linux modding
events/resources, using existing snapshot/readiness tooling and copied offline artifacts.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit: `a6b2649`
- Date: 2026-05-29
- Inputs: copied offline artifacts only under `/servidor/ark/workspace-offline`
- Binary SHA256: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core SHA256: `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- FName root slot: `0x5956f30`
- GObjects candidate: `0x595b7e0`
- Live-server impact: none. No runtime, restart, marker, scanner, ptrace, `gcore`,
  commit, or push.

## Commands Run

Coverage check for the unpromoted P1 target sets:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --target-set mission-compact-intake \
  --target-set tribe-compact-intake \
  --target-set transfer-ufunction-intake \
  --json
```

Regenerated second-source snapshots for the two best next candidates:

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --evidence-pack-manifest /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json \
  --output-root /servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z/ufunction-snapshots \
  --target-set mission-compact-intake \
  --target-set tribe-compact-intake \
  --write
```

Compared readiness:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z/ufunction-snapshots \
  --target-set mission-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json > /servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z/pack/snapshot-comparison/mission-readiness-report.json

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z/ufunction-snapshots \
  --target-set tribe-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json > /servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z/pack/snapshot-comparison/tribe-readiness-report.json
```

## Evidence

Coverage: all 16 requested mission, tribe, and transfer UFunction targets were present
once in the copied core, with `InternalIndex` round-trip checks passing.

Second-source readiness:

- `mission-compact-intake`: `4/4` accepted, `promotion_gate.ready=true`, blockers `[]`.
- `tribe-compact-intake`: `5/5` accepted, `promotion_gate.ready=true`, blockers `[]`.

Useful mission shapes:

- `MissionType.AddPlayerToMission`: object + `bForceAdd` bool + bool return.
- `MissionType.BPAllowPlayerToLeaveMission`: object + bool return.
- `MissionType.BPOnPlayerRemovedFromMission`: object refs + two bool state flags.
- `MissionType.GetPlayerUsableItems`: object + array output; keep value payload blocked.

Useful tribe shapes:

- `ShooterPlayerController.ServerRequestTribeLog`: zero params.
- `ShooterPlayerController.IsInTribe`: bool return only.
- `ShooterPlayerController.AllowTribeGroupPermission`: byte permission + object + bool
  return.
- `ClientReceiveMyTribeOnlineList` and `ClientReceiveActiveMissionTags`: array payloads;
  layout evidence only.

## Ranking

1. `mission-compact-intake` as the first post-RC candidate after RC scope is closed. It
   gives broadly useful mission lifecycle metadata, compact object/bool chains, and
   accepted second-source layout evidence. A copied/redacted design is only a post-RC
   possibility after policy, ABI, lifecycle, runtime observation, and release gates pass.
   Do not expose player/controller pointers, mission object identity, item arrays, or
   return overrides.
2. Split `tribe-compact-intake` into a future scalar internal subset and an internal array
   subset before any public discussion. The scalar subset is high-value for
   permission/log-request telemetry, but tribe identity is sensitive. Online-player IDs
   and active mission tag arrays stay internal.
3. Keep `transfer-ufunction-intake` below mission/tribe despite unique offline coverage.
   It is valuable for resource roadmap work, but upload/download semantics, nested structs,
   items, dinos, player data, and identity make it a higher-risk layout-only track.

## Promotion Criteria

The accepted reports promote only UFunction layout evidence for the exact target sets.
Runtime/public promotion still requires:

- exact name/outer/`ParmsSize`/property-chain recognizers and binary-SHA gates;
- approved debug runtime observation with budget and no sensitive value logging;
- dispatch after original `ProcessEvent` returns, with no mutation and no return override;
- copied Obelisk-owned POD payloads only, with raw UE pointers, FName/GObjects indices,
  player/item/dino/tribe identity, arrays, strings, and object/class pointers redacted;
- append-only ABI, callback owner cleanup tests, installed SDK consumer tests, and docs;
- a reduced public target list for tribe/mission arrays unless deep-copy and redaction
  policy is explicitly accepted.
