# UFunction Snapshot Fixtures

Sanitized `UFunction` property-chain snapshots live here as versioned evidence for
offline analyzer behavior. The committed set is listed in `manifest.json` and can be
regenerated from an existing offline core with:

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core <offline-core-path> \
  --obelisk-commit <obelisk-commit> \
  --artifact-kind offline_core \
  --artifact-sha256 <core-or-evidence-artifact-sha256> \
  --capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-evidence-pack-id> \
  --write
```

Omit `--write` for a dry-run, or use `--check` to compare regenerated output against the
committed fixtures without modifying files. Dry-run, check, layout-check, and write modes
all require complete evidence identity: `--artifact-kind`, `--artifact-sha256`,
`--capture-id`, and `--evidence-pack-id`, or `--evidence-pack-manifest` so the tool can
derive those fields. For second-core regeneration where the evidence commit or
capture-specific identity indices naturally differ, use `--check-layout` with the full
artifact identity and explicit `--fname-root-slot` to compare only target identity,
UFunction fields, and property-chain layout. Use `--target Outer.Function` to regenerate
or check one manifest entry.
The artifact fields are sanitized identifiers used by the comparator to mark
self-comparison, shared artifact identity, or missing second-source identity as
`inconclusive`; do not store absolute core paths here. A valid second source must use a
distinct `artifact_sha256`, `capture_id`, and `evidence_pack_id`. Regeneration accepts
only `artifact_kind=offline_core` and rejects placeholder capture or evidence-pack IDs so
new snapshots do not enter compare/RC gates as permanently inconclusive evidence.

Compare sanitized snapshot layouts between two evidence roots with:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module> \
  --candidate-root /path/to/second-source/ufunction_snapshots/<ark-sha12>/<sdk_module> \
  --target Outer.Function \
  --json
```

The comparator ignores unstable FName/GObjects indices by default. Use
`--strict-identity-indices` only for intentional same-binary identity checks.

For the current player-principal lifecycle blocker, verify only the distinct sanitized
two-target lifecycle root with:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <distinct-sanitized-lifecycle-root> \
  --lifecycle-snapshot-root-check \
  --json
```

That mode consumes sanitized `obelisk.ufunction-chain.snapshot.v1` files only for
`ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`. It requires complete
offline-core identity (`ark_binary_sha256`, `artifact_kind=offline_core`,
`artifact_sha256`, `capture_id`, and `evidence_pack_id`) and distinct artifact identity
from the base fixtures. It rejects protected live-server paths, passive player-principal
manifests, ReflectionScanner/broad scanner outputs, and layout-only comparison/readiness
reports. A passing lifecycle-root check is property-shape planning evidence only and does
not clear `approved_runtime_evidence_missing` or promote runtime/public SDK readiness.

This two-target check is deliberately narrower than the `players-lifecycle-anchor-candidates`
planning target set. The current approved player-principal lifecycle triplet source policy
is exactly `ShooterGameMode.HandleNewPlayer`, `ShooterGameMode.CheckJoinInProgress`, and
`ShooterGameMode.OnLogout`: `HandleNewPlayer` and `OnLogout` are the static lifecycle
anchor sources, while `CheckJoinInProgress` is only the rejected-start observer/triplet
source. `GameMode.K2_PostLogin` stays non-anchor chronology context, including property
FName mismatch diagnostics, and the all-six planning gap remains non-evidence until a
separate durable non-protected snapshot root is reviewed through the non-promotional
planning-layout path.

Minimal lifecycle candidate root contract:

```text
<distinct-sanitized-lifecycle-root>/<ark-sha12>/players_lifecycle/ShooterGameMode.HandleNewPlayer.snapshot.json
<distinct-sanitized-lifecycle-root>/<ark-sha12>/players_lifecycle/ShooterGameMode.OnLogout.snapshot.json
```

Each file must be a sanitized `obelisk.ufunction-chain.snapshot.v1` payload with exactly
one `targets[]` entry, `evidence.source=offline_core`,
`evidence.status=candidate-only`, `evidence.generated_by` set to
`scripts/inspect_core_ufunctions.py --snapshot-json`, complete offline-core artifact
identity, `target.membership` values of `candidate-uobject`, target
`status=candidate`, property-chain `status=candidate`, and per-property target/class/
outer membership values of `candidate-uobject`. For these two lifecycle anchors the
semantic comparison intentionally checks outer/name/class, `NumParms`, `ParmsSize`,
`ReturnValueOffset`, property order, property classes, offsets, element sizes, array
dims, flags, and bool metadata, while ignoring unstable FName/object identity indices.

Do not commit a synthetic duplicate `.snapshot.json` lifecycle candidate under this base
fixture root merely to exercise the check: the comparator recursively loads
`*.snapshot.json` files and would see duplicate `ShooterGameMode.HandleNewPlayer` and
`ShooterGameMode.OnLogout` targets when `--base-root tests/fixtures/ufunction_snapshots`
is used. For a comparator-only smoke test, copy the two committed lifecycle snapshots to
a temporary or separate offline candidate root and change only the artifact identity to a
distinct sanitized value. Such a smoke test is not evidence; real blocker closure still
requires a distinct non-protected offline artifact.

Before a second evidence root exists, summarize current fixture coverage and the remaining
second-source gap with a named target set:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set minimal-second-source-intake
```

