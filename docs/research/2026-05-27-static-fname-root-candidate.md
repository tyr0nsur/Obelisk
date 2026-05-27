# Static FName Root Candidate

## Objective

Find an offline, static route toward `GNames`/`FNamePool` in the current ARK Linux
`ShooterGameServer` after live FName reject logging showed that chat-derived globals are
`UObject`/`UFunction` leads, not name table roots.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk commit during lead-side analysis: `4892005bec1c`
- Agent session: `019e673a-afe1-7480-adb0-ca85e95f0362`
- Agent result: blocked by its Codex sandbox before it could run `readelf`, `objdump`, or
  `strings`; it did not edit files or promote offsets.
- Lead-side objdump artifact:
  `/tmp/ShooterGameServer.7e7ded49.objdump`

## Hypothesis

The real name root is not reachable by treating chat-related object globals as an
indirect table. Instead, it should appear through UE4 name initialization and lookup code:
hashing names, maintaining name buckets, allocating fixed-size name chunks, and storing a
global pointer to the table.

## Method

Commands used:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
file /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -h -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -S -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
readelf -l -W /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
strings -a -tx /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer | rg -i 'FName|GNames|NamePool|UnrealNames|ClientMessage|ServerChat|None'
objdump -d -M intel /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer > /tmp/ShooterGameServer.7e7ded49.objdump
rg -n '430b440|470b440|GNAMES_FROM_SECTNAME|42fc805|UnrealNames|455b315|ClientMessage|41d6f7f7|ServerChat' /tmp/ShooterGameServer.7e7ded49.objdump
rg -n 'call   1c990d|call   1c990d0|5956f30|5956f38|594e020' /tmp/ShooterGameServer.7e7ded49.objdump
```

Relevant ELF ranges:

- `.text`: `0x0648400 - 0x3f6170f`
- `.rodata`: `0x3f61740 - 0x47f2c83`
- `.data`: `0x5825080 - 0x58446a7`
- `.bss`: `0x58446c0 - 0x5a25b8f`

## Evidence

Useful string hits:

- `D:\ASE\Engine\Source\Runtime\Core\Private\UObject\UnrealNames.cpp`
  at file offset `0x3efc805`, runtime address `0x42fc805`.
- `ClientMessage` at file offset `0x415b315`, runtime address `0x455b315`.
- `ServerChat` at file offset `0x3d6f7f7`, runtime address `0x416f7f7`.
- `GNAMES_FROM_SECTNAME` at runtime address `0x470b440`.

`GNAMES_FROM_SECTNAME` is rejected as a useful UE4 name-root clue in this pass. It sits in
OpenSSL-style section-name strings near `DO_EXT_CONF`, `hex_to_string`, and ASN.1 helper
names, and no direct objdump xref was found in the generated artifact.

Stronger candidate path:

- Function `0x1c89a70` initializes name state:
  - sets byte `0x5956f40`,
  - clears bucket array `0x594e020` for `0x8000` bytes,
  - initializes mutex global `0x5956f38`,
  - allocates `0x808` bytes,
  - zeroes that allocation,
  - stores it to global pointer slot `0x5956f30`.
- Function `0x1c88e70` is a small accessor/initializer for the same table pointer:
  - loads `QWORD PTR [rip+...] # 0x5956f30`,
  - if null, allocates `0x808`,
  - zeroes it,
  - stores it back to `0x5956f30`.
- Function `0x1c990d0` performs name lookup/add-style work:
  - hashes wide name input using CRC tables,
  - masks the hash to `0xfff`,
  - indexes bucket array `0x594e020`,
  - lazily initializes mutex global `0x5956f38`,
  - lazily initializes table pointer global `0x5956f30`,
  - uses table fields `[table + 0x800]` and `[table + 0x804]`,
  - allocates chunks of `0x20000`,
  - stores chunk pointers at `table + chunk_index * 8`,
  - stores name entry pointers into chunk storage.
- Caller `0x1c892f4` converts/normalizes input names and calls `0x1c990d0` at
  `0x1c89410`; another path calls the adjacent `0x1c995f0` for short names.

This shape is highly compatible with the current Obelisk indirect-table probe layout:

```text
table[0..255]      chunk pointers
table + 0x800      num elements
table + 0x804      num chunks
chunk size         0x20000
```

The important distinction is that the static candidate root is the global pointer slot
`0x5956f30`. The runtime table should be the value loaded from that slot, not the slot
address itself and not the chat UObject globals.

## Result

Status: `research-candidate`, not definitive.

The most plausible current route to `GNames`/legacy `TNameEntryArray` is:

```text
global pointer slot: 0x5956f30
runtime table value: *0x5956f30
name buckets:        0x594e020
mutex slot:          0x5956f38
init flag:           0x5956f40
init/accessors:      0x1c88e70, 0x1c89a70
lookup/add path:     0x1c990d0 and adjacent 0x1c995f0
```

Do not promote `0x5956f30` as a stable offset yet. It is tied to the current binary hash
and still needs a second validation path.

## Rejected Paths

- Rejected: treating chat-derived globals as FName tables. The live capture produced
  `22` FName rejects and zero probes.
- Rejected for now: `GNAMES_FROM_SECTNAME`. It appears to be unrelated library string data,
  not a UE4 name-root xref.

## Risks

- The stripped binary's symbol context is misleading: objdump labels many addresses under
  unrelated exported names. Use raw addresses and instruction evidence, not the nearest
  symbol name.
- Static evidence does not prove that `None`, `ClientMessage`, or `ServerChat` decode at
  expected indices in a live process.
- A direct hardcoded offset in runtime code would be fragile unless guarded by binary hash
  and explicit opt-in.

## Next Steps

1. Add an isolated-only explicit FName root probe path that can read candidate global
   pointer slots supplied by environment/config, for example `0x5956f30`, then run the
   existing `None`, `ClientMessage`, and `ServerChat` clue checks against `*slot`.
2. Require binary SHA256 match before testing a static root.
3. Capture a short debug run with:
   - plugins disabled,
   - native exec probes unset,
   - FName reject logging enabled,
   - explicit static root candidate list enabled.
4. Promote only if the runtime probe logs `matched_clues=3/3` for known indices and the
   analyzer records an evidence pack against the same binary hash.

## Skill Updates Needed

None yet. This is one experiment and belongs in `docs/research/`. If the explicit static
root probe becomes the standard workflow, update `obelisk-static-binary-analysis` and
`obelisk-ue4-type-reconstruction`.
