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
- ResourceHandle remains blocked on UObject flag/lifetime semantics and a fail-closed
  runtime policy. Use the dated ResourceHandle, GObjects, and weak-helper research notes
  for scan counts, helper addresses, serial evidence, flag-sweep evidence, and blocker
  history. Static `0x1d18a90` evidence shows a `FUObjectArray` sweep that sets
  `UObject+0x8` bit `0x100` and conditionally sets `0x8000`, but this is still unnamed
  lifecycle evidence and does not promote public handles.
  Do not answer the remaining ResourceHandle blocker with another broad FName, GObjects,
  or core scan unless the binary hash changes or existing evidence is contradicted.
  The next useful blocker evidence is rejected runtime object samples plus runtime
  serial reuse/wraparound semantics under an approved live-ops brief.
- Accepted compact target sets are layout evidence only. They do not promote public module
  SDKs, object identity, mutation, return overrides, raw params, or `ResourceHandle`.
  Current module routing belongs in `docs/agent-handoff/CURRENT.md` and dated research
  notes.
- Strict redacted-signature artifacts and consume-gate acceptance are planning inputs
  only unless a separate promotion gate says otherwise.
- Copied `BoolProperty` observations must reject non-canonical bytes greater than `1`;
  do not normalize arbitrary nonzero bytes to `true`.
- Observer/helper gates must prove "no read, no budget" for disabled gates, missing
  profile/window/marker/SHA, unsupported SHA, zero budget, and non-target `fname_index`.
  Rejection paths must clear copied output, and recognition-only object/array fields must
  reject forged copied ranges.
- `ue/MissionReflection.*` implements the first internal mission recognizer for those
  four mission targets. It is SHA-gated and fixture-backed, exposes copied bool ranges
  only, and keeps player/controller/character object refs plus `OutItemIDs` arrays
  recognition-only. Do not add hooks, dispatchers, public Mission SDK, identity, mutation,
  or return override from this recognizer without a separate promotion gate.
- Native exec field patching was unsafe and must remain disabled. Do not use
  `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` unless a future written plan proves a separate
  throwaway process can tolerate crashes.
- The ReflectionScanner analyzer strict mode now requires a repeat-confirmed exact
  `matched_clues=3/3` table candidate; a single exact row is only a clue.
- If a reviewed FName root slot is already available for the same binary/artifact, abort
  broad reverse FName table scans and pass that root slot explicitly into evidence-pack,
  GObjects sampling, or snapshot regeneration tooling. Reopen scanning only when a new
  binary hash or contradictory artifact evidence invalidates the known root.
- Runtime debug control can trigger bounded probes after the process is alive. Do not keep
  waiting for bootstrap retries or promote candidates from a single core-dump session.

## Research Principles

- ArkServerApi/AseApi is reference material only: use it as names and demand signals for
  familiar Unreal/ARK plugin concepts, then verify every `UFunction`/`UProperty` through
  Obelisk reflection evidence. Never use it as architecture, ergonomics, behavior, or
  implementation guidance, and never
  import its offsets, vtables, struct layouts, `.lib` linkage, MSVC conventions,
  constants, schemas, control flow, command parsers, return semantics, source-derived
  implementations, or direct field/native-call wrappers into Obelisk.
- Prefer reflection-backed decoding over raw memory scanning in plugins.
- Do not scan arbitrary params on every `ProcessEvent` in live servers.
- Use filtered callbacks by `fname_index` only inside an explicit debug gate; stable
  plugin surfaces should consume copied Obelisk-level events instead of raw UE params.
- Treat `ReflectionScanner` as an offline/debug tool, not a production startup feature.
- Treat ReflectionScanner `evidence_pack.status=research-candidate` as candidate ranking
  only. The structured `promotion_gate` must remain `ready=false` and non-promotable for
  GNames/GObjects until second-source or independent static evidence exists.
- Prefer post-start or offline evidence over blind startup waits. If a server is joinable
  and the scanner still reads zero/invalid tables, change the method instead of extending
  sleep/retry windows.
- Every new offset or signature must include how it was derived and what binary/version it was tested against.
- Use `scripts/build_weak_helper_provenance_bundle.py` to archive weak-helper static or
  decompiler artifacts with hashes and source-provenance sidecars. Missing or invalid
  sidecars are blockers, not hard failures, and keep `promotion_ready=false`; such bundles
  remain archival evidence only.
- FName index manifest resolution must use offline inputs or an explicit SHA256. Do not
  point `--manifest`, `--ark-binary`, or accepted entry evidence-pack manifest paths at
  protected `/servidor/ark` live paths; direct and symlinked live-server paths are rejected
  by the validator.
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
export OBELISK_INSTANCE_ID=<approved-instance>
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

## Post-RC Research Route

1. For the current binary hash, reuse the reviewed FName root and `GUObjectArray`
   research-candidate as offline inputs; do not restart broad FName/GObjects discovery
   unless a new binary hash or contradictory evidence invalidates them.
2. Advance new module work through closed target-set snapshots, redacted signatures, and
   second-source comparison before promoting copied recognizers.
3. Keep public/runtime GObjects, object identity, lookup, and `ResourceHandle` promotion as
   separate blocked gates. ResourceHandle needs approved runtime rejection samples plus
   serial reuse/wraparound semantics, not more broad offline scans.
4. Register callbacks by function name, not raw index.
5. Decode function params from UProperty metadata.
6. Replace raw FString and arbitrary param probing with reflected param decoding.
