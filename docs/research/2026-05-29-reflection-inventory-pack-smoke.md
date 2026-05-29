# Reflection Inventory Pack Smoke

## Objective

Validate a reusable offline pack builder that combines FName root validation and redacted
UFunction inventory without promoting UE4 internals as public API.

## Environment

- Obelisk commit: smoke run after `9fa65d0`; builder and note committed in `1094214`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Second-source core SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- Evidence-pack manifest:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json`
- Output pack:
  `/servidor/ark/workspace-offline/reflection-inventory-pack-smoke-20260529T000000Z`
- Second-source output pack:
  `/servidor/ark/workspace-offline/reflection-inventory-pack-second-source-20260529T000000Z`
- Server impact: none. This used copied offline artifacts under `workspace-offline`.

## Command

```bash
python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json \
  --target-set minimal-second-source-intake \
  --target-set mission-compact-intake \
  --fname-index None=0 \
  --fname-index ClientMessage=4884 \
  --fname-index ServerChat=9619 \
  --fname-index SetActiveMissionDebugFlags=9622 \
  --include-functions \
  --output-dir /servidor/ark/workspace-offline/reflection-inventory-pack-smoke-20260529T000000Z
```

## Result

The generated manifest used schema `obelisk.reflection-inventory-pack.v1`, status
`candidate-only`, and `promotion_status=not_promoted_candidate_only`.

Summary:

- `fname_root_ready=true`
- `function_count=5269`
- `target_requested_count=8`
- `target_matched_count=8`
- `target_missing_count=0`
- `blockers=[]`

The emitted `ufunction-inventory.json` function rows are redacted to these keys only:
`family`, `function_flags`, `name`, `num_parms`, `outer_class_name`, `outer_name`, and
`parms_size`.

The pack manifest still records binary-scoped offline reproducibility addresses such as
`gobjects`, `fname_root_slot`, and `fname_table`. Those fields are for reproducing offline
research against the same binary/core artifacts. They are not public SDK data, not
publishable module metadata, and not promotion evidence for runtime-stable globals.

## Second-Source Inventory Check

Generated an equivalent candidate-only pack from the distinct second-source core with
explicit artifact identity:

```bash
python3 scripts/build_reflection_inventory_pack.py \
  --core /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core \
  --binary /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --artifact-kind offline_core \
  --capture-id second-source-arkserver2-TheIsland-20260529T011227Z \
  --evidence-pack-id direct-second-source-reflection-pack \
  --target-set minimal-second-source-intake \
  --target-set mission-compact-intake \
  --fname-index None=0 \
  --fname-index ClientMessage=4884 \
  --fname-index ServerChat=9619 \
  --fname-index SetActiveMissionDebugFlags=9622 \
  --include-functions \
  --output-dir /servidor/ark/workspace-offline/reflection-inventory-pack-second-source-20260529T000000Z
```

The second pack also reported `fname_root_ready=true`, `function_count=5269`,
`target_matched_count=8`, `target_missing_count=0`, and `blockers=[]`. A quick local key
comparison found `0` missing `(outer_name, name)` pairs in either direction, and the eight
requested target rows matched on flags, parameter count, and parameter size. This remains a
candidate-only inventory check, not a replacement for strict snapshot readiness reports.

## Non-Claims

This pack does not promote `GObjects`/`GUObjectArray` as runtime-stable, expose `UObject`
pointers, raw params, object identity, mutation, or return overrides, prove
`ResourceHandle` lifetime/serial reuse semantics, or claim portability across ARK binary
hashes.

## Next Steps

- Use this pack shape to speed target-set review and roadmap planning.
- Keep module promotion tied to strict second-source readiness reports, not global
  inventory presence.
- Keep inventory as the fastest internal copied-scalar path because it already has a
  minimal bridge and accepted compact evidence; use mission as the next cleaner new module
  candidate after the core RC boundary remains stable.
