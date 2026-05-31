# Player Identity Offline Pack Preflight

This note records the current offline preflight for closing the two remaining
`players-identity-lifecycle-intake` snapshot gaps without touching a live server.

## Result

No usable `obelisk.reflection-inventory-pack.v1` manifest was found under the current
non-protected durable artifact root:

```bash
python3 scripts/check_reflection_inventory_pack_readiness.py \
  --root /home/flowcommunity-ark/obelisk-artifacts
```

For the complete read-only player-identity lane preflight, use:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_first_evidence_readiness.py \
  --artifact-root /home/flowcommunity-ark/obelisk-artifacts
```

This wrapper combines reflection-inventory readiness, committed fixture coverage, and
the fail-closed `obelisk.players-identity-first-evidence.v1` build attempt. It writes no
artifacts, touches no servers, and must keep reporting candidate-only/planning-only
non-claims even if the first evidence pack becomes buildable.
When a distinct sanitized second-source root exists, pass it explicitly:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_first_evidence_readiness.py \
  --artifact-root /home/flowcommunity-ark/obelisk-artifacts \
  --candidate-root <distinct-sanitized-second-source-root>
```

The wrapper reports missing second-source evidence separately from compared-but-rejected
or compared-but-inconclusive second-source evidence, so a present but unusable candidate
root cannot be mistaken for accepted layout evidence.

The checker is read-only and emits
`schema=obelisk.reflection-inventory-pack-readiness-check.v1`. It fails closed with
machine-readable reasons: `missing_reflection_inventory_pack`,
`artifact_pack_container_not_reflection_inventory`,
`scriptstruct_pack_not_reflection_inventory`, `schema_mismatch`,
`missing_core_evidence_pack`, `missing_ufunction_inventory`, `wrong_target_scope`, or
`missing_target`. It also accepts `--json` as a compatibility flag; JSON output is the
default either way.

For operator-facing summaries, the report now includes compact top-level readiness
boundaries:

- `accepted_for_candidate_planning=<bool>`;
- `promotion_ready=false`;
- `public_sdk_ready=false`;
- `runtime_ready=false`;
- `next_step=<compact_next_step>`;
- `operator_next_step.server_access_required=false`;
- `operator_next_step.summary=<candidate-only boundary>`.

When a reflection inventory pack is accepted, that acceptance means only
candidate-only focal snapshot planning. It is not player identity promotion, Inventory
SDK promotion, public SDK promotion, runtime identity readiness, lookup readiness, or
`ResourceHandle` readiness.

Current result:

- `status=blocked`;
- `ready=false`;
- `manifests_scanned=16`;
- `reason=missing_reflection_inventory_pack`;
- `reason=artifact_pack_container_not_reflection_inventory`;
- `reason=scriptstruct_pack_not_reflection_inventory`;
- `reason=schema_mismatch` for the static-global preflight manifest;
- `accepted_pack=null`.

The combined preflight currently reports:

- `reflection_inventory.ready=false`;
- `fixture_coverage.targets=12`;
- `fixture_coverage.comparable=10`;
- `fixture_coverage.blocked=2`;
- `first_evidence.ready=false`;
- `first_evidence.missing_required_targets=[ServerKickPlayer, ServerListPlayers]`;
- `next_step=produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack`.

It also emits a top-level `progress_signal` field for leads/operators who need the
current blocker without reading the whole report. The field is only a compact rendering
of existing gates:

- `progress_signal.coverage.fixture_targets=10/12`;
- `progress_signal.coverage.reflection_inventory_accepted=false`;
- `progress_signal.missing.required_targets=[ServerKickPlayer, ServerListPlayers]`;
- `progress_signal.accepted_anchors.session_start=false`;
- `progress_signal.accepted_anchors.session_end=false`;
- `progress_signal.primary_blocker=<next_actionable_blocker.code>`.

If a matching non-protected `ShooterGameServer` is present but the non-protected core
input is absent, `progress_signal.primary_blocker` reports
`non_protected_core_input_missing` and the top-level `status` remains `blocked`.
The signal must not be read as progress beyond the underlying fail-closed checks.

The durable root currently contains normalized artifact packs and a ScriptStruct inventory
pack, but no UFunction reflection-inventory pack with
`schema=obelisk.reflection-inventory-pack.v1`. That means the next player-identity
snapshot step cannot be planned from `/home/flowcommunity-ark/obelisk-artifacts` alone.
It also does not currently contain a non-protected
`obelisk.core-dump-evidence-pack.v1` manifest that can be passed directly to
`scripts/build_reflection_inventory_pack.py`; the current durable root by itself is
therefore not enough to produce the missing UFunction inventory pack.

## V1 SDK Progress Signal

Player identity is a complete-SDK v1 blocker because permissions, commands/replies,
moderation, economy, and mobility need a copied principal model. Current progress should
be reported internally as:

