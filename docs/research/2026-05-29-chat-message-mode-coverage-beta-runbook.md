# ChatMessageEvent Mode Coverage Beta Runbook

## Objective

Reusable approval-required runbook for future regression/revalidation windows proving
copied plugin-facing `ChatMessageEvent` delivery across chat send modes without logging
raw chat text, player identity, UE pointers, or live-server paths. Initial all-mode copied
plugin-facing validation is recorded in
`2026-05-29-chat-message-second-source-readiness.md`.

This runbook is not standing approval. Execute it only after an operator gives explicit
current-turn approval for the exact beta window, marker/env deltas, restart expectation,
rollback, evidence capture, and notice path, and after the beta-test notice is sent through
that current-turn approved path.

## Preconditions

- Target: `arkserver` / Ragnarok, only during the current-turn approved beta window.
- Current-turn operator approval names the exact beta window start/end, expected restart
  behavior, plugin posture delta, rollback delta, evidence capture, and beta-test notice
  path.
- Record a beta preflight note before marker/env changes:

```text
run_id=<YYYYMMDDThhmmssZ-chat-mode-coverage>
target=arkserver/Ragnarok
approval=current-turn operator-approved beta window, not standing approval
window_start_utc=<approved-start>
window_end_utc=<approved-end>
expected_marker_delta=+allow-observer-debug-window,+allow-experimental-observers,+enable-chat-events,-disable-plugins
expected_env_delta=+OBELISK_WRAPPER_PROFILE,+OBELISK_ENABLE_CHAT_EVENTS,+OBELISK_CHAT_EVENTS_BINARY_SHA256,+OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
rollback_delta=reverse expected_marker_delta/env_delta and restore baseline plugin posture
baseline_marker_snapshot=<secret-free summary captured before changes>
baseline_env_snapshot=<secret-free summary captured before changes>
baseline_plugin_snapshot=oChatLogger only candidate; no other plugin loadable
```

- Send the beta-test notice before activation. Preserve only a secret-free artifact:

```text
notice_sent=true
notice_path=<current-turn operator-approved channel/path label only; no endpoint, webhook, token, or message URL>
notice_time_utc=<timestamp>
notice_digest_sha256=<sha256 of sanitized local notice text or sanitized screenshot/export>
```

Sanitized notice template:

```text
Obelisk beta test window for ARK chat-mode delivery is starting on Ragnarok.
Scope: verify copied plugin event delivery for global, tribe, local, and alliance chat.
Privacy: Obelisk test logging records mode, sequence, flags, and message size only; no raw
chat text, player identity, UE pointers, or moderation/blocking behavior is collected.
Expected impact: a narrow restart/config window may occur; test ends with rollback and
stable posture verification.
```

- Stable pre-check passes before changing markers:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map Ragnarok --instance arkserver
```

- `oChatLogger` is built, installed through the normal plugin installer, safe-disabled by
  default, and allowlisted only for `arkserver` for the beta window.
- Record evidence that no other plugin can load during the window. If `disable-plugins` is
  removed, `oChatLogger` must be the only enabled/allowlisted plugin candidate.
- Do not enable `OBELISK_CHAT_REFLECTION_LOG_TEXT`.
- Keep the internal route observer off for the plugin-delivery acceptance phase:
  `OBELISK_ENABLE_CHAT_ROUTE_OBSERVER`, `OBELISK_CHAT_ROUTE_OBSERVER_*`, and
  `state/instances/arkserver/enable-chat-route-observer` must be absent unless a separate
  route-only diagnostic phase is explicitly current-turn approved and labeled.
- Do not treat route-observer evidence as plugin delivery evidence.

## Go/No-Go Checklist

Go only if all of the following are true before activation:

- Operator gives current-turn approval for instance, UTC start/end, restart expectation,
  rollback, evidence capture, and notice path.
- Notice artifact is recorded without endpoint, webhook, token, message URL, raw player
  text, or player identity.
- Stable posture pre-check passes.
- Baseline marker/env/plugin snapshots are recorded.
- Server binary SHA matches the supported SHA in this runbook.
- `oChatLogger` is the only plugin that can load during the window.
- Positive gates are exactly the chat-event gates listed below.
- Negative gates are absent: route observer, chat reflection, raw text logging, scanner,
  native exec, ptrace/gcore, broad ProcessEvent tracing, global callbacks, public
  `CallProcessEvent`, ProcessEvent blocking, and unrelated observer env/markers.
- Each claimed send mode has a recorded in-game precondition and controlled-send record.
- Rollback can be applied inside the current-turn approved window.

No-go if any privacy blocker appears, another plugin can load, pre/post posture fails, the
server SHA differs, a required mode precondition is absent for a full-coverage claim, chat
ambient noise prevents correlation, or rollback is not defined.

## Exact Feature Gates

Use only the minimal copied delivery path named by the current-turn approval:

```text
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_CHAT_EVENTS=1
OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=<controlled message count + ambient margin>
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/allow-observer-debug-window
state/instances/arkserver/allow-experimental-observers
state/instances/arkserver/enable-chat-events
```

For one controlled message in each mode `0,1,2,3`, the absolute minimum dispatch limit is
`4`. Use a quiet beta window and a margin such as `16` or higher so unrelated chat cannot
consume the budget before all controlled modes are sent. The experimental `oChatLogger`
currently logs up to sixteen accepted events per mode, so set the runtime dispatch limit
high enough for the planned sends plus ambient margin.

`disable-plugins` must be absent for the plugin load window. Restore it afterward if that
is the intended stable posture.

## Controlled Messages

For full coverage, collect at least one accepted copied delivery for each send mode:

```text
0 GlobalChat
1 GlobalTribeChat
2 LocalChat
3 AllianceChat
```

Mode-specific in-game preconditions must be true before the controlled send for that mode:

```text
0 GlobalChat: beta tester is connected and can send normal global chat.
1 GlobalTribeChat: beta tester is in a tribe and can send tribe chat.
2 LocalChat: beta tester is connected near at least one eligible local-chat observer or
   otherwise confirms the server accepts local chat for the controlled send.
