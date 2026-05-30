# Mission Copied-Bool Observer Plan

Date: 2026-05-30

## Objective

Freeze the docs-only model for a future default-off Mission copied-bool observer. This is
a runbook and review contract only; it does not authorize runtime wiring, server access,
marker changes, wrapper changes, commits, pushes, or public Mission SDK work.

The current evidence source is
`docs/research/2026-05-29-mission-reflection-internal-readiness.md`, including the
2026-05-30 strict signature and second-source bool semantics refresh.

## Evidence Baseline

- Target set: `mission-compact-intake`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Refreshed second-source scope: `layout_only`
- Refreshed target result: `targets=4`, `comparable=4`, `second_source_accepted=4`
- Redacted signature schema: `obelisk.redacted-ufunction-signatures.v1`
- Redacted signature status: `candidate_only`
- Consume gate: `accepted`
- Promotion ready: `false`
- Copied scalar count: `5` bool fields
- Redacted field count: `6` object/container fields

This closes the Mission compact bool second-source gap for observer planning only. It
does not close runtime observer, dispatcher lifecycle, callback ABI, public SDK, identity,
array payload, mutation, return override, or server-validation gates.

## Frozen Target Surface

Only these four reflected functions are in scope:

- `MissionType.AddPlayerToMission`
- `MissionType.BPAllowPlayerToLeaveMission`
- `MissionType.BPOnPlayerRemovedFromMission`
- `MissionType.GetPlayerUsableItems`

Only these five one-byte bool fields may ever be copied into an observer record:

- `MissionType.AddPlayerToMission.bForceAdd`
- `MissionType.AddPlayerToMission.ReturnValue`
- `MissionType.BPAllowPlayerToLeaveMission.ReturnValue`
- `MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent`
- `MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess`

Only these six object/container fields may be recognized, counted, and named as redacted
metadata. Their pointer, object, array, identity, and payload values must not be copied or
logged:

- `MissionType.AddPlayerToMission.PlayerCharacter`
- `MissionType.BPAllowPlayerToLeaveMission.PlayerPawn`
- `MissionType.BPOnPlayerRemovedFromMission.Player`
- `MissionType.BPOnPlayerRemovedFromMission.Controller`
- `MissionType.GetPlayerUsableItems.Character`
- `MissionType.GetPlayerUsableItems.OutItemIDs`

`GetPlayerUsableItems` is recognition-only in this model. It may produce a matched
observer record with `copied_bool_count=0`, but `OutItemIDs` stays redacted and no item
array or item identity may be exposed.

## Observer Model

The observer is internal, log-only, post-original, and default-off. It must never dispatch
plugin callbacks or write back to UE parameters.

The runtime recognizer, if later approved, must:

- apply the exact Mission FName prefilter before any reflected metadata or parameter read;
- accept only the current Mission prefilter index set: `7702`, `7649`, `1211`, `1582`;
- validate supported binary SHA, exact outer/function name, `ParmsSize`,
  `ReturnValueOffset`, property classes, property names, offsets, sizes, bool masks, and
  SHA-scoped internal class/outer identities before copying bool bytes;
- reject non-canonical bool bytes greater than `1`;
- reserve observation sequence and consume log budget only after the exact prefilter and
  recognizer acceptance;
- run only after the original `ProcessEvent` returns for return-bool fields;
- copy only the five frozen bool fields into Obelisk-owned memory;
- clear copied output on every rejection path;
- leave params, return values, object fields, array fields, and gameplay state unchanged.

## Log Grammar Proposal

The first runtime log line for an approved window should identify the internal observer
without claiming SDK delivery:

```text
MissionCopiedBoolObserver enabled binary_sha256=<64hex> target_set=mission-compact-intake limit=<uint64> delivery_claim=none.
```

Each accepted observation should use one line with fixed keys. `copied_bool_values` uses
`0` or `1` in the same order as `copied_bool_fields`; absent bools use empty lists.

```text
MissionCopiedBoolObserver event sequence=<uint64> target=<MissionType.FunctionName> post_original=true copied_bool_count=<0..2> copied_bool_fields=<csv-or-empty> copied_bool_values=<csv-or-empty> redacted_count=<0..2> redacted_fields=<csv-or-empty> delivery_claim=none.
```

Allowed `target` values are exactly the four frozen functions above. Allowed
`copied_bool_fields` values are exactly the five frozen bool fields above. Allowed
`redacted_fields` values are exactly the six frozen redacted fields above.

