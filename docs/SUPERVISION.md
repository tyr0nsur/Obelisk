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

## Manual ServerSendChatMessage Check

Use this after deploying a build that recognizes
`ShooterPlayerController.ServerSendChatMessage`. The expected safe posture is ProcessEvent
hook enabled, plugins disabled, and chat reflection enabled only for the supported binary
SHA gate.

Before sending chat, start a live tail in one shell:

```bash
tail -Fn 0 /servidor/ark/obelisk/logs/arkserver/Obelisk.log \
  | rg --line-buffered 'Experimental chat reflection|Reflected chat|Chat reflection rejected|Reflected chat rejected'
```

In another shell, keep a read-only snapshot command ready:

```bash
cd /home/flowcommunity-ark/Obelisk
scripts/obelisk_supervisor_snapshot.sh
latest=/servidor/ark/obelisk/dumps/supervisor/latest
cat "${latest}/chat-reflection.txt"
tail -n 80 "${latest}/obelisk-log-tail.txt"
```

Then send exactly one normal in-game chat message from a client on Ragnarok. Expected
successful evidence is a bounded `Reflected chat ProcessEvent` line for
`ServerSendChatMessage`, with reflected metadata showing the
`ShooterPlayerController.ServerSendChatMessage` path and parameter ranges for
`ChatMessage` at offset `0x0` and `SendMode` at offset `0x10`. This proves the reflected
`ProcessEvent` path was hit; it does not by itself promote public plugin ABI or justify
broader chat-name scans.

Interpret the snapshot counters this way:

- `reflected_chat_lines=0`: no accepted reflected chat hit is present in the reviewed log.
  If the player definitely sent chat after deployment, treat this as inconclusive or a
  runtime-path miss, not as proof that chat is absent from `ProcessEvent`.
- `reflected_chat_lines>0`: review the actual `Reflected chat ProcessEvent` lines. Accept
  only lines that name `ServerSendChatMessage` or its reflected fields; older `ServerChat*`
  lines are cheat-manager coverage, not proof of normal player chat.
- `rejected_chat_lines>0`: the cheap chat filter saw a candidate FName, but reflected
  `UFunction`/property/`ParmsSize` validation rejected it. Rejections are useful evidence
  for debugging constants, but they are not successful chat capture.
- `rejected_chat_lines=0`: no bounded rejection line was logged. This can also mean the
  diagnostic path or log limit suppressed rejection details.

Rollback is marker-only plus a controlled restart:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver/enable-chat-reflection
/servidor/ark/arkserver restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable
scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
```

After rollback, `chat_reflection_marker=disabled` is expected. Do not remove
`enable-process-event-hook` or `disable-plugins` for this rollback; they are part of the
current stable baseline.
