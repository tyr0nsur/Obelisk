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

| Leaf | Current evidence/checker status | Current blocker | Allowed v1 outcome | Explicit non-claims |
| --- | --- | --- | --- | --- |
| `mission` | `mission-compact-intake` has accepted internal layout evidence. `scripts/check_mission_copied_bool_readiness.py --json` reports `ready=true`, consume accepted, promote blocked, `accepted_for_internal_planning=true`, `public_sdk_ready=false`, and `runtime_ready=false` for the copied-bool policy slice. | Runtime observer, dispatcher lifecycle, public ABI/API, identity, arrays, mutation, return override, and live-ops validation remain unresolved. | Keep a consume-only internal copied-bool planning slice for exact Mission metadata; preserve recognition-only redaction for object/container fields. | No public Mission SDK, no mission identity, no player/controller/character identity, no item-array payload, no runtime hook approval, no mutation, no return override, no `ResourceHandle`, no v1 completion. |
| `transfer` | `transfer-baccept-only-policy-slice` has a focused readiness checker. `scripts/check_transfer_baccept_readiness.py --json` reports `ready=true`, consume accepted, promote blocked, `accepted_for_internal_planning=true`, and explicit false flags for public SDK/ABI/runtime/identity/ownership/payload contracts. | Transfer payload ownership, downloaded-character and dino payload contracts, player identity, cross-map state, ownership, mutation, return override, runtime wiring, and public ABI remain unresolved. | Keep only the `bAccept` copied-bool slice as candidate internal planning evidence. | No public Transfer SDK, no transfer payload decoding, no downloaded-character contract, no dino payload contract, no player identity, no cross-map state contract, no ownership, no runtime hook wiring, no mutation, no return override, no `ResourceHandle`, no v1 completion. |
| `dino_policy` | `dino-compact-intake` has accepted internal layout evidence. `scripts/check_dino_scalar_readiness.py --json` reports `ready=true`, `precall_scalar_ready=true`, `scalar_only_ready=true`, `postcall_return_ready=false`, `public_dino_sdk_ready=false`, and `runtime_ready=false`. | Dino/player/passenger identity, object lifetime, lookup, ownership, post-call returns, dispatcher lifecycle, runtime observation, public ABI, mutation, return override, and `ResourceHandle` remain unresolved. | Keep pre-call scalar-only internal planning for the compact passenger/carry policy pair; defer return values and redact object refs. | No public Dino SDK, no public C ABI, no dino/player/passenger identity, no lookup, no ownership, no runtime observer, no UE function call, no mutation, no return override, no `ResourceHandle`, no production/v1 completion claim. |
| `tribe_policy` | `tribe-compact-intake` has accepted internal layout evidence in the existing second-source notes. `compare_reflection_snapshots.py --list-target-sets` classifies it as `internal_layout_only` with `release_readiness=false`, `promotion_ready=false`, and `public_sdk_ready=false`. No leaf-specific tribe readiness checker was found in `scripts/`. | Tribe/player identity, permission semantics, log/string/array ownership, online-list and mission-tag payload policy, dispatcher lifecycle, runtime observation, public ABI, mutation, and return override remain unresolved. | Keep as internal layout evidence only; split any future work into a scalar permission/log-request planning slice and a separately blocked array/string payload slice before public discussion. | No public Tribe SDK, no tribe identity, no player identity, no membership contract, no log payload, no online-list payload, no mission-tag payload, no permission enforcement API, no runtime observer, no mutation, no return override, no v1 completion. |
| `buff_status` | `buff-compact-intake` and `buff-breadth-intake` have internal layout evidence in existing notes, but current scalar readiness is not green across both target sets: breadth is accepted while the fresh compact path is incomplete because two compact candidates lack current `BoolProperty` tail metadata. No leaf-specific buff readiness checker was found in `scripts/`. | Buff gameplay semantics, object/class redaction policy, copied payload policy, refreshed compact evidence, dispatcher lifecycle, runtime observation, public ABI, mutation, return override, and `ResourceHandle` remain unresolved. | Keep compact and breadth Buff target sets as internal layout evidence only; repair/regenerate compact evidence before any scalar-readiness claim, then define copied scalar/status payloads and redaction tests. | No public Buff SDK, no buff identity, no controller/character/damage-causer/class exposure, no object/class pointer contract, no runtime hook approval, no mutation, no return override, no raw params, no `ResourceHandle`, no v1 completion. |

## Decision

`obelisk.mission_transfer_dino_tribe.v1` should not be treated as one public
module, one SDK milestone, or one release gate. The safe decomposition is five
independent leaf decisions, each blocked until its own copied-data ownership,
redaction, lifecycle, runtime, ABI, and public documentation gates are satisfied.

For v1, the allowed outcome is documentation and consume-only/internal planning
evidence. Public SDK promotion remains blocked for all five leaves.

## Validation

Local/offline commands used for this note:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_mission_copied_bool_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_transfer_baccept_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_dino_scalar_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py --list-target-sets
```

No servers, live logs, debuggers, Discord, Git commands, manifest/test/script
edits, or `/servidor/ark` writes were used for this docs-only split.
