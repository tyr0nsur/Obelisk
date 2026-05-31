# Module Readiness Matrix

> Historical/superseded module-readiness snapshot. The `sdk.*` names below are research
> track labels, not public SDK namespaces, C ABI surfaces, or release promises. Current
> contributor direction is core-first: runtime bootstrap, hook safety, C ABI stability,
> release readiness, and explicitly gated public surfaces first; gameplay modules only
> after their named evidence, ABI, lifecycle, and operator gates pass.

## Objective

Summarize the current module readiness state after the first manifest-backed real-core
snapshot rounds, without implying public SDK or runtime readiness.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- ScriptStruct fixture manifest:
  `tests/fixtures/scriptstruct_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `05fe0a3 Document reversing objective map` plus the current marker-gate follow-up.
- Live-server impact: none.

## Historical Readiness Snapshot

General v1 lane guardrail: this historical table keeps chat as one small copied
notification row, not the product center. Inventory, structures, items, mission, transfer,
buff, dino, tribe, and admin/permissions remain separate module lanes with independent
promotion gates before public work: exact layout evidence, fixtures,
second-source/static support, copied-data ownership, privacy/redaction policy, callback
lifetime cleanup, append-only ABI tests, installed SDK consumer coverage, and approved
runtime validation when runtime evidence is required.

| Research Track Label | Current Level | Real Snapshots | Evidence | Next Gate |
| --- | --- | ---: | --- | --- |
| `sdk.inventory` | `internal-marker-gated-observer` | 5 | Item/controller exact snapshots plus internal `InventoryReflection` and hook-side metadata observer for `CanUse` and `AllowRemoteAddToInventory`; arrays/structs/item contents stay blocked. | Offline/posture review before any approved debug/development activation under current operator direction; no SDK callbacks or gameplay mutation. |
| `sdk.items` | `fixture-backed` | 4 | Compact `PrimalItem` snapshots for equip, repair, blueprint crafting, and item-on-item use; copied scalar ranges are planning evidence only, with object refs still redacted. | Keep public Items SDK, Inventory SDK, item identity, mutation, return override, and `ResourceHandle` blocked. |
| `sdk.buffs` | `offline-internal-recognizer` | 6 | Focused `PrimalBuff` exact snapshots plus `ue/BuffReflection.*` tests for inventory-access, allow-add, prevent-add, bool-return, and zero-param shapes. This broadens the gameplay API substrate while staying metadata-only. | Keep runtime hooks, callbacks, return overrides, object/class exposure, and gameplay semantics blocked until second-source evidence and SDK policy exist. |
| `sdk.dinos` | `fixture-backed` | 2 | Passenger/carry real snapshots plus broader synthetic coverage for attack, tame-state, and controller dino stats. | Promote more real snapshots only for compact exact targets. |
| `sdk.structures` | `internal-marker-gated-observer` | 6 | Access/demolish plus pincode, container activation, seating, and variant snapshots; `StructureReflection` and disabled-by-default runtime gate require env, SHA, log budget, and `enable-structure-reflection` instance marker. | Any runtime activation still needs an explicit operator window and stable-posture rollback; keep placement/build-authoritative targets deferred. |
| `sdk.missions` | `fixture-backed` | 4 | Add, leave-policy, removal lifecycle, and usable-item array metadata snapshots. | Keep array/struct payloads metadata-only until second-source evidence. |
| `sdk.tribes` | `fixture-backed` | 5 | Tribe log control, permission enum-shape, membership bool-return, online-list array, and mission-tag array snapshots; log string remains deferred. | Keep string gates separate; do not decode client payload arrays yet. |
| `sdk.chat` | `minimal-event-rc-surface` | 1 | `ShooterPlayerController.ServerSendChatMessage` exact snapshot plus accepted copied-delivery validation for all four known send modes; public surface remains copied `ChatMessageEvent` only, without sender identity, UE internals, commands, mutation, or return override. | Further chat windows are regression/revalidation only unless a separate core-first promotion gate is defined; this historical note is not approval to activate any instance. |
| `sdk.transfers` | `fixture-backed` | 7 UFunction + 2 ScriptStruct | Compact transfer/download/upload scalar, object, class, bool-return snapshots, plus dino/player tribute ScriptStruct field fixtures. | Keep `ItemNetInfo`, nested arrays, strings, and runtime dispatch deferred. |
| `sdk.admin` | `documentation-only` | 0 | Admin surfaces identified but intentionally blocked. | Permission model and explicit policy; no runtime work. |
| `ue.reflection` | `internal-substrate` | n/a | FName/GObjects/UObject/UFunction/UProperty plus ScriptStruct inspection tooling underpins all modules. | Second-source evidence and runtime safety gates. |

## Result

The strongest general offline tracks are now `sdk.inventory`, `sdk.structures`,
`sdk.items`, `sdk.buffs`, `sdk.missions`, `sdk.tribes`, and `sdk.dinos`.
`sdk.transfers` also has fixture-backed evidence, but it remains intentionally risk-gated
because transfer payloads are gameplay-sensitive. None of these are public SDK modules:
current snapshots provide candidate evidence for exact metadata shape, membership checks,
and bounded property chains only.
The `sdk.` prefix in this historical note must not be reused as evidence that public
Inventory, Structure, Item, Buff, Dino, Mission, Tribe, Transfer, Admin, or broad Chat SDKs
exist.

## Policy Notes

- `StructProperty`, `ClassProperty`, and `NameProperty` in snapshots are metadata evidence,
  not public decoding contracts.
- Valid large chains can still be deferred for policy/runtime reasons.
- Rejected real-core snapshots should not be fabricated; non-`UFunction` rejected hits stay
  in research notes.
- Runtime observation remains gated to the currently approved debug/development target or
  an isolated debug instance during an approved window.

## Next Priorities

1. Keep first-stable work core-first; module labels here do not bypass release/public SDK
   gates.
2. Obtain second-source validation for `FName`/`GObjects`/`UObject`/`UFunction` before
   promoting recognizers beyond candidate-only.
3. Review the disabled-by-default `sdk.inventory` observation gate before any approved
   debug/development activation.
4. Add second-source validation for ScriptStruct transfer field layouts.
5. Keep `ItemNetInfo`, admin/NetExec, placement/build, and gameplay-authoritative mutation
   out of runtime work.
