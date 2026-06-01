# Player Identity Runtime Capture Readiness Checklist

Date: 2026-06-01

## Scope

Operator-facing offline checklist for a future approved
`PlayerPrincipalLifecycleObserver` runtime evidence window. This note is derived from
current repo docs and scripts only. It does not authorize server access, marker edits,
wrapper/env changes, restarts, Discord/community notices, Git actions, runtime capture,
public SDK work, lookup, `ResourceHandle`, mutation, return override, or release claims.

The only future runtime evidence in scope is copied, redacted, bounded observer evidence
for:

- `ShooterGameMode.HandleNewPlayer`
- `ShooterGameMode.OnLogout`

## Preconditions

Do not request or run the window unless all items are explicitly true in a current-turn
operator-approved live-ops brief:

- Exact target instance id and map are named.
- ARK binary SHA256 is
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Reviewed Obelisk build contains `PlayerPrincipalLifecycleObserver`.
- Approved UTC start/end window, restart expectation, final posture, rollback owner, and
  rollback delta are named.
- User policy is named as `no_regular_users` or `operator_approved_beta_users`; beta-user
  windows also name privacy bounds and notice evidence.
- Plugins remain disabled and dispatch limit remains `0`.
- First-window log budget is exactly `10`.
- ProcessEvent hook is enabled only as the stable baseline; `OBELISK_PE_TRACE_LIMIT=0`.
- Scanner, native-exec probes, ptrace, gcore, broad ProcessEvent tracing, debug control,
  global/filtered callback escapes, public `CallProcessEvent`, and unrelated observer
  families are absent.
- The copied evidence destination is a run directory under
  `/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`.
- The target has a read-only stable preflight before activation and a same-target stable
  posture check after rollback.

Exact first-window observer env posture to be reviewed from a secret-free env snapshot:

```text
OBELISK_INSTANCE_ID=<instance-id>
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PE_TRACE_LIMIT=0
```

Exact first-window marker names:

```text
enable-process-event-hook
disable-plugins
allow-observer-debug-window
allow-experimental-observers
enable-player-principal-lifecycle-observer
```

## Read-Only Preflight

Use these checks only under the future approved brief. They are read-only and must not be
used as approval by themselves:

```bash
scripts/check_player_principal_lifecycle_preflight.sh \
  --offline-only \
  --allow-stopped \
  --instance <instance-id> \
  --mode stable \
  --obelisk-root /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/obelisk-root \
  --installed-wrapper /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/ObeliskRun.sh \
  --server-binary /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/ShooterGameServer \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520

scripts/check_player_principal_lifecycle_preflight.sh \
  --offline-only \
  --allow-stopped \
  --instance <instance-id> \
  --mode observer-window \
  --obelisk-root /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/obelisk-root \
  --installed-wrapper /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/ObeliskRun.sh \
  --server-binary /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/ShooterGameServer \
  --env-file /servidor/ark/workspace-offline/player-principal-preflight/<run-id>/observer-window.env \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

For offline copies, `--offline-only` must not be pointed at live install paths. The
preflight must fail closed for duplicate env keys, missing keys, extra observer/gate env
keys, symlinked markers, unexpected sibling markers, SHA mismatch, plugin-enabled
posture, or a log/dispatch limit mismatch.

## Expected Log Cases

The copied log must contain exactly one private observer module:
`player_principal_lifecycle`.

Required observer enable line:

```text
PlayerPrincipalLifecycleObserver enabled binary_sha256=<expected-sha256> target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
```

Required event cases, in accepted lifecycle order:

- `session_start`: target `ShooterGameMode.HandleNewPlayer`, `post_original=true`,
  copied bool fields `bIsFromLogin,ReturnValue`, copied bool values `1,1`, redacted
  fields `NewPlayer,PlayerData,PlayerCharacter`,
  `principal_action=candidate_created`, `principal_id_logged=false`,
  `principal_generation_logged=false`, `delivery_claim=none`.
- `session_start_rejected`: target `ShooterGameMode.HandleNewPlayer`,
  `post_original=true`, copied bool fields `bIsFromLogin,ReturnValue`, copied bool
  values `0,1`, same three redacted fields, `principal_action=none`,
  `principal_id_logged=false`, `principal_generation_logged=false`,
  `delivery_claim=none`.
- `session_end`: target `ShooterGameMode.OnLogout`, `post_original=true`, no copied bool
  fields or values, redacted field `Exiting`,
  `principal_action=candidate_invalidated`, `principal_id_logged=false`,
  `principal_generation_logged=false`, `delivery_claim=none`.

The analyzer/checker route also requires fail-closed consumer boundary cases for
`stale_after_logout` and `malformed_or_unsupported_evidence`.

## Offline Bundle Commands

After the approved window, analyze only the copied offline log and its secret-free
manifest. Do not analyze direct live log paths.

Generate the manifest template from the copied log, then replace template values with the
reviewed window facts:

```bash
python3 scripts/check_player_principal_lifecycle_window_manifest.py \
  --emit-template /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env \
  --copied-log /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
