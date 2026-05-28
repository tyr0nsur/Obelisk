# Reversing Objective Map

## Objective

Define the broad Obelisk reverse-engineering and research objective after the first
gameplay recognizers, so future rounds collect the evidence needed for a stable modding
runtime and a general ARK Linux API/SDK core.

## Environment

- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Current repository baseline:
  `1b33a2e Harden runtime observer log analysis`
- Primary evidence source:
  existing offline core and committed sanitized fixtures.
- Live-server impact: none.

## P0 Evidence Gaps

| Area | Needed Evidence | Current Gate |
| --- | --- | --- |
| Instance safety | Instance-scoped marker gates for runtime observers. | Chat, inventory, and structures now require env, binary SHA, explicit budget, and per-instance markers before runtime observation. |
| Second source | Independent debug core or static path for `FName`/`GObjects`/`UObject`/`UFunction` layout comparison. | Existing packs derive from one core only; operational checklist is in `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`. |
| Runtime budget | Every observer gate must have explicit budget defaulting to zero. | Chat, inventory, and structures all follow bounded observer discipline; copied/sanitized logs can be summarized offline without touching live instances. |
| Public SDK readiness | Copied-data ownership and callback lifecycle for each event family. | No new public ABI until proven. |

## P1 Research Tracks

| Track | Next Step | Blocked Items |
| --- | --- | --- |
| `sdk.structures` | Add wrapper/posture tests and keep runtime observation blocked until an approved `arkserver2` / TheIsland window or a dedicated isolated debug instance exists; keep `arkserver` / Ragnarok untouched while users are active. | Placement/build/snapping mutation. |
| `sdk.inventory` | Keep the internal marker-gated observer metadata-only and use copied-log summaries plus second-source layouts before any public SDK surface. | Item ids, arrays, item contents, NetExec. |
| `sdk.buffs` | Maintain the offline internal recognizer and use it to harden exact reflected metadata validation. | Runtime hooks, callbacks, return override, object/class pointer exposure, gameplay mutation. |
| `sdk.transfers` | Capture or obtain second source for tribute ScriptStruct layouts. | `ItemNetInfo`, upload/download dispatch. |
| `ue.reflection` | Keep strengthening exact identity and property-chain validation through the second-source matrix. | Treating FName/object indices as cross-build contracts. |

## P2 Broadening Tracks

- `sdk.dinos`: compact passenger/carry recognition after inventory gate discipline is
  proven.
- `sdk.tribes`: read-only membership/permission recognition only; tribe logs and arrays
  stay deferred.
- `sdk.buffs`: active offline broadening track; the first metadata recognizer exists, but
  Blueprint-heavy semantics and runtime observation remain blocked.
- `sdk.missions`: lifecycle fixtures are useful, but array/struct payloads stay offline.

## Hard Blocks

- Do not run Obelisk tests on `arkserver` / Ragnarok while users are active.
- `arkserver2` / TheIsland starts powered off; use it only for an explicit approved
  scoped test and shut it down afterward.
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
privacy gates exist. For gameplay-authoritative functions, observers must not override
returns, mutate params, call original manually, or dispatch public plugin callbacks until
copied-data ownership and authority policy are proven.

`scripts/analyze_runtime_observer_log.py` is a summary tool for copied or sanitized
observer logs. Its `obelisk.runtime-observer-log-summary.v1` JSON has
`review_scope=runtime_observer_evidence_summary`, `readiness_gate=none`, and
`promotion_gate.gate_type=runtime_observer_observational_only`. It is useful for comparing
chat, inventory, structure, and future observer families, and `--fail-on-quality-blockers`
can reject copied captures that are empty, missing gates, mix binary SHA values, contain
malformed observer lines, or require redaction. It is still not a promotion evidence pack
by itself and must not be used as a reason to read or tail live Ragnarok logs.
