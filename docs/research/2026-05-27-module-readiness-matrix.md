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
  `29c5851 Require Function snapshot targets`
- Live-server impact: none.

## Readiness Snapshot

| Module | Current Level | Real Snapshots | Evidence | Next Gate |
| --- | --- | ---: | --- | --- |
| `sdk.inventory` | `fixture-backed` | 4 | Item/controller exact snapshots, including object/bool/int and small `StructProperty` shapes. | Keep struct values metadata-only; defer transform and NetExec. |
| `sdk.buffs` | `fixture-backed` | 6 | Focused `PrimalBuff` exact snapshots for inventory-access, allow-add, prevent-add, bool-return, and zero-param shapes. | Keep gameplay semantics candidate-only; defer mission/grapple/companion surfaces. |
| `sdk.dinos` | `fixture-backed` | 2 | Passenger/carry real snapshots plus broader synthetic coverage for attack, tame-state, and controller dino stats. | Promote more real snapshots only for compact exact targets. |
| `sdk.structures` | `fixture-backed` | 2 | Access/demolish real snapshots plus synthetic coverage for variant, pincode, seating, and elevator. | Consider pincode or seating real snapshots before placement/build. |
| `sdk.missions` | `fixture-backed` | 1 | `AddPlayerToMission` real snapshot plus synthetic mission add/leave/notify fixtures. | Promote leave/notify snapshots; keep string/array candidates deferred. |
| `sdk.tribes` | `fixture-backed-control` | 1 | `ServerRequestTribeLog` zero-param control snapshot. | Focused tribe inventory before more snapshots. |
| `sdk.chat` | `runtime-observed-internal` | 0 in manifest | Separate internal chat reflection evidence and runtime hit notes. | TheIsland A/B validation and copied-data ownership before public API. |
| `sdk.transfer` | `candidate` | 0 | Valid metadata chain exists for `ServerRequestDownloadDino`, but struct payload is large. | Deep struct decoding and policy gates. |
| `sdk.admin` | `documentation-only` | 0 | Admin surfaces identified but intentionally blocked. | Permission model and explicit policy; no runtime work. |
| `ue.reflection` | `internal-substrate` | n/a | FName/GObjects/UObject/UFunction/UProperty tooling underpins all modules. | Second-source evidence and runtime safety gates. |

## Result

The strongest offline tracks are now `sdk.inventory`, `sdk.buffs`, `sdk.dinos`,
`sdk.structures`, and `sdk.missions`. They are still not public SDK modules: current
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

1. Add real snapshots for structure pincode/seating or mission leave/notify.
2. Add focused tribe inventory before expanding `sdk.tribes`.
3. Keep transfer/admin/NetExec out of runtime work.
