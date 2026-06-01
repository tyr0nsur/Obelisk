# Player Principal Runtime Capture Plan

Date: 2026-06-01

## Scope

This note turns the minimum consume-only runtime capture plan for the private
`PlayerPrincipalLifecycleObserver` into durable research guidance.

It is documentation-only. It does not authorize server access, marker edits, wrapper/env
changes, restarts, player-facing tests, Discord/community notices, Git actions, public SDK
work, plugin dispatch, lookup, mutation, return override, or release claims.

The only future evidence this plan may organize is copied, redacted, bounded runtime
observer evidence for:

- `ShooterGameMode.HandleNewPlayer`
- `ShooterGameMode.OnLogout`

The plan must remain consume-only. Passing every checker below would make runtime
principal lifecycle evidence reviewable for the player-principal lane only; it would not
promote `obelisk.player_identity.v1`, permissions/admin, command replies, moderation,
storage, economy, `ResourceHandle`, UE lookup, or v1 SDK readiness.

## Current Inputs

Reusable facts from the current research lane:

- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- `players-identity-lifecycle-intake` has complete planning-only fixture coverage.
- `players-lifecycle-anchor-candidates` has accepted planning-layout evidence for six
  lifecycle candidates.
- The first runtime observer consumes only `HandleNewPlayer` as a candidate
  `session_start` anchor and `OnLogout` as a candidate `session_end` anchor.
- The accepted first-window `HandleNewPlayer` copied bool cases are:
  - `bIsFromLogin=1,ReturnValue=1`: `session_start`,
    `principal_action=candidate_created`.
  - at least one canonical rejected combination such as `bIsFromLogin=0,ReturnValue=1`:
    `session_start_rejected`, `principal_action=none`.
- The accepted first-window `OnLogout` case is `session_end`,
  `principal_action=candidate_invalidated`.
- Object fields remain redacted only. Principal id and generation values must not be
  logged.

Do not rerun broad FName/GObjects/core discovery, admin snapshots, second-source layout,
or lifecycle layout routes to satisfy this plan. The remaining blocker is approved
runtime principal lifecycle evidence plus later public-contract review.

## Prerequisites

A future runtime window may proceed only with explicit current-turn operator approval for
the exact scoped run. That approval must name:

- target instance id and map;
- ARK binary path and SHA256;
- Obelisk build or commit containing the observer;
- exact start/end window and restart expectation;
- exact marker and environment deltas;
- log budget and maximum expected observer event lines;
- whether any player-facing action is required;
- connected-user policy for the window;
- notice path if any user-facing/beta action is involved;
- copied evidence destination under an approved offline workspace;
- rollback owner and rollback delta;
- post-check command and expected final posture or shutdown state.

## Exact Approved-Window Preflight

This checklist is the exact preflight contract for a future approved
`PlayerPrincipalLifecycleObserver` runtime window. It is still documentation-only and is
not standing approval to touch a server.

Operator approval must name the exact values for:

```text
instance=<instance-id>
map=<map>
ark_binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
obelisk_commit=<reviewed build containing PlayerPrincipalLifecycleObserver>
run_id=<YYYYMMDDThhmmssZ-player-principal-lifecycle>
window=<approved start/end UTC>
final_posture=<stable|stopped>
copied_evidence_dir=/servidor/ark/workspace-offline/live-validation-logs/<run-id>/
```

Before any marker/env activation, run the read-only stable preflight for the same target:

