# Obelisk Supervision

This project can use unattended observation, but not unattended development.

## Safe Overnight Cron

Allowed unattended job:

```cron
*/30 * * * * /home/flowcommunity-ark/Obelisk/scripts/obelisk_supervisor_snapshot.sh >/dev/null 2>&1
```

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

If `posture.txt` shows failure, stop and restore stable posture before launching agents or
runtime experiments.
