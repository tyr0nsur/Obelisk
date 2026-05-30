# Offline-Useful Dino Audit

## Objective

Independently audit the next small module-relevant evidence after the current Structures
and Inventory work. The focus is the UE4 reconstruction chain that still matters for
internal layout promotion:

1. artifact-specific `FName` root,
2. `GObjects`/`UObject` membership,
3. `UFunction` parameter layouts bounded by `ParmsSize`,
4. the smallest useful dino snapshot target set.

No live servers were touched. This note used only repo files and offline-safe artifacts
under `/servidor/ark/workspace-offline`.

Status update: this note records the pre-regeneration audit point. The later
`2026-05-29-dino-compact-second-source-readiness.md` note accepts
`dino-compact-intake` as offline layout evidence only. Use that later note for current
layout status; keep this note as the object-membership and next-task audit that preceded
the regenerated snapshot comparison.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Obelisk commit observed: `a6b2649`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Independent vanilla core SHA256 from the workspace pack:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Workspace pack:
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack`

## Bounded Commands Run

These commands were lightweight reads of committed fixtures or already-generated
workspace text/JSON. They did not run GDB, objdump, scanner workloads, server commands,
or direct protected dump reads.

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set dino-compact-intake \
  --json

jq '{fname_root_slots, gobjects_candidates, gobjects_sample_indices, evidence_status, promotion_gate, binary, core, obelisk}' \
  /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/manifest.json

rg -n 'gobjects|sample|25447|19479|19489|595b7e0|595b7f0|595b804|595b838|FUObject|item|InternalIndex|fname|FName' \
  /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/gdb-core.txt

sed -n '807,1088p' \
  /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/gdb-core.txt
```

## Evidence

At this point in the sequence, the dino compact readiness report was exactly two
comparable primary fixtures and zero accepted second-source fixtures:

```text
target_set=dino-compact-intake
targets=2
comparable=2
missing_second_source=2
promotion_gate.ready=false
targets:
  PrimalDinoCharacter.AddPassenger
  PrimalDinoCharacter.AllowCarryCharacter
```

The workspace pack is complete and already carries the right artifact-specific roots for
the vanilla core:

```text
fname_root_slot verified_fname_root_slot = 0x5956f30
fname_table resolved in core            = 0x5a94660
gobjects candidate                      = 0x595b7e0
gobjects chunks in core                 = 0x734fcc0
gobjects count in core                  = 830438
sampled indices                         = 0, 1, 25447, 19479, 19489
evidence_status.status                  = complete
gdb_core_failed                         = false
promotion_gate.ready                    = false
```

FName decoding through the explicit root is coherent for the known clues:

```text
index 0    -> None
index 4884 -> ClientMessage
index 9619 -> ServerChat
```

The useful new dino-specific "gold" is that the pack directly samples both committed
`dino-compact-intake` UFunction object indices through `GObjects[InternalIndex]`:

```text
GObjects[19479]:
  object name      AddPassenger
  class name       Function
  internal index   19479
  backref match    true

GObjects[19489]:
  object name      AllowCarryCharacter
  class name       Function
  internal index   19489
  backref match    true
```

This is stronger than string proximity: it ties the UFunction identities to the
artifact-specific FName root and to direct object-array membership in the independent
vanilla core. It still is not a sanitized UFunction property-chain comparison.

The committed primary dino layouts remain:

```text
PrimalDinoCharacter.AddPassenger
  NumParms=6 ParmsSize=16 ReturnValueOffset=0xf
  ACharacter ObjectProperty @0x0 size 8
  PassengerSeatIndex IntProperty @0x8 size 4
  bForcePassenger BoolProperty @0xc size 1
  bAllowFlyersAndWaterDinos BoolProperty @0xd size 1
  bSkipLineTrace BoolProperty @0xe size 1
  ReturnValue BoolProperty @0xf size 1

PrimalDinoCharacter.AllowCarryCharacter
  NumParms=2 ParmsSize=9 ReturnValueOffset=0x8
  CanCarryPawn ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1
```

## Rejected Paths

- Do not treat the completed core pack as global `GObjects` promotion. Its manifest
  correctly keeps `promotion_gate.ready=false` with `single_core_artifact` and
  `needs_second_isolated_capture_or_static_path`.
- Do not expose dino object pointers, `InternalIndex`, FName indices, raw `UObject*`,
  `FUObjectItem` values, or pointer-derived IDs through plugin ABI.
- Do not use the sampled `FUObjectItem+0x8/+0xc` values as a public lifetime or handle
  contract. The static accessor path still points to `FUObjectItem+0x8` for serial-like
  handle checks, but these sampled UFunction items show `item_dword_0x8=0`; that keeps
  lifetime semantics unresolved.
- Do not broaden the next dino target into attack, taming, rider, transfer, or controller
  stats yet. Those surfaces add mutation or identity risk without helping the compact
  second-source promotion gate.

## Result

The next internal layout dino target should remain the compact pair:

```text
PrimalDinoCharacter.AddPassenger
PrimalDinoCharacter.AllowCarryCharacter
```

They are the best next target because they are compact, already fixture-backed, and now
have independent-core object-array membership evidence for the exact UFunction objects.
At this point they still needed second-source regenerated snapshots before any runtime
observer or SDK surface discussion. That follow-up is now recorded separately as offline
layout evidence only, not as runtime or SDK readiness.

## Completed Historical Follow-up

Do not route this as an active task. The bounded follow-up is now recorded as accepted
dino compact layout evidence in `2026-05-29-dino-compact-second-source-readiness.md`, not
as runtime or SDK readiness.

Regenerate and compare only the dino compact UFunction snapshots from the existing
workspace pack. This is bounded and should not wait on any active long scan:

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --evidence-pack-manifest /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/manifest.json \
  --output-root /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots \
  --target-set dino-compact-intake \
  --write

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots \
  --target-set dino-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

Acceptance for that task is narrow:

- both targets accepted by layout comparison,
- candidate snapshot evidence records all four identity fields,
- candidate `artifact_sha256`, `capture_id`, and `evidence_pack_id` are distinct from the
  primary fixture evidence,
- every target and property keeps `candidate-uobject` membership,
- no raw addresses or protected paths appear in committed snapshot JSON,
- outputs stay under `/servidor/ark/workspace-offline` unless a later review explicitly
  decides to promote sanitized fixtures.
