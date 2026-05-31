# FName/GObjects Offline Route

Date: 2026-05-31
Obelisk commit reviewed: `81bd839`

## Scope

Inspect the current `FName` / `GNames` / `GObjects` state and identify the fastest
offline-only path toward general reflected `UFunction` parameter decoding without
repeating broad FName, GObjects, core, server, ReflectionScanner, ptrace, or `gcore`
work.

This pass only read repository files and script help text. It did not read or write
`/servidor/ark`, run server tools, run ReflectionScanner, attach to a process, create a
core, commit, tag, push, or use Discord.

## Evidence Consulted

- `docs/agent-handoff/CURRENT.md`: current routing says public `GObjects`,
  `ResourceHandle`, lookup, identity, mutation, return override, and broad raw
  `ProcessEvent` remain blocked. It also says not to rerun broad FName/GObjects/core
  scans for the current binary unless evidence is contradicted or the binary hash changes.
- `docs/research/2026-05-27-static-fname-root-candidate.md` and
  `docs/research/2026-05-27-arkserver-core-fname-evidence.md`: static/runtime evidence
  established the binary-scoped FName root slot `0x5956f30`, with corrected clues
  `None=0`, `ClientMessage=4884`, `ServerChat=9619`, and
  `SetActiveMissionDebugFlags=9622`.
- `docs/research/2026-05-29-gobjects-fuobjectarray-durable-pack.md`: durable internal
  pack records `GObjects` / `GUObjectArray` candidate `0x595b7e0`, a 10-sample
  reconciliation, and static context. It is useful internal evidence but pre-strict
  identity for some gate uses.
- `docs/research/2026-05-29-gobjects-second-core-reconciliation.md` and
  `docs/research/2026-05-29-gobjects-cross-manifest-comparison.md`: second copied core
  accepts the same `0x595b7e0` candidate for sampled objects; manifest comparison agrees
  across existing `gobjects-sampling` packs and reduces the value of repeating discovery.
- `docs/research/2026-05-30-gobjects-strict-consume-recapture-needed.md`: strict
  consume-mode GObjects manifest must be rebuilt durably with complete `artifact_identity`
  when writes to the offline workspace are explicitly allowed. The candidate remains
  consume-only and promote-blocked.
- `docs/research/2026-05-27-ufunction-membership-backrefs.md`: `inspect_core_ufunctions.py`
  validates target/class/outer/property membership by direct `GObjects[InternalIndex]`
  back-reference checks, not broad address-to-index scans.
- `docs/research/2026-05-29-reflection-inventory-pack-smoke.md`: existing tooling can
  build and compare candidate-only reflection inventory packs from two offline cores.
  Both reported `fname_root_ready=true`, `function_count=5269`, and no inventory drift
  for the tested target sets.
- `tests/fixtures/ufunction_snapshots/README.md` and
  `tests/fixtures/ufunction_snapshots/manifest.json`: sanitized UFunction snapshots are
  the current durable shape for reflected property-chain evidence. The manifest is mixed
  RC/internal/post-RC evidence and must be consumed by named target set, not as a whole.
- Script interfaces reviewed with `PYTHONDONTWRITEBYTECODE=1 --help`:
  `scan_core_fname_tables.py`, `build_reflection_inventory_pack.py`,
  `summarize_core_ufunction_inventory.py`, `inspect_core_ufunctions.py`,
  `regenerate_ufunction_snapshots.py`, `compare_reflection_snapshots.py`,
  `build_redacted_ufunction_signatures.py`, and `run_second_source_core_intake.py`.
- `scripts/reflection_target_sets.py`: current closed target sets already cover chat,
  inventory/items, structures, missions, dinos, tribes, transfers, buffs, and planning-only
  player identity/lifecycle.
- `ue/RuntimeReflection.h`: runtime/internal reader already has the binary-scoped layout
  offsets needed to bound decoding by `UFunction::ParmsSize` and `UProperty` offsets.

## Current State

For the current ARK Linux binary hash
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, the fastest path
does not start with more discovery. The useful inputs are already known for offline
reflection:

