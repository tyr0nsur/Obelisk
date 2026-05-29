# Minimal Second-Source Readiness

## Objective

Record the executed direct-root second-source intake result for the compact inventory and
structure UFunction target set.

## Artifact

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Offline workspace:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`
- Readiness report:
  `pack/snapshot-comparison/readiness-report.json`
- Input binary/core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/`
- FName root slot: `0x5956f30`
- GObjects candidate used for snapshot regeneration: `0x595b7e0`

## Result

The executed intake used direct FName-root validation instead of a broad FName scan. The
root validation matched all requested clues:

```text
None=0
ClientMessage=4884
ServerChat=9619
SetActiveMissionDebugFlags=9622
```

Snapshot comparison result:

```text
gate_mode=second_source_promotion
promotion_gate.ready=true
promotion_gate.blockers=[]
targets=4
comparable=4
second_source_accepted=4
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
```

Accepted target modules:

```text
sdk_inventory: 2/2
  PrimalItem.AllowRemoteAddToInventory
  PrimalItem.CanUse

sdk_structures: 2/2
  PrimalStructure.AllowStructureAccess
  PrimalStructure.IsAllowedToDemolish
```

## Promotion Boundary

This promotes compact UFunction layout evidence for the listed inventory and structure
targets only. It does not promote:

- `GObjects` or `FUObjectArray` as a runtime-stable global;
- `ResourceHandle`, object identity, player identity, item identity, or inventory identity;
- raw `UObject*`, `UFunction*`, FName/GObjects indices, raw params, arrays, or structs;
- mutation, return override, or public Inventory SDK callbacks.

## Next Step

Use this evidence to harden copied-scalar observer work. For public API movement, keep the
existing bar: copied POD payloads, owner-token lifecycle cleanup, ABI layout tests,
installed SDK consumer tests, explicit redaction docs, and no UE internals crossing the
SDK boundary.
