# Player Principal Offline To Runtime Plan

Date: 2026-06-01

## Objective

Document the current golden path for player principal evidence after the completed
offline player-identity work. This note is documentation-only. It does not authorize
server access, marker changes, restarts, runtime capture, scanner/native-exec use,
`ptrace`, `gcore`, broad `ProcessEvent` tracing, public SDK work, mutation, return
override, lookup, `ResourceHandle`, publication, community notice, or release claims.

The route is narrow:

1. Reuse the existing binary-scoped FName and GObjects evidence.
2. Consume the focal lifecycle snapshots for `HandleNewPlayer` and `OnLogout`.
3. Request only the next approved runtime consume-only evidence for principal lifecycle.

## Baseline

For the current reviewed ARK Linux binary hash
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, the reusable
reflection inputs are already known:

- FName root slot: `0x5956f30`.
- GObjects / `GUObjectArray` candidate: `0x595b7e0`.
- FName clues: `None=0`, `ClientMessage=4884`, `ServerChat=9619`,
  `SetActiveMissionDebugFlags=9622`.
- GObjects remains internal/offline consume evidence, not public object identity.

Do not restart broad FName, GObjects, core discovery, admin-snapshot discovery,
second-source layout discovery, or lifecycle-layout discovery for this same binary unless
the binary hash changes or a reviewed artifact contradicts the current evidence.

The current lifecycle layout anchors are:

- `ShooterGameMode.HandleNewPlayer`: candidate `session_start` layout.
- `ShooterGameMode.OnLogout`: candidate `session_end` layout.

They are accepted as candidate-only layout inputs through focal snapshots and
consume-only lifecycle-anchor manifests. They do not prove complete login ordering,
rejected admission coverage, reconnect semantics, transfer/download semantics,
controller replacement, stable player identity, public principal readiness, command
sender authentication, permissions, persistence, lookup, `ResourceHandle`, mutation, or
return override.

## Offline Golden Path

Use a complete non-protected offline evidence pack or a staged non-protected offline core
pair. Keep every path under a run-specific artifact root chosen by the operator, shown
here as `<offline-root>`. Do not point commands at protected live-server paths or at
symlinks that resolve into protected trees.

Validate the staged raw files before any pack build:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_player_identity_raw_inputs.py \
  --root <offline-root>/player-identity-offline-<run-id>
```

Build the core evidence pack only from approved offline files, passing the reviewed
globals explicitly:

```bash
ROOT=<offline-root>/player-identity-offline-<run-id>
BIN="${ROOT}/raw/ShooterGameServer"
CORE="${ROOT}/raw/core"
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
```

Build the reflection inventory for the full planning target set. Do not build a
two-function-only inventory:

```bash
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

For lifecycle anchors, consume only the focal snapshot set and the closed
`players-lifecycle-anchor-candidates` target set:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/compare_reflection_snapshots.py \
  --base-root <accepted-sanitized-base-snapshot-root> \
  --candidate-root <distinct-sanitized-second-source-root> \
  --target-set players-lifecycle-anchor-candidates \
  --readiness-report \
  --planning-layout-intake \
  --json