```bash
scripts/check_player_principal_lifecycle_preflight.sh \
  --instance <instance-id> \
  --map <map> \
  --mode stable \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

If the approved target is intentionally stopped before launch, the preflight may be run
with `--allow-stopped`. Do not use `--offline-only` against live install paths; that mode
is for offline copies and rejects live server paths by design.

The future observer-window launch must use only these env gates:

```text
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PE_TRACE_LIMIT=0
```

`LOG_LIMIT=10` is the exact first-window bundle/checker contract. A smaller approved
budget is still privacy-bounded, but the current approved-evidence checker expects the
observer enable line to report `limit=10`; change the checker before the runtime window if
a smaller exact limit is selected.

The future observer-window marker set for the instance must be exactly:

```text
enable-process-event-hook
disable-plugins
allow-observer-debug-window
allow-experimental-observers
enable-player-principal-lifecycle-observer
```

The wrapper/preflight must fail closed if any required marker is missing, malformed, or a
symlink. It must also fail closed if any residual observer or escape marker entry exists,
including symlink entries. Forbidden marker entries for this window are:

```text
allow-ptrace
enable-debug-control
enable-reflection-scanner
enable-native-exec-probes
allow-global-process-event-callbacks
allow-filtered-process-event-callbacks
allow-call-process-event
allow-process-event-blocking
request-static-fname-probe
enable-chat-events
enable-chat-reflection
enable-chat-route-observer
enable-inventory-reflection
enable-structure-reflection
enable-item-return-events
```

Plugins must remain disabled for the entire first window. `dispatch_limit=0` means this
is not a plugin delivery test and must not call public callbacks. The accepted observer
enable line must state `delivery_claim=none` and `principal_claim=none`.

Runtime copied output is reviewable only if all of the following stay true:

- the summary contains exactly one module, `player_principal_lifecycle`;
- `HandleNewPlayer` accepted case logs only `bIsFromLogin,ReturnValue=1,1`,
  redacts `NewPlayer,PlayerData,PlayerCharacter`, and records
  `principal_action=candidate_created`;
- `HandleNewPlayer` rejected case logs only `bIsFromLogin,ReturnValue=0,1`,
  redacts `NewPlayer,PlayerData,PlayerCharacter`, and records
  `principal_action=none`;
- `OnLogout` logs `session_end`, redacts `Exiting`, and records
  `principal_action=candidate_invalidated`;
- every event is post-original and keeps `principal_id_logged=false`,
  `principal_generation_logged=false`, and `delivery_claim=none`;
- no player name, Steam/EOS/platform id, IP, tribe id, persistent lookup key, object
  identity, UE pointer, FName/GObjects index, raw params, raw buffers, chat text, command
  text, permission/admin state, plugin subscriber state, `ResourceHandle`, or hash of a
  redacted identity value appears in logs, summaries, manifests, review text, or bundle
  output.

After rollback and log copy, the secret-free window manifest must be checked offline:

```bash
python3 scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py \
  --json \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env \
  > /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.check.json
```

Then build and check the consume-only bundle from copied evidence only:

```bash
python3 scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py \
  --copied-log /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log \
  --window-manifest /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env \
  --output-dir /servidor/ark/workspace-offline/live-validation-logs/<run-id>/approved-bundle \
  --obelisk-commit <reviewed-obelisk-commit> \
  --reviewed-by <reviewer> \
  --review-note "bounded redacted lifecycle observer summary accepted for consume-only review"
```

The bundle is acceptable only if consume mode passes and the generated promote,
public-readiness, and runtime-readiness checks fail closed. If any public/promotion mode
passes, treat the bundle as invalid.

Before any future activation:

- Stable pre-check for the same approved instance must pass.
- The runtime must be in the stable baseline: ProcessEvent hook enabled intentionally,
  plugins disabled, scanner/native-exec/ptrace/gcore/broad tracing off.
- `disable-plugins` must remain present for this first observer window.
- No experimental observer family other than player-principal lifecycle may be enabled.
  Wrapper launch must fail closed if any residual observer marker entry exists for the
  instance, including symlinks.
- No debug/scanner/callback escape markers may be present for the instance during this
  evidence window: `allow-ptrace`, `enable-debug-control`,
  `enable-reflection-scanner`, `enable-native-exec-probes`,
  `allow-global-process-event-callbacks`,
  `allow-filtered-process-event-callbacks`, `allow-call-process-event`, and
  `allow-process-event-blocking` are all incompatible with approved principal lifecycle
  evidence.
- The approved window must identify whether regular users are connected. If regular users
  are active, no-go unless the operator explicitly chooses a user-facing beta window,
  defines privacy bounds, and approves the notice path for that same turn.
- The log copy destination must be outside live logs, normally:
  `/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`.
- The copied/analyzed runtime summary must contain exactly one observer module:
  `player_principal_lifecycle`.

Read-only preflight examples:

```bash
scripts/check_player_principal_lifecycle_preflight.sh \
  --instance <instance-id> \
  --map <map> \
  --mode stable \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520

scripts/check_player_principal_lifecycle_preflight.sh \
  --instance <instance-id> \
  --map <map> \
  --mode stable \
  --allow-stopped \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

## Markers And Environment

Exact future env gates for the first window:

```text
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PE_TRACE_LIMIT=0
```

