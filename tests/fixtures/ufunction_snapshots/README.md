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

Current UFunction target sets are defined in `scripts/reflection_target_sets.py`.
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

Manifest-backed snapshots may also exist outside any current named target set.
`PrimalInventoryComponent.InventoryCustomFilter` is committed in `manifest.json`, but it
does not currently belong to any named target set in `scripts/reflection_target_sets.py`.

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
