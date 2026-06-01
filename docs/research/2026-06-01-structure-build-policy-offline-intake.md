# Structure Build Policy Offline Intake

## Summary

`APrimalStructure.IsAllowedToBuild` and its Blueprint variants are viable as the next
structure build-policy **offline intake** targets. This is not public SDK evidence and
does not authorize runtime observation, build allow/deny, mutation, enforcement, or return
override.

## Evidence

Read-only checks against the offline workspace:

```text
7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
  /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer
```

The binary is a stripped x86-64 Linux ELF. The second-source reflection inventory contains:

| Target | NumParms | ParmsSize | FunctionFlags |
| --- | ---: | ---: | --- |
| `PrimalStructure.IsAllowedToBuild` | 8 | 152 | `0x4c20400` |
| `PrimalStructure.BPIsAllowedToBuild` | 3 | 104 | `0xc420c00` |
| `PrimalStructure.BPIsAllowedToBuildEx` | 6 | 120 | `0xc420c00` |

Source artifact:
`/servidor/ark/workspace-offline/reflection-inventory-pack-second-source-20260529T000000Z/ufunction-inventory.json`.

No existing sanitized `ufunction-snapshots` were found for these three targets.

## Boundary

The current `structure_census` lane covers aggregate/census-style copied fields only. It
does not include build placement policy, no-collision policy, location/placement structs,
player/controller identity, ownership lookup, mutation, enforcement, or return override.

The next valid step is a candidate-only snapshot/intake pack:

- generate exact sanitized UFunction snapshots for the three targets;
- define a redaction policy for placement structs, location/context, and player/controller
  references before accepting any copied field;
- compare against a distinct source before treating the layout as second-source accepted;
- keep `public_sdk_ready=false`, `runtime_ready=false`, and `promotion_ready=false`.
