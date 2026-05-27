# Quiet Posture Read-Only Audit

## Objective

Use the new `--forbid-chat-reflection` guard to separate stable debug posture from quiet
production/performance posture without changing server state.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit: `5da65d6`
- ARK root: `/servidor/ark`
- Protected performance target: `arkserver` / Ragnarok
- Debug target: `arkserver2` / TheIsland
- Method: read-only posture checks and process listing only

## Method

Commands run:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map Ragnarok --instance arkserver
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
pgrep -af '^./ShooterGameServer'
```

No marker files, configs, deployments, plugins, or server processes were changed.

## Evidence

Ragnarok process:

```text
pid=3940524
OBELISK_INSTANCE_ID=arkserver
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_CHAT_REFLECTION_LOG_LIMIT=25
Forbidden OBELISK_ENABLE_CHAT_REFLECTION is set to '1'.
```

TheIsland check:

```text
No ShooterGameServer process found for map prefix 'TheIsland'.
```

Active ARK process listing showed only the Ragnarok `ShooterGameServer` process.

## Result

- `arkserver` / Ragnarok is up, but it does not satisfy quiet production/performance
  posture because experimental chat reflection remains enabled.
- `arkserver2` / TheIsland is not currently running, so it cannot serve as an immediate
  runtime debug harness until an operator-approved start/restart window opens.
- This audit does not say Ragnarok is crashing or unstable. It says the stricter
  production/performance guard correctly detects an experimental chat reflection gate.

## Risks

- Leaving chat reflection enabled on Ragnarok can contaminate player performance testing
  because it keeps experimental `ProcessEvent` chat observation active.
- Automatically removing the marker and restarting Ragnarok would interrupt players and is
  outside this read-only audit.
- Starting TheIsland without an approved debug window would be operational work, not an
  offline development round.

## Next Steps

1. When the operator opens a maintenance window, remove the Ragnarok chat reflection marker
   and restart only `arkserver`, then run:

   ```bash
   scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map Ragnarok --instance arkserver
   ```

2. When the operator opens a TheIsland debug window, start `arkserver2` in the documented
   stable debug posture and follow
   `docs/research/2026-05-27-theisland-chat-reflection-ab-runbook.md`.
3. Continue offline development, ABI gating, and evidence-pack work while no runtime debug
   window is open.
