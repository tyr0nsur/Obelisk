# Public Gameplay Event Readiness Audit

## Objective

Record the first promoted Obelisk gameplay event and the evidence boundary that keeps it
useful for plugin authors without exposing UE4 internals.

This note is offline documentation. It does not authorize server restarts, marker changes,
runtime observers, scanners, ptrace, `gcore`, broad tracing, or new module promotion.

## Current Public Contract

`docs/public_gameplay_events.json` declares one promoted event:

```json
{
  "event_id": "obelisk.gameplay_policy.v1",
  "public_name": "GameplayPolicyEvent",
  "capability": "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
  "backing_target_set": "structure-observer-intake",
  "inventory_backing_target_set": "minimal-second-source-intake"
}
```

`GameplayPolicyEvent` is an Obelisk-level copied POD policy signal. It is not a public
`StructureEvents` wrapper, public Inventory SDK, or `InventoryPolicyEvent` wrapper, and it
does not expose `UObject`, `UFunction`, `FString`, raw parameter buffers, UE property
pointers, FName/GObjects indices, caller objects, player identity, character identity,
structure identity, inventory identity, item identity, mutable parameter storage, or
pincode values.

## Promotion Decision

`GameplayPolicyEvent` can be promoted as the first public gameplay event because the
structure-backed target set and compact inventory extension now have accepted
second-source evidence:

- `structure-observer-intake` reports `promotion_gate.ready=true` with 6/6 accepted targets;
- `minimal-second-source-intake` reports `promotion_gate.ready=true` with blockers=[] and
  4/4 accepted targets for `sdk_inventory` and `sdk_structures`;
- the public payload is copied Obelisk-owned POD before plugin callbacks run;
- there are no UE internals in the ABI;
- the ABI is append-only in `ObeliskApi` and capability-gated by
  `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS`;
- registration returns process-local owner-token handles;
- unregister is owner-scoped through `UnregisterGameplayPolicyEventWithOwnerToken`;
- plugin-owner cleanup removes callbacks on init failure and unload;
- ABI layout and lifecycle tests cover the public structs, masks, registration, dispatch,
  unregister, and cleanup path;
- C SDK consumer fixtures compile the public struct, callback typedef, masks, and copied
  scalar payload shape.

Runtime-observer summaries and single-instance logs remain review artifacts. They do not
satisfy the SDK contract gate by themselves.

## Public Payload

The ABI uses `field_mask`, `bool_values`, and `int32_values[]` so plugins can read only
fields that are explicitly present. The bridge maps internal structure and inventory
scalars by `switch`, not by enum ordinal.

| Event kind | Public copied fields | Redacted |
| --- | --- | --- |
| `STRUCTURE_ACCESS_CHECK` | `ReturnValue` bool | `ForPC`, player identity, caller/object ptr, FName/GObjects, raw params |
| `STRUCTURE_DEMOLISH_CHECK` | `ReturnValue` bool | `ForPC`, player identity, caller/object ptr, FName/GObjects, raw params |
| `STRUCTURE_VARIANT_CHANGE` | `VariantIndex` int32, `BForceSet` bool, `ReturnValue` bool | caller/object ptr, FName/GObjects, raw params |
| `STRUCTURE_ACTIVATION_TOGGLE` | `ReturnValue` bool | `ForPC`, player identity, caller/object ptr, FName/GObjects, raw params |
| `STRUCTURE_PIN_CODE_CHECK` | `ReturnValue` bool only | `pinCode`, player identity, container/structure object, caller ptr, FName/GObjects, raw params |
| `STRUCTURE_SEAT_CHECK` | `BForce` bool, `ReturnValue` bool | `ForPC`, `forCharacter`, player/character identity, seat/object ptr, FName/GObjects, raw params |
| `INVENTORY_REMOTE_ADD_CHECK` | `BRequestedByPlayer` bool, `ReturnValue` bool | inventory identity, inventory contents, item identity, player identity, caller/object ptr, FName/GObjects, raw params |
| `INVENTORY_USE_CHECK` | `BIgnoreCooldown` bool, `ReturnValue` bool | inventory identity, item identity, player identity, cooldown/mutable item state, caller/object ptr, FName/GObjects, raw params |

`STRUCTURE_PIN_CODE_CHECK` is ReturnValue-only. That still creates a low-detail success/fail
timing signal, so plugins that do not need it should omit
`OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK` from their event-kind mask.

## Still Blocked

Inventory-backed policy signals are now promoted only through `GameplayPolicyEvent`
masks/kinds/fields and `OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED`. No public Inventory SDK is promoted; no public `InventoryPolicyEvent` ABI, Inventory capability bit,
item handle, lookup API, mutation API, or return-override contract is promoted. Chat,
players, tribes, dinos, missions, transfers, permissions, timers, admin, commands, public
`StructureEvents`, mutation, and return overrides also remain blocked until they each have
copied payloads, ABI tests, privacy/redaction policy, owner-token lifecycle cleanup, and
accepted target-set evidence.

`minimal-second-source-intake` is not a standalone public gameplay API. Its inventory
targets back only the copied/redacted inventory resource kind and event masks inside
`GameplayPolicyEvent`; its two structure targets remain a compact subset of the broader
structure observer review.

## Evidence And Tests

Primary public manifest: `docs/public_gameplay_events.json`.

Second-source evidence:

- `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`
- `docs/research/2026-05-28-second-source-core-intake-runbook.md`
- `docs/research/2026-05-29-minimal-second-source-readiness.md`

Runtime/ABI coverage:

- `tests/abi/AbiLayoutTests.cpp`
- `tests/core/PluginManagerTests.cpp`
- `tests/core/StructureEventDispatcherTests.cpp`
- `tests/core/InventoryPolicyEventDispatcherTests.cpp`
- `tests/sdk_consumer/MinimalPlugin.cpp`
- `tests/sdk_consumer/SdkConsumerFixture.cpp`
- `tests/sdk_consumer/CAbiPlugin.c`
- `tests/sdk_installed_consumer/c_abi_plugin.c`

## Next Evidence Needed

Before a richer gameplay SDK surface is added, produce a new manifest entry and evidence
pack with target id, intended public payload fields, ARK binary SHA256, second-source
comparison JSON, runtime observation only from an approved debug/development instance if
needed, ABI layout tests, installed SDK consumer tests, lifecycle cleanup tests, and an
explicit redaction statement.
