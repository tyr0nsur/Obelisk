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
  `76cbc7a Validate enum candidates in snapshots`
- Live-server impact: none.

## Readiness Snapshot

| Module | Current Level | Real Snapshots | Evidence | Next Gate |
| --- | --- | ---: | --- | --- |
| `sdk.inventory` | `fixture-backed` | 4 | Item/controller exact snapshots, including object/bool/int and small `StructProperty` shapes. | Keep struct values metadata-only; defer transform and NetExec. |
| `sdk.buffs` | `fixture-backed` | 6 | Focused `PrimalBuff` exact snapshots for inventory-access, allow-add, prevent-add, bool-return, and zero-param shapes. | Keep gameplay semantics candidate-only; defer mission/grapple/companion surfaces. |
| `sdk.dinos` | `fixture-backed` | 2 | Passenger/carry real snapshots plus broader synthetic coverage for attack, tame-state, and controller dino stats. | Promote more real snapshots only for compact exact targets. |
| `sdk.structures` | `fixture-backed` | 6 | Access/demolish plus pincode, container activation, seating, and variant real snapshots; elevator remains deferred. | Keep placement/build-authoritative targets deferred until policy gates. |
| `sdk.missions` | `fixture-backed` | 3 | Add, leave-policy, and removal lifecycle real snapshots; mission tag array payload remains deferred. | Preserve array inner metadata before mission tag fixtures. |
| `sdk.tribes` | `fixture-backed` | 3 | Tribe log control plus permission enum-shape and membership bool-return snapshots; online-list array and log string remain deferred. | Preserve array inner metadata before online-list fixtures; keep string gates separate. |
| `sdk.chat` | `runtime-observed-internal` | 0 in manifest | Separate internal chat reflection evidence and runtime hit notes. | TheIsland A/B validation and copied-data ownership before public API. |
| `sdk.transfer` | `candidate` | 0 | Valid metadata chain exists for `ServerRequestDownloadDino`, but struct payload is large. | Deep struct decoding and policy gates. |
| `sdk.admin` | `documentation-only` | 0 | Admin surfaces identified but intentionally blocked. | Permission model and explicit policy; no runtime work. |
| `ue.reflection` | `internal-substrate` | n/a | FName/GObjects/UObject/UFunction/UProperty tooling underpins all modules. | Second-source evidence and runtime safety gates. |

## Result

The strongest offline tracks are now `sdk.inventory`, `sdk.structures`, `sdk.buffs`,
`sdk.missions`, `sdk.tribes`, and `sdk.dinos`. They are still not public SDK modules: current
snapshots prove exact metadata shape, membership checks, and bounded property chains only.

## Policy Notes

- `StructProperty`, `ClassProperty`, and `NameProperty` in snapshots are metadata evidence,
  not public decoding contracts.
- Valid large chains can still be deferred for policy/runtime reasons.
- Rejected real-core snapshots should not be fabricated; non-`UFunction` rejected hits stay
  in research notes.
- Runtime observation remains gated to TheIsland or an isolated debug instance during an
  approved window.

## Next Priorities

1. Extend snapshot output with sanitized array inner metadata before array payload fixtures.
2. Consider a focused transfer struct evidence pass without runtime dispatch.
3. Keep admin/NetExec and gameplay-authoritative mutations out of runtime work.
