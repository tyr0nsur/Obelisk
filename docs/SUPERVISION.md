# Obelisk Supervision

This project can use unattended observation, but not unattended development.

## Safe Overnight Cron

Allowed unattended job:

```cron
*/30 * * * * /home/flowcommunity-ark/Obelisk/scripts/obelisk_supervisor_snapshot.sh >/dev/null 2>&1
```

The default snapshot target is `arkserver-obelisk-debug` so Ragnarok player performance
tests and TheIsland fallback windows are not used as the normal evidence stream. To
intentionally snapshot another instance, set `OBELISK_SUPERVISOR_INSTANCE` and
`OBELISK_SUPERVISOR_MAP` explicitly. Use TheIsland only during an explicitly approved
debug window for that named instance.

For an already supervised open shell, use a finite timer loop instead of installing cron:

```bash
/home/flowcommunity-ark/Obelisk/scripts/obelisk_supervisor_loop.sh --interval 1800 --count 8
```

Use `--count 0` only when a human lead is actively keeping the session open and can stop
or review it. The loop only runs the same read-only snapshot script.
Do not edit or redeploy `scripts/obelisk_supervisor_loop.sh` while an instance of that
same script is sleeping; stop it first or let the finite loop finish. Bash reads script
files progressively, so changing the file mid-run can make the old process exit with a
parse error even when the new file is valid.

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
- Quiet production/performance posture check.
- Stable posture summary and PID.
- ARK/Obelisk process list.
- Obelisk marker files.
- Recent Obelisk logs.
- Chat reflection gate marker/env/log summary.
- Disk usage.

## What It Must Not Do

- Restart servers.
- Install runtime libraries.
- Edit marker files.
- Enable scanners or debug control.
- Attach debuggers or create core dumps.
- Commit, push, tag, or change GitHub state.

## Retention

Supervisor snapshots are intentionally small text evidence packs. Keep them under
`/servidor/ark/obelisk/dumps/supervisor/`; they can be pruned after their findings have
been summarized into `docs/research/` or `docs/agent-handoff/`.

Core dumps and evidence packs under `/servidor/ark/obelisk/dumps/` are different: do not
delete them just because they are large. They may be the only reproducible source for
accepted offsets, FName/GObjects evidence, and UFunction property chains. Prune them only
after recording which research notes, commits, and verifier outputs replace that evidence.

## Morning Review

```bash
latest=/servidor/ark/obelisk/dumps/supervisor/latest
cat "${latest}/summary.txt"
cat "${latest}/posture.txt"
cat "${latest}/git-status.txt"
cat "${latest}/chat-reflection.txt"
tail -n 80 "${latest}/obelisk-log-tail.txt"
```

`summary.txt` includes `pid`, `posture_status`, `quiet_posture_status`, and
`stable_posture_summary`. A usable
overnight snapshot must show `posture_status=ok`; if it shows `failed`, the snapshot
stopped early, `chat-reflection.txt` is marked `skipped_unstable_posture=true`, and the
lead should restore stable posture before interpreting chat/reflection evidence.

`quiet_posture_status=failed` does not invalidate a debug snapshot. It means the stricter
production/performance check found chat reflection or chat text logging enabled. Review
`quiet-posture.txt` before using the instance as a Ragnarok-like performance baseline.

`chat-reflection.txt` summarizes marker, env, and log evidence. It proves only whether the
experimental gate and log lines are present; it does not prove chat text capture unless
`reflected_chat_process_event_lines` is non-zero and the lines are reviewed.

`rejected_chat_lines` counts bounded reflection rejections when the runtime is built with
that diagnostic path. `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0` disables those experimental
chat reflection observation logs and short-circuits the reflection observation work.

`server_send_chat_message_lines` counts any log line mentioning `ServerSendChatMessage`,
including the main `ProcessEvent` line and the send-mode summary. Use it as a pointer to
review the lines, not as a count of player messages. The `client_chat_message_lines`,
`client_server_chat_message_lines`, and `client_server_chat_direct_message_lines`
counters track exact metadata-only fallback candidates. `metadata_only_lines` counts
fallback observations that must not be treated as confirmed inbound chat. `chat_candidate_lines`
counts all exact chat candidate function-name lines. `rejected_or_unknown_send_mode_lines`
counts either reflected rejection lines or `send_mode_known=false`; non-zero means the
snapshot found evidence that needs active review before promotion. `last_relevant_line`
shows the last chat/reflection line matched by the snapshot.

