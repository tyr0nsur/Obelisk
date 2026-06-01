# Command/Chat Response Static Orientation

Date: 2026-05-31T00:00:00Z

This note records bounded offline candidate orientation for three
`ShooterPlayerController` response-path targets on the reviewed Linux
`ShooterGameServer`. It is planning evidence for
`obelisk.command_chat_response_path.v1` only. It is not an artifact gate, not runtime
readiness, and not public SDK promotion.

## Scope

- Input binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- ELF: x86-64 `EXEC`, stripped.
- Static address convention: non-PIE ELF VMA for this reviewed ARK Linux binary.
- Tools used: `sha256sum`, `strings`, `readelf`, `objdump`, and
  `scripts/check_command_chat_response_static_orientation.py`.
- Tools not used: radare/rizin analyzer mode, Ghidra imports, core files, runtime probes,
  server access, ptrace, `/servidor/ark`, or broad event tracing.

## Candidate Table

| Target | Exact name evidence | Local registration-window evidence | Candidate thunk | Status |
| --- | --- | --- | --- | --- |
| `ShooterPlayerController.ClientChatMessage` | ASCII `ClientChatMessage` at file offset `0x3d61a92`, VMA `0x4161a92` | `0x1364ed9`: `mov esi,0x4161a92`; `mov edx,0x153b820`; `call 0x1ccc140`; class load resolves to `0x58eebf0` | `0x153b820` | Candidate only |
| `ShooterPlayerController.ClientServerChatDirectMessage` | ASCII `ClientServerChatDirectMessage` at file offset `0x3d622d1`, VMA `0x41622d1` | `0x136603e`: `mov esi,0x41622d1`; `mov edx,0x153f880`; `call 0x1ccc140`; class load resolves to `0x58eebf0` | `0x153f880` | Candidate only |
| `ShooterPlayerController.ClientServerChatMessage` | ASCII `ClientServerChatMessage` at file offset `0x3d622ef`, VMA `0x41622ef` | `0x136607b`: `mov esi,0x41622ef`; `mov edx,0x153f9c0`; `call 0x1ccc140`; class load resolves to `0x58eebf0` | `0x153f9c0` | Candidate only |

The new checker validates only bounded static features:

- unique exact ASCII target name in `.rodata`;
- a 17-byte local registration window per target;
- a 7-byte controller class-slot load resolving to `0x58eebf0`;
- a short native thunk byte-prefix sanity check;
- hash pinning to
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`;
- protected-path and symlink rejection before reading input.

The checker also keeps the principal route invariant explicit: static response-path
orientation cannot create identity or permission claims. Command text and operator config
are not principal sources; a future copied response path may only consume an already
established runtime principal and a separately promoted permissions/admin decision.

## Repro Commands

```bash
sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

strings -a -t x /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  | rg 'ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage'

readelf -l -W /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
readelf -S -W /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  | rg '\.(text|rodata|bss|data)'

objdump -d -M intel /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  | rg -i -A4 -B4 '4161a92|41622d1|41622ef'

python3 scripts/check_command_chat_response_static_orientation.py --json
python3 -m unittest scripts/test_check_command_chat_response_static_orientation.py
```

Portable unit coverage uses a synthetic ELF fixture to prove checker behavior and the
candidate-only JSON contract without requiring the reviewed binary to be present. The
real offline `ShooterGameServer` test is an optional smoke/evidence check only. Neither
path promotes runtime readiness, response delivery, or public SDK surface.

## Stop Conditions

The checker fails closed if the binary hash changes, a protected or symlinked input path
is supplied, ELF layout does not match the reviewed executable, a target name is missing
or non-unique in `.rodata`, a registration local window does not match the expected exact
target, the class slot does not resolve to `0x58eebf0`, or the short thunk prefix check
fails.

## Non-Claims

- Does not claim replies, send-chat API, command router, identity, permissions, raw UE
  pointer exposure, raw `FString` exposure, mutation, return override, runtime readiness,
  or public SDK promotion.
- Does not prove UFunction object identity, FName index stability, UProperty chains,
  parameter offsets, copied-data ownership, response payload shape, command execution, or
  player/principal mapping.
- Does not derive principal identity, permission, or admin authority from command text or
  operator config.
- Does not replace a non-protected complete core evidence pack, reflection inventory pack,
  focal snapshots, second-source evidence, isolated runtime validation, or a copied-data
  response contract.

## Focal Snapshot Follow-up

On 2026-06-01 the planning-only target set
`command-chat-response-route-planning` was added for the three response-path targets in
this note. It remains outside release-readiness and public SDK target sets.

The already reviewed offline reflection inventory pack under
`/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/reflection-inventory-pack`
plans all three focal snapshots with `planned_command_count=3`, `blocked_count=0`, and
`fname_root_ready=true`.

A local `/tmp` extraction produced comparable candidate snapshots for:

- `ShooterPlayerController.ClientServerChatDirectMessage`
- `ShooterPlayerController.ClientServerChatMessage`
- `ShooterPlayerController.ClientChatMessage`

Those temporary snapshots are not committed fixtures and do not close second-source
readiness. A self-comparison reports `second_source_inconclusive=3` with
`same_evidence_artifact_identity`. The next useful offline step is generating or locating
a distinct non-protected second-source snapshot root for the same target set, then running
`compare_reflection_snapshots.py --planning-layout-intake`. Do not add ABI, runtime
response delivery, command router, replies, send-chat, permissions, identity, raw FString,
or public SDK claims from these snapshots.

A second local `/tmp` extraction from the vanilla-gdb reflection inventory produced the
same three target snapshots with distinct `artifact_sha256`, but comparison still reports
`second_source_inconclusive=3` because both roots used generic evidence identity labels:
`capture_id=core` and `evidence_pack_id=core-evidence-pack`. This is an evidence-identity
blocker, not a layout blocker. The next extraction should use distinct capture/pack ids or
a manifest path whose generated snapshots carry distinct evidence identity before it is
cited as second-source planning evidence.
