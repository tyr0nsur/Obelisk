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
- LinuxGSM wrapper drift check.
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
cat "${latest}/wrapper-drift.txt"
cat "${latest}/posture.txt"
cat "${latest}/git-status.txt"
cat "${latest}/chat-reflection.txt"
tail -n 80 "${latest}/obelisk-log-tail.txt"
```

`summary.txt` includes `pid`, `linuxgsm_wrapper_drift_status`, `posture_status`,
`quiet_posture_status`, and `stable_posture_summary`. A usable
overnight snapshot must show `posture_status=ok`; if it shows `failed`, the snapshot
stopped early, `chat-reflection.txt` is marked `skipped_unstable_posture=true`, and the
lead should restore stable posture before interpreting chat/reflection evidence.

`linuxgsm_wrapper_drift_status=failed` does not mean the current process changed; it means
the installed launcher no longer matches the versioned template and must be refreshed
during an approved maintenance window before trusting the next restart.

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

## Candidate Module Observer Pattern

Candidate observers are internal evidence tools, not public SDK surfaces. Use the same
pattern for chat, inventory, structures, buffs, dinos, tribes, missions, transfers, and
admin flows:

- use only an approved debug/development target from `docs/agent-handoff/CURRENT.md`;
- require the global experimental observer marker plus the module marker;
- require the supported binary SHA gate;
- set an explicit non-zero observation budget for the module;
- keep plugins disabled unless the approved test specifically needs them;
- capture copied logs and a supervisor snapshot;
- treat accepted/rejected observer lines as evidence only, not ABI readiness.

Module-specific runbooks can add exact tail filters, player actions, evidence fields, and
rollback details. The historical chat A/B procedure lives in
`docs/research/2026-05-27-theisland-chat-reflection-ab-runbook.md`.

Rollback is marker-only plus a controlled restart during the approved debug window. The
commands below are an example for an explicitly approved TheIsland fallback window; do not
run them from an ordinary documentation review, unattended round, or while `arkserver2`
is intentionally stopped for RAM:

```bash
# Approved debug-window rollback only:
# rm -f /servidor/ark/obelisk/state/instances/arkserver2/allow-experimental-observers
# rm -f /servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection
# /servidor/ark/arkserver2 restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
OBELISK_SUPERVISOR_INSTANCE=arkserver2 OBELISK_SUPERVISOR_MAP=TheIsland scripts/obelisk_supervisor_snapshot.sh
cat /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
```

After rollback, `chat_reflection_marker=disabled` is expected. Do not remove
`enable-process-event-hook` or `disable-plugins` for this rollback if that approved
fallback profile uses them. The current server-backed development/test target is
`arkserver2` / TheIsland only after explicit operator approval; it starts from powered off
and must be shut down when the window ends. Keep `arkserver` / Ragnarok untouched while
users are active.
