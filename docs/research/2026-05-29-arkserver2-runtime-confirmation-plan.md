# arkserver2 Runtime Confirmation Plan

## Purpose

Prepare the next safe `arkserver2` / TheIsland runtime confirmation window for the case
where offline evidence proves a runtime-only question remains. This document is a plan
only. It does not authorize a run by itself, and it does not authorize marker edits,
start/stop/restart, runtime observation, beta/community notice, or changing `arkserver` /
Ragnarok.

Current default: do not run the server. Prefer offline cores, static evidence, fixtures,
and copied logs until they leave a specific runtime-only gap.

## Run Gate

Run only when all of these are true:

- The target is exactly `arkserver2` / TheIsland.
- Offline evidence names the exact module family and expected functions.
- The supported ShooterGameServer SHA gate is known for the artifact under test:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Focused local tests for the observer family, marker gates, budget behavior, and copied
  data ownership have passed.
- The question cannot be answered from staged offline cores, static xrefs, snapshot
  comparison, or copied historical logs.
- The operator gives explicit current-turn approval for the exact scoped run, including the
  target, marker/env deltas, start/restart command, rollback, evidence capture, and
  shutdown-after-test posture.

Do not include ReflectionScanner, native exec probes, ptrace, `gcore`, broad
ProcessEvent tracing, chat text logging, or Ragnarok validation in this plan.

## Evidence That Justifies Running

Runtime confirmation is justified only for a concrete question such as:

- Does the exact supported-binary observer gate activate on `arkserver2` without enabling
  unrelated observers?
- Do real gameplay calls hit the exact accepted FName indexes after the original
  `ProcessEvent` path remains intact?
- Do bounded metadata logs show the accepted field shapes without pincode values,
  inventory contents, player identity, tribe/team identity, object identity, raw params,
  or mutation?
- Does a positive dispatch budget remain bounded and post-original, without requiring a
  public SDK surface or callback mutation?

It is not justified for candidate discovery, waiting longer for static roots, broad event
enumeration, scanner capture, or promotion of GNames/GObjects/global offsets.

## Preflight

Read-only preflight from the repo:

```bash
cd /home/flowcommunity-ark/Obelisk
git status --short
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
pgrep -af '^./ShooterGameServer' || true
find /servidor/ark/obelisk/state/instances/arkserver2 -maxdepth 1 -type f -printf '%f\n' | sort || true
```

Abort if any command shows an unexpected active `arkserver2` profile, stale experimental
observer markers from a previous run, a wrapper drift issue, or any reason to touch
`arkserver` / Ragnarok.

If `arkserver2` is already running in stable posture, verify it before changing anything:

```bash
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
```

The command blocks below are templates for a current-turn approved exact run. They assume
the normal starting point: `arkserver2` is powered off. If preflight proves it is already
running in stable posture, use `./arkserver2 restart` instead of `./arkserver2 start` only
when the current-turn approval names that restart, so the per-launch `observer-debug`
profile and budget variables take effect exactly once.

## Metadata-Only Observer Window

Use one module family per current-turn approved window. The default confirmation is
metadata-only: non-zero log budget, zero dispatch budget, plugins disabled, and
`OBELISK_PE_TRACE_LIMIT=0`.

Structure metadata-only window:

```bash
cd /servidor/ark
instance_dir=/servidor/ark/obelisk/state/instances/arkserver2
mkdir -p "${instance_dir}"
touch "${instance_dir}/enable-process-event-hook"
touch "${instance_dir}/disable-plugins"
touch "${instance_dir}/allow-observer-debug-window"
touch "${instance_dir}/allow-experimental-observers"
touch "${instance_dir}/enable-structure-reflection"
rm -f "${instance_dir}/enable-inventory-reflection" "${instance_dir}/enable-chat-reflection"

env -u TMUX \
  OBELISK_WRAPPER_PROFILE=observer-debug \
  OBELISK_PE_TRACE_LIMIT=0 \
  OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=5 \
  OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=0 \
  ./arkserver2 start
```

Inventory metadata-only window:

```bash
cd /servidor/ark
instance_dir=/servidor/ark/obelisk/state/instances/arkserver2
mkdir -p "${instance_dir}"
touch "${instance_dir}/enable-process-event-hook"
touch "${instance_dir}/disable-plugins"
touch "${instance_dir}/allow-observer-debug-window"
touch "${instance_dir}/allow-experimental-observers"
touch "${instance_dir}/enable-inventory-reflection"
rm -f "${instance_dir}/enable-structure-reflection" "${instance_dir}/enable-chat-reflection"

env -u TMUX \
  OBELISK_WRAPPER_PROFILE=observer-debug \
  OBELISK_PE_TRACE_LIMIT=0 \
  OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5 \
  OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=0 \
  ./arkserver2 start
```

During the run, trigger only the planned TheIsland test action. Stop after the first
useful bounded hit or after the budget is exhausted. Do not increase the budget in-place;
copy logs and analyze first.

