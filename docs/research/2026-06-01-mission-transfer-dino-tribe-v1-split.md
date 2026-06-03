# Mission Transfer Dino Tribe v1 Split

Date: 2026-06-01

## Scope

This note decomposes the umbrella demand label
`obelisk.mission_transfer_dino_tribe.v1` into five leaf decision units:
`mission`, `transfer`, `dino_policy`, `tribe_policy`, and `buff_status`.

This is docs-only blocker documentation. It does not promote a public SDK, ABI,
runtime observer, callback family, capability bit, mutation path, return override,
identity/lookup contract, or v1 completion claim.

ArkApi, AseApi, and NextGenPlugins names are demand/dictionary input only for this
split. Do not copy implementation, offsets, layouts, constants, schemas, control
flow, parsers, or semantics from those sources into Obelisk.

This split is migration vocabulary only. Obelisk does not claim ArkApi source,
ABI, command, config, or direct plugin portability for any similarly named leaf.
Each future surface must be independently designed through Obelisk-owned Linux
reflection evidence, copied-data ownership, lifecycle policy, ABI review, and
promotion gates.

## Leaf Decisions

| Leaf | Current evidence/checker status | Current blocker | Candidate-only non-counting outcome | Explicit non-claims |
| --- | --- | --- | --- | --- |
| `mission` | `mission-compact-intake` has accepted internal layout evidence. `scripts/check_mission_copied_bool_readiness.py --json` reports `ready=true`, consume accepted, promote blocked, `accepted_for_internal_planning=true`, `public_sdk_ready=false`, and `runtime_ready=false` for the copied-bool policy slice. | Runtime observer, dispatcher lifecycle, public ABI/API, identity, arrays, mutation, return override, and live-ops validation remain unresolved. | Keep a consume-only internal copied-bool planning slice for exact Mission metadata; preserve recognition-only redaction for object/container fields. | No public Mission SDK, no mission identity, no player/controller/character identity, no item-array payload, no runtime hook approval, no mutation, no return override, no `ResourceHandle`, no v1 completion. |
| `transfer` | `transfer-baccept-only-policy-slice` has a focused readiness checker. `scripts/check_transfer_baccept_readiness.py --json` reports `ready=true`, consume accepted, promote blocked, `accepted_for_internal_planning=true`, and explicit false flags for public SDK/ABI/runtime/identity/ownership/payload contracts. | Transfer payload ownership, downloaded-character and dino payload contracts, player identity, cross-map state, ownership, mutation, return override, runtime wiring, and public ABI remain unresolved. | Keep only the `bAccept` copied-bool slice as candidate internal planning evidence. | No public Transfer SDK, no transfer payload decoding, no downloaded-character contract, no dino payload contract, no player identity, no cross-map state contract, no ownership, no runtime hook wiring, no mutation, no return override, no `ResourceHandle`, no v1 completion. |
| `dino_policy` | `dino-compact-intake` has accepted internal layout evidence. `scripts/check_dino_scalar_readiness.py --json` reports `ready=true`, `precall_scalar_ready=true`, `scalar_only_ready=true`, `postcall_return_ready=false`, `public_dino_sdk_ready=false`, and `runtime_ready=false`. | Dino/player/passenger identity, object lifetime, lookup, ownership, post-call returns, dispatcher lifecycle, runtime observation, public ABI, mutation, return override, and `ResourceHandle` remain unresolved. | Keep pre-call scalar-only internal planning for the compact passenger/carry policy pair; defer return values and redact object refs. | No public Dino SDK, no public C ABI, no dino/player/passenger identity, no lookup, no ownership, no runtime observer, no UE function call, no mutation, no return override, no `ResourceHandle`, no production/v1 completion claim. |
| `tribe_policy` | `tribe-compact-intake` has accepted internal layout evidence in the existing second-source notes. `scripts/check_tribe_scalar_boundary_readiness.py --json` reports `ready=true`, `accepted_for_internal_planning=true`, `tribe_scalar_boundary_ready=true`, and false public SDK/ABI/runtime/identity/lookup/mutation/return-override/ResourceHandle/v1 flags for the scalar/control boundary. | Tribe/player identity, permission semantics, log/string/array ownership, online-list and mission-tag payload policy, dispatcher lifecycle, runtime observation, public ABI, mutation, and return override remain unresolved. | Keep as internal scalar/control evidence only; keep array/string payload, identity, lookup, permission enforcement, runtime, ABI, mutation, and return-override work separately blocked before public discussion. | No public Tribe SDK, no tribe identity, no player identity, no membership contract, no log payload, no online-list payload, no mission-tag payload, no permission enforcement API, no runtime observer, no mutation, no return override, no `ResourceHandle`, no v1 completion. |
| `buff_status` | `buff-compact-intake` and `buff-breadth-intake` have internal layout evidence in existing notes. The later bool-tail repair note records compact `3/3` layout acceptance, and committed fixtures summarize six Buff candidate bool/redaction shapes; there is still no standalone Buff leaf readiness/accounting checker in `scripts/`. | Buff gameplay semantics, object/class redaction policy, copied payload policy, a Buff-specific consume/readiness checker, dispatcher lifecycle, runtime observation, public ABI, mutation, return override, and `ResourceHandle` remain unresolved. | Keep compact and breadth Buff target sets as internal layout evidence only; add a leaf-specific checker before any scalar/status readiness claim, then define copied scalar/status payloads and redaction tests. | No public Buff SDK, no buff identity, no controller/character/damage-causer/class exposure, no object/class pointer contract, no runtime hook approval, no mutation, no return override, no raw params, no `ResourceHandle`, no v1 completion. |

