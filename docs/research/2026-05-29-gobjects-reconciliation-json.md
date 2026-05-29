# GObjects Reconciliation JSON Helper

## Objective

Implement and run a small offline JSON helper for `GObjects`/`FUObjectItem` reconciliation
against copied artifacts only. This is internal evidence for type reconstruction and
resource-identity research; it does not promote a public handle, runtime API, or stable
`FUObjectItem` contract.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Inputs: `/servidor/ark/workspace-offline` copied artifacts only
- Core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
- FName root slot: `0x5956f30`
- `GObjects` candidate: `0x595b7e0`
- Static comparison window: `0x1d56970..0x1d56eb0`
- Live-server impact: none. No server paths outside the approved offline workspace, no
  ptrace, `gcore`, restarts, staging, commits, or pushes.

## Helper

Added:

```text
scripts/reconcile_gobjects_samples.py
```

The helper requires explicit artifact-specific `--fname-root-slot` and
`--gobjects-candidate`, samples only requested indices, and emits JSON with:

- `index`, `fuobject_item`, `object`
- neutral `item_dword_0x8`, `item_dword_0xc`, and `item_qword_0x8`
- `uobject.internal_index`
- object, class, and outer names
- direct `GObjects[InternalIndex]` membership checks for the target, class, and outer
- a static-handle-accessor reconciliation block that treats `FUObjectItem+0x8` as the
  current serial-backed static hypothesis and keeps `FUObjectItem+0xc` unknown

The script rejects protected `/servidor/ark` input/output paths unless they resolve under
`/servidor/ark/workspace-offline`.

## Command

```bash
python3 scripts/reconcile_gobjects_samples.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --gobjects-candidate 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --sample-index package=0 \
  --sample-index object_class=1 \
  --sample-index primal_dino_character=225 \
  --sample-index shooter_cheat_manager=400 \
  --sample-index package_class=516 \
  --sample-index class_class=517 \
  --sample-index function_class=518 \
  --sample-index server_chat=25447 \
  --sample-index dino_add_passenger=19479 \
  --sample-index dino_allow_carry_character=19489 \
  --output /servidor/ark/workspace-offline/fuobjectitem-reconciliation-json-20260529T153000Z/gobjects-reconciliation.json
```

Output:

```text
/servidor/ark/workspace-offline/fuobjectitem-reconciliation-json-20260529T153000Z/gobjects-reconciliation.json
```

## Results

```text
sample_count=10
accepted_count=10
rejected_count=0
membership_pass_count=10
item_dword_0x8_zero_count=10
item_dword_0x8_nonzero_count=0
promotion_status=internal-only-single-artifact
```

`accepted_count` is the helper's per-sample validation result only. It does not accept or
promote `GObjects`, `GUObjectArray`, `FUObjectItem`, object lifetime, serial semantics,
or any public resource handle.

Sample summary:

```text
index 0      /Script/CoreUObject     class=Package   outer=<null>                item+0x8=0 item+0xc=1919251567
index 1      Object                  class=Class     outer=/Script/CoreUObject   item+0x8=0 item+0xc=1701667175
index 225    PrimalDinoCharacter     class=Class     outer=/Script/ShooterGame   item+0x8=0 item+0xc=808464432
index 400    ShooterCheatManager     class=Class     outer=/Script/ShooterGame   item+0x8=0 item+0xc=808464701
index 516    Package                 class=Class     outer=/Script/CoreUObject   item+0x8=0 item+0xc=1970435155
index 517    Class                   class=Class     outer=/Script/CoreUObject   item+0x8=0 item+0xc=1701999221
index 518    Function                class=Class     outer=/Script/CoreUObject   item+0x8=0 item+0xc=1294482809
index 25447  ServerChat              class=Function  outer=ShooterCheatManager   item+0x8=0 item+0xc=1701016181
index 19479  AddPassenger            class=Function  outer=PrimalDinoCharacter   item+0x8=0 item+0xc=1344421223
index 19489  AllowCarryCharacter     class=Function  outer=PrimalDinoCharacter   item+0x8=0 item+0xc=1382510185
```

## Interpretation

- The sampled object pointers round-trip through direct `GObjects[InternalIndex]` checks
  for target, class, and outer where an outer exists.
- The dino compact functions and their `PrimalDinoCharacter` outer are present as
  candidate UObjects in this copied core.
- `FUObjectItem+0x8` is zero for all sampled objects. This remains compatible with the
  static handle-accessor path because serial publication can be lazy or absent for objects
  that have not materialized weak handles in this core.
- `FUObjectItem+0xc` is nonzero in every sample, but the helper records it neutrally as
  unknown. It must not be treated as a resource-handle serial.
- This is still single-artifact evidence. It does not prove slot reuse, serial
  invalidation, handle lifetime, or public ABI safety.

## Validation

```bash
python3 scripts/test_reconcile_gobjects_samples.py
```

Result:

```text
Ran 5 tests in 0.090s
OK
```
