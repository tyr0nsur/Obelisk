# GObjects Second-Core Reconciliation

## Objective

Record a small independent offline reconciliation for the `0x595b7e0` GObjects candidate
after the bounded static same-`FUObjectArray` check.

## Artifact

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Core:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- Core SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- Same-hash binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Independent comparison core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Output:
  `/servidor/ark/workspace-offline/gobjects-reconcile-second-source-20260529T034447Z/gobjects-reconciliation.json`
- FName root slot: `0x5956f30`
- GObjects candidate: `0x595b7e0`
- Sample indices: `0`, `1`, `25447`

## Command

```bash
python3 scripts/reconcile_gobjects_samples.py \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --sample-index Package0=0 \
  --sample-index Package1=1 \
  --sample-index ServerChat=25447 \
  --output /servidor/ark/workspace-offline/gobjects-reconcile-second-source-20260529T034447Z/gobjects-reconciliation.json
```

The same command was rerun without broad scans or runtime access and reproduced the same
`3/3` accepted result at:

```text
/servidor/ark/workspace-offline/gobjects-reconcile-minimal-second-source-20260529T034612Z/gobjects-reconciliation.json
```

## Result

```text
schema=obelisk.gobjects-sample-reconciliation.v1
sample_count=3
accepted_count=3
rejected_count=0
membership_pass_count=3
item_dword_0x8_zero_count=3
item_dword_0x8_nonzero_count=0
promotion_status=internal-only-single-artifact
```

Accepted samples:

```text
index 0
  object=/Script/CoreUObject
  class=Package
  InternalIndex=0
  target/class/outer membership passes

index 1
  object=Object
  class=Class
  outer=/Script/CoreUObject
  InternalIndex=1
  target/class/outer membership passes

index 25447
  object=ServerChat
  class=Function
  outer=ShooterCheatManager
  InternalIndex=25447
  target/class/outer membership passes
```

## Interpretation

This supports the `0x595b7e0` candidate on a second offline core: sampled
`GObjects[index]` entries round-trip through `UObject.InternalIndex`, and target/class/
outer membership checks pass. Combined with
`2026-05-29-static-gobjects-same-fuobjectarray.md`, the candidate is now much stronger for
offline reflection work.

## Boundary

This still does not promote a runtime-stable public object identity contract. The sampled
`FUObjectItem+0x8` values are zero in this artifact, so serial publication, reuse, and
invalidation semantics remain unproven. `FUObjectItem+0xc` remains unknown and must not be
used as a serial. Keep `ResourceHandle`, lookup, mutation, return override, raw `UObject*`,
class/outer exposure, and persistent object identity blocked.