Do not log player names, controller identity, character identity, mission identity, item
ids, item arrays, object names, class names, UE pointers, function pointers, raw params,
raw buffers, FName indices, GObjects indices, `ResourceHandle`, strings, text, map
location, tribe/platform IDs, return override decisions, plugin subscriber state, or
payload sizes derived from redacted arrays.

Rejected metadata, disabled gates, non-mission FName values, unsupported SHA values,
unreadable params, malformed bool bytes, and exhausted budgets should not emit per-event
value logs. If counters are added later, they must be aggregate-only and must not include
redacted payload values.

## Gates

This plan is not approval to add or enable gates. If a later implementation review
approves runtime wiring, the minimum gate set is:

- `OBELISK_ENABLE_MISSION_REFLECTION=1`;
- supported `ShooterGameServer` SHA256 equals
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`;
- positive, bounded Mission observer log limit;
- observer debug profile selected by the wrapper;
- active observer debug window marker for the instance;
- active `enable-mission-reflection` instance marker;
- exact Mission FName prefilter index set `7702`, `7649`, `1211`, `1582`;
- exact `MissionReflection` metadata recognizer acceptance before budget reservation.

Stable wrapper/profile launches must scrub or ignore the Mission observer env family and
fail closed if an experimental Mission marker is present. A zero or missing log limit,
missing profile, missing observer window, missing marker, missing SHA, unsupported SHA,
or non-mission FName must avoid metadata reads and must not reserve budget.

## Runtime Runbook

No run is approved by this note. A later run request must name:

- instance id, map, ARK binary path, and SHA256;
- exact Obelisk build and whether Mission runtime wiring is present;
- exact marker and env changes;
- log limit and expected maximum event lines;
- player/privacy bounds and whether any player-facing action is required;
- copied-log destination outside live server logs;
- rollback owner and stable-posture verification commands.

During the window, collect only the proposed grammar lines and standard startup/gate
lines needed to prove the observer was enabled and then disabled. Do not run scanners,
ptrace, `gcore`, broad ProcessEvent tracing, raw discovery, native exec probes, dispatcher
callbacks, mutation experiments, or return override experiments as part of this observer
window.

## Rollback Requirements

Rollback for any future approved runtime window must be defined before activation:

- remove or disable Mission observer env values;
- remove the `enable-mission-reflection` marker and any observer-window marker used only
  for the run;
- restore the stable wrapper/profile posture;
- restart only the explicitly approved target instance if the window plan requires it;
- copy relevant logs to the approved offline artifact path before cleanup;
- run the stable posture check and verify no Mission observer env or marker remains;
- record the rollback result and any unexpected Mission observer lines in a follow-up
  research note.

If rollback cannot be proven, the observer result remains operationally blocked even if
the copied bool lines look correct.

## Validation Floor

Before runtime wiring is reviewed, local validation must include at least:

```bash
cmake --build build --target mission_reflection_tests process_event_mission_reflection_tests -j"$(nproc)"
ctest --test-dir build --output-on-failure -R '^(MissionReflectionTests|ProcessEventMissionReflectionTests)$'
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_release_scope_guardrails.py
```

Tests must prove disabled gates, missing profile/window/marker/SHA, unsupported SHA, zero
budget, and non-mission FName values do not read memory or consume budget. They must also
prove accepted compact targets expose exactly the five copied bools, all six
object/container fields stay redacted, rejection clears stale copied output, params are
not mutated, and no dispatcher or public callback is invoked.

## Non-Goals

This plan does not promote or authorize:

- public Mission SDK, public header changes, C ABI changes, capability bits, public JSON,
  plugin callbacks, or SDK consumer fixtures;
- `ProcessEventHook.cpp` wiring, CMake shared-library inclusion, wrapper scripts, marker
  definitions, env parsing, posture scripts, CLI summaries, or live-server activation;
- dispatchers, callback lifecycle claims, object identity, player/controller/character
  identity, mission identity, item identity, arrays, strings, raw params, FName/GObjects
  indices, `ResourceHandle`, lookup APIs, mutation, blocking, return override, or manual
  `ProcessEvent` calls;
- scanner runs, ptrace, `gcore`, native exec probes, broad tracing, or production
  observation.

The next actionable Mission step is still an internal/test-only policy decision. Public
API work remains blocked.
