# Player Identity Static Admin Thunks

This note preserves a bounded static check for the two missing
`players-identity-lifecycle-intake` admin snapshots. It is useful orientation only; it
does not replace a core evidence pack or a UFunction reflection-inventory pack.

## Scope

- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- File type: ELF 64-bit x86-64 executable, stripped, non-PIE `EXEC`, entry `0x81dc59`.
- Tools observed:
  - `/usr/bin/rabin2`: 5.5.0
  - `/usr/bin/radare2`: 5.5.0
  - `/usr/bin/objdump`: GNU Binutils 2.42
  - `/usr/bin/readelf`: GNU Binutils 2.42
  - `/usr/local/bin/analyzeHeadless`: Ghidra 12.1
  Ghidra was smoke-tested with `-noanalysis` only, isolated under `/tmp`; no decompiler
  or full auto-analysis result is part of this note.
- Server impact: none. Offline binary only.

## ELF Ranges

- RX `LOAD`: `0x400000..0x5604aab`
- RW `LOAD` memory: `0x5805000..0x5a25b8f`
- `.text`: `0x648400..0x3f6170e`
- `.rodata`: `0x3f61740..0x47f2c83`
- `.bss`: `0x58446c0..0x5a25b8f`

For this binary hash, the candidate thunks `0x1547320` and `0x1547450` are in `.text`;
ASCII and UTF-32 name strings are in `.rodata`; probable FName-ish slots `0x58eae60` and
`0x58eae68` are in `.bss`.

## Static Clues

String scan:

```bash
BIN=/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
rabin2 -z "${BIN}" | grep -E 'ServerKickPlayer|ServerListPlayers|/Script/ShooterGame$|AShooterPlayerController$'
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
objdump -d -j .text -M intel --no-show-raw-insn \
  --start-address=0x1368f40 --stop-address=0x1368fd0 "${BIN}"
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

`radare2` without global analysis gives the same local registration window quickly:

```bash
r2 -q -e io.cache=true -e scr.color=false \
  -c 's 0x1368f60; pd 30; s 0x1547320; pd 45; s 0x1547450; pd 45; q' "${BIN}"
```

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

Adjacent lifecycle strings and registrations, including `OnLogout`, `GetPlayerState`,
`GetUniqueIdString`, `GetPlayerIDForSteamID`, `GetSteamIDForPlayerID`,
`OnRep_PlayerState`, and `OnRep_UniqueId`, are useful candidate names only. They do not
prove session lifecycle order, principal validity, privacy boundaries, or a stable
identity contract.

## Limitations

- The `objdump` checks are bounded disassembly windows and immediate-value references,
  not a complete xref graph.
- They can miss indirect references, data-only flows, relocations not printed as
  immediates, and runtime writes through `.bss`.
- UTF-32 name initialization and ASCII native-exec registration clues have different
  roles; neither is accepted `UFunction` identity or an accepted FName index.
- `objdump --start-address` can begin in the middle of an instruction if the window is
  cut poorly. Only coherent `mov`/`call` sequences inside the bounded window are treated
  as orientation clues.
- Vtable offsets `0x1520` and `0x1528` are stripped-binary orientation only. They are not
  a vtable definition, public ABI, or cross-build contract.
- `radare2 -A` is not a good short smoke-test path for this binary; a local non-analysis
  disassembly window is faster and less noisy. Full Ghidra/radare analysis should stay a
  separate static-analysis task with `/tmp` output and bounded scripts.

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
