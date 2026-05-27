# Real Chat UFunction Path Hypotheses

## Objective

Investigate offline why real in-game chat may not appear in the Obelisk
`ProcessEvent` chat reflection path as `ServerChat`, `ServerChatTo`, or
`ServerChatToPlayer`.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Obelisk HEAD: `fce4719 Add chat reflection constant verifier`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Current live/snapshot logs:
  `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`,
  `/servidor/ark/obelisk/dumps/supervisor/20260527T051611Z/chat-reflection.txt`

## Method

Read-only commands:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
file /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer

strings -a -tx /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  | rg -i "ServerChat|ServerSendChat|SendServerChat|ClientServerChat|ClientChatMessage|ChatMessage"

rg -n "Experimental chat reflection|Reflected chat|Chat reflection rejected|ProcessEvent absolute" \
  /servidor/ark/obelisk/logs/arkserver/Obelisk.log \
  /servidor/ark/obelisk/dumps/supervisor/20260527T0*/chat-reflection.txt

python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --index 9768 --index 9772 --index 10443 \
  --index 25447 --index 25449 --index 25452 --index 26281 \
  --window-size 0xb8 \
  --max-object-scan 30000
```

Static disassembly spot checks:

```bash
objdump -d -M intel --start-address=0x13c9100 --stop-address=0x13c9280 \
  /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
objdump -d -M intel --start-address=0x15c8f90 --stop-address=0x15c9040 \
  /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
objdump -d -M intel --start-address=0x15d1d70 --stop-address=0x15d1f40 \
  /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
```

## Evidence

Runtime/snapshot evidence:

- `Obelisk.log` shows one ProcessEvent pattern candidate and successful hook install.
- The chat reflection gate is enabled for the matching binary SHA256.
- Supervisor snapshots from `20260527T050318Z` through `20260527T051611Z` report
  `reflected_chat_lines=0`.
- `Chat reflection rejected` is logged at trace level, so zero reject lines in normal logs
  does not prove zero attempts for FName indices `9619..9621`.

String and registration evidence:

- ASCII reflection names exist:
  - `0x416f7f7` / file offset `0x3d6f7f7`: `ServerChat`
  - `0x416f802` / file offset `0x3d6f802`: `ServerChatTo`
  - `0x416f80f` / file offset `0x3d6f80f`: `ServerChatToPlayer`
  - `0x41638f1` / file offset `0x3d638f1`: `ServerSendChatMessage`
  - `0x4170322` / file offset `0x3d70322`: `SendServerChatMessage`
- Registration-like code references the three `ServerChat*` names at `0x13c918e`,
  `0x13c91cb`, and `0x13c9208`, pairing them with native exec pointers
  `0x15c8f90`, `0x15c9040`, and `0x15c9170`.

Core UFunction evidence:

- `ServerChat`, `ServerChatTo`, and `ServerChatToPlayer`:
  - object indices `25447`, `25449`, `25452`;
  - outer class: `ShooterCheatManager`;
  - `FunctionFlags=0x20601`;
  - native exec candidates `0x15c8f90`, `0x15c9040`, `0x15c9170`;
  - parameter names match admin/cheat-style command forms:
    `MessageText`, `SteamID`, `PlayerName`.
- `ServerSendChatMessage`:
  - object index `10443`;
  - outer class: `ShooterPlayerController`;
  - `FunctionFlags=0x220cc0`;
  - native exec candidate `0x154a600`;
  - property chain: `StrProperty ChatMessage` offset `0x0`, `ByteProperty SendMode`
    offset `0x10`, `ParmsSize=0x11`.
- `ClientServerChatMessage` and `ClientServerChatDirectMessage`:
  - object indices `9772` and `9768`;
  - outer class: `ShooterPlayerController`;
  - `FunctionFlags=0x1820cc0`;
  - parameters include `MessageText`, `MessageColor`, and `bIsBold`.
- `SendServerChatMessage`:
  - object index `26281`;
  - outer class: `ShooterGameMode`;
  - `FunctionFlags=0x4820400`;
  - parameters include `MessageText`, `MessageColor`, `bIsBold`,
    `ReceiverTeamId`, and `ReceiverPlayerID`.

## Result

Most likely, the current chat reflection filter is watching cheat-manager exec commands,
not the normal player chat RPC path. Real player chat should be investigated first through
`ShooterPlayerController.ServerSendChatMessage`, with outbound/broadcast paths likely
including `ClientServerChatMessage`, `ClientServerChatDirectMessage`, and
`ShooterGameMode.SendServerChatMessage`.

This does not disprove the `ProcessEvent` hook. It explains why a valid hook and valid
`ServerChat*` metadata can still produce no real chat matches.

## Rejected Paths

- Do not treat the existence of `ServerChat*` UFunction metadata as proof that normal
  in-game chat uses those functions.
- Do not use zero trace-level rejection lines in normal logs as proof that no chat FName
  index ever passed the cheap filter.
- Do not hook native exec pointers from this evidence alone.

## Risks

- The core capture did not include a known chat event timestamp.
- Function flag interpretation is inferred from UE4 flag conventions and should be
  confirmed by a bounded runtime trace or independent static path.
- Extending runtime recognition to `ServerSendChatMessage` requires new metadata
  validation and a rate-limited capture; do not broaden to arbitrary chat-like names.

## Next Steps

1. Add a gated, isolated-debug-only recognition path for
   `ShooterPlayerController.ServerSendChatMessage` using the reflected shape above.
2. In a confirmed isolated/debug instance, send one real player chat message and use a
   small `OBELISK_PE_TRACE_LIMIT` or a dedicated chat-candidate counter to confirm whether
   `ServerSendChatMessage` appears in `ProcessEvent`.
3. If `ServerSendChatMessage` matches, decode only the reflected `ChatMessage` `FString`
   after `UFunction`, property-chain, and `ParmsSize` validation.
