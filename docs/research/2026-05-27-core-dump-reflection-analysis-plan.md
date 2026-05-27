# Core Dump Reflection Analysis Plan

## Objective

Define an offline workflow for analyzing a Linux `ShooterGameServer` core dump after an
operator has produced one from an authorized debug harness. This plan does not require
attaching to a running server, restarting ARK, editing `/servidor/ark`, or enabling any
runtime probe.

## Scope

- Target: existing Linux core dump plus the matching `ShooterGameServer` ELF.
- Goal: advance evidence for `FName`/`GNames`, `GObjects`, and `UFunction` type
  reconstruction.
- Non-goal: operating the server, creating the core, changing Obelisk runtime behavior, or
  promoting offsets directly into runtime code.

## Evidence Pack Command

Preferred offline pack:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /path/to/ShooterGameServer \
  --core /path/to/core.ShooterGameServer.<pid> \
  --output-dir /servidor/ark/obelisk/dumps/core-pack-$(date -u +%Y%m%dT%H%M%SZ)
```

Add extra virtual addresses when static analysis or logs provide candidates:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /path/to/ShooterGameServer \
  --core /path/to/core.ShooterGameServer.<pid> \
  --output-dir /tmp/obelisk-core-pack-extra \
  --candidate gobjects_slot=0xADDR \
  --candidate ufunction_candidate=0xADDR
```

The script records `file`, `readelf`, `objdump`, `strings`, GDB core inspection, hashes,
candidate memory windows, and a manifest. Under `/servidor/ark`, it only writes to
`/servidor/ark/obelisk/dumps`.

## Manual Commands

Use these when a script is not available or when splitting artifacts by hand:

```bash
sha256sum /path/to/ShooterGameServer
sha256sum /path/to/core.ShooterGameServer.<pid>
file /path/to/ShooterGameServer
file /path/to/core.ShooterGameServer.<pid>

readelf -h -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-header.txt
readelf -S -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-sections.txt
readelf -l -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-programs.txt
readelf -h -W /path/to/core.ShooterGameServer.<pid> > /tmp/core.readelf-header.txt
readelf -n -W /path/to/core.ShooterGameServer.<pid> > /tmp/core.readelf-notes.txt
readelf -l -W /path/to/core.ShooterGameServer.<pid> > /tmp/core.readelf-programs.txt

strings -a -tx /path/to/ShooterGameServer \
  | rg -i 'UnrealNames|FName|GNames|NamePool|ClientMessage|ServerChat|None|UFunction|UObject'

objdump -d -M intel /path/to/ShooterGameServer > /tmp/ShooterGameServer.objdump
rg -n '5956f30|594e020|5956f38|5956f40|1c88e70|1c89a70|1c990d0|ClientMessage|ServerChat' \
  /tmp/ShooterGameServer.objdump
```

Core-only GDB triage:

```bash
gdb -q -nx -batch \
  -ex 'set pagination off' \
  -ex 'info files' \
  -ex 'info proc mappings' \
  -ex 'info threads' \
  -ex 'thread apply all bt 24' \
  -ex 'maintenance info sections ALLOBJ' \
  -ex 'x/gx 0x5956f30' \
  -ex 'x/16gx 0x5956f30' \
  -ex 'x/16gx 0x594e020' \
  /path/to/ShooterGameServer /path/to/core.ShooterGameServer.<pid> \
  > /tmp/gdb-core.txt
```

If `0x5956f30` is readable and non-null, inspect the table value from the GDB transcript
with a second pass:

```bash
gdb -q -nx -batch \
  -ex 'set pagination off' \
  -ex 'set $t = *(void**)0x5956f30' \
  -ex 'p/x $t' \
  -ex 'x/272gx $t' \
  -ex 'x/wx ((char*)$t)+0x800' \
  -ex 'x/wx ((char*)$t)+0x804' \
  /path/to/ShooterGameServer /path/to/core.ShooterGameServer.<pid> \
  > /tmp/gdb-fname-table.txt
```

Do not script broad memory searches over the whole core as an acceptance path. Use them
only as clue generation and record exact ranges if needed.

## What A Core Can Advance

`FName` / `GNames`:

- Confirm whether a static global slot such as `0x5956f30` is mapped and initialized in
  the captured process.
- Show the runtime table pointer, chunk pointers, and counters at `table + 0x800` and
  `table + 0x804`.
- Let us inspect specific known indices if the storage model is already understood.
- Preserve a frozen memory state for repeatable offline reads by another engineer.

`GObjects`:

- Confirm whether a candidate global/root points into readable memory with plausible
  counts/chunks.
- Check whether candidate `UObject.InternalIndex` values map back through a suspected
  array.
- Cross-check that object vtables land in executable mappings and class/name/outer fields
  are mapped.

`UFunction`:

- Preserve candidate function objects and their surrounding fields for bounded layout
  comparison.
- Check whether candidate objects have plausible class/outer/name relationships once
  `FName` and `GObjects` are available.
- Inspect candidate `FunctionFlags`, `NumParms`, `ParmsSize`, and property-chain pointers
  without running more server code.

## What A Core Cannot Prove

- It cannot prove an offset is stable across ARK updates, maps, startup timing, or binary
  hashes.
- It cannot prove an initialization path by itself; static xrefs or decompiler evidence
  must explain how a global is written and read.
- It cannot safely establish `UFunction` identity before `FName` resolution and object
  array reachability exist.
- It cannot validate live timing, race behavior, plugin callback safety, or shutdown
  posture.
- It cannot replace an isolated second capture for promotion. A core is one frozen process
  state, not a reproducible runtime contract.

## Acceptance And Rejection

Treat core evidence as `supporting` unless all of these are true:

- matching binary SHA256 is recorded;
- core mappings match the binary and expected non-PIE virtual addresses;
- the candidate pointer is mapped, aligned, and readable;
- counts/chunks are plausible for the known clue indices;
- static xrefs explain the candidate root or accessor path;
- a later isolated capture or independent static path repeats the same conclusion.

Reject or keep inconclusive when:

- a slot is null only because the core was captured before initialization;
- table counters are zero while entry reads are ambiguous;
- candidate previews mismatch `None`, `ClientMessage`, or `ServerChat`;
- a `UObject` candidate is not reachable from a validated object array;
- a `UFunction` candidate relies only on a nearby executable pointer or string proximity.

## Next Steps

1. When a core exists, build an offline core evidence pack under
   `/servidor/ark/obelisk/dumps` or another explicitly chosen artifact directory.
2. Compare the GDB memory windows for `0x5956f30` against the existing static-root notes.
3. If a candidate table is readable, add a small offline decoder only after documenting the
   exact entry layout observed in the core.
4. Keep `GObjects` and `UFunction` work gated behind accepted `FName` resolution.
