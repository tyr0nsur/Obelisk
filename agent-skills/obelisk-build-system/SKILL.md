---
name: obelisk-build-system
description: Use when changing Obelisk CMake, dependencies, build outputs, install scripts, or centralized deployment layout for the runtime and plugins.
---

# Obelisk Build System

Obelisk uses CMake, C++20, and Linux x86_64 shared objects.

## Build

```bash
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

Expected outputs:

```text
build/libobelisk.so
build/_deps/subhook-build/libsubhook.so
build/plugins/oBaseEvents/oBaseEvents.so
```

## Central Install

Use:

```bash
./scripts/install_obelisk.sh /servidor/ark/obelisk
```

Install layout:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  config/
  logs/
  state/instances/
```

Do not install runtime artifacts directly into `ShooterGame/Binaries/Linux` except the thin `ObeliskRun.sh` wrapper.

## Dependency Rules

- Pin dependency versions where possible; avoid tracking `master` for reproducible builds.
- Runtime links currently include `fmt`, `spdlog`, `subhook`, `dl`, and `pthread`.
- Do not commit `.so` outputs, logs, config state, or build directories.
- `oBaseEvents` is the first official plugin target and should remain small,
  instructional, and safe by default.
- Experimental/research plugins should not be installed into `plugins/` by default.

## Before Commit

```bash
git diff --check
cmake --build build -j"$(nproc)"
git status --short --ignored
```

Check that no files matching these patterns are staged:

```text
build/
*.so
*.log
chat_config.json
/servidor/ark/obelisk/state/*
```
