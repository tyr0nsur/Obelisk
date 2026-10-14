---
name: obelisk-live-ops
description: "Use when operating Obelisk on ARK server instances: central install root, arkmanager wrappers, per-instance state markers, log symlinks, config restore backups, restart safety, isolated debug instances, and production experiment gates."
---

# Obelisk Live Ops

Use this skill when touching server deployment, `/servidor/ark`, arkmanager scripts,
runtime marker files, restore backups, or operational checks after installing Obelisk.
Even if an operator calls both instances "development", treat shared/public/clustered
instances as live-like until an isolated debug instance is confirmed.

## Live Layout

Central root:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  config/
  logs/
  state/instances/
```

Managed subdirectories under the central root must be real directories, not symlinks.
Runtime/plugin installers own layout creation, and `PluginManager` should fail closed if
the plugin directory is missing, a symlink, or not a directory.

Only the thin launcher/wrapper should live inside the ARK binary directory. Runtime
libraries, plugin `.so` files, plugin config, logs, and state markers belong under the
central Obelisk root.
Wrappers must fail before exporting `LD_PRELOAD` when `OBELISK_ROOT` is relative, `/`, a
symlink, missing managed directories, or has a symlinked `lib/libobelisk.so`. They must
execute the `ShooterGameServer` located beside the wrapper, not a CWD-relative binary.

Convenience log links may live under:

```text
/home/flowcommunity-ark/logs/ark/
```

Independent of the current map assignment, never keep three ARK servers running at the
same time. Never run more than two ARK servers at once. Any approved posture transition
must keep ARK server concurrency at two or fewer by confirming one instance is off before
another is brought online.

Known Genesis2 instance ports: `arkserver3` / Genesis2 uses game UDP `7783`, raw UDP
`7784`, Steam query UDP `27017`, and RCON TCP `27022`. Local health is not enough after
router/NAT/firewall or port-forwarding work. After any approved router/NAT/firewall or
port-forwarding change, verify Genesis2 public Steam/GameDig query from outside the LAN;
local health does not prove public reachability. If Genesis2 is healthy locally but absent
from public query, treat missing forwarding for UDP `7783`/`7784`/`27017` as the likely
network-scope cause until operator/network evidence says otherwise. This is operator
knowledge only; it does not authorize starts, stops, restarts, router/NAT/firewall edits,
port forwarding, or any other network changes without current-turn approval.

Current instance posture belongs in `docs/agent-handoff/CURRENT.md`, not in this durable
skill. Before server-backed validation, read that file for active scope. Current-turn
exact scope is required for live server/log reads, marker/env changes, Discord sends, and
runtime capture unless `docs/agent-handoff/CURRENT.md` and
`docs/agent-handoff/COMPACT_CONTEXT.md` both record an active standing operator
authorization that names the launch/evidence purpose, server set, allowed operations,
evidence paths, notice path, safety limits, and revocation condition. Passive/read-only
observation and beta tester notices are not exceptions outside that approved scope;
passive/read-only observation still requires one of the approved scopes.
When that recorded standing authorization is present and unretracted, do not treat
compaction or a resumed turn as revocation; use it for the named runtime/beta evidence
window and keep all recorded safety limits attached.
Marker edits, start/stop/restart commands, runtime observation, live reads of server
state or logs, live log reads/tails, RCON/admin-console commands, ReflectionScanner,
native exec probes, ptrace/gcore, broad ProcessEvent tracing,
text/gameplay-payload logging,
beta/community notices, and player-facing validation all require either exact current-turn
operator approval or the recorded standing launch authorization. Agents may use only the
approved scope and must not broaden it into publication, release tags, Plugin Hub, or SDK/
stable/public-readiness claims. Approval must name the target instance, marker/env gates,
start/stop/restart window, rollback plan, evidence paths, notice path when applicable, and
shutdown/posture expectation; a recorded standing authorization satisfies this only for
the fields it explicitly records.
Request packs, preflight outputs, accepted planning artifacts, status reports,
`progress_normalization_trace`, source_overclaim diagnostics, the latest
release-readiness pass, release-readiness passes, `source_overclaim_total_flag_count=0`,
the latest validation pass, closed-agent/all-six-agent closure notes, `.codex` cleanup,
passive observation, passive summaries/snapshots, passive monitor ticks/output, passive
monitors, public reachability, beta tester notices, Discord notice drafts,
package-shape installs, package installs, exact-version
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
install/package success, package-shape install success, Plugin Hub planning/readiness,
support-tier or package-shape labels, prior approvals, historical live approvals/map
names, historical approvals/map names, and historical server/map names can
support a request or chronology only; they do not authorize markers, env changes, runtime
observation, live reads of server state or logs, live log reads/tails, RCON/admin-console
actions, starts, stops, restarts, Discord sends, runtime capture, runtime evidence, runtime
readiness, live-op authorization, Discord authorization, public SDK readiness, SDK
evidence, approved in-game evidence, SDK/P0 counter progress, publication authority,
publication, Plugin Hub readiness, public package readiness, support-tier activation,
stable SDK readiness, stable SDK claims, stable claims, or current-turn live-op scope. Do not
write or execute an operational runbook unless those details are named by the current-turn
brief or recorded standing launch authorization.

## Production Baseline

Keep production/shared baselines simple: ProcessEvent hook enabled only when intended,
plugins disabled unless a maintenance window explicitly scopes a plugin test,
scanner/native-exec/broad tracing off, and no restarts or marker edits without
current-turn approval for the exact scoped run or the recorded standing launch
authorization for the same named operation. Server restarts are never implied by research
progress: require explicit current-turn operator approval for the exact scoped run when
the recorded standing launch authorization does not apply, and only request or reuse that
authority when new runtime logs are needed after a concrete offline/code advance.
Offline config preparation tools must not read `ShooterGameServer` directly from
`/servidor/ark`; use a copied offline binary artifact or an explicit, recorded SHA256.
Offline evidence-pack and release-readiness report tools must not write under protected
live-server paths or historical dump subdirectories. `/servidor/ark/workspace-offline` is
allowed only when a current-turn operator-approved offline artifact scope explicitly
permits under-`/servidor/ark` writes, or when the recorded standing launch authorization
names the same evidence path and operation; it is not standing approval to read or write
`/servidor/ark` outside those named evidence operations. Otherwise use `/tmp` or another
current-turn operator-approved or standing-authorized offline artifact workspace.

```bash
# Only run marker/start/stop commands when that exact change is part of a
# current-turn operator-approved debug/development instance test window or a
# standing-authorized launch/evidence run:
# mkdir -p /servidor/ark/obelisk/state/instances/<approved-instance-id>
# touch /servidor/ark/obelisk/state/instances/<approved-instance-id>/enable-process-event-hook
# touch /servidor/ark/obelisk/state/instances/<approved-instance-id>/disable-plugins
# env -u TMUX ./<approved-instance-id> start
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