## Candidate Module Observer Example

This historical chat observer flow is an example for candidate module validation, not the
center of the SDK roadmap. Use it only after deploying a build that recognizes
`ShooterPlayerController.ServerSendChatMessage`. The expected safe posture is ProcessEvent
hook enabled, plugins disabled, and chat reflection enabled only for the supported binary
SHA gate.

For the full approved-window A/B flow, including reflection-off baseline, metadata-only
validation, text-log gate, evidence fields, and rollback, use
`docs/research/2026-05-27-theisland-chat-reflection-ab-runbook.md`.

Run this on `arkserver-obelisk-debug`. Use `arkserver2` / TheIsland only during an
explicitly approved debug window for that named instance, not on Ragnarok while players
are testing performance. Before sending chat, start a live tail in one shell:

```bash
tail -Fn 0 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log \
  | rg --line-buffered 'Experimental chat reflection|Reflected chat|Chat reflection rejected|Reflected chat rejected|metadata_only=true|ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage'
```

In another shell, keep a read-only snapshot command ready:

```bash
cd /home/flowcommunity-ark/Obelisk
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
latest=/servidor/ark/obelisk/dumps/supervisor/latest
cat "${latest}/chat-reflection.txt"
tail -n 80 "${latest}/obelisk-log-tail.txt"
```

Then send exactly one normal in-game chat message from a client on the approved debug
target. For TheIsland, do this only after explicit approval for that run window. Expected
successful evidence is a bounded `Reflected chat ProcessEvent` line for
`ServerSendChatMessage`, with reflected metadata showing the
`ShooterPlayerController.ServerSendChatMessage` path and parameter ranges for
`ChatMessage` at offset `0x0` and `SendMode` at offset `0x10`. A supporting
`Reflected chat ServerSendChatMessage send_mode=<n> send_mode_name=<name>` line should
also appear when the parameter range is readable. This proves the reflected `ProcessEvent`
path was hit; it does not by itself promote public plugin ABI or justify broader
chat-name scans.

If `ServerSendChatMessage` does not appear but a `ClientChatMessage`,
`ClientServerChatMessage`, or `ClientServerChatDirectMessage` line appears with
`metadata_only=true`, record it as fallback evidence only. It can guide the next runtime
investigation, but it must not dispatch plugin chat events or decode text.

Interpret the snapshot counters this way:

- `reflected_chat_process_event_lines=0`: no accepted reflected chat hit is present in the reviewed log.
  If the player definitely sent chat after deployment, treat this as inconclusive or a
  runtime-path miss, not as proof that chat is absent from `ProcessEvent`.
- `reflected_chat_process_event_lines>0`: review the actual `Reflected chat ProcessEvent` lines. Accept
  only lines that name `ServerSendChatMessage` or its reflected fields; older `ServerChat*`
  lines are cheat-manager coverage, not proof of normal player chat.
- `server_send_chat_message_lines>0`: review the matching lines; this counter can include
  field or send-mode diagnostics for the same ProcessEvent hit.
- `metadata_only_lines>0`: review exact fallback lines. These are useful path evidence,
  not accepted inbound chat.
- `client_chat_message_lines>0`, `client_server_chat_message_lines>0`, or
  `client_server_chat_direct_message_lines>0`: review the matching fallback candidate
  lines and keep them separate from `ServerSendChatMessage`.
- `rejected_chat_lines>0`: the cheap chat filter saw a candidate FName, but reflected
  `UFunction`/property/`ParmsSize` validation rejected it. Rejections are useful evidence
  for debugging constants, but they are not successful chat capture.
- `rejected_or_unknown_send_mode_lines>0`: at least one rejection or
  `send_mode_known=false` line is present. Treat it as a prompt for active review rather
  than success evidence.
- `rejected_chat_lines=0`: no bounded rejection line was logged. This can also mean the
  diagnostic path or log limit suppressed rejection details.

Rollback is marker-only plus a controlled restart during the approved debug window. Do not
run this block from an ordinary documentation review or unattended round:

```bash
# Approved debug-window rollback only:
# rm -f /servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection
# /servidor/ark/arkserver2 restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
```

After rollback, `chat_reflection_marker=disabled` is expected. Do not remove
`enable-process-event-hook` or `disable-plugins` for this rollback; they are part of the
current TheIsland debug baseline.