Use `--json` with readiness reports when creating evidence packs. The JSON includes
per-module `target_details` entries with each target key, fixture path, comparability,
block reasons, second-source status, and a top-level `promotion_gate` summary with a
boolean `ready` value plus blocker counts. Target-set entries missing from the base root
are `not_applicable` for second-source status and block the gate as missing base coverage.
Named target-set readiness reports also carry `target_set_coverage`, derived from the
same per-target details. The offline artifact gate rejects reports that omit it or whose
coverage disagrees with the named set, the observed target details, or the catalog in
`scripts/reflection_target_sets.py`; passing this check remains layout evidence only.

When building redacted signatures from direct `--snapshot` inputs, add
`--source-target-set <name>` only when the snapshots exactly cover that named set. Direct
snapshot reports without `--source-target-set` are valid ad hoc review artifacts, but
their `target_set_coverage` is `not_declared`/`complete=false` and must not be cited as
exact target-set coverage.
Reports that do claim exact named coverage must also carry redacted `artifact_identity`
derived from complete snapshot evidence (`ark_binary_sha256`, `artifact_sha256`,
`capture_id`, and `evidence_pack_id`). The offline artifact gate rejects coverage that is
declared only inside `target_set_coverage`, coverage metadata that contradicts
`exact_coverage`/`coverage_scope`/`blockers`, and named redacted-signature artifacts with
missing source evidence IDs. New redacted-signature reports also bind each
`generated_from.input_snapshots[]` hash to the target or targets read from that snapshot;
strict or named target-set gate checks reject missing bindings, swapped source-snapshot
targets, and stale coverage that no longer matches emitted signatures.
The builder rejects duplicate `--target-set` and `--source-target-set` values instead of
deduplicating them silently, and the consume gate requires current
`target_set_revision_source_sha256` metadata for named coverage. Candidate artifacts that
carry positive `ResourceHandle`, GObjects lookup/identity, lookup availability, mutation,
or return-override wording are blockers even when the rest of the payload remains
candidate/consume-only.

When this readiness report is acting as a promotion gate, add
`--fail-on-readiness-gaps` or run
`scripts/check_release_readiness.sh --require-second-source-readiness`.

To inspect copied-scalar candidates from committed snapshots without reading cores or
touching servers, use:

```bash
python3 scripts/summarize_reflection_scalar_candidates.py \
  --target-set mission-compact-intake
```

This helper is a review aid only. It classifies one-byte `BoolProperty` candidates as
copyable and keeps object, array, string, and struct fields redacted; it does not replace
second-source readiness reports or promote public SDK callbacks. It is not a release
readiness gate, not RC scope, and the `mission-compact-intake` example remains
candidate-only until an explicit promotion PR names that target set with accepted
second-source evidence and SDK guardrails.

