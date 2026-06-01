# Player Principal Runtime Window Brief Template

Date: 2026-06-01

## Purpose

This is a documentation-only live-ops brief template for a future
`PlayerPrincipalLifecycleObserver` evidence window. It does not authorize server access,
marker edits, wrapper/env changes, restarts, player-facing tests, Discord/community
notices, Git actions, public SDK work, plugin delivery, lookup, mutation, return override,
or release claims.

Use this template to ask an operator for exact current-turn approval. If approval omits
any required value below, the window is no-go.

## Minimum Operator Approval To Request

Ask the operator to approve exactly this scoped target and nothing broader:

```text
Approve one consume-only PlayerPrincipalLifecycleObserver runtime evidence window:

target instance=<instance-id>
target map=<map>
run_id=<YYYYMMDDThhmmssZ-player-principal-lifecycle>
ARK binary path=<path>
ARK binary SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
Obelisk commit/build=<reviewed build containing PlayerPrincipalLifecycleObserver>
approved UTC window=<start/end>
restart expectation=<none|start|restart|stop-after-window>
final posture=<stable|stopped>
connected-user policy=<no_regular_users|operator_approved_beta_users>
notice path=<not_applicable|operator-approved notice path label>
copied evidence dir=/servidor/ark/workspace-offline/live-validation-logs/<run-id>/
rollback owner=<operator/person>
rollback delta=remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins
post-checks=<same target stable preflight and posture check>
```

Approval must state that plugins stay disabled, dispatch limit stays `0`, log limit stays
`10`, no sibling marker entries may exist beyond the exact approved instance marker set,
and the resulting evidence is consume-only with no public SDK, lookup, permissions,
commands, `ResourceHandle`, mutation, return override, plugin delivery,
runtime-readiness, or release claim.

## Required Window Contract

Exact env gates for the future approved launch:

```text
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PE_TRACE_LIMIT=0
```

Exact instance marker set for the future approved window:

```text
enable-process-event-hook
disable-plugins
allow-observer-debug-window
allow-experimental-observers
enable-player-principal-lifecycle-observer
```

No sibling marker entry may exist for the same instance beyond the exact marker set above,
including malformed entries or symlinks. Forbidden entries include:

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

The wrapper/preflight must fail closed if the approved target, SHA, marker set, env gates,
plugin-disabled posture, `dispatch_limit=0`, `log_limit=10`, or observer exclusivity do
not match the approved brief.

## Evidence And Copy Boundary

Do not analyze direct live log paths. After the approved window and before review, copy
the relevant log into:

```text
/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
```

Keep the secret-free `window-manifest.env` beside the copied log. The manifest checker
validates offline sidecar posture only; it does not approve the run and cannot substitute
for the wrapper/preflight marker exclusivity checks.

The manifest must record the exact target, approved and actual timestamps, copied log
path/SHA, pre/post posture, rollback timestamps, rollback delta, `log_budget=10`,
`dispatch_limit=0`, `plugins_disabled=true`, `observer_exclusivity=player_principal_lifecycle_only`,
`debug_escape_markers=absent`, `callback_escape_markers=absent`, and
`single_module_summary=player_principal_lifecycle`.

## Rollback

Rollback must be inside the approved window unless the operator explicitly approves a
different final posture. Preserve evidence before cleanup or further changes.

Remove these observer-only env values:

```text
OBELISK_WRAPPER_PROFILE
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT
```

Remove these observer-only markers unless another current-turn approval owns them:

```text
allow-observer-debug-window
allow-experimental-observers
enable-player-principal-lifecycle-observer
```

Preserve stable markers:

```text
enable-process-event-hook
disable-plugins
```

The copied manifest remains blocked unless rollback completed, post-check passed for the
same target, `observer_env_survived=false`, and `observer_marker_survived=false`.

## No-Go Checklist

- No exact current-turn operator approval for the target instance/map, window, gates,
  user policy, evidence path, rollback, and final posture.
- Any plugin loading is allowed, `disable-plugins` is absent, or
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT` is not `0`.
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT` is not exactly `10`.
- Any sibling marker entry beyond the exact approved marker set is present, including
  observer, scanner, native-exec, ptrace, callback escape, broad tracing, or
  `CallProcessEvent` entries.
- The copied evidence destination is not under
  `/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`.
- The evidence or manifest contains player identity, raw UE pointers, raw params, chat or
  command text, private user data, or hashes of redacted identity values.
- The result is described as public SDK readiness, player identity promotion, lookup,
  permissions/admin, command reply support, plugin delivery, mutation, return override, or
  runtime readiness.

## Checker Alignment

The window manifest checker
`scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py` requires
`approval=current-turn operator-approved runtime window, not standing approval`,
`log_budget=10`, `dispatch_limit=0`, `plugins_disabled=true`,
`wrapper_profile=observer-debug`, `observer_exclusivity=player_principal_lifecycle_only`,
`delivery_claim=none`, `principal_claim=none`, a copied log path ending in
`live-validation-logs/<run-id>/Obelisk.log`, and no identity/UE-internal terms in either
manifest keys or values.

Passing the checker means only that the offline manifest is acceptable for the next
consume-only evidence step. It does not authorize server operations and does not promote a
public player identity SDK.
