# Next Offline Gold Extraction

## Objective

Choose the fastest next offline extraction that helps plugin/resource work without touching
live servers or colliding with the active minimal second-source intake.

Candidates considered:

- Broader `FName`/`GObjects`/`UFunction` parameter-layout extraction.
- `dino-compact-intake` target promotion.
- `FUObjectItem` reconciliation for future internal resource identity work.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit: `a6b2649b4895`
- Date: 2026-05-29
- Inputs: copied offline artifacts only under `/servidor/ark/workspace-offline`
- Binary:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
- Core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- FName root slot used for this artifact: `0x5956f30`
- `GObjects` candidate used for this artifact: `0x595b7e0`
- Live-server impact: none. No server path reads outside the approved offline workspace,
  restarts, marker changes, ptrace, `gcore`, scanner runs, staging, commits, or pushes.

## Recommendation

The fastest next high-value extraction is `FUObjectItem` reconciliation, with the dino
compact targets used as bounded sample indices.

Reasoning:

- Broad `FName`/`GObjects`/`UFunction` extraction already has enough candidate evidence to
  regenerate focused target sets. More broad scanning is lower value than resolving the
  fields that block resource identity and object-lifetime reasoning.
- `dino-compact-intake` is useful and cheap, but it is not the best public/plugin surface
  ahead of the existing structure and inventory work. Its two targets are still good
  samples because they are compact and resource-adjacent.
- `FUObjectItem` reconciliation directly supports future internal `ResourceHandle` design:
  it checks point-in-time `GObjects[index]` membership, records `item+0x8` and `item+0xc`
  neutrally, and tests whether the static handle-accessor hypothesis is compatible with
  real copied-core samples.

Do not promote a public resource handle from this note. The result is still a
single-core reconciliation artifact, not lifetime/reuse proof.

## Commands Run

Inventory the dino compact target set from the copied core:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --target-set dino-compact-intake \
  --json | jq '{status, unfiltered_function_count, target_set_coverage}'
```

Build a bounded evidence pack that samples baseline objects plus the two dino UFunction
objects:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --output-dir /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack \
  --no-default-candidates \
  --no-default-fname-roots \
  --fname-root-slot verified_fname_root_slot=0x5956f30 \
  --gobjects-candidate gobjects=0x595b7e0 \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447 \
  --gobjects-sample-index 19479 \
  --gobjects-sample-index 19489
```

Output artifacts:

- `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/manifest.json`
- `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/gdb-core.txt`
- `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/ShooterGameServer.objdump`
- `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/ShooterGameServer.strings.txt`
- readelf/file sidecars for the binary and core in the same pack directory

## Results

Dino target coverage from offline inventory:

```text
status=offline-inventory
unfiltered_function_count=5269
dino-compact-intake requested=2 matched=2 missing=0
PrimalDinoCharacter.AddPassenger:
  index=19479 object=0x7ffff10aca90 name_index=8267 flags=0x4020401
  num_parms=6 parms_size=16 internal_index_matches=true
PrimalDinoCharacter.AllowCarryCharacter:
  index=19489 object=0x7ffff10ad000 name_index=8269 flags=0x4020400
  num_parms=2 parms_size=9 internal_index_matches=true
```

Evidence-pack status:

```text
created_at_utc=2026-05-29T03:13:44.944465+00:00
evidence_status.status=complete
gdb_core_failed=false
promotion_gate.ready=false
promotion_gate.blockers=single_core_artifact, needs_second_isolated_capture_or_static_path
```

`GObjects` membership and neutral `FUObjectItem` field samples:

```text
index 0:
  object=0x7ffff0e59000 name=/Script/CoreUObject class=Package
  fuobject_item=0x7d90000 item_qword_0x8=0x7265746f00000000
  item_dword_0x8=0x0 item_dword_0xc=1919251567
  internal_index=0 internal_index_match=1

index 1:
  object=0x5b0d340 name=Object class=Class
  fuobject_item=0x7d90010 item_qword_0x8=0x656d616700000000
  item_dword_0x8=0x0 item_dword_0xc=1701667175
  internal_index=1 internal_index_match=1

index 25447:
  object=0x7ffff1176d40 name=ServerChat class=Function
  fuobject_item=0x7df3670 item_qword_0x8=0x6563727500000000
  item_dword_0x8=0x0 item_dword_0xc=1701016181
  internal_index=25447 internal_index_match=1

index 19479:
  object=0x7ffff10aca90 name=AddPassenger class=Function
  fuobject_item=0x7ddc170 item_qword_0x8=0x50223d6700000000
  item_dword_0x8=0x0 item_dword_0xc=1344421223
  internal_index=19479 internal_index_match=1

index 19489:
  object=0x7ffff10ad000 name=AllowCarryCharacter class=Function
  fuobject_item=0x7ddc210 item_qword_0x8=0x52676e6900000000
  item_dword_0x8=0x0 item_dword_0xc=1382510185
  internal_index=19489 internal_index_match=1
```

## Interpretation

This supports the current cautious model:

- Direct `GObjects[index]` point checks work for baseline objects and the dino compact
  UFunction targets.
- The sampled objects resolve through the artifact-specific FName root to the expected
  names and class names.
- The low dword at `FUObjectItem+0x8` is zero for all five sampled objects. That does not
  reject the static handle-accessor path; it is compatible with serial publication being
  lazy or absent for objects that have not been materialized into weak handles in this core.
- `FUObjectItem+0xc` is nonzero in all samples, but remains unknown. Do not reinterpret it
  as a serial field just because it has nonzero values.
- This pack improves reconciliation evidence only. It does not prove object lifetime,
  slot reuse, serial invalidation, or safe handle duration after a hook frame.

## Rejected Paths

- Do not spend the next offline turn on another broad UFunction inventory unless a target
  set is missing from inventory. The dino compact targets are present and unique.
- Do not rerun minimal second-source intake phases from this dino task. The accepted
  minimal report is already recorded under
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`,
  and its scope is limited to compact inventory/structure UFunction layout evidence.
- Do not treat `item+0xc` as a resource-handle serial.
- Do not expose `GObjects` indices, raw pointers, `FUObjectItem` fields, or FName indices
  through the public ABI.

## Next Agent-Ready Task

Implement a small offline reconciliation report, not runtime code:

1. Add a script mode or helper that reads a core plus explicit `--fname-root-slot` and
   `--gobjects-candidate`, samples named indices, and emits JSON with:
   `index`, `fuobject_item`, `object`, `item_dword_0x8`, `item_dword_0xc`,
   `item_qword_0x8`, `uobject.internal_index`, object/class/outer names, and membership
   pass/fail.
2. Feed it this pack's five indices plus a few high-value live-object class samples from
   existing offline inventories.
3. Compare those values against the static handle-accessor evidence from
   `0x1d56970..0x1d56eb0`.
4. Keep the output under `/servidor/ark/workspace-offline` and summarize it in a new
   `docs/research/` note. Acceptance remains internal-only unless a separate second
   isolated capture or independent static path proves the lifetime and reuse rules.
