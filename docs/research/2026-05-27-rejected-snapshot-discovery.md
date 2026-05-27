# Rejected Snapshot Discovery

## Objective

Look for real-core `UFunction` targets that naturally produce rejected snapshot evidence
instead of fabricating rejected examples in synthetic fixtures.

## Environment

- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `011ee6d Add PrimalBuff UFunction snapshot fixtures`
- Live-server impact: none.

## Hypothesis

Large struct-heavy or command-like functions might reveal real rejected chains if the
current inspector hits `ParmsSize` bounds, membership mismatches, or property-count
inconsistencies.

## Method

Inspected exact high-risk/deferred targets with `--snapshot-json`:

```text
ShooterPlayerController.ServerRequestInventoryUseItemWithTransform
PrimalItem.ServerSendItemExecCommandToPlayer
ShooterPlayerController.ServerRequestDownloadDino
PrimalItem.UseItemAddCharacterStatusValue
PrimalItem.UseSpawnActorLocOffset
```

## Evidence

All three resolved as valid candidate chains:

```text
ShooterPlayerController.ServerRequestInventoryUseItemWithTransform
  InventoryComp ObjectProperty @0x0 size 8
  ItemId StructProperty @0x8 size 8
  SpawnTransform StructProperty @0x10 size 48
  ParmsSize 64
  status candidate

PrimalItem.ServerSendItemExecCommandToPlayer
  ToPC ObjectProperty @0x0 size 8
  CommandName NameProperty @0x8 size 8
  ExecParams StructProperty @0x10 size 64
  bIsReliable BoolProperty @0x50 size 1
  bForceSendToLocalPlayer BoolProperty @0x51 size 1
  bIgnoreRelevancy BoolProperty @0x52 size 1
  ParmsSize 83
  status candidate

ShooterPlayerController.ServerRequestDownloadDino
  DownloadedDino StructProperty @0x0 size 288
  ParmsSize 288
  status candidate

PrimalItem.UseItemAddCharacterStatusValue
  target class_name ScriptStruct
  property_chain status rejected
  reject reason property_count_mismatch

PrimalItem.UseSpawnActorLocOffset
  target class_name StructProperty
  property_chain status rejected
  reject reasons property_0_not_readable_as_uobject, property_chain_depth_limit
```

## Result

No real rejected `UFunction` snapshot was found in this pass. The three deferred functions
resolved as valid metadata chains. The two rejected exact hits were not functions
(`ScriptStruct` and `StructProperty`), confirming that broad `Use` inventory matches can
surface non-call metadata objects.

## Rejected Paths

- Do not commit a fake rejected real-core snapshot.
- Do not commit non-`UFunction` rejected snapshots under the `UFunction` snapshot manifest.
- Do not treat large valid chains as public decoding readiness.
- Keep transfer, transform, and item NetExec surfaces deferred until struct decoding and
  policy gates are stronger.

## Risks

- A valid metadata chain can still be unsafe for runtime or public SDK use.
- Large `StructProperty` snapshots may invite over-interpretation if committed too early.

## Next Steps

1. Keep synthetic rejected fixtures for analyzer failure behavior.
2. Add real rejected snapshots only when core evidence naturally produces rejection.
3. Treat exact non-function matches as rejected discovery evidence in research notes, not
   snapshot fixtures.
