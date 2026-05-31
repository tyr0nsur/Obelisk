# Player Identity Static Admin Thunks

This note preserves a bounded static check for the two missing
`players-identity-lifecycle-intake` admin snapshots. It is useful orientation only; it
does not replace a core evidence pack or a UFunction reflection-inventory pack.

## Scope

- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Tools observed: `radare2`/`rabin2` 5.5.0. Ghidra headless is available, but no Ghidra
  import was used for this lightweight pass.
- Server impact: none. Offline binary only.

## Static Clues

String scan:

```bash
rabin2 -z ShooterGameServer | grep -E 'ServerKickPlayer|ServerListPlayers|/Script/ShooterGame$|AShooterPlayerController$'
```

Relevant hits:

```text
0x03b63b7c 0x03f63b7c utf32le /Script/ShooterGame
0x03cd7418 0x040d7418 utf32le AShooterPlayerController
0x03cfd540 0x040fd540 utf32le ServerKickPlayer
0x03cfd5e4 0x040fd5e4 utf32le ServerListPlayers
0x03d632da 0x041632da ascii   ServerKickPlayer
0x03d632eb 0x041632eb ascii   ServerListPlayers
```

Registration-like xrefs:

```bash
objdump -d -j .text -M intel --no-show-raw-insn ShooterGameServer \
  | grep -i -E -B6 -A10 '41632da|41632eb'
```

Relevant static pattern:

```text
0x1368f6c: mov esi,0x41632da
0x1368f71: mov edx,0x1547320
0x1368f78: call 0x1ccc140

0x1368fa9: mov esi,0x41632eb
0x1368fae: mov edx,0x1547450
0x1368fb5: call 0x1ccc140
```

Candidate native exec thunks for this binary hash:

- `ServerKickPlayer`: `0x1547320`
- `ServerListPlayers`: `0x1547450`

Focused disassembly suggests `ServerKickPlayer` decodes two script parameters before a
virtual dispatch through `AShooterPlayerController` vtable offset `0x1528`.
`ServerListPlayers` appears thinner and dispatches through vtable offset `0x1520`.
These offsets are static orientation clues only; they are not public ABI, vtable
contracts, or reusable cross-build evidence.

UTF-32 name initialization around `0x78d740..0x78d7d0` also references probable
runtime-initialized FName globals:

- `0x58eae60` for `ServerKickPlayer`;
- `0x58eae68` for `ServerListPlayers`.

Because those are `.bss` runtime values, the ELF alone does not provide accepted FName
indices.

## Decision

This is helpful context for manual review, but it does not unblock player identity. The
v1 route still needs a non-protected complete `obelisk.core-dump-evidence-pack.v1`, a
reviewed UFunction `obelisk.reflection-inventory-pack.v1`, and sanitized snapshots for
`ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer`.

Do not treat this static note as evidence for:

- accepted `UFunction` object identity;
- `UProperty` chain, offsets, or parameter names;
- FName indices;
- login/logout lifecycle anchors;
- public player identity, permissions, commands, economy, lookup, `ResourceHandle`,
  mutation, return override, runtime hooks, or SDK surface.
