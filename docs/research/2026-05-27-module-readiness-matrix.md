# Module Readiness Matrix

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

## Readiness Snapshot

| Module | Current Level | Real Snapshots | Evidence | Next Gate |
| --- | --- | ---: | --- | --- |
| `sdk.inventory` | `internal-marker-gated-observer` | 5 | Item/controller exact snapshots plus internal `InventoryReflection` and hook-side metadata observer for `CanUse` and `AllowRemoteAddToInventory`; arrays/structs/item contents stay blocked. | Offline/posture review before any approved TheIsland/debug activation; no SDK callbacks or gameplay mutation. |
| `sdk.buffs` | `offline-internal-recognizer` | 6 | Focused `PrimalBuff` exact snapshots plus `ue/BuffReflection.*` tests for inventory-access, allow-add, prevent-add, bool-return, and zero-param shapes. This broadens the gameplay API substrate while staying metadata-only. | Keep runtime hooks, callbacks, return overrides, object/class exposure, and gameplay semantics blocked until second-source evidence and SDK policy exist. |
| `sdk.dinos` | `fixture-backed` | 2 | Passenger/carry real snapshots plus broader synthetic coverage for attack, tame-state, and controller dino stats. | Promote more real snapshots only for compact exact targets. |
| `sdk.structures` | `internal-marker-gated-observer` | 6 | Access/demolish plus pincode, container activation, seating, and variant snapshots; `StructureReflection` and disabled-by-default runtime gate require env, SHA, log budget, and `enable-structure-reflection` instance marker. | TheIsland/debug activation still needs explicit operator window and stable-posture rollback; keep placement/build-authoritative targets deferred. |
| `sdk.missions` | `fixture-backed` | 4 | Add, leave-policy, removal lifecycle, and usable-item array metadata snapshots. | Keep array/struct payloads metadata-only until second-source evidence. |
| `sdk.tribes` | `fixture-backed` | 5 | Tribe log control, permission enum-shape, membership bool-return, online-list array, and mission-tag array snapshots; log string remains deferred. | Keep string gates separate; do not decode client payload arrays yet. |
| `sdk.chat` | `runtime-observed-internal` | 0 in manifest | Separate internal chat reflection evidence and runtime hit notes. | TheIsland A/B validation and copied-data ownership before public API. |
| `sdk.transfers` | `fixture-backed` | 7 UFunction + 2 ScriptStruct | Compact transfer/download/upload scalar, object, class, bool-return snapshots, plus dino/player tribute ScriptStruct field fixtures. | Keep `ItemNetInfo`, nested arrays, strings, and runtime dispatch deferred. |
| `sdk.admin` | `documentation-only` | 0 | Admin surfaces identified but intentionally blocked. | Permission model and explicit policy; no runtime work. |
| `ue.reflection` | `internal-substrate` | n/a | FName/GObjects/UObject/UFunction/UProperty plus ScriptStruct inspection tooling underpins all modules. | Second-source evidence and runtime safety gates. |

## Result

The strongest general offline tracks are now `sdk.inventory`, `sdk.structures`,
`sdk.buffs`, `sdk.missions`, `sdk.tribes`, and `sdk.dinos`. `sdk.transfers` also has
fixture-backed evidence, but it remains intentionally risk-gated because transfer payloads
are gameplay-sensitive. None of these are public SDK modules: current snapshots provide
candidate evidence for exact metadata shape, membership checks, and bounded property
chains only.

## Policy Notes

- `StructProperty`, `ClassProperty`, and `NameProperty` in snapshots are metadata evidence,
  not public decoding contracts.
- Valid large chains can still be deferred for policy/runtime reasons.
- Rejected real-core snapshots should not be fabricated; non-`UFunction` rejected hits stay
  in research notes.
- Runtime observation remains gated to TheIsland or an isolated debug instance during an
  approved window.

## Next Priorities

1. Obtain second-source validation for `FName`/`GObjects`/`UObject`/`UFunction` before
   promoting recognizers beyond candidate-only.
2. Review the disabled-by-default `sdk.inventory` observation gate before any TheIsland/debug
   activation.
3. Add second-source validation for ScriptStruct transfer field layouts.
4. Keep `ItemNetInfo`, admin/NetExec, placement/build, and gameplay-authoritative mutation
   out of runtime work.
