# Structure Build Policy Offline Intake

## Summary

`PrimalStructure.IsAllowedToBuild` and its Blueprint variants are viable as a
candidate-only structure build-policy **offline intake** target set. This is not public
SDK evidence and does not authorize runtime observation, build allow/deny, mutation,
enforcement, or return override.

The implemented target set is `structure-build-policy-offline-intake`:

- `obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild`
- `obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild`
- `obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx`

It is classified `planning_only`, assigned to the `structures` lane, and excluded from
`RELEASE_READINESS_TARGET_SETS`.

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

No existing sanitized `ufunction-snapshots` were found for these three targets. The
target set therefore records intake scope only; it is not an accepted layout claim.

## Boundary

The current `structure_census` and `structure-observer-intake` lanes remain unchanged.
They do not include build placement policy, no-collision policy, location/placement
structs, player/controller identity, ownership lookup, mutation, enforcement, or return
override.

The next valid step is a candidate-only snapshot/intake pack through
`structure-build-policy-offline-intake`:

- generate exact sanitized UFunction snapshots for the three targets;
- define a redaction policy for placement structs, location/context, and player/controller
  references before accepting any copied field;
- compare against a distinct source before treating the layout as second-source accepted;
- keep `public_sdk_ready=false`, `runtime_ready=false`, and `promotion_ready=false`;
- keep the set out of release-readiness, public SDK, runtime hook, mutation, enforcement,
  and return-override paths.

## Fast Offline Snapshot Path

The two existing offline inventory packs already plan all three targets with
`planned_command_count=3` and `blocked_count=0`; do not rebuild broad inventories first.
Use the reviewed copied cores and compare the resulting roots in planning-layout mode:

```bash
python3 scripts/plan_ufunction_focal_snapshots.py \
  --inventory-pack /servidor/ark/workspace-offline/reflection-inventory-pack-second-source-20260529T000000Z \
  --target-set structure-build-policy-offline-intake \
  --evidence-obelisk-commit <commit> > <root>/base-plan.json

python3 scripts/plan_ufunction_focal_snapshots.py \
  --inventory-pack /servidor/ark/workspace-offline/reflection-inventory-pack-20260529T091700Z-minimal \
  --target-set structure-build-policy-offline-intake \
  --evidence-obelisk-commit <commit> > <root>/candidate-plan.json

python3 scripts/compare_reflection_snapshots.py \
  --base-root <root>/base \
  --candidate-root <root>/candidate \
  --readiness-report \
  --target-set structure-build-policy-offline-intake \
  --planning-layout-intake \
  --json > <root>/readiness.json
```

Expected success remains planning-only: `targets=3`, `comparable=3`,
`second_source_accepted=3`, `planning_layout_gate.ready=true`, while
`promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`.

## 2026-06-01 Fast Offline Snapshot Execution

Artifact root:
`/home/flowcommunity-ark/obelisk-artifacts/structure-build-policy-offline-intake-20260601T064502Z`.

The fast path was executed against the two existing offline inventory packs above at
Obelisk commit `981dcf2fff9d9b5a274609c13210fa2df8efa08a`. Both focal plans reported
`planned_command_count=3` and `blocked_count=0`; all three exact targets were present
once in each inventory pack.

Generated snapshots:

- `base/PrimalStructure.IsAllowedToBuild.snapshot.json`
- `base/PrimalStructure.BPIsAllowedToBuild.snapshot.json`
- `base/PrimalStructure.BPIsAllowedToBuildEx.snapshot.json`
- `candidate/PrimalStructure.IsAllowedToBuild.snapshot.json`
- `candidate/PrimalStructure.BPIsAllowedToBuild.snapshot.json`
- `candidate/PrimalStructure.BPIsAllowedToBuildEx.snapshot.json`

Readiness report:
`/home/flowcommunity-ark/obelisk-artifacts/structure-build-policy-offline-intake-20260601T064502Z/readiness.json`.

Planning-only readiness result:

```text
targets=3
comparable=3
blocked=0
second_source_accepted=3
second_source_rejected=0
second_source_inconclusive=0
second_source_missing=0
planning_layout_gate.ready=true
planning_layout_gate.ready_scope=planning_only
planning_layout_gate.promotion_ready=false
planning_layout_gate.public_sdk_ready=false
planning_layout_gate.runtime_ready=false
promotion_gate.ready=false
promotion_gate.blockers=planning_layout_intake_not_promotion_gate:1
```

This accepts `structure-build-policy-offline-intake` only as planning-layout evidence.
It does not promote runtime observation, public SDK surface, StructureEvents, mutation,
enforcement, return override, object identity, lookup, raw params, or `ResourceHandle`
lifetime.

## 2026-06-01 HEAD Audit

Rechecked at local HEAD `a1ad030` without server access, restarts, ptrace/gcore,
ReflectionScanner, commits, pushes, tags, Discord, or runtime observation.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root /home/flowcommunity-ark/obelisk-artifacts/structure-build-policy-offline-intake-20260601T064502Z/base \
  --candidate-root /home/flowcommunity-ark/obelisk-artifacts/structure-build-policy-offline-intake-20260601T064502Z/candidate \
  --readiness-report \
  --target-set structure-build-policy-offline-intake \
  --planning-layout-intake \
  --json
```

Observed result:

```text
readiness_sha256=d9742e5ea97dbd1d6f12e40154c5891c72184126e90a29a2c57b43a507a38072
targets=3
comparable=3
blocked=0
second_source_accepted=3
second_source_rejected=0
second_source_inconclusive=0
second_source_missing=0
planning_layout_gate.ready=true
planning_layout_gate.ready_scope=planning_only
planning_layout_gate.promotion_ready=false
planning_layout_gate.public_sdk_ready=false
planning_layout_gate.runtime_ready=false
promotion_gate.ready=false
promotion_gate.blockers=planning_layout_intake_not_promotion_gate:1
```

This is the small offline blocker reduction available now: the three build-policy
targets have accepted sanitized second-source layout accounting in planning-layout mode.
The remaining blocker is no longer "missing exact snapshots"; it is unresolved promotion
policy: redaction for placement/location/player context, copied payload design,
identity/ownership/privacy semantics, no-read/no-budget runtime guard tests, live-ops
approval for any observation, SDK consumer ABI design, and a separate decision on whether
build denial/enforcement or return override can ever be exposed. Until those are resolved,
`structure-build-policy-offline-intake` must stay out of release readiness, public SDK,
runtime hook, enforcement, mutation, and return-override paths.

## 2026-06-01 Offline Fixture Guardrail

`scripts/check_structure_build_policy_offline_intake.py` now treats the referenced
snapshot paths in the readiness report as part of the offline fixture contract. It freezes
the three accepted targets, their `NumParms`/`ParmsSize`, property order, reflected
property class, offset, element size, struct type where present, and candidate-only
membership status.

The checker also reports the redaction posture for every observed field. `PC`,
`AtLocation`, `AtRotation`, `OutPlacementData`, and `PlayerViewRotation` remain redacted
context/placement fields; scalar bools and `CurrentAllowedReason` remain layout-only; and
`ReturnValue` remains a layout-only return candidate with no override authority. Any
truthy claim of public payload exposure, runtime, enforcement, or return override fails
closed.
