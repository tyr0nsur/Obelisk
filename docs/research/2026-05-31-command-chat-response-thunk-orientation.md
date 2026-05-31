# Command/Chat Response Thunk Orientation

Date: 2026-05-31T00:00:00Z

This note records bounded static orientation for three candidate
`ShooterPlayerController` chat response thunks in the reviewed Linux
`ShooterGameServer`. It extends
`2026-05-31-command-chat-response-static-orientation.md` with local thunk-shape
observations only.

This is navigation evidence for future `obelisk.command_chat_response_path.v1`
work. It is not an artifact gate, not runtime readiness, and not public SDK
promotion.

## Scope

- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- ELF: x86-64 `EXEC`, stripped.
- Address convention: non-PIE ELF VMA for this reviewed ARK Linux binary.
- Tools used: `sha256sum`, `objdump`.
- Tools not used: runtime probes, server access, `/servidor/ark`, core files, ptrace,
  broad ProcessEvent tracing, Ghidra imports, or analyzer auto-renaming.

## Repro Commands

```bash
BIN=/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
sha256sum "$BIN"
objdump -d -M intel --start-address=0x153b820 --stop-address=0x153b920 "$BIN"
objdump -d -M intel --start-address=0x153f940 --stop-address=0x153f9c0 "$BIN"
objdump -d -M intel --start-address=0x153fa80 --stop-address=0x153fb00 "$BIN"
```

## Candidate Thunk Table

| Target | Thunk VMA | Stack frame | FFrame-like parse shape | Candidate vtable slot | Call shape | Confidence |
| --- | ---: | ---: | --- | ---: | --- | --- |
| `ShooterPlayerController.ClientChatMessage` | `0x153b820` | `0x120` | One larger local region around `rbp-0xa0`, then a local transform/copy before dispatch. | `0x19d0` | `mov rbx, [vtable+0x19d0]`; `call rbx` with `rdi=r14`. | Candidate only |
| `ShooterPlayerController.ClientServerChatDirectMessage` | `0x153f880` | `0x30` | Repeated parse into locals around `rbp-0x20`, `rbp-0x30`, and bool-like dword `rbp-0x34`. | `0x1790` | `mov rcx, [vtable+0x1790]`; `call rcx` with `rdi=r14`, `rsi=&local`, `edx=bool`. | Candidate only |
| `ShooterPlayerController.ClientServerChatMessage` | `0x153f9c0` | `0x30` | Same compact skeleton as direct-message thunk: locals around `rbp-0x20`, `rbp-0x30`, and bool-like dword `rbp-0x34`. | `0x1788` | `mov rcx, [vtable+0x1788]`; `call rcx` with `rdi=r14`, `rsi=&local`, `edx=bool`. | Candidate only |

## Observations

- `ClientChatMessage` has a larger thunk body and local frame than the two
  server-chat message thunks. The static window shows one dispatch through vtable slot
  `0x19d0` after building or transforming local data.
- `ClientServerChatDirectMessage` and `ClientServerChatMessage` have near-identical
  compact skeletons. Both normalize a bool-like local with `cmp [rbp-0x34],0x0` and
  `setne al`, advance the FFrame-like cursor at `[rbx+0x20]`, then dispatch through
  adjacent vtable slots.
- The adjacent slots, `0x1790` and `0x1788`, are useful static orientation for later
  response-path research, but do not identify a stable public response API by
  themselves.

## Non-Claims

- No public command API, reply API, send-chat API, broadcast API, moderation API, or
  command router is promoted by this note.
- No player identity, principal mapping, permissions/admin contract, response payload
  ownership, rate limiting, audit trail, or privacy contract is proven here.
- No raw `ProcessEvent`, raw params, raw `FString`, raw UE object pointer, FName index,
  GObjects index, direct native-call wrapper, or `CallProcessEvent` response path is
  approved as public ABI.
- No runtime hook, live-server test, beta-test request, mutation, return override, or
  response delivery claim is made.
- This note does not replace a non-protected core evidence pack, reflection inventory
  pack, focal snapshot, second-source evidence, isolated runtime validation, or copied
  response contract.

## Next Steps

- Keep `obelisk.command_chat_response_path.v1` blocked until player identity,
  permissions/admin, and a copied owner-token response contract are promoted or
  explicitly excluded by a reviewed release statement.
- If this lane is resumed, convert the orientation into a redacted candidate artifact
  only after adding provenance sidecars and a fail-closed schema that still rejects
  promotion. Do not use this note as an offline artifact-gate input.
- Prefer future work that proves copied response ownership and lifecycle semantics over
  exposing these thunk or vtable details to plugin authors.
