---
name: obelisk-linux-hooking
description: Instructions for using subhook or funchook on Linux ELF binaries, memory protection, and detours for the Obelisk runtime.
---

# Obelisk Linux Hooking Skill

**Context:** Obelisk is a Linux-native runtime. Standard Windows tools like MinHook, Detours, and PE-parsing libraries are strictly prohibited. We operate on ELF binaries using native Linux APIs.

**When to use this skill:**
- When setting up a new hook (e.g., hooking `ProcessEvent` or `LD_PRELOAD` initialization).
- When resolving memory protection issues.

## Hooking Guidelines

### 1. Allowed Libraries
Use lightweight, cross-platform or Linux-compatible hooking libraries:
- `subhook`
- `funchook`

### 2. Finding Targets (dlsym vs Signature Scanning)
- **dlsym:** For exported symbols, use `dlsym(RTLD_NEXT, "symbol_name")`.
- **Signature Scanning:** For internal functions (like `ProcessEvent`), use a pattern scanner on the mapped memory segments.

### 3. Memory Protection (`mprotect`)
Linux strictly enforces W^X (Write XOR Execute). When applying a hook manually or when writing a pattern scanner, you must modify page permissions.
- Get the page size: `sysconf(_SC_PAGESIZE)`
- Align the address: `(uintptr_t)addr & ~(page_size - 1)`
- Change permissions before hooking: `mprotect(aligned_addr, len, PROT_READ | PROT_WRITE | PROT_EXEC)`
- **CRITICAL:** Always restore original permissions after modifying `.text` sections.

### 4. Avoiding DLL Loaders
Do not implement custom PE or DLL loaders. The runtime is injected using `LD_PRELOAD`.
```bash
LD_PRELOAD=./libobelisk.so ./ShooterGameServer
```
Inside the code, use `__attribute__((constructor))` for initialization.

**Example Bootstrap:**
```cpp
#include <cstdio>

__attribute__((constructor))
void Obelisk_Init() {
    printf("[Obelisk] Runtime Loaded natively via LD_PRELOAD.\n");
    // Initialize hooking engine...
}
```

## Checklist
- [ ] Is the hooking library native to Linux/ELF?
- [ ] Are memory pages aligned correctly before calling `mprotect`?
- [ ] Is the runtime initialized using compiler constructors rather than external injectors?
