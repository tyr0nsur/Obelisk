# Reversing Objective Map

## Objective

Define the broad Obelisk reverse-engineering and research objective after the first
non-chat recognizers, so future rounds collect the evidence needed for a stable modding
runtime without drifting back into chat-only work.

## Environment

- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Current repository baseline:
  `4a80d17 Add internal inventory reflection recognizer`
- Primary evidence source:
  existing offline core and committed sanitized fixtures.
- Live-server impact: none.

## P0 Evidence Gaps

| Area | Needed Evidence | Current Gate |
| --- | --- | --- |
| Instance safety | Instance-scoped marker gates for runtime observers. | Do not run env-only observers on shared hosts. |
| Second source | Independent debug core for ScriptStruct and UFunction layout comparison. | Existing packs derive from one core only. |
| Runtime budget | Every observer gate must have explicit budget defaulting to zero. | Structures has this; inventory must copy it. |
| Public SDK readiness | Copied-data ownership and callback lifecycle for each event family. | No new public ABI until proven. |

## P1 Research Tracks

| Track | Next Step | Blocked Items |
| --- | --- | --- |
| `sdk.structures` | Add instance marker gate before debug activation. | Placement/build/snapping mutation. |
| `sdk.inventory` | Add disabled-by-default observation gate after audit. | Item ids, arrays, item contents, NetExec. |
| `sdk.transfers` | Capture or obtain second source for tribute ScriptStruct layouts. | `ItemNetInfo`, upload/download dispatch. |
| `ue.reflection` | Keep strengthening exact identity and property-chain validation. | Treating FName/object indices as cross-build contracts. |

## P2 Broadening Tracks

- `sdk.dinos`: compact passenger/carry recognition after inventory gate discipline is
  proven.
- `sdk.tribes`: read-only membership/permission recognition only; tribe logs and arrays
  stay deferred.
- `sdk.buffs`: useful type-coverage track, but Blueprint-heavy semantics need stricter
  policy notes before runtime observation.
- `sdk.missions`: lifecycle fixtures are useful, but array/struct payloads stay offline.

## Hard Blocks

- Ragnarok is not a reversing target while players test performance.
- No native exec probes.
- No broad `ProcessEvent` tracing on live instances.
- No public callbacks for raw `UObject*`, `FString`, `TArray`, `StructProperty`, or
  transfer payloads.
- No admin, NetExec, upload/download, placement/build, or gameplay mutation APIs from
  candidate-only evidence.

## Result

The active objective is to turn reverse-engineering into reproducible, reviewable assets:
fixtures, recognizers, analyzer tests, runbooks, and skill updates. Runtime observation is
allowed only after the corresponding offline recognizer, budget, marker, rollback, and
privacy gates exist.
