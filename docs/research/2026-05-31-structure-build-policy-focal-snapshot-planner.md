# Structure Build-Policy Focal Snapshot Planner

Date: 2026-05-31
Obelisk commit reviewed: `0b0bd4f`

## Scope

Offline-only follow-up for the second-wave structure build-policy lane:
`PrimalStructure.IsAllowedToBuild` / `APrimalStructure.IsAllowedToBuild`.

This pass did not use a server, `/servidor/ark` direct input, ReflectionScanner,
runtime observation, ptrace/gcore, Discord, push, tag, rebase, commit, SDK promotion,
runtime hooks, descriptors, or target-set release work.

ArkApi/AseApi remains a names and demand dictionary only. No offsets, layouts, wrappers,
ABI choices, or allow/deny semantics are imported from it.

## Finding

The repository already had most of the required guardrails:

- `compare_reflection_snapshots.py` gives explicit blocked guidance for both exact
  `IsAllowedToBuild` spellings and keeps them out of promoted target sets.
- `snapshot_evidence_pack.py` rejects protected manifest/core paths before reading the
  evidence-pack core and requires complete evidence-pack status, binary SHA, core SHA,
  FName root, and GObjects candidate fields.
- `inspect_core_ufunctions.py --snapshot-json` is focused and candidate-only: exact
  target selection, complete evidence metadata, `offline_core`, and `candidate-only`.
- `regenerate_ufunction_snapshots.py` can consume a complete evidence-pack manifest, but
  it is manifest/fixture oriented and rejects unknown target filters.

The practical gap was narrower: there was no candidate-only planner for an exact ad hoc
UFunction target that is intentionally not in the committed snapshot manifest or target
sets yet.

## Tooling Applied

Added `scripts/build_reflection_inventory_pack.py --plan-target Outer.Name`.

The new plan mode:

- accepts schema-qualified or short exact UFunction targets;
- works with `--evidence-pack-manifest` after the existing protected-path, SHA, status,
  FName root, and GObjects validation;
- emits `obelisk.ufunction-focal-snapshot-plan.v1` inside `ufunction-inventory.json`;
- uses unfiltered redacted inventory for exact target planning, so broad inventory display
  filters cannot create a false missing-target blocker;
- emits an exact `scripts/inspect_core_ufunctions.py --snapshot-json` command using the
  resolved offline core path, GObjects, FName root slot, binary SHA, artifact SHA,
  capture id, evidence-pack id, current Obelisk commit, command cwd, and
  `PYTHONDONTWRITEBYTECODE=1` environment;
- blocks command generation when FName root validation is not ready;
- blocks missing or ambiguous inventory matches instead of inventing fixture entries;
- records redaction review reminders for placement structs, location/rotation values,
  player/controller context, object refs, arrays, and raw params;
- records non-claims: no target set, no fixture, no StructureEvents/build-policy SDK,
  no runtime hook, no mutation, and no return override.

Example command shape once a complete non-protected evidence pack exists:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest <non-protected-pack>/manifest.json \
  --plan-target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild \
  --output-dir <ignored-non-protected-review-output>
```

If `APrimalStructure` is proven as the reflected owner, run the same planner with:

```bash
--plan-target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild
```

Do not add either spelling to `reflection_target_sets.py` until an exact sanitized
candidate snapshot exists and the redaction policy is reviewed.

## Current Status

Planner confidence is limited to offline command planning from a complete, non-protected
evidence-pack manifest or direct copied/offline core. A `planned` target means only that
the exact owner/name appears once in the redacted inventory and the FName root validation
is ready enough to run the emitted snapshot command. It is not layout acceptance,
second-source evidence, runtime readiness, target-set promotion, or SDK readiness.

The tooling cannot extract the actual `IsAllowedToBuild` snapshot until an eligible input
exists.

Still missing for extraction:

- a readable copied/offline ELF core whose path resolves outside protected server roots,
  or a complete core evidence-pack manifest whose `core.path` resolves outside protected
  server roots;
- matching `core.sha256` and binary SHA identity;
- usable FName root slot and GObjects candidate in the evidence-pack manifest;
- exactly one inventory match for `PrimalStructure.IsAllowedToBuild` or, if observed,
  `APrimalStructure.IsAllowedToBuild`.

Inputs required before the next offline review attempt:

- one sanitized candidate snapshot for the exact observed owner/name only;
- a redaction review marking placement structs, location/rotation context, player or
  controller refs, structure/object refs, arrays, strings, and raw params redacted or
  recognition-only unless separately promoted;
- a distinct sanitized second-source snapshot with different artifact identity before
  any layout readiness claim;
- no mutation, return override, runtime observation, public SDK, or target-set promotion
  from this planner output alone.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_build_reflection_inventory_pack.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_compare_reflection_snapshots.CompareReflectionSnapshotsTests.test_structure_build_policy_targets_stay_out_of_rc_compact_sets_with_missing_base_gap \
  scripts.test_compare_reflection_snapshots.CompareReflectionSnapshotsTests.test_structure_build_policy_guidance_can_be_listed_without_snapshots \
  scripts.test_compare_reflection_snapshots.CompareReflectionSnapshotsTests.test_structure_build_policy_guidance_rejects_unmatched_explicit_target
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_research_doc_guardrails
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_public_sdk_guardrails.PublicSdkGuardrailTests.test_v1_modding_route_keeps_broad_surface_without_sdk_promise
```
