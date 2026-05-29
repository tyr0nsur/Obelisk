---
name: obelisk-reversing-research
description: "Use when researching ARK/UE4 internals for Obelisk: FName/GNames/GObjects, UFunction/ScriptStruct discovery, ProcessEvent fname_index mapping, ReflectionScanner analysis, module recognizers, and safe debug-server experiments."
---

# Obelisk Reversing Research

Use this skill for UE4/ARK research, offline reversing, and explicitly approved debug
experiments. Keep runtime-core edits out of scope unless the research proves a required
ABI or hook change.

## Scope

Own these areas:

- `ue/ReflectionScanner.*`
- `ue/Memory.*`
- `ue/Reflection.h`
- docs describing offsets, signatures, and experiments

## Known Findings

- Current `UObject::ProcessEvent` candidate: runtime address `0x1d34e20` on the tested
  non-PIE binary where the ELF image base is `0x400000`. Treat this as build-specific
  evidence, not a universal formula.
- Previous candidate `0x1d11cb0` was a false positive and did not receive gameplay events.
- Vtable-derived ProcessEvent slot observed around slot 61.
- Confirmed core FName clues for the current ARK binary hash:
  - `4884 -> ClientMessage`
  - `9619 -> ServerChat`
  - `9622 -> SetActiveMissionDebugFlags`
- Older notes that used `9619 -> ClientMessage` and `9622 -> ServerChat` are obsolete
  historical evidence.
- Clean vanilla `arkserver2` / TheIsland core
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
  confirmed FName root slot `0x5956f30 -> 0x5a94660` for the current ARK binary hash and
  exact clues `None=0`, `ClientMessage=4884`, `ServerChat=9619`, and
  `SetActiveMissionDebugFlags=9622`.
- Core evidence promotes `0x595b7e0` to `GUObjectArray research-candidate`; first object
  resolves to `/Script/CoreUObject` and class resolves to `Package`.
- The same clean vanilla core sampled `0x595b7e0` at indices `0`, `1`, and `25447`; all
  sampled objects round-tripped by `InternalIndex`, and index `25447` resolved to
  `ServerChat` / `Function`.
- A second offline core reconciliation
  (`gobjects-reconcile-second-source-20260529T035559Z`) accepted the same sample set
  `3/3`: target/class/outer membership passed for indices `0`, `1`, and `25447`, and
  `ServerChat` resolved as a `Function`. This strengthens `0x595b7e0` for offline
  reflection work, but it does not promote runtime-stable GObjects or public object
  identity.
- Bounded manual static evidence supports interpreting `0x595b7e0` as a base with
  `0x595b7f0=base+0x10`, `0x595b804=base+0x24`, and `0x595b838=base+0x58` for this
  binary hash. The official static machine gate remains inconclusive because no
  non-oversized coherent field window contains root/chunks/count/serial together.
- Static handle-accessor evidence favors `FUObjectItem+0x8` as the serial-backed dword for
  object handles. Treat `FUObjectItem+0xc` as unknown, not accepted serial evidence.
  Offline tooling should record both fields neutrally until independent core reconciliation
  proves exact semantics and reuse/invalidation rules.
- Broad copied-core scans now found nonzero `FUObjectItem+0x8` serial candidates in both
  available cores: first 200,000 readable object slots showed `817` nonzero serials,
  `197330` zero serials, and `0` internal-index mismatches per core. This weakens the old
  tiny-sample `zero_or_missing_fuobjectitem_serial_candidates` blocker for broad evidence,
  but public `ResourceHandle` remains blocked by lifetime/reuse and `UObject+0x8` flag
  semantics. Use `scripts/scan_resource_handle_serials.py` for repeatable offline scans.
- Targeted Ghidra/radare2 evidence for this binary hash confirms a weak-object helper at
  `0x1d56a30` that validates `{index, serial}` against `0x595b804`, `0x595b7f0`,
  `FUObjectItem+0x8`, and `UObject+0x8` masks `0x100`/`0x4000`. Serial-publication
  candidates at `0x1d56980` and `0x1d56e20` allocate through `lock xadd [0x595b838]` and
  `cmpxchg [FUObjectItem+0x8]`. This strengthens serial evidence only; it does not prove
  public handle lifetime, flag semantics, or same-instance promotion by itself.