Post-checks after a current-turn approved or standing-authorized runtime experiment should
use the same exact target and should reject experimental observers unless the approved
maintenance plan explicitly says otherwise:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

## Experiment Gates

- Keep experimental plugins outside `plugins/` until an isolated server test passes.
- Publish plugin `.so` files with
  `scripts/install_obelisk_plugin.sh <PluginName.so> <obelisk-root>` or an equivalent
  staged non-`.so` copy plus atomic rename. Do not copy directly into the active shared
  plugin directory while ARK instances may restart.
- Enable one marker/config gate at a time and record the exact change.
- Use instance markers under `state/instances/<instance-id>/`; map markers are obsolete.
- Observer markers are launch guards, not passive labels: a stable wrapper start must fail
  closed when any observer marker exists on the target instance. An approved observer
  window must use per-launch `OBELISK_WRAPPER_PROFILE=observer-debug`; set only the
  observer env/SHA/budget variables required by the exact observer marker on that same
  instance, and unset them for stable starts.
- When starting a LinuxGSM instance from a Codex/tmux shell, use `env -u TMUX ./<instance>
  start` so LinuxGSM does not fail with `tmuxception`. This does not authorize a start by
  itself; it is only the required form inside an already approved start window.
- Experimental runtime observers must have their own instance markers in addition to env
  gates, `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`, and
  `allow-experimental-observers` on the same instance. Current observer markers:
  - `allow-observer-debug-window`
  - `allow-experimental-observers`
  - `enable-chat-events`
  - `enable-chat-reflection`
  - `enable-chat-route-observer`
  - `enable-structure-reflection`
  - `enable-inventory-reflection`
  - `enable-item-return-events`
  - `enable-player-principal-lifecycle-observer`
