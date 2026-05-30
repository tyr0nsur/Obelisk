# Mission Reflection Internal Readiness

## Objective

Review the latest `tests/core/MissionReflectionTests.cpp` expansion and record whether
`MissionReflection` is ready as an internal module readiness pack without promoting a
public Mission SDK.

This note is documentation only. It does not authorize live-server access, restarts,
marker changes, runtime observers, scanner runs, ptrace, `gcore`, hook wiring,
dispatcher/API work, gameplay mutation, return overrides, commits, or pushes.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Files reviewed: `ue/MissionReflection.{h,cpp}`, `tests/core/MissionReflectionTests.cpp`,
  `hooks/ProcessEventInventoryReflection.{h,cpp}`,
  `hooks/ProcessEventStructureReflection.{h,cpp}`, `hooks/ProcessEventHook.cpp`,
  `CMakeLists.txt`
- Files changed: this note
- Live-server impact: none. Review and validation used local source and unit tests only.

## Test Review

The latest test expansion supports an internal mission recognizer readiness pack for the
accepted compact mission target set:

- `MissionType.GetPlayerUsableItems` is recognition-only for object/array fields and does
  not read unreadable params for those fields.
- `MissionType.AddPlayerToMission`, `MissionType.BPAllowPlayerToLeaveMission`, and
  `MissionType.BPOnPlayerRemovedFromMission` expose only bounded 1-byte bool ranges.
- Object, controller, player, character, and array fields stay recognition-only with no
  exposed range.
- Metadata-only recognition works when params are absent.
- Bool ranges fail closed when params are unreadable.
- Unsupported binary/layout gates reject before memory reads.
- Wrong outer, numbered `FName`, wrong function/property class, wrong property name,
  wrong flags, wrong `ParmsSize`, wrong return offset, truncated chains, overlong chains,
  and null function pointers are rejected.
- Property class, `Function` class, and `MissionType` outer identity are now strict for
  the supported binary hash: the recognizer checks both FName and observed internal object
  index for the validated fixture identities. These indices remain internal
  SHA-scoped guardrails, not public contracts.

## Boundary Decision

`MissionReflection` is ready only as an internal, fixture-backed recognizer/copy-readiness
pack. The tests support exact metadata recognition and reduced copied scalar planning, but
they do not promote:

- a public Mission SDK, C ABI, callback, capability bit, or plugin event;
- live `ProcessEventHook.cpp` wiring, dispatcher integration, runtime observer enablement,
  or server validation;
- player/controller/mission identity, object pointers, arrays, strings, raw params,
  `FName`/GObjects indices, `ResourceHandle`, lookup APIs, mutation, or return override.

The only plausible copied fields from the reviewed compact set are the bool scalar fields:

```text
AddPlayerToMission.bForceAdd
AddPlayerToMission.ReturnValue
BPAllowPlayerToLeaveMission.ReturnValue
BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent
BPOnPlayerRemovedFromMission.bLastPhaseSuccess
```

`GetPlayerUsableItems.OutItemIDs` remains recognition-only; item arrays and item identity
stay blocked.

## Validation

Local unit validation:

```bash
cmake --build build --target mission_reflection_tests && ./build/mission_reflection_tests
```

Result:

```text
[100%] Built target mission_reflection_tests
MissionReflectionTests passed
```

## Risks

- This is fixture-backed internal readiness, not runtime-observed evidence.
- The existing second-source layout evidence remains layout-only; it does not validate
  callback lifecycle, dispatcher ownership, or public ABI behavior.
- Any future runtime observation still needs a separate approval, supported-SHA gate,
  exact cheap prefilters, explicit non-zero budget, marker/env gating, bounded logs,
  rollback posture, no mutation, and no return override.

## ProcessEventMissionReflection Scaffold Decision

Decision: a minimal `ProcessEventMissionReflection` scaffold is viable only as a
test-first, log-only, default-off helper layer. It should not wire into the live
`ProcessEventHook.cpp` path, the `obelisk` shared-library source list, any dispatcher, or
any public Mission SDK in the first step.

The current local scaffold is enough to support that narrow helper:

- `ue/MissionReflection.{h,cpp}` already validates exact compact mission metadata, binary
  SHA, outer/name, flags, `ParmsSize`, `ReturnValueOffset`, property class/name/offset/size,
  and bounded bool ranges.
- `tests/core/MissionReflectionTests.cpp` already covers accepted shapes, metadata-only
  recognition, unreadable params, unsupported binary/layout gates, wrong outer/name number,
  wrong classes, wrong offsets/sizes, wrong flags, truncated/overlong property chains, and
  null function pointers.