- FName root slot: `0x5956f30`.
- GObjects candidate: `0x595b7e0`.
- Two copied cores have accepted point checks for the GObjects candidate.
- Existing snapshot tooling can resolve UFunction names, outers, `NumParms`, `ParmsSize`,
  return offsets, property names/classes, property offsets/sizes/flags, BoolProperty tail
  metadata, and direct candidate-UObject membership.

The accepted evidence is still candidate/internal unless a target-set-specific gate says
otherwise. It does not promote public GObjects, object identity, ResourceHandle, lookup,
mutation, return override, raw params, or UE pointer access.

## 2026-05-31 Static Field-Window Refresh

A bounded offline Ghidra/radare2 refresh was run against the non-protected offline binary
copy under `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/`, with raw output
kept under `/tmp`. No server, dump, `ReflectionScanner`, ptrace, `gcore`, Discord, GitHub,
or `/servidor/ark` path was touched.

Strict output root:

```text
/tmp/obelisk-static-global-field-window-strict-20260531T040157
```

Validation result:

```text
static-global consume gate: accepted
static-global blockers: []
artifact identity sha256: b2929c5061aefdf3cfd24c9a8c42b27490edb89b551dff1a3d544b4da42a9113
manifest file sha256: bcc44f2b0a007deb50f1605eb78c771834d6739bb7e6ced732e58e6cbe197edc
field-window sha256: 86957b02e41445595c5082d192fe4988b12397913336d099d3f68b079fdafc1e
fname_root fields: root_slot
gobjects fields: chunks, count, root, serial
```

This clears the static coherent field-window blocker for the reviewed `gobjects`
candidate in consume-mode static evidence only. The gate now has a minimal durable
artifact-pack shape for the redacted FUObjectArray field-window child manifest:
`obelisk.fuobjectarray-field-window-redacted.v1` is accepted only with redacted
binary/candidate fields, both static source hashes, same-base evidence, required
`root/chunks/count/serial` field coverage, `promotion_gate_ready=false`, and no absolute
path strings. It still does not promote public `GObjects`, `ResourceHandle`, object
identity, lookup, mutation, return override, runtime hooks, or any SDK surface.

Follow-up audit confirmed the blocker is the pack schema, not local tooling. `radare2`,
`r2`, and Ghidra `analyzeHeadless` are available on the machine, while `rizin` remains
optional. A durable pack must regenerate pack-relative child manifests.
Copying the `/tmp` manifest tree into a normalized pack is not enough because unknown `obelisk.*`
child schemas and absolute scratch paths remain fail-closed blockers. This turn only
teaches the offline artifact gate how to consume the field-window schema; gate-result and
provenance child manifests remain blocked with `unsupported_manifest_schema` until they
have their own schema-specific validators.

The same field-window evidence was re-materialized under the durable non-protected
artifact root:

```text
/home/flowcommunity-ark/obelisk-artifacts/static-global-field-window-strict-20260531T040157Z
```

Refresh result:

```text
static-global consume gate: accepted
static-global blockers: []
artifact identity sha256: b2929c5061aefdf3cfd24c9a8c42b27490edb89b551dff1a3d544b4da42a9113
promotion_gate.ready: false
```

This refresh is hygiene for static global evidence only. It still does not satisfy the
current `v1.0` SDK blockers, does not replace a complete core evidence pack or reflection
inventory pack, and does not promote public `GObjects`, `ResourceHandle`, identity,
lookup, mutation, return override, runtime hooks, or SDK surface.

## Fastest Offline Route

1. Do not rerun broad FName/GObjects scans for the current binary. If the artifact already
   has reviewed globals, pass `--fname-root-slot 0x5956f30` and `--gobjects 0x595b7e0`
   explicitly. If an artifact-specific root must be checked, use direct root validation
   only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/scan_core_fname_tables.py \
  --core <offline-core> \
  --root-slot 0x5956f30 \
  --require-exact-root \
  --index None=0 \
  --index ClientMessage=4884 \
  --index ServerChat=9619 \
  --index SetActiveMissionDebugFlags=9622 \
  --json