Exact future instance markers:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
state/instances/<instance-id>/allow-observer-debug-window
state/instances/<instance-id>/allow-experimental-observers
state/instances/<instance-id>/enable-player-principal-lifecycle-observer
```

First-window invariants:

- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT` must be `10` for the current
  approved-evidence checker. A different approved value in the safe `1..10` range is a
  checker-change-before-window item, not a runtime improvisation.
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT` must be `0`.
- `disable-plugins` must stay present.
- `OBELISK_PE_TRACE_LIMIT` must stay `0`.
- Any missing, malformed, overflowing, unsupported-SHA, non-zero-dispatch, or wrong-marker
  posture must fail closed without copied output.
- `OBELISK_WRAPPER_PROFILE=observer-debug` must not survive rollback or become normal
  service posture.

## Capture Window

The future approved run should capture only the smallest signal set:

- one observer enable line proving the supported binary SHA, target set, log limit,
  `dispatch_limit=0`, `delivery_claim=none`, and `principal_claim=none`;
- at least one post-original `HandleNewPlayer` accepted `session_start` event with
  copied bool values `1,1`, redacted object fields, and no principal id/generation logged;
- at least one post-original `HandleNewPlayer` `session_start_rejected` event with a
  copied bool values `0,1`, `principal_action=none`, and no principal id/generation
  logged;
- at least one exact `OnLogout` `session_end` event with `Exiting` redacted and
  `principal_action=candidate_invalidated`.

This capture is not a delivery test. It must keep `delivery_claim=none`, no plugin
callbacks, no public principal action, and no command/permission/economy behavior.

Do not collect or log player names, Steam/EOS/platform ids, IP-like values, tribe ids,
transfer ids, saved player data ids, controller identity, player-state identity, character
identity, object names, class names, UE pointers, raw params, raw buffers, FName indices,
GObjects indices, `ResourceHandle`, map location, command text, chat text, permissions,
admin state, plugin subscriber state, or hashes of redacted identity values.

## Log Copying

Do not analyze direct live log paths. After a future approved window, copy the relevant
log window into an offline run directory such as:

```text
/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
```

Keep a secret-free window manifest beside the copied log. Generate the initial file from
the checker rather than hand-writing fields:

```bash
python3 scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py \
  --emit-template /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env
```

Then replace the template values with the reviewed run id, target, timestamps,
`copied_log_path`, `copied_log_sha256`, `obelisk_commit`, posture fields, rollback fields,
and notice/user-policy fields for the approved window. Validate the manifest before
building an evidence bundle; stale or extra keys must fail closed. The emitted template is
not acceptance-ready evidence by itself: the checker must run only after replacing the
placeholder SHA, copying the log under the matching `<run-id>` evidence directory, and
verifying that `copied_log_sha256` matches the copied file bytes.

If users are involved, the manifest may record only a notice path label and a sanitized
notice digest. It must not record endpoints, webhooks, tokens, message URLs, player
identity, raw chat text, or private user data.

The copied log must include enough context to prove pre-check posture, observer enable,
bounded events, rollback, and post-check posture. A cropped event-only excerpt is useful
for review but is not sufficient evidence.

## Manifest And Checker

Analyze only the copied or sanitized log:

```bash
python3 scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py \
  --copied-log /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log \
  --window-manifest /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env \
  --output-dir /servidor/ark/workspace-offline/live-validation-logs/<run-id>/approved-bundle \
  --obelisk-commit <reviewed-obelisk-commit> \
  --reviewed-by <reviewer> \
  --review-note "bounded redacted lifecycle observer summary accepted for consume-only review"
```

The bundle helper runs analyzer -> approved manifest builder -> approved-evidence checker
-> offline consume gate, rejects direct server log paths through the underlying analyzer,
and reports only the `player_principal_lifecycle` module.

Manual equivalent analyzer command:

```bash
python3 scripts/analyze_runtime_observer_log.py \
  --obelisk-commit <reviewed-obelisk-commit> \
  --fail-on-quality-blockers \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log \
  > /servidor/ark/workspace-offline/live-validation-logs/<run-id>/runtime-observer-summary.json
```

The summary must use schema `obelisk.runtime-observer-log-summary.v1`, reject direct
server paths by default, and report only the `player_principal_lifecycle` module.

Then create a reviewed approved-evidence manifest beside the summary using schema:

```text
obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1
```

Required manifest posture:

- `artifact_status=approved_runtime_observer_summary`
- `readiness_classification=runtime_evidence_only`
- `approved_runtime_evidence_present=true`
- `runtime_evidence_ready=true`
- `promotion_ready=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `approval.runtime_evidence_reviewed=true`
- `approval.runtime_work_authorized_by_this_manifest=false`
- `approval.server_operations_authorized_by_this_manifest=false`
- `approval.publication_authorized_by_this_manifest=false`
- `approval.discord_authorized_by_this_manifest=false`
- `privacy_boundary.lookup_allowed=false`
- `privacy_boundary.resource_handle_allowed=false`
- `privacy_boundary.mutation_allowed=false`
- `privacy_boundary.return_override_allowed=false`

Required consumer boundary cases:

- `stale_after_logout`: `result=fail_closed`
- `malformed_or_unsupported_evidence`: `result=fail_closed`

Validate the reviewed manifest locally:

```bash
python3 scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py \
  --json \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/approved-runtime-principal-lifecycle-evidence.json
```

Optional consume-gate cross-check:

```bash
python3 scripts/validate_offline_artifact_gate.py \
  --mode consume \
  --manifest /servidor/ark/workspace-offline/live-validation-logs/<run-id>/approved-runtime-principal-lifecycle-evidence.json
```

