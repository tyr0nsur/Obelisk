# Inventory Observation Gate Plan

## Objective

Define the safe shape for a future disabled-by-default `sdk.inventory` runtime observer.
This is a design note only; no server restart, marker change, scanner, or live probe is
authorized by this document.

## Current Evidence

- Internal recognizer: `ue/InventoryReflection.{h,cpp}`.
- Fixture-backed targets:
  - `PrimalItem.CanUse`, FName index `6252`
  - `PrimalItem.AllowRemoteAddToInventory`, FName index `6236`
- Current binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Current status: internal hook-side observer is being added behind marker/env/SHA/budget
  gates. There is no public SDK event.

## Required Gate Shape

A future `ProcessEventInventoryReflection` gate must require all of these:

- `OBELISK_ENABLE_INVENTORY_REFLECTION=1`
- exact supported ShooterGameServer SHA256
- explicit non-zero observation budget, defaulting to `0`
- per-instance marker:
  `/servidor/ark/obelisk/state/instances/<instance>/enable-inventory-reflection`
- ProcessEvent hook enabled on an approved debug instance
- plugins disabled for the first runtime window

The order matters:

1. confirm the gate is enabled;
2. reject non-inventory `fname_index` with the cheap exact filter;
3. reserve observation budget;
4. read reflected metadata and bounded scalar ranges.

This avoids spending the budget on unrelated `ProcessEvent` calls.

## Privacy And Authority Rules

Inventory functions are gameplay-authoritative. The observer must not:

- override return values;
- mutate params;
- call original `ProcessEvent` manually;
- dispatch public plugin callbacks;
- expose raw `UObject*`, inventory contents, item ids, `ItemNetInfo`, arrays, actor refs,
  player identity, tribe/team identity, locations, cooldown bypass details, or container
  contents.

Initial logs should include only observation number, function name, FName index, outer FName
index, field count, field names, offsets, sizes, and `has_range`. `bIgnoreCooldown`,
`bRequestedByPlayer`, and `ReturnValue` remain internal metadata/scalar candidates only.

## Tests Before Runtime

Before implementation can be used in an approved debug/development window, add tests
proving:

- disabled gate does not read memory;
- missing marker does not enable observation;
- unsupported or missing SHA rejects;
- absent or `0` log limit reads nothing;
- non-inventory FName reads nothing and does not consume budget;
- budget is reserved only after exact inventory FName match;
- object params do not expose ranges;
- wrong outer, name number, property class, offset, size, or property chain shape rejects.

## Runtime Scope

Runtime inventory observation should remain offline-only until an explicit approved
`arkserver2` / TheIsland window or a dedicated isolated debug instance exists, with
rollback, stable posture verification, and shutdown afterward. Keep `arkserver` / Ragnarok
untouched while users are active.

## Current Status

Blocked before runtime. The next engineering step after the hook-side observer is more
offline validation and posture review, not a server run.