- `players-identity-lifecycle-intake coverage=10/12 committed candidate snapshots`;
- `second-source comparable=not complete until 12/12`;
- `accepted login anchors=0/1`;
- `accepted logout anchors=0/1`;
- `promotion_ready=false`;
- `public_sdk_ready=false`;
- `runtime_ready=false`;
- `target_set=planning_only`.

Closing `ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer` reduces the admin-surface fixture gap. It does
not unblock permissions, command routing, operator ingress/storage, Inventory SDK, runtime
identity, login/logout lifecycle anchors, or any public v1 SDK claim.

## Safe Next Step

The next useful action is to produce or approve a reviewed, non-protected
reflection-inventory pack with:

- `schema=obelisk.reflection-inventory-pack.v1`;
- `status=candidate-only`;
- `promotion_status=not_promoted_candidate_only`;
- `inputs.evidence_pack_manifest` pointing to a complete non-protected
  `obelisk.core-dump-evidence-pack.v1` manifest;
- complete `artifact_identity` for an offline core;
- `summary.fname_root_ready=true`;
- empty `blockers`;
- a redacted `ufunction-inventory.json` containing
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`.

Once that pack exists outside protected live-server paths, the safe planning command is:

```bash
python3 scripts/plan_ufunction_focal_snapshots.py \
  --inventory-pack <reviewed-reflection-inventory-pack>/manifest.json \
  --target ShooterPlayerController.ServerListPlayers \
  --target ShooterPlayerController.ServerKickPlayer \
  --evidence-obelisk-commit <reviewed-obelisk-id> \
  --json-out <ignored-non-protected-output>/players-identity-admin-focal-plan.json
```

The planner emits candidate-only `inspect_core_ufunctions.py --snapshot-json` commands.
It does not reread a core, execute snapshot commands, promote identity, authorize runtime
work, or create a public SDK surface.

Before running the planner, re-run:

```bash
python3 scripts/check_reflection_inventory_pack_readiness.py \
  --root <non-protected-artifact-root>
```

Proceed only when the checker reports `ready=true`. A valid pack for this lane must
record `target_set_coverage` for the full 12-target
`players-identity-lifecycle-intake` set and contain inventory rows for both missing admin
targets: `ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer`. Do not build a two-function-only reflection
inventory pack; only the later focal snapshot plan narrows to the two missing admin
snapshots. Treat checker acceptance as permission to plan those candidate-only focal
snapshots, not as identity, Inventory SDK, public SDK, runtime, lookup, or
`ResourceHandle` promotion.

The checker and planner also fail closed when the inventory
`target_set_coverage.target_sets` drifts from the pack manifest `inputs.target_sets`, so
a mixed or stale coverage block cannot be used to plan the player-identity admin
snapshots.

An offline `ShooterGameServer` binary, copied core, manual `--gobjects`, and manual
`--fname-root-slot` are not enough by themselves for this lane. The reflection inventory
pack must be tied back to the complete core evidence-pack manifest before
`players-identity-lifecycle-intake` planning is accepted.

If a complete non-protected core evidence pack is available, a safe inventory-build route
is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest <non-protected-pack>/manifest.json \
  --ark-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --target-set players-identity-lifecycle-intake \
  --include-functions \
  --output-dir /tmp/obelisk-reflection-inventory-identity-pack
```

If only non-protected copied core and binary files are available, first stage them outside
both `/servidor/ark` and the repository, then build the core evidence pack explicitly
without relying on Git or default candidate scans:

Operator preflight for this direct route:

- Use a fresh, run-specific `ROOT` under a non-protected artifact location such as
  `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>`.
- Confirm `ROOT/raw/ShooterGameServer` and `ROOT/raw/core` are copied files, not symlinks
  or paths back into `/servidor/ark`, the repository, or a live-server tree.
- Set `COMMIT` from the reviewed checkpoint metadata already in hand. This recipe does
  not require `git status`, `git rev-parse`, network access, GitHub, Discord, or any
  server interaction.
- Treat the address values below as evidence-bound to the same offline binary/core pair.
  If the binary hash differs from the reviewed evidence, stop and collect new evidence
  instead of reusing the sample addresses.
- Keep all outputs under `ROOT`; the expected pack manifests are
  `${ROOT}/core-evidence-pack/manifest.json` and
  `${ROOT}/reflection-inventory-pack/manifest.json`.

Dry-run the raw input layout before running any builder:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_player_identity_raw_inputs.py \
  --root /home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>
