# Player Identity Static Target Orientation

Date: 2026-05-31T09:57:09Z

This note records candidate-only static orientation for the 12
`players-identity-lifecycle-intake` targets. It is useful for matching future focal
snapshot and reflection-inventory work, but it does not replace the required non-protected
core evidence pack or reflection inventory pack.

## Scope

- Input binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- ELF: x86-64 `EXEC`, stripped.
- Static address convention: `.rodata` VMA is file offset plus `0x400000`.
- Tools used: `strings`, `readelf`, `objdump`; no Ghidra project, runtime, server, ptrace,
  or `/servidor/ark` access.

## Candidate Table

| Target | Static evidence | Confidence | Notes |
| --- | --- | --- | --- |
| `ShooterPlayerController.ServerListPlayers` | string `0x3d632eb` -> VMA `0x41632eb`; xref `0x1368fa9`; pattern `mov esi,0x41632eb; mov edx,0x1547450; call 0x1ccc140`; thunk candidate `0x1547450` | Medium | Admin/list orientation only. |
| `ShooterPlayerController.ServerKickPlayer` | string `0x3d632da` -> VMA `0x41632da`; xref `0x1368f6c`; thunk candidate `0x1547320` | Medium | Admin mutation pressure only; fields remain redacted. |
| `ShooterPlayerController.ServerSendChatMessage` | string `0x3d638f1` -> VMA `0x41638f1`; xref `0x1369d01`; thunk candidate `0x154a600` | Medium | Does not prove sender identity or command/reply SDK. |
| `ShooterPlayerController.ServerRequestTribeLog` | string `0x3d63853` -> VMA `0x4163853`; xref `0x1369b56`; thunk candidate `0x1549ef0` | Medium | Tribe/admin pressure only. |
| `ShooterPlayerController.AllowTribeGroupPermission` | string `0x3d610f3` -> VMA `0x41610f3`; xrefs `0x135f14e`, `0x1364921`; thunk candidates `0x1535570`, `0x153a140` | Medium-low | Double xref; do not assign overload or permission semantics. |
| `ShooterPlayerController.IsInTribe` | string `0x3d612e6` -> VMA `0x41612e6`; xrefs `0x135f6c9`, `0x13679bd`; thunk candidates `0x15365b0`, `0x1543e10` | Medium-low | Double xref; no tribe/player lookup proof. |
| `ShooterPlayerController.ClientReceiveMyTribeOnlineList` | string `0x3d620d9` -> VMA `0x41620d9`; xref `0x1365c31`; thunk candidate `0x153e780` | Medium | No online-list identity exposure. |
| `ShooterPlayerController.ClientReceiveActiveMissionTags` | string `0x3d62084` -> VMA `0x4162084`; xref `0x1365b7a`; thunk candidate `0x153e390` | Medium | No mission tags public API. |
| `ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters` | string `0x3d61762` -> VMA `0x4161762`; xref `0x136008e`; thunk candidate `0x1537ff0` | Medium | Transfer/download lifecycle pressure only. |
| `MissionType.AddPlayerToMission` | string `0x3d65dbf` -> VMA `0x4165dbf`; xref `0x1386f2e`; thunk candidate `0x156c280` | Medium | Mission lifecycle precedent only. |
| `MissionType.BPAllowPlayerToLeaveMission` | string `0x3d65dfb` -> VMA `0x4165dfb`; xref `0x1386fe5`; thunk candidate `0x156c560` | Medium | Candidate-only. |
| `MissionType.BPOnPlayerRemovedFromMission` | string `0x3d66098` -> VMA `0x4166098`; xref `0x1387654`; thunk candidate `0x156df30` | Medium | No accepted session-end/logout semantics. |

## Static Corroboration Pattern

A second cheap static pass found the same 12 functions in registration-like sequences:

```text
mov rdi, [class_slot]
mov esi, <ascii_function_name_addr>
mov edx, <native_exec_thunk_addr>
call 0x1ccc140
```

The useful orientation signal is the tuple `class_slot + name + thunk + registrar call`.
Name-only matching is ambiguous for at least `AllowTribeGroupPermission` and `IsInTribe`,
which also appear near a `ShooterPlayerState`-like class slot. The machine-readable
companion JSON records the selected class slots and `registrar_call_vma=0x1ccc140` for
each target, but remains `candidate_blocked`.

## Repro Commands

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets --json
python3 scripts/compare_reflection_snapshots.py --list-target-guidance --target-set players-identity-lifecycle-intake --json

sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
file /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
readelf -h -W /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
readelf -l -W /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
readelf -S -W /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer | rg '\.(rodata|text|data|bss|dynstr|eh_frame)'

strings -a -t x /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer | rg 'ServerListPlayers|ServerKickPlayer|ServerSendChatMessage|ServerRequestTribeLog|AllowTribeGroupPermission|IsInTribe|ClientReceiveMyTribeOnlineList|ClientReceiveActiveMissionTags|ServerRequestSpawnPointsForDownloadedCharacters|AddPlayerToMission|BPAllowPlayerToLeaveMission|BPOnPlayerRemovedFromMission'

objdump -d -M intel /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer | rg -i '41610f3|41612e6|4161762|4162084|41620d9|41632da|41632eb|4163853|41638f1|4165dbf|4165dfb|4166098'
objdump -d -M intel /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer | rg -i -A3 '41610f3|41612e6|4161762|4162084|41620d9|41632da|41632eb|4163853|41638f1|4165dbf|4165dfb|4166098'
```

## Non-Claims

- Does not prove UFunction object identity, UProperty chains, parameter offsets, runtime
  event delivery, login/logout lifecycle, principal validity, or invalidation semantics.
- Does not promote public player identity, permissions, commands/replies, economy,
  moderation, lookup, mutation, return override, `ResourceHandle`, or any SDK surface.
- Does not replace the blocked player-identity route: produce a non-protected complete
  `obelisk.core-dump-evidence-pack.v1`, then a full `obelisk.reflection-inventory-pack.v1`
  for `players-identity-lifecycle-intake`, then exact focal plans for
  `ShooterPlayerController.ServerListPlayers` and `ShooterPlayerController.ServerKickPlayer`.
