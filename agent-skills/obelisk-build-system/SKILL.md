---
name: obelisk-build-system
description: Standard CMake configuration rules and build environment requirements for the Obelisk runtime and its plugins.
---

# Obelisk Build System Skill

**Context:** Obelisk uses CMake and C++20. It builds a shared object (`libobelisk.so`) meant to be injected into the ARK Dedicated Server via `LD_PRELOAD`.

**When to use this skill:**
- When setting up `CMakeLists.txt` for the core runtime.
- When creating a template for a new plugin.
- When adding external dependencies.

## Build Requirements

### 1. Toolchain
- **Language Standard:** C++20 (`set(CMAKE_CXX_STANDARD 20)`)
- **Compiler:** `clang` or `gcc` on Linux (Ubuntu 22.04 or Debian 12 minimum).
- **Architecture:** x86_64.

### 2. CMake Targets

**Runtime:**
The core Obelisk runtime should be built as a `SHARED` library.
```cmake
add_library(obelisk SHARED src/main.cpp src/hooking.cpp ...)
target_link_libraries(obelisk PRIVATE dl pthread)
```

**Plugins:**
Plugins should also be `SHARED` or `MODULE` libraries that link against the Obelisk API headers but do not static link the Obelisk runtime itself.
```cmake
add_library(MyPlugin MODULE src/plugin_main.cpp)
```

### 3. Dependency Management
- Use `FetchContent` or standard Linux package managers for dependencies.
- Required dependencies:
  - `spdlog` (for logging)
  - `fmt` (string formatting)
  - `capstone` (for binary analysis and signature scanning)
  - `subhook` or `funchook` (hooking)

### 4. Compiler Flags
To ensure proper `LD_PRELOAD` behavior and ELF symbol resolution:
- Use `-fPIC` (Position Independent Code).
- Consider `-fvisibility=hidden` by default, explicitly exporting only what is needed to avoid symbol collision with `ShooterGameServer`.

## Checklist
- [ ] Is C++20 strictly enforced in CMake?
- [ ] Are dependencies integrated without breaking the build on a clean Ubuntu/Debian system?
- [ ] Is the output a `.so` file that can be loaded via `LD_PRELOAD`?