```

This validator writes nothing and returns JSON. It requires the exact
`ROOT/raw/ShooterGameServer` and `ROOT/raw/core` sibling layout, rejects direct or
symlink-resolved `/servidor/ark` paths, rejects symlink components, hashes only the
binary against the reviewed `ShooterGameServer` SHA, and checks the core file by metadata
only. It does not parse core contents, run `gdb`, attach to processes, run scanners, or
build/stage evidence packs. `status=accepted` and
`ready_for_core_evidence_pack_command=true` mean the raw input pair is shaped correctly
for the next offline command; it is not proof that the core is semantically usable.

If the raw files are already known explicitly, the equivalent no-staging check is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_player_identity_raw_inputs.py \
  --binary /home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/ShooterGameServer \
  --core /home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/core
```

Use the staging helper when the source binary/core already exist as explicit
non-protected files. It verifies the reviewed `ShooterGameServer` SHA, rejects symlinks
and protected paths, and prepares the exact raw sibling layout without creating or
validating a core:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare_player_identity_offline_raw_layout.py \
  --binary <non-protected-ShooterGameServer> \
  --core <non-protected-core> \
  --artifact-root /home/flowcommunity-ark/obelisk-artifacts \
  --run-id <run-id>
```

After the helper reports `ready_for_core_evidence_pack_command=true`, use its
`next_command` or the equivalent explicit command below.

```bash
ROOT=/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>
BIN=${ROOT}/raw/ShooterGameServer
CORE=${ROOT}/raw/core
COMMIT=<reviewed-obelisk-id>

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_core_dump_evidence_pack.py \
  --binary "${BIN}" \
  --core "${CORE}" \
  --output-dir "${ROOT}/core-evidence-pack" \
  --obelisk-commit "${COMMIT}" \
  --no-default-candidates \
  --no-default-fname-roots \
  --no-default-fname-indices \
  --fname-root-slot verified_fname_root_slot=0x5956f30 \
  --fname-index None=0 \
  --fname-index ClientMessage=4884 \
  --fname-index ServerChat=9619 \
  --fname-index SetActiveMissionDebugFlags=9622 \
  --gobjects-candidate gobjects=0x595b7e0 \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_reflection_inventory_pack.py \
  --evidence-pack-manifest "${ROOT}/core-evidence-pack/manifest.json" \
  --ark-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --evidence-pack-fname-root-label verified_fname_root_slot \
  --evidence-pack-gobjects-label gobjects \
  --target-set players-identity-lifecycle-intake \
  --include-functions \
  --output-dir "${ROOT}/reflection-inventory-pack"

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_inventory_pack_readiness.py \
  --root "${ROOT}/reflection-inventory-pack"
```

Operator stop/continue rule:

- Stop if any command fails, if the core evidence pack manifest is missing, or if the
  reflection readiness checker does not report `ready=true`.
- Continue to focal snapshot planning only after the readiness checker accepts the
  reflection-inventory pack and the pack records the full
  `players-identity-lifecycle-intake` target-set coverage.
- Even on success, the result remains candidate-only. Re-run the combined preflight
  against the artifact root and expect the broader player-identity lane to remain blocked
  until second-source evidence and lifecycle anchors are accepted.

This direct staged-input route requires a matching offline `ShooterGameServer` and ELF
core file. Always pass the reviewed `--ark-binary-sha256` shown above so the inventory
builder fails closed if the core evidence-pack manifest is paired with a different ARK
binary. Do not use `--skip-core-sha256`, do not use `--allow-partial-gdb`, and do not
reuse `0x5956f30` or `0x595b7e0` for a different ARK binary hash without new evidence.

This command shape is still offline and candidate-only. It must not use direct or
symlinked `/servidor/ark` paths without a current scoped approval.

Even after the two missing admin snapshots exist, the combined preflight must still stay
blocked until a distinct second-source snapshot root is accepted and session-start plus
session-end lifecycle anchors are accepted. The wrapper reports those as
`second_source_evidence_missing`, `second_source_evidence_not_accepted`, and
`accepted_lifecycle_anchors_missing` as appropriate, so fixture coverage cannot be
mistaken for player identity readiness.

## Boundary

The two missing snapshots close only the admin-surface fixture gap. They do not establish
login/logout lifecycle anchors, principal validity, identity privacy, permission
authority, command routing, economy identity, runtime readiness, mutation, return
override, `ResourceHandle`, or player lookup.

After those admin snapshots exist, the player identity lane still remains planning-only
until a separate candidate pack proves at least one real session-start anchor and one real
session-end anchor. That pack must record exact `Outer.Function`, `ParmsSize`, property
order, offsets, sizes, property classes, and a distinct second-source/static comparison.
It also needs a copied opaque-principal policy, forced redaction for names, IP-like
values, tribe ids, object references, raw params, and UE pointers, plus fail-closed
invalidation for disconnect, transfer, reconnect, stale controller, and restart cases.
`ChatMessageEvent` must continue to treat `principal=unknown` until that lifecycle and
privacy work is promoted.