- Existing hook-side patterns in `ProcessEventInventoryReflection` and
  `ProcessEventStructureReflection` provide the narrow gate/budget/attempt API shape.

The first implementation slice now exists locally and remains test-only. It touched only
these files:

- `hooks/ProcessEventMissionReflection.h`;
- `hooks/ProcessEventMissionReflection.cpp`;
- `tests/core/ProcessEventMissionReflectionTests.cpp`;
- one CMake test target, `process_event_mission_reflection_tests`, built from the helper,
  `ue/MissionReflection.cpp`, and `ue/RuntimeReflection.cpp`.

The helper now rejects mismatched FName prefilters, preserves copied-only observation
payload shape, and tests that parameter memory is not mutated while building
observations.

The current slice deliberately avoids these files and surfaces:

- no `hooks/ProcessEventHook.cpp` include, counters, env parsing, log statements, or call
  path until the helper tests pass and a separate runtime-wiring review approves it;
- no addition of `hooks/ProcessEventMissionReflection.cpp` to the `obelisk` shared-library
  source list in the first slice;
- no `core/*Dispatcher*`, no public headers under `include/obelisk/**`, no plugin callback,
  no capability bit, no SDK consumer fixture, no release docs, and no public JSON surface;
- no server access, markers, restarts, scanner runs, ptrace, `gcore`, or runtime observer.

The helper API should be smaller than inventory/structure because Mission is log-only:

- `EvaluateGate(OBELISK_ENABLE_MISSION_REFLECTION, observerDebugProfile,
  observerDebugWindow, enable-mission-reflection marker, binarySha256)`;
- `IsReflectedMissionNameIndex`, covering only `7702`, `7649`, `1211`, and `1582`;
- `ShouldAttemptObservation`, `ShouldAttemptNameObservation`, `HasObservationBudgetRemaining`,
  `TryReserveObservationBudget`, and `ShouldLogObservation`, with no dispatch budget;
- `TryIdentifyInvocation`, which calls `MissionReflection::TryIdentifyMissionInvocation`
  only after gate, exact name prefilter, and non-zero log budget.

Tests must precede any runtime wiring and prove:

- disabled gate, missing observer profile, missing observer window, missing marker, missing
  SHA, unsupported SHA, and zero log limit do not read memory;
- non-mission `fname_index` does not read memory and does not consume budget;
- budget is reserved only after exact mission FName prefiltering;
- accepted compact targets produce `Matched` attempts and expose only the five approved bool
  scalar ranges;
- `GetPlayerUsableItems.OutItemIDs`, player/controller/character/object fields, arrays,
  strings, raw params, object identity, mission identity, and `ResourceHandle` remain
  recognition-only or absent from logs;
- rejected metadata shapes remain `Rejected` without mutation, return override, dispatcher
  calls, or public callback behavior.

Runtime wiring is a later decision, not part of this scaffold. If it is ever approved, the
next review must separately justify edits to `hooks/ProcessEventHook.cpp`, mission env
parsing, mission counters, logging text, marker naming, CMake shared-library inclusion, and
operator rollback posture.

## Next Step

If MissionReflection work continues, keep the `ProcessEventMissionReflection` helper tests
as the validation floor. The next step is a separate runtime-observation/lifecycle review;
no live hook wiring, dispatcher, API surface, marker/env gate, or runtime log claim should
be added from this readiness note alone.

## Test-Only Hardening Follow-Up

A later local test-only slice widened `tests/core/ProcessEventMissionReflectionTests.cpp`
without changing runtime wiring, public ABI, markers, servers, or dispatchers.

Additional guardrails now cover:

- hook-level disabled gates and non-mission `fname_index` values do not read metadata,
  reserve observation budget, or keep an observation number;
- every recognition-only object/array field rejects forged ranges: `Character`,
  `OutItemIDs`, `PlayerCharacter`, `PlayerPawn`, `Player`, and `Controller`;
- copied bool construction rejects a one-byte range with `Data == nullptr`;
- rejection paths clear pre-seeded copied output instead of leaving stale data;
- the internal copied-bool surface remains exactly five fields:
  `bForceAdd`, two `ReturnValue` fields, `bFromMissionCompleteEvent`, and
  `bLastPhaseSuccess`.

Validation for this follow-up:

```bash
cmake --build build -j$(nproc)
ctest --test-dir build --output-on-failure -R '^(MissionReflectionTests|ProcessEventMissionReflectionTests)$'
python3 scripts/test_release_scope_guardrails.py
```

