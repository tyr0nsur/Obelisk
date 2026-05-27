# Chat Reflection No-Hit Audit

Update: later read-only log review found accepted `ServerSendChatMessage` hits after this
snapshot window. Keep this note as evidence for the earlier no-hit window, but use
`2026-05-27-server-send-chat-runtime-hit.md` for current chat-reflection status.

## Objective

Investigate why the current `arkserver` process shows no chat reflection observations
even though the ProcessEvent hook is installed and the chat reflection gate is active.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Current repo HEAD during audit: `9e1af2f Document supervisor evidence retention`
- Runtime process from existing snapshots: `arkserver` PID `3289000`, map `Ragnarok`
- ARK binary SHA256 gate:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Existing core used for offline constant verification:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Existing runtime log:
  `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`
- Existing supervisor snapshot:
  `/servidor/ark/obelisk/dumps/supervisor/20260527T101357Z`

## Method

Read-only commands only:

```bash
sed -n '1,220p' /servidor/ark/obelisk/dumps/supervisor/latest/chat-reflection.txt
sed -n '1,220p' /servidor/ark/obelisk/dumps/supervisor/latest/summary.txt
sed -n '1,240p' /servidor/ark/obelisk/dumps/supervisor/latest/posture.txt

rg -n 'ProcessEvent|detour hit|vtable-derived|candidate\[|absolute x64 hook|hook installed|hook NOT installed|Failed to find ProcessEvent|Experimental chat reflection|Reflected chat|fname_index=' \
  /servidor/ark/obelisk/logs/arkserver/Obelisk.log

python3 scripts/verify_chat_reflection_constants.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --json
```

No server restarts, marker edits, plugin changes, live probes, ptrace, native exec probes,
or `/servidor/ark` writes were performed by this audit.

## Evidence

Latest supervisor snapshot `20260527T101357Z` reports stable posture:

```text
pid=3289000
posture_status=ok
stable_posture_summary=stable; instance=arkserver; process_event_hook=1; plugins_disabled=1; libobelisk_mapped=1; scanner_debug_native_exec_absent=1
chat_reflection_gate_env=1
chat_reflection_binary_sha256=present
```

The same snapshot reports the chat reflection gate is active but no recognized chat
candidate has been logged:

```text
chat_reflection_marker=enabled
chat_reflection_env=1
chat_reflection_binary_sha256=present
experimental_gate_lines=1
reflected_chat_process_event_lines=0
server_send_chat_message_lines=0
client_chat_message_lines=0
client_server_chat_message_lines=0
client_server_chat_direct_message_lines=0
metadata_only_lines=0
chat_candidate_lines=0
rejected_chat_lines=0
last_relevant_line=[09:06:57] [warning] Experimental chat reflection enabled for ShooterGameServer SHA256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.
```

The runtime log confirms hook install and the chat gate:

```text
[09:06:34] [info] ProcessEvent vtable-derived pattern candidates found: 1
[09:06:34] [info] ProcessEvent candidate[0] = 0x1d34e20
[09:06:34] [info] Found ProcessEvent at address: 0x1d34e20
[09:06:34] [info] ProcessEvent absolute x64 hook installed successfully. patch_size=18 trampoline=0x7e8eaf0c2000
[09:06:57] [warning] Experimental chat reflection enabled for ShooterGameServer SHA256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520.
```

Offline constant verification against the existing core returns `overall=ok` with zero
bad checks for all currently recognized candidates:

```text
ServerChat status=ok gobjects=25447 object=0x79b62fc1cd40 bad_checks=0
ServerChatTo status=ok gobjects=25449 object=0x79b62fc1ce70 bad_checks=0
ServerChatToPlayer status=ok gobjects=25452 object=0x79b62fc1d010 bad_checks=0
ServerSendChatMessage status=ok gobjects=10443 object=0x79b62fa23db0 bad_checks=0
ClientChatMessage status=ok gobjects=9548 object=0x79b62fa03800 bad_checks=0
ClientServerChatDirectMessage status=ok gobjects=9768 object=0x79b62fa0b4f0 bad_checks=0
ClientServerChatMessage status=ok gobjects=9772 object=0x79b62fa0b720 bad_checks=0
```

The runtime recognizer only logs after the cheap `UFunction.NamePrivate.ComparisonIndex`
filter matches one of these exact FName indices: `1865`, `1983`, `1984`, `2697`,
`9619`, `9620`, or `9621`. Non-chat `ProcessEvent` calls are intentionally silent, and
the current process does not have `OBELISK_PE_TRACE_LIMIT` set in the latest posture
snapshot.

## Result

The current evidence does not show a broken ProcessEvent hook, disabled chat gate, or
wrong known chat reflection constants. It shows that no currently recognized chat
candidate reached the bounded chat logger in the reviewed log window.

Most likely explanations, in priority order:

1. No real in-game chat message occurred after the PID `3289000` deployment and chat gate
   startup. The handoff already notes that no chat message has been observed yet in the
   log, and the supervisor counters cannot prove that a client sent chat.
2. The real runtime chat path for the tested action does not use any of the seven
   recognized `UFunction` FName indices. Existing core evidence still leaves
   `ShooterGameMode.SendServerChatMessage` and
   `OnServerChatMessage__DelegateSignature` as exact, uninstrumented follow-up
   candidates if a confirmed player chat send remains invisible.
3. A candidate FName reached the cheap filter but failed reflection validation after the
   log limit was exhausted or disabled is unlikely for this snapshot: posture shows
   `OBELISK_CHAT_REFLECTION_LOG_LIMIT=25`, and the log has zero reflected rejection lines.
   Still, absence of rejection lines is not proof that no candidate ever occurred because
   only the first bounded observations are logged.

## Rejected Paths

- Do not blame the old `ServerChat*` targets first; they are still likely
  `ShooterCheatManager` command coverage rather than normal player chat.
- Do not promote a text decoder or plugin-facing chat ABI from this evidence; there is no
  accepted runtime chat hit yet.
- Do not broaden runtime matching to substring `Chat`; use exact `UFunction` metadata and
  bounded counters.
- Do not hook or patch native exec candidates from this evidence.

## Risks

- The current snapshots do not include an operator-confirmed timestamp for a real chat
  message after the latest PID started.
- Without a trace window or candidate counters for unrecognized chat-like functions, a
  silent miss cannot distinguish "no event occurred" from "wrong exact candidate set".
- Broad ProcessEvent tracing on live Ragnarok may be noisy; keep any next capture
  bounded and preferably isolated/debug.

## Next Steps

1. Safest immediate experiment: run the documented manual check on a confirmed
   isolated/debug instance, or on the development instance only with explicit operator
   approval, by sending exactly one normal Ragnarok chat message while tailing the
   bounded reflected-chat lines and then reading a supervisor snapshot.
2. If that confirmed chat send still produces zero `ServerSendChatMessage` and zero
   metadata-only fallback lines, add metadata-only exact recognizers for
   `ShooterGameMode.SendServerChatMessage` and
   `OnServerChatMessage__DelegateSignature`, after verifying their constants against the
   core with `scripts/inspect_core_ufunctions.py`.
3. If exact expanded candidates still miss, use a very small `OBELISK_PE_TRACE_LIMIT` or
   a dedicated exact-candidate counter in an isolated/debug server to prove whether the
   chat path passes through `ProcessEvent` at all.

## Skill Updates Needed

None. This audit reinforces the existing static/core-first workflow and the ban on live
native exec probes.