- `uobject_flags_validity_semantics_unproven` blocks public/post-callback
  `ResourceHandle` work. `UObject+0x8` is a 32-bit flags field for the current hash; static
  helpers consult `0x100` and `0x4000` after `{index, serial}` validation, accepted samples
  include `0x81`/`0xc7`/`0xc5`, and no rejected sample or named lifetime semantic is
  proven. Keep identity, handles, mutation, and return overrides unpromoted.
- `minimal-second-source-intake` has accepted offline second-source UFunction layout
  evidence from
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`:
  `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, empty blockers, and
  `4/4` accepted compact targets for `sdk_inventory` and `sdk_structures`
  (`PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory`,
  `PrimalStructure.AllowStructureAccess`, and `PrimalStructure.IsAllowedToDemolish`).
  This promotes layout evidence only. It does not promote `GObjects`, `ResourceHandle`,
  `UObject` identity, mutation, return overrides, raw params, player/item/inventory
  identity, or public Inventory/StructureEvents SDK surfaces.
- `structure-observer-intake` now has a clean second-source readiness report with
  `promotion_gate.ready=true`, `blockers=[]`, and `6/6` accepted UFunction targets for
  `sdk.structures`. This backs the copied/redacted `GameplayPolicyEvent` promotion only.
  `StructureEventDispatcher` remains internal; do not promote public `StructureEvents`,
  raw pincode values, player identity, mutation, or return overrides.
- `dino-compact-intake` has accepted offline second-source layout evidence for
  `PrimalDinoCharacter.AddPassenger` and `PrimalDinoCharacter.AllowCarryCharacter`
  (`2/2`, `promotion_gate.ready=true`, empty blockers) from the
  `fuobjectitem-dino-reconcile-20260529T120000Z` workspace pack. Treat this as internal
  layout evidence only; it does not promote public Dino callbacks, object identity,
  mutation, return overrides, or resource handles.
- `buff-compact-intake` has accepted offline second-source UFunction layout evidence from
  `/servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z`:
  `promotion_gate.ready=true`, empty blockers, and `3/3` accepted targets
  (`PrimalBuff.AllowPostProcessEffect`, `PrimalBuff.BPBuffPreventUploading`, and
  `PrimalBuff.BP_OnBuffLifetimeUpdated`). Treat this as layout evidence only; it does not
  promote a public Buff SDK, runtime hooks, callbacks, mutation, return overrides, object
  identity, or raw params.
- `mission-compact-intake` and `tribe-compact-intake` have accepted offline second-source
  UFunction layout evidence from
  `/servidor/ark/workspace-offline/next-targetset-discovery-20260529T000000Z`:
  mission is `4/4` accepted and tribe is `5/5` accepted, both with
  `promotion_gate.ready=true` and empty blockers. Treat both as layout evidence only.
  Mission is the cleaner next module candidate; tribe should be split into a scalar subset
  before any public work. Do not promote player/tribe identity, arrays, strings, object
  pointers, mutation, return overrides, or public Mission/Tribe SDK surfaces.
- Native exec field patching was unsafe and must remain disabled. Do not use
  `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` unless a future written plan proves a separate
  throwaway process can tolerate crashes.
- The ReflectionScanner analyzer strict mode now requires a repeat-confirmed exact
  `matched_clues=3/3` table candidate; a single exact row is only a clue.
- If a reviewed FName root slot is already available for the same binary/artifact, abort
  broad reverse FName table scans and pass that root slot explicitly into evidence-pack,
  GObjects sampling, or snapshot regeneration tooling. Reopen scanning only when a new
  binary hash or contradictory artifact evidence invalidates the known root.
- Runtime debug control can trigger bounded probes after the process is alive. The first
  post-start `request-static-fname-probe` for `0x5956f30` executed correctly but still
  rejected the slot (`table=0x13733660`, `implausible_num_elements`). Do not keep waiting
  for bootstrap retries or promote `0x5956f30` from a single core-dump session.

## Research Principles

