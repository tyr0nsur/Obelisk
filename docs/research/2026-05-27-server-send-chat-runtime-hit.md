# ServerSendChatMessage Runtime Hit

## Objective

Record the first observed runtime `ServerSendChatMessage` chat reflection hits after the
previous no-hit audit, and define the next promotion boundary.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Runtime log: `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`
- ARK instance: `arkserver` / Ragnarok
- ProcessEvent hook target: `0x1d34e20`
- Binary SHA256 gate:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Existing core evidence:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`

## Method

Read-only commands only:

```bash
tail -n 300 /servidor/ark/obelisk/logs/arkserver/Obelisk.log

python3 scripts/verify_chat_reflection_constants.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --json
```

No restart, marker edit, plugin activation, scanner, ptrace, native exec probe, or
`/servidor/ark` write was performed for this note.

## Evidence

The runtime booted with the expected hook and chat gate:

- `ProcessEvent absolute x64 hook installed successfully`
- `Experimental chat reflection enabled for ShooterGameServer SHA256 ...`
- `ReflectionScanner disabled`
- `Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1`

The log now contains accepted reflected chat hits:

- `14:07:27`: `function=ServerSendChatMessage`, `fname_index=2697`,
  `metadata_only=false`, `send_mode=0`, `send_mode_name=GlobalChat`,
  `send_mode_known=true`
- `14:17:13`: same accepted `ServerSendChatMessage` shape and `GlobalChat`
- `16:12:02`: same accepted `ServerSendChatMessage` shape and `GlobalChat`
- `16:12:45`: same accepted `ServerSendChatMessage` shape and `GlobalChat`

Each accepted hit logs bounded field ranges for:

- `ChatMessage offset=0x0 size=16 has_range=true`
- `SendMode offset=0x10 size=1 has_range=true`

The same log also contains rejected `ClientChatMessage` observations with
`reason=chat UFunction outer FName index mismatch`. Treat those as useful guardrail
evidence: the outer validation is rejecting at least one tempting metadata-only fallback
instead of broadening the recognizer unsafely.

Offline verification against the existing core returned `status=ok` for all current chat
recognizers, including `ServerSendChatMessage`, the `ShooterPlayerController`
metadata-only fallbacks, and the new `ShooterGameMode` metadata-only candidates.

## Result

`ShooterPlayerController.ServerSendChatMessage` is now a runtime-observed chat
`ProcessEvent` path for this binary and deployment posture. This promotes the previous
best candidate from "needs one real runtime hit" to "observed runtime path" for
experimental logging.

This does not promote a public SDK chat event yet.

Follow-up local implementation now wires the existing UTF-32 `FString` decoder into the
experimental `ServerSendChatMessage` logger. Metadata/range logging remains controlled by
the chat reflection gate, but decoded text requires the extra
`OBELISK_CHAT_REFLECTION_LOG_TEXT=1` opt-in. When enabled, it logs sanitized text only
when `SendMode` is known (`0..3`), and still does not dispatch plugin callbacks or change
public ABI. This implementation was validated locally but is not recorded here as deployed
runtime evidence.

## Risks

- The log does not capture player identity, caller semantics, or copied text ownership.
- `ServerSendChatMessage` evidence is binary-hash-scoped.
- Chat reflection remains experimental and should not be treated as stable baseline for
  high-population/live operation without overhead measurement.
- Metadata-only `ShooterGameMode` candidates remain fallback observations only.

## Next Steps

1. Deploy the local UTF-32 chat-text logger only in a controlled restart window if runtime
   text evidence is needed.
2. Keep dispatch blocked until text is copied into Obelisk-owned memory and callback
   lifetime/ownership is specified.
3. Reject `send_mode >= 4` before logging or dispatching text.
4. Benchmark ProcessEvent overhead with chat reflection enabled vs disabled before keeping
   the marker active for long sessions.
5. Re-run `scripts/verify_chat_reflection_constants.py` for any new ARK binary/core before
   accepting the constants.

## Skill Updates Needed

- Update `obelisk-ue4-reflection` with the `ServerSendChatMessage` runtime-hit fact and
  the copied-ownership boundary for future SDK work.