## Decision

`obelisk.mission_transfer_dino_tribe.v1` should not be treated as one public
module, one SDK milestone, or one release gate. The safe decomposition is five
independent leaf decisions, each blocked until its own copied-data ownership,
redaction, lifecycle, runtime, ABI, and public documentation gates are satisfied.

For v1, the allowed outcome is documentation and consume-only/internal planning
evidence. Public SDK promotion remains blocked for all five leaves.
These side-lane outcomes are non-counting: a leaf becomes v1-accounted only by
explicit release exclusion or by a future promoted-evidence gate that is outside
this candidate-only note.

## Mission Leaf Accounting Boundary

The `mission` leaf is the selected narrow accounting lane for the next internal
hardening pass. Its current useful surface is only
`mission-copied-bool-policy-slice`: consume-mode planning evidence with
promote-mode blocked. This lane is narrower than `mission-compact-intake` and
must stay candidate/accounting-only.

Copied target accounting is limited to these three reflected targets:

- `MissionType.AddPlayerToMission`
- `MissionType.BPAllowPlayerToLeaveMission`
- `MissionType.BPOnPlayerRemovedFromMission`

Copied bool field accounting is limited to these five one-byte bool fields:

- `MissionType.AddPlayerToMission.bForceAdd`
- `MissionType.AddPlayerToMission.ReturnValue`
- `MissionType.BPAllowPlayerToLeaveMission.ReturnValue`
- `MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent`
- `MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess`

Recognition-only redaction accounting is limited to these fields. Their pointer,
object, array, identity, and payload values are not copied, logged, or promoted:

- `MissionType.AddPlayerToMission.PlayerCharacter`
- `MissionType.BPAllowPlayerToLeaveMission.PlayerPawn`
- `MissionType.BPOnPlayerRemovedFromMission.Player`
- `MissionType.BPOnPlayerRemovedFromMission.Controller`
- `MissionType.GetPlayerUsableItems.Character`
- `MissionType.GetPlayerUsableItems.OutItemIDs`

`MissionType.GetPlayerUsableItems` remains a recognition-only target for this
lane. It is not part of the copied bool target set and does not authorize item
array exposure, item identity, mission identity, lookup, runtime hook wiring,
mutation, return override, `ResourceHandle`, or public Mission SDK promotion.

## Validation

Local/offline commands used for this note:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_mission_copied_bool_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_transfer_baccept_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_dino_scalar_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_tribe_scalar_boundary_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py --list-target-sets
PYTHONDONTWRITEBYTECODE=1 python3 scripts/summarize_reflection_scalar_candidates.py --target-set buff-compact-intake --target-set buff-breadth-intake --json
```

The original split pass was docs-only. The 2026-06-01 mission leaf accounting
hardening pass edited only the accounting checker, its corresponding test, and
this note. No servers, live logs, debuggers, Discord, Git commands, runtime
probes, manifest edits, ABI/runtime code edits, or `/servidor/ark` writes were
used.

The later Mission copied-bool readiness/accounting hardening pass kept the same
offline-only boundary while making the reports explicitly `consume_only` and
`internal_reusable_evidence_only`, with public Mission SDK, ABI, runtime
observer, identity, lookup, mutation, return override, and v1 completion flags
remaining false.

The 2026-06-03 tribe scalar boundary pass added the leaf-specific offline checker
referenced above. That checker is candidate-only accounting for three accepted scalar and
control fields plus required redactions; it is not artifact-gate promotion, public Tribe
SDK evidence, runtime observation, identity/lookup evidence, mutation authority, return
override support, `ResourceHandle` evidence, or v1 completion.

The 2026-06-03 stale-evidence audit updated the Buff row to stop treating compact
bool-tail repair as still missing. Buff remains candidate-only because the current tree
has fixture and scalar-summary evidence, not a dedicated Buff leaf consume/readiness
checker or any public/runtime/identity/mutation/return-override promotion.