All passed locally. Mission remains internal/test-only and post-RC; this does not promote
Mission SDK, runtime observer wiring, public callbacks, identity, mutation, return
override, or server validation.

## Strict Identity And Signature Artifact Follow-Up

On 2026-05-30, a post-RC local hardening pass tightened the Mission recognizer and
hook-side copied-bool helper without adding runtime wiring or public SDK surface.

Code hardening:

- `MissionReflection` now validates exact SHA-scoped internal object identity for the
  `Function` class (`518`), `MissionType` outer (`179`), `BoolProperty` class (`532`),
  `ObjectProperty` class (`534`), and `ArrayProperty` class (`528`) in addition to FName,
  number, flags, size, offset, chain, and range checks.
- `ProcessEventMissionReflection` rejects copied bool bytes greater than `1` instead of
  normalizing non-canonical bytes to `true`.
- Public SDK guardrails now generate and block unpromoted module consumer tokens such as
  `ObeliskMissionEvent`, `RegisterMissionEvent`, and Mission policy-event variants.

Offline artifact generated under the protected workspace:

```text
/servidor/ark/workspace-offline/mission-compact-redacted-signatures-strict-20260530T015442Z/
```

Artifact summary:

- `signatures.json` schema: `obelisk.redacted-ufunction-signatures.v1`;
- target set: `mission-compact-intake`;
- coverage: complete for `MissionType.AddPlayerToMission`,
  `MissionType.BPAllowPlayerToLeaveMission`, `MissionType.BPOnPlayerRemovedFromMission`,
  and `MissionType.GetPlayerUsableItems`;
- signature count: `4`;
- copied scalar count: `5` bool fields;
- redacted fields: `6` object/container fields;
- consume gate: `accepted`;
- artifact status: `candidate_only`;
- promotion ready: `false`.

Validation:

```bash
cmake --build build --target mission_reflection_tests process_event_mission_reflection_tests -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(MissionReflectionTests|ProcessEventMissionReflectionTests|AbiLayoutTests|CAbiLayoutTests|SdkConsumerFixture.*)$'
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_release_scope_guardrails.py
git diff --check
```

All passed locally.

Remaining blockers are unchanged: this does not promote Mission SDK, runtime observer
wiring, dispatcher lifecycle, callback ABI, identity/lookup, arrays, mutation, return
override, or server validation. A current strict second-source comparison still needs a
comparable artifact that includes bool semantics for the three bool-bearing Mission
targets; the strict redacted-signature artifact closes target-set coverage, not the full
promotion ladder.

## Second-Source Bool Semantics Refresh

Later on 2026-05-30, the stale second-source Mission snapshots were regenerated from the
existing offline TheIsland core with current snapshot tooling. No server was started and
no live instance was touched.

Offline inputs:

- core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`;
- binary:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`;
- core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`;
- binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`;
- FName root slot: `0x5956f30`;
- GObjects candidate: `0x595b7e0`.

Generated evidence root:

```text
/servidor/ark/workspace-offline/mission-compact-intake-bool-semantics-refresh-20260530T020021Z/
```

Important outputs:

- `pack/fname-root-validation/core.fname-root-validation.json`;
- `pack/gobjects-sampling/manifest.json`;
- `ufunction-snapshots/7e7ded49e0c6/sdk_missions/*.snapshot.json`;
- `pack/snapshot-comparison/mission-readiness-report.json`;
- `pack/redacted-signatures.json`;
- `pack/redacted-signatures.consume-gate.json`.

The refreshed snapshot comparison now reports:

```text
target_set=mission-compact-intake
targets=4
comparable=4
second_source_accepted=4
second_source_inconclusive=0
second_source_missing=0
second_source_rejected=0
promotion_gate.ready=true
ready_scope=layout_only
```

The refreshed redacted signature manifest reports:

```text
signature_count=4
bool_masked_field_count=5
copied_scalar_by_kind.bool=5
redacted_count_total=6
artifact_status=candidate_only
promotion_ready=false
consume_gate.status=accepted
consume_gate.sha256=09074e71666f755801802e5d796361cf4f84d3e7d8c00663801d84f981a1cc13
```

This closes the earlier Mission bool second-source gap for the compact target set. It
still does not promote a public Mission SDK, runtime observer wiring, dispatcher,
callback ABI, object/class identity, arrays, mutation, return override, or server
validation. The next Mission step remains an internal/test-only policy decision, not
public API work.
