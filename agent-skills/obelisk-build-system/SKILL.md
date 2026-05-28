---
name: obelisk-build-system
description: "Use when changing Obelisk CMake, dependencies, build outputs, install scripts, or centralized deployment layout for the runtime and plugins."
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

The installed SDK must also expose a CMake package:

```text
<root>/include/obelisk/ObeliskApi.h
<root>/lib/cmake/Obelisk/ObeliskConfig.cmake
<root>/lib/cmake/Obelisk/ObeliskTargets.cmake
```

External plugin projects should prefer:

```cmake
find_package(Obelisk CONFIG REQUIRED)
target_link_libraries(my_plugin PRIVATE Obelisk::obelisk_sdk)
```

Do not install runtime artifacts directly into `ShooterGame/Binaries/Linux` except the thin `ObeliskRun.sh` wrapper.

## Dependency Rules

- Pin dependency versions where possible; avoid tracking `master` for reproducible builds.
- Runtime links currently include `fmt`, `spdlog`, `subhook`, `dl`, and `pthread`.
- Do not commit `.so` outputs, logs, config state, or build directories.
- `oBaseEvents` is the first official plugin target and should remain small,
  instructional, and safe by default.
- Experimental/research plugins should not be installed into `plugins/` by default.
- Install roots and managed subdirectories must not be symlinks. Reject existing symlinks
  for `lib`, `plugins`, `include`, `config`, `logs`, and `state/instances` before writing
  runtime, SDK, or plugin artifacts.
- Runtime and SDK publication are one compatibility unit. Preflight all required runtime
  and SDK build artifacts before publishing runtime libraries, and roll back the published
  runtime pair if SDK install fails after runtime publication.

## Before Commit

```bash
git diff --check
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
python3 -m unittest scripts/test_analyze_reflectionscanner_capture.py
python3 -m unittest scripts/test_build_core_dump_evidence_pack.py
scripts/test_check_obelisk_server_posture.sh
scripts/test_install_obelisk_layout.sh /tmp/obelisk-install-layout-check
git status --short --ignored
```

For runtime/server work, also run the posture check after the server is restored:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map Ragnarok --instance arkserver
```

Use explicit `--map` and `--instance`; do not rely on script defaults during Obelisk debug
rounds. Under current RAM constraints, keep `arkserver2` / TheIsland stopped unless the
operator explicitly reopens it for a named window.

Check that no files matching these patterns are staged:

```text
build/
*.so
*.log
chat_config.json
/servidor/ark/obelisk/state/*
```