- The player-principal lifecycle evidence window is stricter than a normal observer
  window: plugins disabled, `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0`,
  log limit exactly `10` for first approved evidence, exact observer exclusivity, and no
  debug/scanner/callback escape markers. Do not set
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1` for an approved evidence
  window; diagnostic candidate lines are useful debug signals but make the copied log
  non-promotable. Do not set
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1` in an
  approved evidence window either; it is a metadata-only debug aid for separate
  non-promotable windows. Do not set
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1` or
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT` in an approved evidence window;
  route samples log only bounded FName metadata and are diagnostic non-evidence for
  separate debug windows. Smaller safe limits require checker/test updates before the
  approved window, not operator improvisation. Organic-player wait windows must be bounded by the
  checked request tooling, with a 15-minute minimum and a 2-hour maximum for broad
  passive waits when the window request, beta notice, activation preconditions, and
  completed receipt bind either the current-turn approval or the recorded standing launch
  authorization before the window starts. A longer wait is a passive capture window, not
  permission to chain restarts while waiting for players. The wrapper must reject
  residual observer markers or symlink marker entries on the same instance, and approved
  evidence must be copied/analyzed as a single-module `player_principal_lifecycle`
  summary only. Evidence bundles must be bound to a checked sibling set:
  `window-request.json`, `observer-window.env`, `operator-approval-request.md`,
  completed `operator-approval-receipt.json`, `preflight-pre.json`,
  `preflight-post.json`, `window-manifest.env`, and the copied `Obelisk.log`. Generated
  receipt templates never count; completed receipts count only in `--post-window-replay`.
  The checked `--window-manifest` source path/SHA must match the analyzed copied log and
  preserve stable posture, rollback, no-claim, and no-public-readiness semantics. This
  remains consume-only and does not promote public player identity, lookup, permissions,
  commands, or SDK completion. Post-correlation accepted evidence must include safe
  observer fields: `session_end` requires `apply_status=session_end_invalidated` and
  `correlation_status=matched`; old-format logout lines, unresolved, missing, duplicate,
  stale, unsupported, or registry-failure logout outcomes remain non-evidence.
- Runtime debug/scanner gates also require both env and instance markers:
  - `allow-ptrace`
  - `enable-debug-control`
  - `enable-reflection-scanner`
  - `enable-native-exec-probes`
- Never enable native exec probes without explicit current-turn operator approval or the
  recorded standing launch authorization for the named debug run.
- Do not set `OBELISK_DEBUG_ALLOW_PTRACE=1` by default in debug wrappers. Ptrace requires
  a current-turn approved or standing-authorized isolated run plus the `allow-ptrace`
  marker.
- Never enable `ReflectionScanner` on a player-facing instance while users are active.
  When the operator explicitly selects a live/beta instance for in-game function testing,
  keep the window narrow: announce the test through the current-turn operator-approved or
  standing-authorized notice path before activation, enable only the markers required by
  the exact feature under test, preserve copied-log evidence, avoid raw player
  text/identity logging, and make marker/env rollback explicit.
- For player-backed evidence windows, the approved notice path is an action, not passive
  documentation. If the current-turn brief or recorded standing authorization names the
  beta testers Discord path or another player notice path, send the approved
  dry-run-checked notice before activation; otherwise request the missing notice scope
  instead of silently waiting for players.
- Player counting can be inconsistent during ARK load, cluster transfer, or local RCON
  timeouts. Treat GameDig, redacted RCON `ListPlayers`, and the latest Obelisk lifecycle
  observer event as separate signals. For Obelisk debug windows, an unclosed latest
  `session_start` is a player-presence candidate even when GameDig reports `0/70` and
  RCON times out; a later matched `session_end` clears that candidate. Broadcast/Discord
  the recommended action and scheduled operation, then continue the development-critical
  operation after the courtesy window under the recorded standing authorization.
  Passive monitor `player_presence_context` output is the preferred combined summary:
  `presence_detected=false` is not the same as `no_users_confirmed=true`. When GameDig
  says `0/70` but RCON is timeout/unknown, keep `unknown_player_context=true` and avoid
  claiming a confirmed empty server from that tick alone.
