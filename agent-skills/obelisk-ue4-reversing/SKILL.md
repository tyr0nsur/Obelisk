---
name: obelisk-ue4-reversing
description: Commands, procedures, and tools for reverse engineering the Linux UE4 ShooterGameServer to maintain Obelisk's compatibility.
---

# Obelisk UE4 Reversing Skill

**Context:** ARK updates frequently break signatures and offsets. Obelisk maintains an active reversing strategy to keep the runtime working. This skill covers how to inspect the Linux binary.

**When to use this skill:**
- When an update breaks the `ProcessEvent` hook or reflection system.
- When you need to find the signature of a new UE4 function.
- When debugging a crash related to `ShooterGameServer`.

## Reversing Toolkit

### 1. Static Analysis Command-line Tools
The primary tools for ELF inspection are native to Linux binutils:
- **`readelf`**: Use `readelf -Ws ShooterGameServer` to dump all symbols.
- **`nm`**: Use `nm -D ShooterGameServer` or `nm -C` (to demangle C++ names) to find exported and internal symbols.
- **`objdump`**: Use `objdump -d ShooterGameServer` to disassemble specific sections if you need to build a byte signature.

### 2. GDB (Dynamic Analysis)
Use `gdb` to attach to a running server or start it under debug.
- Run under GDB: `gdb --args ./ShooterGameServer "TheIsland?listen"`
- Set environment variables in GDB: `set environment LD_PRELOAD=./libobelisk.so`
- Find memory maps: `info proc mappings`

### 3. Signature Generation
When `dlsym` isn't enough (because a symbol is stripped or internal), create an IDA/Ghidra style pattern (e.g., `48 89 5C 24 ? 48 89 6C 24 ? 48 89 74 24 ? 57 41 56 41 57 48 83 EC ? 48 8B 05 ? ? ? ? 48 33 C4`).
- Use Capstone at runtime to verify instructions if you are scanning memory dynamically.

### 4. UE4SS and Dumper-7
While Obelisk operates natively, you can use output from `Dumper-7` or `UE4SS` (run on a Windows client or server if necessary) to understand the `UObject` layouts and `UFunction` names.
- Map the dumped `FNames` and `ProcessEvent` structures to your Linux signatures.

## Checklist
- [ ] Have you verified if the symbol is exported via `nm -D` before resorting to signature scanning?
- [ ] Are you using demangled names (`c++filt`) when searching for specific UE4 classes?
- [ ] Have you tested the signature against the latest `ShooterGameServer` binary using Capstone or GDB?