## Dispatch-Budget Variant

Use this variant only when offline evidence asks for the internal copied dispatch path,
not just metadata, and the operator gives current-turn approval for that exact dispatch
scope. Keep only one observer marker enabled and keep plugins disabled unless a separate
current-turn approved plugin-capture plan explicitly names the minimal plugin and
rollback.

Structure dispatch-budget confirmation:

```bash
cd /servidor/ark
instance_dir=/servidor/ark/obelisk/state/instances/arkserver2
touch "${instance_dir}/enable-process-event-hook"
touch "${instance_dir}/disable-plugins"
touch "${instance_dir}/allow-observer-debug-window"
touch "${instance_dir}/allow-experimental-observers"
touch "${instance_dir}/enable-structure-reflection"
rm -f "${instance_dir}/enable-inventory-reflection" "${instance_dir}/enable-chat-reflection"

env -u TMUX \
  OBELISK_WRAPPER_PROFILE=observer-debug \
  OBELISK_PE_TRACE_LIMIT=0 \
  OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=5 \
  OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=1 \
  ./arkserver2 start
```

Inventory dispatch-budget confirmation:

```bash
cd /servidor/ark
instance_dir=/servidor/ark/obelisk/state/instances/arkserver2
touch "${instance_dir}/enable-process-event-hook"
touch "${instance_dir}/disable-plugins"
touch "${instance_dir}/allow-observer-debug-window"
touch "${instance_dir}/allow-experimental-observers"
touch "${instance_dir}/enable-inventory-reflection"
rm -f "${instance_dir}/enable-structure-reflection" "${instance_dir}/enable-chat-reflection"

env -u TMUX \
  OBELISK_WRAPPER_PROFILE=observer-debug \
  OBELISK_PE_TRACE_LIMIT=0 \
  OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5 \
  OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=1 \
  ./arkserver2 start
```

Success for this variant means the dispatch budget is reserved only after an exact
matched observer attempt and the server remains healthy. A zero callback dispatch count is
acceptable when plugins are disabled.

## Evidence Capture

Copy logs out to a non-live evidence directory and analyze the copy:

```bash
cd /home/flowcommunity-ark/Obelisk
evidence_dir=/tmp/obelisk-arkserver2-runtime-confirmation-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "${evidence_dir}"
cp -a /servidor/ark/obelisk/logs/arkserver2/Obelisk.log "${evidence_dir}/Obelisk.log"

OBELISK_SUPERVISOR_INSTANCE=arkserver2 \
OBELISK_SUPERVISOR_MAP=TheIsland \
OBELISK_SUPERVISOR_OUT="${evidence_dir}/supervisor" \
scripts/obelisk_supervisor_snapshot.sh

python3 scripts/analyze_runtime_observer_log.py \
  --fail-on-quality-blockers \
  "${evidence_dir}/Obelisk.log" \
  > "${evidence_dir}/runtime-observer-summary.json"
```

Do not publish or summarize gameplay text, pincode values, inventory contents, player
identity, tribe/team identity, locations, object identity, raw pointer values, or raw
params.

## Rollback And Shutdown

Rollback removes observer markers, restarts once into stable posture, verifies it, then
shuts TheIsland down only when those actions are part of the current-turn approved run:

```bash
cd /servidor/ark
instance_dir=/servidor/ark/obelisk/state/instances/arkserver2
rm -f "${instance_dir}/allow-observer-debug-window"
rm -f "${instance_dir}/allow-experimental-observers"
rm -f "${instance_dir}/enable-chat-reflection"
rm -f "${instance_dir}/enable-inventory-reflection"
rm -f "${instance_dir}/enable-structure-reflection"
touch "${instance_dir}/enable-process-event-hook"
touch "${instance_dir}/disable-plugins"

env -u TMUX ./arkserver2 restart

cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2

cd /servidor/ark
env -u TMUX ./arkserver2 stop
```

If the observer start crashes during a current-turn approved run, preserve copied logs and
any core/evidence first, then remove the observer markers, keep
`enable-process-event-hook` and `disable-plugins`, and stop `arkserver2` only as approved
by the current-turn approval for that exact rollback. Do not rebuild, redeploy, or change
markers again until copied evidence has been reviewed offline and a new current-turn
approval exists.

## Acceptance Criteria

Accept the run only if all of these hold:

- No commands targeted `arkserver` / Ragnarok.
- Plugins were disabled unless a separate current-turn approved plugin-capture plan
  existed.
- Only one observer family was enabled.
- `OBELISK_WRAPPER_PROFILE=observer-debug` was per-launch only.
- Log and dispatch budgets were explicit and small.
- `OBELISK_PE_TRACE_LIMIT` remained `0`.
- No scanner, ptrace, `gcore`, native exec probes, or broad tracing ran.
- Copied log analysis produced no quality blockers.
- Stable posture passed before final shutdown.
- `arkserver2` / TheIsland was stopped after the test window.