Promotion, public-readiness, and runtime-readiness modes must still fail closed. If a
future report passes consume mode but passes any public promotion mode, treat that as a
checker bug or an overclaim, not as identity promotion.

## Rollback

Rollback must preserve evidence before cleanup or further changes.

Future rollback delta:

```text
unset/remove env:
  OBELISK_WRAPPER_PROFILE
  OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER
  OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256
  OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT
  OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT

remove markers unless another current-turn approved window owns them:
  allow-observer-debug-window
  allow-experimental-observers
  enable-player-principal-lifecycle-observer

preserve stable markers:
  enable-process-event-hook
  disable-plugins
```

Post-check must be for the same approved instance and map:

```bash
scripts/check_player_principal_lifecycle_preflight.sh \
  --instance <instance-id> \
  --map <map> \
  --mode stable \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520

scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

The window manifest must record rollback start/end, the exact reverse delta applied, the
post-check result, and whether any observer env or marker survived. If stable posture
cannot prove that observer env/markers are gone, the evidence remains operationally
blocked even if the copied observer lines look correct.

## No-Go List

No-go for any future runtime window if any item is true:

- No current-turn operator approval for the exact instance, map, gates, restart
  expectation, rollback, evidence path, user policy, and final posture.
- Regular users are active and the operator has not explicitly approved a player-facing
  beta window for that same turn.
- A user-facing/beta window is selected but privacy bounds, notice path, or sanitized
  notice evidence are missing.
- Any request asks this documentation note to authorize Discord/community notices, server
  operations, marker edits, restarts, Git publication, tags, or release claims.
- `disable-plugins` would be removed or any plugin would be allowed to load.
- Scanner, native exec probes, ptrace, `gcore`, broad ProcessEvent tracing, route
  observers, chat observers, inventory/structure/item observers, global callbacks, or
  public `CallProcessEvent` are present.
- The ARK binary SHA does not match the expected SHA for this plan.
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT` is absent, not `10`, malformed, or
  overflowing for the current approved-evidence checker.
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT` is not `0`.
- The log copy destination is a live log path, symlinked path, protected path outside the
  approved offline workspace, or missing a manifest.
- Any copied log, analyzer output, or manifest includes player identity, raw UE
  coordinates, raw params, raw chat/command text, private user data, or hashes of redacted
  identity values.
- Rollback cannot be completed inside the approved window or stable posture cannot be
  verified afterward.

## 2026-06-01 Offline Blocker Audit

Existing offline evidence is sufficient to avoid another broad FName, GObjects, admin
snapshot, second-source layout, or lifecycle-layout pass for the current binary hash. The
shortest remaining blocker is:

```text
approved_runtime_evidence_missing
```

That means a future current-turn approved, bounded, consume-only
`PlayerPrincipalLifecycleObserver` window must produce a copied/offline observer log,
accepted window-manifest check, built approved-evidence manifest, and passing consume
check. The exact first-window budget remains `log_budget=10`; a `5`-line manifest is a
checker/test mismatch, not accepted runtime evidence.

The local checker reports now expose the next gate explicitly:

- shape-only fixture report: `next_blocker=approved_runtime_evidence_missing`;
- accepted window manifest report:
  `next_blocker=approved_runtime_observer_log_summary_and_manifest_missing`;
- accepted approved runtime evidence report:
  `next_blocker=identity_public_contract_gate_missing`.

These are diagnostic labels only. They do not authorize server work, promotion, public
readiness, plugin delivery, identity lookup, mutation, return override, or SDK claims.

## Gaps

Remaining gaps after this plan:

- No runtime window has been authorized by this note.
- No copied runtime log or approved runtime evidence manifest is present here.
- The first observer proves only a private observed lifecycle shape, not complete
  login/logout ordering.
- Reconnect, duplicate start, logout without active private candidate, transfer/download,
  respawn, controller replacement, player-state replacement, plugin reload, and server
  restart semantics remain unresolved.
- Principal id shape, generation semantics, scope flags, storage policy, cross-instance
  policy, and public ABI are still blocked.
- Permissions/admin and command replies remain blocked until player principal semantics
  are promoted separately and fail closed.
- Operator/user notice policy is intentionally not selected by this note; any user-facing
  window must be approved in the current turn that runs it.

## Related Notes

- [2026-06-01-player-principal-runtime-observer-brief.md](2026-06-01-player-principal-runtime-observer-brief.md)
- [2026-06-01-player-principal-policy-route.md](2026-06-01-player-principal-policy-route.md)
- [2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md](2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md)
- [2026-05-31-player-identity-privacy-invalidation-contract.md](2026-05-31-player-identity-privacy-invalidation-contract.md)
