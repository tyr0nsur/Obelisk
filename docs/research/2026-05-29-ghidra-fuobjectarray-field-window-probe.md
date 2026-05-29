# Ghidra FUObjectArray Field Window Probe

## Objective

Use bounded offline Ghidra/radare2 windows to test whether static GObjects/FUObjectItem
serial evidence belongs to one coherent object base, without promoting public object
identity or exposing runtime handles.

## Environment

- ARK binary: `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`
- ARK binary SHA256: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Tools: `analyzeHeadless` from Ghidra 12.1, `radare2 5.5.0`
- Output root: `/tmp/obelisk-guobjectarray-field-window-ghidra-20260529`
- Server posture: no server touched; offline binary only.

## Evidence

The Ghidra run used `-noanalysis` and
`scripts/ghidra/DumpFuObjectArrayWindows.java`, which creates functions only at the
bounded target windows. The script emits `script_version`, `program`, `language`,
`image_base`, `window_count`, and one `window_spec` line per bounded range before any
decompiler/disassembly output, so archived stdout records the exact replay window set.
Raw output stayed under `/tmp`.

Observed shape:

- `static_init_caller` passes `BASE` to the constructor/helper and registers a finalizer
  with the same `BASE`.
- The constructor/helper writes fields under that `BASE`, including the chunks/count
  region and a serial seed field.
- Allocation/destructor helpers read and write through the same chunks/count field family.
- Serial accessors compare against the count field, derive `FUObjectItem` from the chunks
  pointer, allocate serials through the serial seed, and publish them into
  `FUObjectItem+0x8`.
- The radare2 window dump confirms the same target-window instructions as the Ghidra
  decompiler/disassembly output.

## Result

Confirmed as internal static research evidence only. This strengthens the hypothesis that
the static GObjects candidate and serial-bearing accessors refer to one coherent
FUObjectArray-style field window for the current ARK binary hash.

It does not promote:

- public `GObjects` access;
- public object identity;
- `ResourceHandle`;
- post-callback object lifetime guarantees;
- mutation or return overrides.

## Remaining Gate

`scripts/convert_fuobjectarray_field_window_probe.py` now converts the bounded Ghidra/r2
outputs into `obelisk.fuobjectarray-field-window-redacted.v1` JSON. The converter keeps
raw decompiler text, raw disassembly, absolute paths, and absolute addresses out of the
JSON, while preserving artifact hashes, tool versions, window roles, and relative field
offsets.

`scripts/build_static_global_promotion_evidence.py` can consume that redacted JSON through
`--fuobjectarray-field-window-evidence`. Valid evidence may clear only
`missing_gobjects_coherent_field_window` for the matching `gobjects` candidate and binary
SHA. The static global promotion gate still remains `ready=false` with
`static_only_evidence`, so this is internal research evidence only.

Validation:

```bash
OUT=/tmp/obelisk-guobjectarray-field-window-ghidra-20260529
BIN=/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
mkdir -p "$OUT/raw" "$OUT/ghidra-project"
analyzeHeadless "$OUT/ghidra-project" ObeliskGObjectsFieldWindow \
  -import "$BIN" \
  -scriptPath scripts/ghidra \
  -postScript DumpFuObjectArrayWindows.java \
  -noanalysis \
  -deleteProject \
  > "$OUT/raw/ghidra-headless.stdout" \
  2> "$OUT/raw/ghidra-headless.stderr"

python3 scripts/test_convert_fuobjectarray_field_window_probe.py
python3 scripts/test_build_static_global_promotion_evidence.py
```