```

2. Build a candidate-only reflection inventory from a complete non-protected evidence-pack
   manifest, or from an explicitly copied offline core. This gives a redacted list of
   resolved UFunctions without exposing pointers:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest <complete-non-protected-pack>/manifest.json \
  --target-set <closed-target-set> \
  --include-functions \
  --output-dir <ignored-non-protected-output>/inventory-pack
```

3. For a concrete UFunction family, generate sanitized snapshots instead of raw param
   probes. Use a named target set when it exists:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/regenerate_ufunction_snapshots.py \
  --core <offline-core> \
  --gobjects 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --artifact-kind offline_core \
  --artifact-sha256 <offline-core-sha256> \
  --capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-pack-id> \
  --target-set <closed-target-set> \
  --output-root <ignored-non-protected-output>/ufunction-snapshots \
  --write
```

4. Compare against a distinct second-source snapshot root before accepting layout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <second-source-output>/ufunction-snapshots \
  --target-set <closed-target-set> \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

5. Convert accepted sanitized snapshots into redacted signature metadata for decoder
   planning, not public SDK promotion:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_redacted_ufunction_signatures.py \
  --snapshot-root <accepted-snapshot-root> \
  --target-set <closed-target-set> \
  --json
```

This is the shortest route to reflected parameter decoding because it uses the existing
metadata chain:

`FName root -> GObjects membership -> UObject/UClass/UStruct -> UFunction -> UProperty chain -> ParmsSize-bounded parameter ranges`.

## Blockers

- Durable strict GObjects consume evidence is stale by current artifact-identity rules.
  `2026-05-30-gobjects-strict-consume-recapture-needed.md` records the exact rebuild
  command, but this turn was not allowed to write `/servidor/ark/workspace-offline`.
- Some existing notes and manifests reference `/servidor/ark/workspace-offline` artifacts.
  They are useful evidence records, but this task could not dereference those paths.
- General parameter decoding still needs target-set discipline. A full unfiltered
  UFunction property-chain dump would be easy to misuse as broad discovery; the safer
  route is closed target sets plus exact ad hoc `--plan-target` for one-off candidates.
- Public runtime use remains blocked by copied-data ABI, callback lifecycle, privacy,
  installed SDK consumer coverage, approved runtime validation, and explicit no-mutation /
  no-return-override policy. More offline GObjects samples do not clear those blockers.
- `ResourceHandle` remains blocked on lifecycle/reuse/rejection semantics. The path above
  can unlock reflected parameter layouts, not public object lookup or persistent handles.

## Exact Tooling Gaps

1. The focal snapshot planner now exists as `scripts/plan_ufunction_focal_snapshots.py`.
   Use it after an accepted reflection inventory pack to emit exact
   `inspect_core_ufunctions.py --snapshot-json` commands for reviewed targets with
   complete evidence identity. Keep using explicit target names for one-off candidates;
   do not treat broad name searches or partial inventories as accepted layout evidence.

2. Add a consume-only gate/report for `obelisk.reflection-inventory-pack-comparison.v1`.
   `compare_reflection_inventory_packs.py` already compares two packs, but the offline
   artifact gate should be able to index the report as planning evidence while keeping it
   promote-blocked.

3. Rebuild the strict durable two-core GObjects manifest only in a future turn that
   explicitly allows offline-workspace writes. Use the existing command from
   `2026-05-30-gobjects-strict-consume-recapture-needed.md`; do not scan again.

4. For any new broad module family, create a small closed target set in
   `scripts/reflection_target_sets.py` only after an inventory pack proves exact names
   exist once. Then use snapshot regeneration/comparison. Do not use `--name-contains`
   output as accepted layout evidence.

## Decision

The fastest offline-only unlock is not another FName/GObjects discovery pass. It is a
strict, target-set-driven snapshot pipeline over the already evidenced `0x5956f30` /
`0x595b7e0` pair, followed by redacted signature generation and decoder planning bounded
by reflected `ParmsSize`.
