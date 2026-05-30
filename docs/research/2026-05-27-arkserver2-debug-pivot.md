# arkserver2 Debug Pivot

> Historical/superseded as of 2026-05-28: do not execute these `arkserver2` /
> TheIsland commands unless the operator explicitly approves a scoped test window.
> Current operator direction protects `arkserver` / Ragnarok while users are active;
> start `arkserver2` only for the approved test and shut it down afterward.

## Objective

Record the operational pivot requested on 2026-05-27: protect `arkserver` / Ragnarok for
player performance testing and use `arkserver2` / TheIsland as the Obelisk
debug/development target for future runtime validation and research.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- ARK root: `/servidor/ark`
- Stable production/performance target: `arkserver` / Ragnarok
- Debug/development target: `arkserver2` / TheIsland
- Central Obelisk root: `/servidor/ark/obelisk`
- This note changes workflow documentation only. It does not restart servers, edit marker
  files, deploy runtime, or inspect live player data.

## Decision

`arkserver` / Ragnarok is currently reserved for player performance testing. Development
work must not use it for experiments while that testing is active.

Future runtime validation and research that needs an ARK server harness should target
`arkserver2` / TheIsland instead.

## Safety Rules

Allowed on `arkserver2` after normal maintainer review:

- controlled runtime validation;
- plugin lifecycle/debug checks;
- bounded chat reflection validation;
- copied-log analysis;
- stable posture verification with `scripts/check_obelisk_server_posture.sh --expect-stable
  --map TheIsland --instance arkserver2`.

Still requires a specific operator-approved run window:

- `ReflectionScanner`;
- `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1`;
- ptrace/gcore;
- broad `ProcessEvent` tracing;
- `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`;
- plugin experiments with HTTP, threads, file readers, or external ingress.

Forbidden on `arkserver` / Ragnarok during player performance testing:

- restarts;
- marker changes;
- runtime deployment;
- scanner/native-exec/ptrace;
- broad logging or tracing;
- chat text logging;
- plugin activation experiments.

## Standard TheIsland Debug Baseline

When an approved TheIsland debug window exists, start from the quiet stable posture:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
touch /servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
./arkserver2 restart
```

Post-check:

```bash
tail -n 100 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer TheIsland' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
```

## Rollback

For any TheIsland debug run:

1. Remove the experiment marker or env.
2. Keep `disable-plugins`.
3. Restart only `arkserver2`.
4. Run stable posture check with `--map TheIsland --instance arkserver2`.
5. Preserve copied logs outside Git and summarize only the evidence.

## Result

Workflow documentation and relevant skills have been updated so future debug work targets
`arkserver2` / TheIsland for Obelisk debug/development rounds and avoids disrupting
Ragnarok performance testing.

## Next Steps

- Audit scripts/docs for remaining Ragnarok-default commands before any runtime operation.
- If a higher-risk scanner capture is needed, request an explicit TheIsland debug window
  or create the cleaner `arkserver-obelisk-debug` instance.
- Continue offline SDK/runtime work while players are testing Ragnarok performance.
