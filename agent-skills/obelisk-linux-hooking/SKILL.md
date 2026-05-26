---
name: obelisk-linux-hooking
description: Use when implementing or auditing Linux ELF/x86_64 hooks in Obelisk, especially absolute jumps, LD_PRELOAD, mprotect, trampolines, and ProcessEvent hook safety.
---

# Obelisk Linux Hooking

Obelisk is Linux-native. Do not use Windows PE/DLL tooling or MinHook-style assumptions.

## Preferred ProcessEvent Hook

For `ShooterGameServer` internal functions, use an absolute x64 jump:

```text
48 B8 <imm64> FF E0
mov rax, imm64; jmp rax
```

Reason: a 5-byte `jmp rel32` only reaches +/-2GB. ARK maps the executable low and shared libraries high, so rel32 detours can jump to the wrong address and crash.

`subhook` may remain for isolated experimental probes, but it is not the preferred implementation for `UObject::ProcessEvent`.

Before installing a ProcessEvent hook, validate that the target is inside the
ShooterGameServer executable segment and starts with a known compatible instruction-boundary
prologue. Direct-offset fallbacks such as `base + 0x1D34E20` are not acceptable unless they
pass the same range and prologue checks; if the prologue changes, refuse to hook until an
instruction decoder or deliberately updated validation is in place.

## Memory Protection

When patching `.text`:

1. Get page size with `sysconf(_SC_PAGESIZE)`.
2. Align start address down to page boundary.
3. Align end address up to page boundary.
4. `mprotect(..., PROT_READ | PROT_WRITE | PROT_EXEC)`.
5. Write patch.
6. Flush instruction cache with `__builtin___clear_cache`.
7. Restore the mapping's original permissions when they are known. Use `PROT_READ |
   PROT_EXEC` only when the target is confirmed to be an executable text mapping and the
   original permissions cannot be recovered.

## Operational Safety

- Keep hook enablement per map via `/servidor/ark/obelisk/state`.
- Validate the core hook with plugins disabled first.
- Keep tracing disabled by default: `OBELISK_PE_TRACE_LIMIT=0`.
- Never run startup scanners or native exec probes by default.

## Validation

```bash
cmake --build build -j"$(nproc)"
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
./arkserver restart
tail -n 80 /servidor/ark/obelisk/logs/Obelisk-Ragnarok.log
```

Expected:

- `ProcessEvent absolute x64 hook installed successfully`
- server process remains alive
- player can join
