# Module Readiness Matrix

## Objective

Summarize the current module readiness state after the first manifest-backed real-core
snapshot rounds, without implying public SDK or runtime readiness.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `763ba2e Preserve struct type metadata in snapshots`
- Live-server impact: none.

## Readiness Snapshot

| Module | Current Level | Real Snapshots | Evidence | Next Gate |
| --- | --- | ---: | --- | --- |
| `sdk.inventory` | `fixture-backed` | 5 | Item/controller exact snapshots plus inventory array filter metadata with inner candidates. | Keep struct/array values metadata-only; defer transform and NetExec. |
| `sdk.buffs` | `fixture-backed` | 6 | Focused `PrimalBuff` exact snapshots for inventory-access, allow-add, prevent-add, bool-return, and zero-param shapes. | Keep gameplay semantics candidate-only; defer mission/grapple/companion surfaces. |
| `sdk.dinos` | `fixture-backed` | 2 | Passenger/carry real snapshots plus broader synthetic coverage for attack, tame-state, and controller dino stats. | Promote more real snapshots only for compact exact targets. |
| `sdk.structures` | `fixture-backed` | 6 | Access/demolish plus pincode, container activation, seating, and variant real snapshots; elevator remains deferred. | Keep placement/build-authoritative targets deferred until policy gates. |
| `sdk.missions` | `fixture-backed` | 4 | Add, leave-policy, removal lifecycle, and usable-item array metadata snapshots. | Keep array/struct payloads metadata-only until second-source evidence. |
| `sdk.tribes` | `fixture-backed` | 5 | Tribe log control, permission enum-shape, membership bool-return, online-list array, and mission-tag array snapshots; log string remains deferred. | Keep string gates separate; do not decode client payload arrays yet. |
| `sdk.chat` | `runtime-observed-internal` | 0 in manifest | Separate internal chat reflection evidence and runtime hit notes. | TheIsland A/B validation and copied-data ownership before public API. |
| `sdk.transfers` | `fixture-backed` | 7 | Compact transfer/download/upload scalar, object, class, and bool-return snapshots; large transfer structs have type candidates only. | Reconstruct `ARKTributeDino`, `ArkTributePlayerData`, and `ItemNetInfo` fields before payload fixtures. |
| `sdk.admin` | `documentation-only` | 0 | Admin surfaces identified but intentionally blocked. | Permission model and explicit policy; no runtime work. |
| `ue.reflection` | `internal-substrate` | n/a | FName/GObjects/UObject/UFunction/UProperty tooling underpins all modules. | Second-source evidence and runtime safety gates. |

## Result

The strongest offline tracks are now `sdk.inventory`, `sdk.structures`, `sdk.buffs`,
`sdk.missions`, `sdk.tribes`, and `sdk.dinos`. They are still not public SDK modules: current
snapshots provide candidate evidence for exact metadata shape, membership checks, and
bounded property chains only.

## Policy Notes

- `StructProperty`, `ClassProperty`, and `NameProperty` in snapshots are metadata evidence,
  not public decoding contracts.
- Valid large chains can still be deferred for policy/runtime reasons.
- Rejected real-core snapshots should not be fabricated; non-`UFunction` rejected hits stay
  in research notes.
- Runtime observation remains gated to TheIsland or an isolated debug instance during an
  approved window.

## Next Priorities

1. Add second-source validation for array inner and compact transfer metadata.
2. Build a struct-field evidence pass for deferred transfer payloads.
3. Keep admin/NetExec and gameplay-authoritative mutations out of runtime work.