3 AllianceChat: beta tester is in a tribe with an active alliance chat path and can send
   alliance chat.
```

If any in-game precondition is absent, blocked by game state, or not recorded for the
window, mark that mode `inconclusive_precondition_missing`. Do not report it as a failed
delivery mode and do not use it as negative proof against `ChatMessageEvent` coverage.

Record one controlled-send line per attempted mode without player identity or raw text:

```text
mode=<0|1|2|3>
planned_send_time_utc=<timestamp>
observed_send_time_utc=<timestamp>
precondition=confirmed|inconclusive_precondition_missing
expected_message_size_bytes=<byte-count>
tester_result=accepted_by_game|not_sent|unknown
correlation=controlled_quiet_window|inconclusive_ambient_chat
```

If `correlation=inconclusive_ambient_chat`, do not claim full mode coverage from analyzer
output alone.

## Evidence

Copy the beta-window log into:

```text
/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
```

Do not analyze direct live log paths. Keep a window manifest beside the copied log:

```text
run_id=<run-id>
target=arkserver/Ragnarok
approved_window_start_utc=<approved-start>
approved_window_end_utc=<approved-end>
actual_capture_start_utc=<first copied-log timestamp included>
actual_capture_end_utc=<last copied-log timestamp included>
copied_log_path=/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
copied_log_sha256=<sha256 of copied Obelisk.log>
copy_method=<operator-local copy command summary without live paths or secrets>
complete_window_evidence=true
notice_sent=true
pre_check=passed
post_check=passed|failed
rollback_completed=true|false
controlled_send_records_complete=true|false
```

The copied log and manifest must show the full current-turn approved window: pre-check
context before activation, producer/plugin activation, all controlled sends attempted,
rollback, and post-check context through `actual_capture_end_utc`. A cropped
delivery-only excerpt is useful for review but is not sufficient evidence for the runbook.

Validate the manifest with `scripts/validate_chat_mode_coverage_manifest.py` before
treating analyzer success as accepted evidence. Analyzer success alone is not enough for a
full beta result.

Expected copied delivery lines:

```text
Chat message event producer enabled for ShooterGameServer SHA256 <sha>.
[Plugin] [oChatLogger] Registered ChatMessageEvent callback.
[Plugin] [oChatLogger] ChatMessageEvent received sequence=<n> send_mode=<0..3> flags=0x1 message_size=<nonzero>. mode_count=<n> first_observed=<true|false>.
```

## Analyzer Gate

```bash
scripts/analyze_chat_delivery_log.py \
  --expected-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --require-send-modes 0,1,2,3 \
  --require-workspace \
  --fail-on-quality-blockers \
  --json \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log
```

Use `--expected-message-size <controlled-size>` only if every controlled mode message uses
the same known size.

The analyzer JSON `source.sha256` must match `copied_log_sha256` in the window manifest.
If analyzer mode coverage is missing for a mode whose in-game precondition was absent,
record the mode as `inconclusive_precondition_missing` rather than relaxing
`--require-send-modes` for a full-coverage claim.

## Manifest Gate

The manifest gate is repo-local and does not touch servers:

```bash
scripts/validate_chat_mode_coverage_manifest.py \
  --json \
  /servidor/ark/workspace-offline/live-validation-logs/<run-id>/chat-mode-coverage-manifest.json
```

It requires the copied log and analyzer JSON to live under
`/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`, rejects symlinks,
secret endpoints, raw chat text, player identity, UE pointers, route-only delivery
claims, missing rollback/post-check evidence, and any claimed mode without a matching
accepted copied `ChatMessageEvent` delivery.

## Rollback

- Apply exactly the reverse of the preflight delta:

```text
remove env: OBELISK_WRAPPER_PROFILE, OBELISK_ENABLE_CHAT_EVENTS,
  OBELISK_CHAT_EVENTS_BINARY_SHA256, OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
remove markers: allow-observer-debug-window, allow-experimental-observers,
  enable-chat-events
restore marker: disable-plugins if it was present in the stable pre-check baseline
restore plugin allowlist/config: undo only the oChatLogger beta-window delta
```

- Do not remove unrelated markers, unrelated plugin config, or operator state.
- Do not leave observer-debug env or experimental observer markers present after the
  beta window.
- Run the stable post-check:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map Ragnarok --instance arkserver
```

- Record rollback evidence in the window manifest:

```text
rollback_started_utc=<timestamp>
rollback_completed_utc=<timestamp>
rollback_delta_applied=<reverse of preflight delta>
post_check=passed|failed
post_check_time_utc=<timestamp>
```

## Boundary

Passing this runbook proves copied plugin delivery for the observed send modes only. It
is a research beta result, not a release claim. It does not promote sender identity,
command routing, moderation/blocking, chat-send authority, mutation, return override, raw
`FString`, FName/GObjects exposure, UE lookup, or UE pointer access.