- Prefer reflection-backed decoding over raw memory scanning in plugins.
- Do not scan arbitrary params on every `ProcessEvent` in live servers.
- Use filtered callbacks by `fname_index` whenever possible.
- Treat `ReflectionScanner` as an offline/debug tool, not a production startup feature.
- Treat ReflectionScanner `evidence_pack.status=research-candidate` as candidate ranking
  only. The structured `promotion_gate` must remain `ready=false` and non-promotable for
  GNames/GObjects until second-source or independent static evidence exists.
- Prefer post-start or offline evidence over blind startup waits. If a server is joinable
  and the scanner still reads zero/invalid tables, change the method instead of extending
  sleep/retry windows.
- Every new offset or signature must include how it was derived and what binary/version it was tested against.
- FName index manifest resolution must use offline inputs or an explicit SHA256. Do not
  point `--manifest`, `--ark-binary`, or accepted entry evidence-pack manifest paths at
  `/servidor/ark`; direct and symlinked live-server paths are rejected by the validator.
- Raw captures may be stored under `/servidor/ark/obelisk/dumps` for disk-space reasons,
  but snapshot regeneration and promotion tooling must consume hardlinked or copied
  offline artifacts from `/servidor/ark/workspace-offline` or another approved offline
  root. Direct or symlink-resolved `dumps` inputs/outputs remain protected.
- Evidence-pack manifests are executable inputs for snapshot regeneration. Treat
  manifest `core.path` as a read path and reject direct or symlink-resolved
  `/servidor/ark` targets before hashing or deriving defaults.
- Current instance posture belongs in `docs/agent-handoff/CURRENT.md`. Read it before
  server-backed reversing, then require explicit approval for the exact target, marker
  changes, restart window, rollback plan, and shutdown expectations.
- Run scanner/native-exec/ptrace/gcore/broad tracing only after explicit operator approval
  for the exact debug instance window, with plugins disabled, copied-log
  evidence, rollback, and shutdown at the end of the test.

## Safe Experiment Pattern

Use the operator-approved debug/development target for reversing/runtime validation. For
marker changes, restarts, or runtime observation windows, keep the run scoped, record
rollback posture, and shut the server down afterward when the approved plan requires it.

On protected production/shared instances, stop: no Obelisk restarts, marker changes,
scanners, or runtime tests are allowed without an explicit maintenance window.

For scanner, `gcore`/`ptrace`, native exec experiments, or broad event discovery, enable
one experiment at a time only in an approved debug window. The wrapper should set explicit
environment variables from safe per-instance markers such as
`enable-process-event-hook` and `disable-plugins`:

```bash
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_INSTANCE_ID=arkserver2
export OBELISK_PE_TRACE_LIMIT=0
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
```

Set `OBELISK_ENABLE_REFLECTION_SCANNER=1` only for the specific scanner capture start and
only with the matching `enable-reflection-scanner` instance marker. Native exec probes also
require both `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` and the
`enable-native-exec-probes` marker. Then copy the log and analyze it offline:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --strict /path/to/isolated/Obelisk.log
```

Strict success is still research evidence, not a committed offset. Require either a second
isolated capture or static xref validation before promoting a candidate.

For live-like development captures authorized by the operator, keep the run short and
restore stable posture immediately:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>
```

Use explicit target flags for the approved debug instance. If this fails, fix the server
posture before doing more code or agent work.

## Test Strictness

- Analyzer tests must include accepted, rejected, and strict-mode failure fixtures for every
  new ReflectionScanner log family.
- Runtime probes must have explicit env gates and default to off.
- A sample, weak probe, or partial match must not satisfy analyzer `--strict`.
- Every capture note should include the post-capture stable posture check result.

## Post-RC Research Backlog

1. Resolve `fname_index -> name` through GNames/FNamePool.
2. Add a bounded live data-mapping scanner or offline core scanner for FName-table-shaped
   pointers instead of relying on one static slot.
3. Locate GObjects and enumerate UFunction objects.
4. Register callbacks by function name, not raw index.
5. Decode function params from UProperty metadata.
6. Compare sanitized UFunction/ScriptStruct snapshots against a second source before
   promoting module recognizers.
7. Replace raw FString and arbitrary param probing with reflected param decoding.
