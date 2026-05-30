# Item Compact Second-Source Readiness

## Objective

Record the accepted strict second-source layout comparison for `item-compact-intake`.
This note captures offline UFunction layout evidence only. It does not authorize
live-server access, restarts, marker changes, runtime observers, scanners, ptrace,
`gcore`, hook wiring, gameplay mutation, return overrides, commits, or pushes.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Offline workspace:
  `/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z`
- Input binary:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer`
- Input core:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Candidate core artifact SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- Primary fixture artifact SHA256:
  `1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e`
- FName root slot: `0x5956f30`
- GObjects candidate: `0x595b7e0`
- Target set: `item-compact-intake`
- Live-server impact: none. Validation used sanitized snapshots and the approved
  offline workspace.

## Commands

The wrapper plan for the strict full-intake path is:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --pack-dir /servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/pack \
  --snapshot-root /servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/ufunction-snapshots \
  --verified-fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --target-set item-compact-intake \
  --json-plan
```

The persisted acceptance report is reproduced by:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/ufunction-snapshots \
  --target-set item-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

The wrapper validation checks for the persisted artifacts are:

```bash
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
import run_second_source_core_intake as intake
root = Path('/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z')
intake.require_persisted_gobjects_manifest(
    root / 'pack/gobjects-sampling/manifest.json',
    expected_gobjects_candidate='0x595b7e0',
    expected_sample_indices=['0', '1', '25447'],
    expected_fname_root_slot='0x5956f30',
)
intake.require_persisted_readiness_report(
    root / 'pack/snapshot-comparison/readiness-report.json',
    expected_target_sets=['item-compact-intake'],
)
intake.require_distinct_snapshot_artifact_identities(
    Path('tests/fixtures/ufunction_snapshots'),
    root / 'ufunction-snapshots',
    target_set='item-compact-intake',
)
print('wrapper_validation=ok')
PY
```

## Outputs To Preserve

```text
/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/pack/fname-root-validation/core.fname-root-validation.json
sha256=75ef1fc4256fe7ba33f1847fa5dc6d5449169c5f0866b37ae57d4e584096f783

/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/pack/gobjects-sampling/manifest.json
sha256=29d935f77af1d2a3926dfd0bd8eabe95dd75065611dd03c261f9d4d5e7585b40

/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/ufunction-snapshots/7e7ded49e0c6/sdk_items/
PrimalItem.AllowEquipItem.snapshot.json
PrimalItem.CanRepair.snapshot.json
PrimalItem.CraftBlueprint.snapshot.json
PrimalItem.UseItemOntoItem.snapshot.json

/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/pack/snapshot-comparison/readiness-report.json
sha256=ff73ae173f2d631c163090bec5b4d915d5b29b8fbde82df641c3bf9bc07ebf3a
```

No `readiness-report.stderr.txt` is present for this accepted run.

## Result

`readiness-report.json` reports:

```text
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
target_sets=item-compact-intake
promotion_gate.ready=true
promotion_gate.blockers=[]
targets=4 comparable=4 blocked=0
second_source_accepted=4
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
strict_identity_indices=false
```

Accepted targets:

```text
PrimalItem.AllowEquipItem
PrimalItem.CanRepair
PrimalItem.CraftBlueprint
PrimalItem.UseItemOntoItem
```

The candidate snapshots carry distinct second-source artifact identity relative to the
primary fixtures:

```text
artifact_sha256=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78
capture_id=core
evidence_pack_id=gobjects-sampling
artifact_kind=offline_core
```

The FName root validation reports `ready=true`, `requested_count=4`, and
`exact_match_count=4` for `None=0`, `ClientMessage=4884`, `ServerChat=9619`, and
`SetActiveMissionDebugFlags=9622`. The GObjects sampling manifest reports
`evidence_status.status=complete`, `gdb_core_failed=false`, the expected
`gobjects=0x595b7e0`, the expected `verified_fname_root_slot=0x5956f30`, and sample
indices `0`, `1`, and `25447`.

## Boundary

This accepts compact `PrimalItem` UFunction layout evidence only. It does not promote a
public Items SDK, Inventory SDK, item identity, inventory identity, resource handles,
object lookup, raw UE pointers, raw params, mutation, crafting/use authority, return
override, runtime hooks, or public callbacks.

The current candidate-only redacted signature artifact remains separate:
`/servidor/ark/workspace-offline/item-compact-redacted-signatures-20260529T142100Z`.
Older item redacted-signature artifacts from before BoolProperty fixture regeneration are
historical only. Consume-mode artifact-gate acceptance is planning hygiene, not runtime
validation.

## Internal Recognizer Follow-Up

The first internal recognizer slice now exists as `ue/ItemReflection.{h,cpp}` with
`tests/core/ItemReflectionTests.cpp` and the `item_reflection_tests` CMake target. It is
fixture-backed and SHA-gated for the supported ARK binary only.

Recognized targets:

```text
PrimalItem.AllowEquipItem
PrimalItem.CanRepair
PrimalItem.CraftBlueprint
PrimalItem.UseItemOntoItem
```

The recognizer exposes ranges only for copied bool fields. `ToInventory`,
`DestinationItem`, and `AdditionalData` remain metadata-only; null `params` also produces
metadata-only invocations with no exposed ranges. This remains internal planning code:
no hook wiring, dispatcher, SDK/API header, public callback, mutation, return override, raw
UE pointer exposure, item identity, inventory identity, or `ResourceHandle` is promoted.

Lead validation:

```bash
cmake --build build --target item_reflection_tests obelisk -j"$(nproc)"
./build/item_reflection_tests
git diff --check -- CMakeLists.txt ue/ItemReflection.h ue/ItemReflection.cpp tests/core/ItemReflectionTests.cpp docs/agent-handoff/CURRENT.md docs/research/2026-05-29-item-compact-second-source-readiness.md
```