- Restart a server with connected players only when it is strictly necessary to advance
  ObeliskSDK. When that is unavoidable, use the approved RCON/beta-notice path to
  broadcast the planned action, give a prudent timer, and tell players which available
  cluster server to transfer to. Keep at least one ARK server available for player
  cluster transfer when players must move, while preserving the hard maximum of two
  running ARK servers. Do not start an extra transfer server for a restart when no players
  are detected.
- Never persist `OBELISK_WRAPPER_PROFILE=observer-debug` in a normal service environment.
  It is a per-launch debug-window profile for the normal wrapper.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for
  current-turn approved or standing-authorized exact evidence windows.
- Do not move debug instrumentation to any player-facing instance until the same posture
  is proven on the current approved isolated target and the operator gives current-turn
  approval or the recorded standing launch authority applies for an exact privacy-bounded
  player signal window.
- For player-dependent evidence, prefer a passive wait window over repeated restarts once
  the scoped observer build is deployed. A passive window may wait for organic player logs
  while offline development continues only when the operator has approved the exact
  target, env/markers, evidence path, rollback posture, and privacy bounds. During that
  wait, use read-only Steam/GameDig query or log tailing; do not call LinuxGSM `monitor`,
  and do not start/stop/restart again just because no player has joined yet. Once players
  are connected, do not restart merely to broaden observer coverage or add side-lane
  logging; capture with the already active gates, keep optional side-lane packs prepared
  offline, and defer broader observers to the next necessary deploy/restart window unless
  a code/gate change is strictly required to advance ObeliskSDK. Candidate-only
  diagnostic lines must remain non-evidence until the approved checkers accept a copied
  evidence bundle. Passive-wait approval is wait-only: passive monitor ticks,
  player-presence detections, snapshots, and diagnostic summaries do not authorize
  deployment, marker/env changes, starts/stops/restarts, runtime capture, publication, or
  readiness claims. Any active follow-up must request fresh current-turn exact scope when
  the recorded standing launch authority does not apply, or use the recorded standing
  launch authority for the named action. The canonical connected-player warning check is
  read-only and must stay inside the approved passive/read-only scope:
  `scripts/monitor_ark_player_presence_passive.sh --once --no-details <instance-id>:<map>[:query-port]`.
  Treat `player_presence_detected` and `query_warning` output as operator warning
  metadata only, not lifecycle evidence or authorization for any follow-up action. For
  long passive waits, run
  `scripts/monitor_ark_player_presence_passive.sh` with `--no-details` when stopped
  instances are included, and use `--linger-after-detect` when short organic joins may
  otherwise end before delayed lifecycle lines are tailed. This avoids slow LinuxGSM
  `details` helper processes while still using GameDig query and Obelisk log tails.

## Debug Profiles

Use named profiles instead of ad hoc env mixes:

- Stable dev: ProcessEvent hook on, plugins disabled, scanner/static roots/native exec off.
- Runtime debug control: plugins disabled, scanner/native exec off,
  `enable-debug-control` marker enabled only for a short window, request marker consumed,
  then immediate restart back to stable dev.
- Scanner capture: current-turn operator-approved or standing-authorized debug window
  only, named instance,
  plugins disabled, native exec off, one scanner env family enabled, copied logs analyzed
  offline, then immediate restart back to stable dev inside the same approved window.
- Plugin capture: scanner off, only the target plugin installed, plugin config backed up,
  short run, then return to stable dev.
- Item-return copied-event capture: current-turn operator-approved or standing-authorized
  debug window only, named instance, plugin/subscriber plan explicit,
  `enable-item-return-events` gated by observer-debug markers, positive dispatch budget,
  optional bounded log budget, copied logs analyzed offline, then return to stable dev.

