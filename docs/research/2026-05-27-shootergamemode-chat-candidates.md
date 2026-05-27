# ShooterGameMode Chat Candidate Offline Validation

## Objective

Validate offline whether `ShooterGameMode.SendServerChatMessage` and
`OnServerChatMessage__DelegateSignature` have enough UE4 reflection evidence to be added
as exact metadata-only chat recognizers.

No runtime, server restart, marker edit, ptrace, plugin ABI, or config work was performed.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Obelisk HEAD during validation: `feeb58d`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Binary type: stripped ELF64 x86-64 executable
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Reflection globals used by the existing offline scripts:
  `GObjects=0x595b7e0`, `FName root slot=0x5956f30`

## Commands

```bash
sed -n '1,220p' agent-skills/obelisk-ue4-reflection/SKILL.md
sed -n '1,220p' agent-skills/obelisk-ue4-reversing/SKILL.md
sed -n '1,220p' agent-skills/obelisk-static-binary-analysis/SKILL.md
sed -n '1,220p' agent-skills/obelisk-agent-handoff/SKILL.md
sed -n '1,220p' docs/agent-handoff/CURRENT.md
git status --short --ignored
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
file /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
git rev-parse --short HEAD

python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --index 26281 --index 26240 \
  --window-size 0xb8 \
  --max-object-scan 30000

python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --name-contains SendServerChatMessage \
  --name-contains OnServerChatMessage__DelegateSignature \
  --outer-contains ShooterGameMode \
  --window-size 0xb8 \
  --max-object-scan 30000

python3 scripts/verify_chat_reflection_constants.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --json

rg -n "SendServerChatMessage|OnServerChatMessage__DelegateSignature|k.*ServerChat|MetadataOnly|ChatFunction" \
  ue/ChatReflection.cpp ue/ChatReflection.h tests/core/ChatReflectionTests.cpp

strings -a -tx /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  | rg -i "SendServerChatMessage|OnServerChatMessage__DelegateSignature|MessageText|ReceiverTeamId|ReceiverPlayerID|MessageColor|bIsBold"
```

## Evidence

The exact-index and `name_contains + outer_contains` inspector runs resolved the same two
`Function` objects under `ShooterGameMode`.

| Candidate | GObjects index / object | FName index | Outer | ParmsSize | Properties |
| --- | ---: | ---: | --- | ---: | --- |
| `SendServerChatMessage` | `26281` / `0x79b62fc38d90` | `9801` | `ShooterGameMode` (`GObjects` `411`, object `0x2b1e9080`) | `0x2c` | `MessageText:StrProperty@0x0` size `0x10`; `MessageColor:StructProperty@0x10` size `0x10`; `bIsBold:BoolProperty@0x20` size `0x1`; `ReceiverTeamId:IntProperty@0x24` size `0x4`; `ReceiverPlayerID:IntProperty@0x28` size `0x4` |
| `OnServerChatMessage__DelegateSignature` | `26240` / `0x79b62fc376b0` | `28549` | `ShooterGameMode` (`GObjects` `411`, object `0x2b1e9080`) | `0x18` | `MessageText:StrProperty@0x0` size `0x10`; `ReceiverTeamId:IntProperty@0x10` size `0x4`; `ReceiverPlayerID:IntProperty@0x14` size `0x4` |

Additional observed fields:

- `SendServerChatMessage`: `NumParms=5`, `FunctionFlags=0x4820400`, native function
  pointer candidate `0x15d1d70`, property chain status `candidate`.
- `OnServerChatMessage__DelegateSignature`: `NumParms=3`, `FunctionFlags=0x130000`,
  native function pointer candidate `0x1d33a00`, property chain status `candidate`.
- Every property in both chains has `owner_matches=true`, valid positive element size,
  and `offset + size <= ParmsSize`.
- `strings` finds the static ASCII name `SendServerChatMessage` at file offset
  `0x3d70322`. It did not find a static ASCII
  `OnServerChatMessage__DelegateSignature` line in the same binary scan; the delegate
  name is still resolved through the core FName table and GObjects metadata.
- Follow-up integration updated `scripts/verify_chat_reflection_constants.py` to include
  these two `ShooterGameMode` candidates. It now verifies nine recognizers against the
  core and returned `status=ok` for both `SendServerChatMessage` and
  `OnServerChatMessageDelegate`.
- Follow-up runtime integration defines these two recognizers in `ue/ChatReflection.cpp`
  as exact metadata-only candidates and adds them to the cheap ProcessEvent FName filter.

## Result

Both candidates have enough offline reflection evidence for exact metadata-only
recognizers. They are now implemented as observation-only fallback recognizers.

They are not stronger than `ShooterPlayerController.ServerSendChatMessage` for normal
incoming player chat. `SendServerChatMessage` looks like a server broadcast/helper path,
and `OnServerChatMessage__DelegateSignature` is a delegate signature/supporting event
shape. Neither should decode text, dispatch plugin events, or change public ABI based on
this core alone.

## Recommendation

- Keep current priority on the observed `ShooterPlayerController.ServerSendChatMessage`
  path: copied UTF-32 text decoding first, then plugin-facing ownership design.
- If a confirmed chat send produces only these `ShooterGameMode` lines, treat that as
  routing evidence first; do not promote them to accepted incoming player-chat events
  without decoding and caller semantics.
- Recognition should require exact `FName` index, `Function` class, outer
  `ShooterGameMode`, `NumParms`, `ParmsSize`, property count, property names/classes,
  offsets, and bounded property sizes.
- Do not decode `FString`, dispatch SDK/plugin events, or hook native exec pointers from
  this evidence.