List the named target sets used by focused readiness checks with:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
```

Current reflection snapshot target sets are defined in `scripts/reflection_target_sets.py`.
The comparator runs a fail-closed target-set catalog hygiene preflight before listing,
expanding, comparing, or reporting readiness for named sets. That preflight rejects
duplicate entries within a set, malformed or unsupported schema-qualified targets,
mixed UFunction/ScriptStruct schemas inside a single named set, missing module-lane
metadata, and conflicting readiness classifications. Treat those failures as offline
catalog fixes in `scripts/reflection_target_sets.py`; do not answer them with broad
FName/GObjects scans or runtime evidence collection.
Comparison commands also reject duplicate or unknown `--target-set` filters before they
load snapshot roots, so accidental set deduplication cannot hide stale or mismatched
coverage.
The `--list-target-sets` and `--list-target-guidance` modes are catalog/guidance outputs
only; they do not read snapshots and explicitly report that they are not second-source
layout evidence, runtime readiness, public SDK readiness, release readiness, or `v1`
completion evidence.
Snapshot inputs that include positive public/runtime aliases such as `public_sdk_ready`,
`runtime-ready`, `ResourceHandle` readiness, object/item identity, lookup, mutation, or
return-override claims are blocked as non-reusable evidence even if their layout fields
match. Direct or symlinked protected live-server paths are also rejected before loading
snapshot JSON.
JSON artifacts presented through the generic artifact path must use an allowlisted gate
schema; a valid provenance sidecar alone does not make an unknown scan schema reusable.
Provenance sidecars and embedded provenance are also scanned for protected-root strings or
relative paths that resolve into the protected root.
`scripts/check_release_readiness.sh --require-second-source-readiness` automatically
gates the public RC UFunction backing sets below, even when they are not supplied
explicitly:

- `minimal-second-source-intake`: first inventory/structure layout backing for copied
  `GameplayPolicyEvent` policy fields. This is layout evidence only and does not promote
  a public Inventory or StructureEvents SDK.
- `structure-observer-intake`: all six structure observer UFunctions used as layout
  backing for copied/redacted `GameplayPolicyEvent` fields. This does not promote raw
  structure callbacks, object identity, mutation, or return overrides.
- `item-return-only-policy-slice`: the three item return-only UFunctions used as layout
  backing for copied `GameplayPolicyEvent` `ReturnValue` fields. This does not promote an
  Inventory SDK, Items SDK, item identity, lookup, mutation, or return override authority.
- `chat-message-intake`: `ShooterPlayerController.ServerSendChatMessage`, the layout
  backing for the minimal copied `ChatMessageEvent` RC/public callback. This covers the
  copied notification contract only, not command routing, sender identity, moderation,
  raw `FString` storage, mutation, or return override.

Internal or RC-excluded UFunction target sets require explicit
`--ufunction-second-source-target-set` selection and do not replace the public RC backing
sets:

- `buff-compact-intake`: compact `PrimalBuff` bool/scalar shapes for internal research.
- `buff-breadth-intake`: broader `PrimalBuff` inventory/add/prevent shapes for internal
  research.
- `dino-compact-intake`: compact dino passenger/carry shapes for internal research.
- `mission-compact-intake`: compact mission lifecycle and usable-item targets. Scalar
  summaries are review aids only and are not RC scope.
- `tribe-compact-intake`: compact tribe/admin-adjacent identity and log targets.

Post-RC layout-only target sets are accepted as offline fixture/comparison evidence only
unless a later focused promotion gate explicitly changes release scope:

- `item-compact-intake`: compact `PrimalItem` policy/action layouts.
- `inventory-action-compact-intake`: compact inventory-use request layouts.
- `transfer-ufunction-intake`: transfer upload/download and validation layouts; no public
  Transfer SDK, runtime hook, payload decoding, identity, mutation, or return override is
  promoted by this target set.

The comparator's promotion mode (`--readiness-report --fail-on-readiness-gaps`) only
accepts the release-readiness backing target sets listed above. Internal/general v1
target sets such as players, tribes, dinos, buffs, transfers, structures, and missions
may have accepted second-source layout comparisons, but the gate still reports
`target_set_not_release_readiness`; use `--list-target-guidance --target-set <name>` for
offline blocker guidance.

Manifest-backed snapshots may also exist outside release-readiness target sets.
`PrimalInventoryComponent.InventoryCustomFilter` is committed in `manifest.json` and is
named only by the planning-only `inventory-custom-filter-array-boundary` target set in
`scripts/reflection_target_sets.py`. It is candidate-only ArrayProperty metadata, not
Inventory SDK, public API, runtime, mutation, return override, ResourceHandle, or
release-readiness scope.

## RC Checkpoint Scope

`manifest.json` is a mixed fixture inventory. It contains RC backing targets, internal
research targets, and post-RC candidates, all as sanitized snapshot evidence. Do not cite
the whole manifest as RC readiness evidence. RC readiness is target-set-scoped and must
come from the release gate target sets above plus an accepted second-source comparison.
The RC second-source root assembler also requires complete snapshot evidence identity
before it writes a manifest, so an assembled root cannot hide partial artifact identity
until a later promotion gate.

Snapshot fields such as `object_index`, `name_index`, `class_object_index`, and target
identity values are correlation fields for comparing sanitized snapshots. They are not
stable object identity, public `ResourceHandle` evidence, UE lookup evidence, lifecycle
proof, or proof that all FNames/UFunctions are known.

Naming:

```text
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.snapshot.json
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.rejected.snapshot.json
```

These fixtures must not contain core paths, server paths, absolute object addresses,
pointer windows, integer windows, raw logs, player data, or native function pointers. Keep
one target per file so review diffs stay small.