```

Expected planning result: `layout_ready=true` is useful only as planning evidence, while
`promotion_ready=false` and `ready_scope=planning_only` remain required. Promotion-mode
checks must keep failing closed for public readiness.

The accepted focal runtime shapes remain:

- `ShooterGameMode.HandleNewPlayer`: `ParmsSize=26`, `NumParms=5`,
  `NewPlayer:ObjectProperty@0/8`, `PlayerData:ObjectProperty@8/8`,
  `PlayerCharacter:ObjectProperty@16/8`, `bIsFromLogin:BoolProperty@24/1`,
  `ReturnValue:BoolProperty@25/1`.
- `ShooterGameMode.OnLogout`: `ParmsSize=8`, `NumParms=1`,
  `Exiting:ObjectProperty@0/8`.

`HandleNewPlayer` may become a private candidate start observation only when observed
after the original call returns and copied bool bytes are canonical
`bIsFromLogin=1,ReturnValue=1`. Other canonical combinations are rejected starts with no
principal action. Non-canonical bool bytes reject the record. `OnLogout` is an
invalidation-shaped private event only; by itself it does not prove complete lifecycle
ordering or public invalidation semantics.

## Runtime Consume-Only Next Evidence

The next useful evidence is not another offline scan. It is a bounded,
operator-approved runtime window for the private `PlayerPrincipalLifecycleObserver`, with
plugins disabled, dispatch disabled, copied redacted logs, and a reviewed manifest.

The runtime evidence must be consume-only and private:

- target set: `players-lifecycle-anchor-candidates`;
- exact targets: `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`;
- dispatch limit: `0`;
- first-window log budget: exactly `10` for the current approved-evidence bundle;
- copied fields: only canonical bools from `HandleNewPlayer`;
- redacted fields: all object references;
- no principal id or generation values logged;
- no player names, platform ids, IP-like values, tribe ids, transfer ids, object names,
  object addresses, raw params, buffers, FName indices, GObjects indices, hashes of
  private identifiers, chat text, command text, permission state, or admin state.

Template for a future approved window request:

```bash
export OBELISK_WRAPPER_PROFILE=observer-debug
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_PE_TRACE_LIMIT=0
export OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=<reviewed-ark-binary-sha256>
export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
unset OBELISK_ENABLE_REFLECTION_SCANNER
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
```

Required instance markers for such a window, expressed as names only:

```text
enable-process-event-hook
disable-plugins
allow-observer-debug-window
allow-experimental-observers
enable-player-principal-lifecycle-observer
```

A run request must separately name the approved instance, map, binary SHA, Obelisk build,
marker/env changes, rollback owner, copied-log destination, stable-posture verification,
and final shutdown or restored-posture expectation. This note does not grant that
approval.

After an approved run, copy the bounded observer log and all request sidecars to a
non-protected offline evidence root. Do not consume a raw copied log by itself. The
post-window evidence path is accepted only when the same run directory contains the
freshness-bound `window-request.json`, `observer-window.env`,
`operator-approval-request.md`, completed `operator-approval-receipt.json`, checked
`window-manifest.env`, and pre/post preflight JSON sidecars beside the copied log. The
request pack must include `prepared_at_utc`, and the completed receipt's
`approval_recorded_at_utc` must be after `prepared_at_utc` and before the approved window
start.

Validate the copied window manifest and then build the approved runtime evidence bundle:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py \
  --json \
  --post-window-replay \
  <offline-evidence-root>/window-manifest.env

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py \
  --copied-log <offline-evidence-root>/Obelisk.log \
  --window-manifest <offline-evidence-root>/window-manifest.env \
  --output-dir <offline-evidence-root>/approved-bundle \
  --obelisk-commit <reviewed-40-character-lowercase-git-sha> \
  --reviewed-by <reviewer>

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py \
  --json \
  <offline-evidence-root>/approved-bundle/approved-runtime-principal-lifecycle-evidence.json
```

The reviewed manifest must remain `promotion_ready=false`, `public_sdk_ready=false`, and
`runtime_ready=false` unless a later explicit promotion gate changes those rules. A
synthetic template or a passing consume-mode manifest is not public runtime evidence and
does not create an SDK surface.

## Stop Conditions

Stop and do not consume the evidence if any of these occur:

- binary SHA differs from the reviewed evidence and no new evidence pack exists;
- any path is protected, symlinked into a protected tree, or not an approved offline copy;
- broad FName/GObjects/core scanning is proposed for the same binary without
  contradictory evidence;
- plugins are enabled during the first runtime observer window;
- dispatch limit is non-zero;
- observer log budget is missing, zero, malformed, overflowing, or not exactly `10`
  for the current approved-evidence bundle;
- a log line contains a private identifier, object coordinate, raw param, pointer, FName
  index, GObjects index, chat text, command text, or hashed private identifier;
- copied bool bytes are not canonical `0` or `1`;
- `post_original=true` is missing for lifecycle observations;
- `HandleNewPlayer` or `OnLogout` metadata differs from the accepted focal shape;
- any consumer treats candidate principal action as public identity, permissions,
  command routing, persistence, lookup, `ResourceHandle`, mutation, or return override.

## Result

The current golden route is:

```text
reviewed FName root 0x5956f30
-> reviewed GObjects candidate 0x595b7e0
-> complete player identity reflection inventory
-> focal HandleNewPlayer / OnLogout snapshots
-> candidate-only lifecycle anchor and principal policy manifests
-> approved private runtime consume-only observer evidence
-> later, separate public ABI and promotion review
```

Anything beyond that chain is out of scope for this lane. In particular, public player
identity, permissions/admin, command sender identity, command responses, economy,
persistence, cross-instance identity, object lookup, `ResourceHandle`, mutation, return
override, and SDK promises remain blocked until separate gates accept them.
