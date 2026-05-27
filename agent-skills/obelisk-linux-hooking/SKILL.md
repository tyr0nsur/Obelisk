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
prologue. Direct-offset fallbacks such as `base + 0x1D34E20` are not acceptable in active
runtime code. If the signature or prologue changes, refuse to hook until the target is
deliberately rediscovered and validation is updated.

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

- Keep hook enablement per instance via `/servidor/ark/obelisk/state/instances/<id>`.
- Validate the core hook with plugins disabled first.
- Keep tracing disabled by default: `OBELISK_PE_TRACE_LIMIT=0`.
- Never run startup scanners or native exec probes by default.
- Do not use `write(/dev/null, ptr, size)` as a Linux readability probe. Obelisk's
  `Memory::IsReadable` is maps-backed; arbitrary scanner reads still need metadata and
  range validation, and UE-owned hot-path pointers should avoid syscall-style probing when
  provenance is strong.

## Validation

```bash
cmake --build build -j"$(nproc)"
mkdir -p /servidor/ark/obelisk/state/instances/arkserver
touch /servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
./arkserver restart
tail -n 80 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
```

Expected:

- `ProcessEvent absolute x64 hook installed successfully`
- server process remains alive
- player can join