After any scanner/plugin capture, run the posture check for the same current-turn approved
or standing-authorized debug target:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Use the matching explicit `--map` and `--instance` for the current-turn approved or
standing-authorized debug target. That check must pass before launching another agent
round that assumes a stable server.
In `--expect-stable` mode it must fail closed if `libobelisk.so` is not mapped, if a
deleted `libobelisk` mapping remains after redeploy, if `LD_PRELOAD` does not include the
central `${OBELISK_ROOT}/lib/libobelisk.so`, if scanner/native-exec variables are still
present, if stable markers `enable-process-event-hook` and `disable-plugins` are missing,
if the instance id or marker directory would be rejected by the wrapper/runtime, if
chat, chat-route, inventory, or structure observer variables are present, or if per-instance marker entries
would re-enable forbidden experimental features at the next restart. It rejects a
forbidden marker name even when the entry is malformed or a symlink.
Its parser is tested offline with procfs fixtures; do not weaken those tests to depend on a
live ARK process.

## Runtime Debug Control

`OBELISK_ENABLE_DEBUG_CONTROL=1` watches:

```text
/servidor/ark/obelisk/state/instances/<instance-id>/
```

Current request marker:

```text
request-static-fname-probe
```

Use it to trigger bounded probes after the ARK process is already alive. Do not use it as
stable posture, and do not leave `enable-debug-control` present after the capture.

Known result: a post-start probe of `0x5956f30` on `arkserver` worked mechanically but
rejected the slot (`table=0x13733660`, `implausible_num_elements`). This proves waiting
longer in bootstrap is not the right strategy; next work should scan live data mappings or
derive roots from code/data references instead of pinning that single slot.

## Overnight Supervision

Unattended cron-style work may collect read-only snapshots only when the operator has
explicitly approved that recurring read-only snapshot scope:

- git status/log head,
- server posture,
- LinuxGSM wrapper drift status,
- recent Obelisk logs,
- marker list,
- disk/memory/process summary.

Do not let cron build, install, restart, edit marker files, attach debuggers, run gcore,
enable scanners, commit, push, or create GitHub state. Those require an active lead turn.

## Config Restore Backups

Before SteamCMD/LinuxGSM updates or risky server config work, refresh the gameplay config
backup described in `docs/SERVER_RESTORE.md`. The latest symlink should be:

```text
/home/flowcommunity-ark/backups/ark-config-latest
```

Preserve at minimum:

```text
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
/servidor/ark/lgsm/config-lgsm/arkserver/*.cfg
```

Do not restore old binary-local `libobelisk.so`, `ObeliskPlugins/`, logs, or state markers
as part of config recovery.

## Operational Checks

Before a current-turn approved or standing-authorized restart, these checks are read-only
context:

```bash
git -C /home/flowcommunity-ark/Obelisk status --short
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/plugins
ls -la /servidor/ark/obelisk/state
```

LinuxGSM `details` or failure lines may report `servername`/`SessionName` from the shared
`GameUserSettings.ini`; do not use that label to identify which instance started or
failed. Verify the instance from wrapper args/map, `OBELISK_INSTANCE_ID`, PID command
line, ports, marker path, and copied logs.

After a current-turn approved or standing-authorized maintenance-window restart on a
protected live-like instance, use the profile named for that exact run and explicit
map/instance values:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /path/to/copied/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer <map>' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Current server-backed debug target context comes from `docs/agent-handoff/CURRENT.md`, but
that file alone does not grant approval; use it with `COMPACT_CONTEXT.md` to confirm a
recorded standing launch authorization, or use an exact current-turn approval. The target
may be a dedicated debug instance or a current-turn approved or standing-authorized
beta-test instance. For powered-off debug instances, start only for the exact scoped test,
restore stable posture, then shut down when the approved run plan requires it. For
player-facing beta instances, do not assume shutdown; follow the current-turn approved or
standing-authorized maintenance/beta window:

```bash
tail -n 100 /servidor/ark/obelisk/logs/<instance-id>/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer <map>' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

## Rollback

If a current-turn approved or standing-authorized target crashes after an Obelisk change,
preserve logs/core files first. For a powered-off debug target, stop it at the end of the
exact test or rollback window. For a player-facing beta target, restore the approved
stable markers/config and restart only if the maintenance plan requires it:

```bash
# Preserve evidence first.
# mkdir -p /servidor/ark/obelisk/state/instances/<instance-id>
# touch /servidor/ark/obelisk/state/instances/<instance-id>/disable-plugins
# env -u TMUX ./<instance-id> stop
```

Preserve logs and core files before rebuilding or changing markers again.