```

Validate the completed manifest:

```bash
python3 scripts/check_player_principal_lifecycle_window_manifest.py \
  --json \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env
```

Build the consume-only evidence bundle:

```bash
python3 scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py \
  --copied-log /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log \
  --window-manifest /servidor/ark/workspace-offline/live-validation-logs/<run-id>/window-manifest.env \
  --output-dir /servidor/ark/workspace-offline/live-validation-logs/<run-id>/approved-bundle \
  --obelisk-commit <reviewed-obelisk-commit> \
  --reviewed-by <reviewer> \
  --review-note "bounded redacted lifecycle observer summary accepted for consume-only review"
```

Expected bundle behavior:

- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py --json`
  accepts consume-only runtime evidence.
- `validate_offline_artifact_gate.py --mode consume --json --manifest <approved-manifest>`
  accepts the bundle.
- Promotion, public-readiness, and runtime-readiness checks fail closed.
- `next_blocker` becomes `identity_public_contract_gate_missing`, not public identity
  readiness.

## Fail-Closed No-Go Conditions

No-go if any item is true:

- No exact current-turn operator approval for the target, window, gates, evidence path,
  user policy, rollback, and final posture.
- Any requested action would mutate server state outside the approved runbook.
- Regular users are active without an operator-approved beta-user window and notice path.
- ARK binary SHA differs from the reviewed SHA above.
- Plugins can load, `disable-plugins` is absent, or dispatch limit is not `0`.
- Log limit is absent, malformed, overflowing, or not exactly `10`.
- Any sibling marker/env exists for scanner, native exec, ptrace/gcore, debug control,
  callback escape, `CallProcessEvent`, broad tracing, chat, inventory, structure, item, or
  unrelated observer families.
- Copied evidence is missing, not under the approved offline workspace, symlinked through
  a protected path, or lacks a matching `window-manifest.env`.
- The log has no safe enable line, more than one observer gate, missing required event
  cases, out-of-order lifecycle cases, duplicate/non-monotonic sequence ids, or quality
  blockers beyond `runtime_observer_evidence_only`.
- Any copied bool byte is non-canonical or outside `0`/`1`.
- Any event is not `post_original=true`.
- Any output contains player names, Steam/EOS/platform ids, IP-like values, tribe ids,
  saved player identifiers, object names, class names, UE pointers, raw params, raw
  buffers, FName/GObjects indices, `ResourceHandle`, map locations, chat text, command
  text, permissions/admin state, plugin subscriber state, or hashes of redacted identity
  values.
- Rollback is incomplete, observer env/markers survive rollback, or same-target stable
  posture cannot be verified afterward.
- Any checker reports promotion/public/runtime readiness instead of consume-only evidence.

## Non-Claims

This checklist does not claim approval exists. It also does not claim public player
identity, stable principal identity, permissions/admin, commands/replies, chat sender
authentication, economy/storage, persistence, cross-instance identity, lookup,
`ResourceHandle`, public GObjects, UE pointer validity, plugin delivery, callback ABI,
mutation, return override, runtime readiness, v1 SDK completion, production validation,
Discord/community approval, GitHub publication, tags, or release readiness.
