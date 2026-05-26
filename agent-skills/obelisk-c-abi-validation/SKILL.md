---
name: obelisk-c-abi-validation
description: Ensures any code crossing the plugin boundary uses C ABI, POD structs, and avoids STL/exceptions to guarantee stable execution for Obelisk plugins.
---

# Obelisk C ABI Validation Skill

**Context:** Obelisk is a Linux-first Runtime for ARK: Survival Evolved. To ensure a stable ABI across updates, the communication between the Obelisk runtime and dynamically loaded plugins (`.so`) must exclusively use a C ABI. 

**When to use this skill:**
- When defining an API struct or function that a plugin will call.
- When writing the `Plugin_Load` entry point for a new plugin.
- When auditing code that crosses the runtime-plugin boundary.

## ABI Rules

### 1. 🟢 ALWAYS USE:
- `extern "C"` for any function exported or imported by a plugin.
- POD (Plain Old Data) structs.
- Primitive types (`uint64_t`, `const char*`, `bool`, etc.).
- Function pointers inside structs to simulate interfaces without vtables.

**Correct Example:**
```cpp
extern "C"
{
    typedef struct
    {
        uint64_t steam_id;
        const char* name;
    } ObeliskPlayer;

    typedef struct
    {
        void (*Log)(const char* message);
        ObeliskPlayer* (*GetPlayer)(uint64_t steam_id);
    } ObeliskAPI;

    // Plugin entry point
    void Plugin_Load(ObeliskAPI* api);
}
```

### 2. 🔴 NEVER USE:
- STL containers (`std::string`, `std::vector`, `std::unordered_map`) crossing the boundary.
- C++ exceptions (`throw`, `try/catch` must be caught inside the plugin, NEVER bubble up).
- Abstract C++ classes with virtual methods crossing the boundary (e.g. `virtual void Load() = 0;`).
- RTTI or typeid that relies on compiler-specific mangling.

## Validation Checklist
- [ ] Are all boundary structs `extern "C"`?
- [ ] Are strings passed as `const char*` or pre-allocated buffers rather than `std::string`?
- [ ] Does the plugin entry point have a C-compatible signature (`void Plugin_Load(...)`)?
- [ ] Have all potential exceptions within the plugin logic been handled internally to avoid crashing the C host?
