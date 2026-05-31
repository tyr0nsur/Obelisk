# Batch/Focal Snapshot Planner Design

Date: 2026-05-31
Scope: offline-only repository inspection for the missing batch/focal UFunction snapshot
planner referenced by `docs/research/2026-05-31-fname-gobjects-offline-route.md`.

This pass did not read or write `/servidor/ark`, did not run server tools,
ReflectionScanner, ptrace, `gcore`, or snapshot extraction, and did not change runtime
code.

## Current Tooling Shape

- `scripts/build_reflection_inventory_pack.py` already has the safest focal primitive:
  `focal_snapshot_plan(...)` emits candidate-only `inspect_core_ufunctions.py
  --snapshot-json` commands with FName root, GObjects, binary SHA, artifact SHA,
  capture id, evidence-pack id, Obelisk commit, command cwd, and
  `PYTHONDONTWRITEBYTECODE=1`.
- `--plan-target` is repeatable and blocks duplicate, missing, ambiguous, and
  FName-root-not-ready targets. It is good for one or a small handful of exact ad hoc
  targets while building a fresh inventory pack.
- `scripts/summarize_core_ufunction_inventory.py::target_set_regeneration_plan(...)`
  covers named target sets, but it plans `regenerate_ufunction_snapshots.py` against the
  committed snapshot manifest. That is fixture/manifest oriented and rejects unknown
  targets, so it is not the missing pre-target-set focal batch mode.
- `scripts/regenerate_ufunction_snapshots.py` is correct for committed manifest entries
  and named target sets after review. It is not the first planner for a reviewed closed
  list that intentionally has no target set or fixture yet.
- `scripts/compare_reflection_snapshots.py` is the second-source layout/readiness gate.
  It should remain downstream of focal snapshot extraction, not become a planner.
- `scripts/compare_reflection_inventory_packs.py` already compares two redacted
  inventory packs and enforces distinct artifact identity, but its schema is not yet
  accepted by `scripts/validate_offline_artifact_gate.py`.

## Fastest Safe Implementation

Add a small planner that consumes an already built reflection inventory pack plus a
reviewed exact target list, then reuses the existing focal planner logic to emit one
candidate-only `inspect_core_ufunctions.py --snapshot-json` command per target.

Current bridge: `scripts/build_reflection_inventory_pack.py` now supports
`--plan-snapshot-target-set` for closed UFunction target sets while building a fresh
inventory pack. The standalone planner below remains the preferred follow-up when we need
to plan from an already reviewed inventory pack without rereading a core.

Preferred patch shape:

1. Extract these helpers from `scripts/build_reflection_inventory_pack.py` into a new
   `scripts/ufunction_focal_snapshot_plan.py` module:
   - `parse_exact_target`
   - `plan_output_filename`
   - `focal_snapshot_plan`
2. Update `scripts/build_reflection_inventory_pack.py` to import the shared helpers so
   the existing `--plan-target` behavior and tests stay intact.
3. Add `scripts/plan_ufunction_focal_snapshots.py` with:
   - `--inventory-pack <dir-or-manifest>` to read `manifest.json` and
     `ufunction-inventory.json`.
   - repeatable `--target Outer.Name` and `--target-file <newline-list>` inputs.
   - optional `--json-out <path>`; default stdout is enough for review.
   - no core reads, no snapshot writes, no server access, no command execution.
4. Validate the pack before command emission:
   - manifest schema is `obelisk.reflection-inventory-pack.v1`;
   - status is `candidate-only`;
   - promotion status is `not_promoted_candidate_only`;
   - `artifact_identity` includes `offline_core`, `artifact_sha256`, `capture_id`, and
     `evidence_pack_id`;
   - `binary.sha256`, `core.sha256`, `core.path`, `addresses.gobjects`, and
     `addresses.fname_root_slot` are present and parseable;
   - `summary.fname_root_ready` is true;
   - manifest `blockers` is empty;
   - manifest and core paths pass protected-path and symlink checks before being copied
     into planned commands;
   - inventory function rows are redacted rows only, with the same field policy as
     `compare_reflection_inventory_packs.py`.
5. Feed the validated rows and identity fields into the shared `focal_snapshot_plan(...)`.
   Keep `inventory_source` as `accepted_redacted_inventory_pack` or add a wrapper field
   identifying the pack path and target-list source.

This is safer and faster than adding another mode to
`run_second_source_core_intake.py`: the wrapper is intentionally target-set and
regeneration/comparison oriented, while the missing step is pre-target-set focal command
planning from reviewed inventory.

## Tests To Add

- `scripts/test_plan_ufunction_focal_snapshots.py`
  - accepts a minimal candidate-only pack and emits two planned commands from
    `--target-file`;
  - preserves complete artifact identity and does not emit `--target-set`;
  - blocks a missing target without inventing a fixture or manifest entry;
  - blocks ambiguous duplicate inventory rows for the same `Outer.Name`;
  - rejects duplicate target inputs after schema normalization;
  - rejects `fname_root_ready=false` or non-empty pack blockers;
  - rejects incomplete artifact identity, invalid SHA fields, protected core paths, and
    symlinked pack/core path components.
- Existing coverage to keep green:
  - `scripts/test_build_reflection_inventory_pack.py`
  - `scripts/test_compare_reflection_inventory_packs.py`
  - focused `scripts/test_compare_reflection_snapshots.py` readiness/guidance tests.

## Optional Follow-Up

Add consume-mode support for
`obelisk.reflection-inventory-pack-comparison.v1` in
`scripts/validate_offline_artifact_gate.py` after the planner lands. That is useful
indexing/planning hygiene, but it is not required to emit focal snapshot commands.

## Risks And Non-Claims

- A planned target is not a snapshot, layout acceptance, second-source evidence, target
  set coverage, release readiness, runtime readiness, or SDK readiness.
- Inventory-pack agreement does not promote public GObjects, UObject identity, lookup,
  mutation, return override, raw params, or `ResourceHandle`.
- The planner must not treat target files as public target sets. A target file is a
  reviewed local batch input only.
- The planner should not hash or parse large cores while planning; the inventory pack is
  the reviewed input. The emitted commands will perform focused extraction later.
- Any generated focal snapshot still needs redaction review and a distinct
  second-source comparison before layout claims.
