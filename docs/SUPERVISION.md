# Obelisk Supervision

This project can use unattended observation, but not unattended development.

## Safe Overnight Cron

Allowed unattended job:

```cron
*/30 * * * * /home/flowcommunity-ark/Obelisk/scripts/obelisk_supervisor_snapshot.sh >/dev/null 2>&1
```

For an already supervised open shell, use a finite timer loop instead of installing cron:

```bash
/home/flowcommunity-ark/Obelisk/scripts/obelisk_supervisor_loop.sh --interval 1800 --count 8
```

Use `--count 0` only when a human lead is actively keeping the session open and can stop
or review it. The loop only runs the same read-only snapshot script.

It writes read-only snapshots under:

```text
/servidor/ark/obelisk/dumps/supervisor/
```

and updates:

```text
/servidor/ark/obelisk/dumps/supervisor/latest
```

## What It Captures

- Git status and recent commits.
- Server posture check.
- ARK/Obelisk process list.
- Obelisk marker files.
- Recent Obelisk logs.
- Chat reflection marker/log summary.
- Disk usage.

## What It Must Not Do

- Restart servers.
- Install runtime libraries.
- Edit marker files.
- Enable scanners or debug control.
- Attach debuggers or create core dumps.
- Commit, push, tag, or change GitHub state.

## Morning Review

```bash
latest=/servidor/ark/obelisk/dumps/supervisor/latest
cat "${latest}/summary.txt"
cat "${latest}/posture.txt"
cat "${latest}/git-status.txt"
cat "${latest}/chat-reflection.txt"
tail -n 80 "${latest}/obelisk-log-tail.txt"
```

`chat-reflection.txt` summarizes marker and log evidence. It proves only whether the
experimental gate and log lines are present; it does not prove chat text capture unless
`reflected_chat_lines` is non-zero and the lines are reviewed.

`rejected_chat_lines` counts bounded reflection rejections when the runtime is built with
that diagnostic path. `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0` disables those experimental
chat reflection observation logs.

If `posture.txt` shows failure, stop and restore stable posture before launching agents or
runtime experiments.
