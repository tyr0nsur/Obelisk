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

## Bridge Audit

The `--plan-snapshot-target-set` bridge matches this design's narrow bridge role: it
expands named UFunction target sets into exact `Outer.Name` requests, keeps
`manifest.inputs.target_sets=[]`, records the requested planning set separately under
`manifest.inputs.plan_snapshot_target_sets`, and reuses `focal_snapshot_plan(...)` so the
output remains candidate-only and emits `inspect_core_ufunctions.py --snapshot-json`
commands rather than `--target-set` regeneration commands.

The main test gap was bridge-specific success coverage. Existing tests covered ad hoc
`--plan-target` success, target-set missing-target blocking, duplicate normalization, and
offline-core identity gates, but not a named target set that actually plans a command from
the unfiltered redacted inventory while the visible inventory output is filtered. Added
coverage in `scripts/test_build_reflection_inventory_pack.py` now pins that behavior.

Decision: do not keep expanding the bridge before the next implementation step. The bridge
is adequate as a fresh-pack convenience path; the next useful implementation remains the
standalone `scripts/plan_ufunction_focal_snapshots.py` that consumes an already reviewed
reflection inventory pack without rereading a core.

Implemented patch shape:

1. `scripts/ufunction_focal_snapshot_plan.py` remains the shared candidate-only helper
   module used by fresh-pack planning and standalone planning.
2. `scripts/build_reflection_inventory_pack.py` continues to import the shared helpers,
   preserving existing `--plan-target` and `--plan-snapshot-target-set` behavior.
3. Added `scripts/plan_ufunction_focal_snapshots.py` with:
   - `--inventory-pack <dir-or-manifest>` to read `manifest.json` and
     `ufunction-inventory.json`.
   - repeatable `--target Outer.Name` and `--target-file <newline-list>` inputs.
   - optional `--json-out <path>`; default stdout is enough for review.
   - no core reads, no snapshot writes, no server access, no command execution.
4. The standalone planner validates the pack before command emission:
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
5. The validated rows and identity fields feed into shared `focal_snapshot_plan(...)`.
   The emitted payload changes `inventory_source` to `accepted_redacted_inventory_pack`
   and records the pack manifest, `ufunction-inventory.json`, target file paths, and
   loaded target count for review traceability.

The script intentionally does not hash, parse, mmap, or otherwise reread the core. It
checks that the recorded core path is offline-safe and non-symlinked before placing that
path into the planned command argv. Missing core files are not blockers at planning time;
snapshot extraction remains a separate later step.

This is safer and faster than adding another mode to
`run_second_source_core_intake.py`: the wrapper is intentionally target-set and
regeneration/comparison oriented, while the missing step is pre-target-set focal command
planning from reviewed inventory.

## Tests Added

- `scripts/test_plan_ufunction_focal_snapshots.py`
  - accepts a minimal candidate-only pack with a missing core path and emits two planned
    commands from
    `--target-file`;
  - preserves complete artifact identity and does not emit `--target-set`;
  - blocks a missing target without inventing a fixture or manifest entry;
  - blocks ambiguous duplicate inventory rows for the same `Outer.Name`;
  - rejects duplicate target inputs after schema normalization;
  - rejects `fname_root_ready=false` or non-empty pack blockers;
  - rejects incomplete artifact identity, invalid SHA fields, protected core paths, and
    symlinked pack/core path components.
  - rejects non-redacted inventory rows with extra keys.
- Existing coverage to keep green:
  - `scripts/test_build_reflection_inventory_pack.py`
  - `scripts/test_compare_reflection_inventory_packs.py`
  - focused `scripts/test_compare_reflection_snapshots.py` readiness/guidance tests.

## Optional Follow-Up

Add consume-mode support for
`obelisk.reflection-inventory-pack-comparison.v1` in
`scripts/validate_offline_artifact_gate.py` after the planner lands. That is useful
indexing/planning hygiene, but it is not required to emit focal snapshot commands.

### 2026-05-31 Gate Readiness Check

Decision: keep this follow-up documented; do not implement gate support yet. The
producer schema exists in `scripts/compare_reflection_inventory_packs.py`, but the
preferred standalone planner for consuming an already reviewed pack has not landed, so
adding the comparison schema to the artifact gate now would create an accepted indexing
surface before the consuming workflow is complete.

Required guardrails before implementation:

- consume mode accepts only `status=accepted` with empty `blockers`,
  `promotion_status=not_promoted_candidate_only`, matching base/candidate binary SHA,
  distinct `artifact_identity` fields, and no missing/new/changed function rows;
- promote mode always blocks this schema as candidate-only planning hygiene;
- `base.pack` and `candidate.pack` must be checked as offline workspace paths, not just
  scanned as generic strings;
- required non-claims must preserve the existing boundaries: no runtime-stable GObjects,
  no UObject pointers/raw params/object identity/mutation/return override, and no
  replacement for strict per-target snapshot readiness reports;
- tests should cover accepted consume mode, blocked comparison status, promote-mode
  rejection, protected-path pack references, identity reuse, binary mismatch, and
  missing/new/changed rows.

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
