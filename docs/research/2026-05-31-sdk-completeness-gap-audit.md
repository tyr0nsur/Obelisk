# SDK Completeness Gap Audit

Scope: packaging, public headers, installed SDK consumer coverage, and first-party example
buildability for a v0.1.0/v0.2 SDK usability check. No server paths, runtime scanners,
restarts, Git operations, tags, pushes, or Discord actions were used.

## Decision

mostly-resolved

The current installed SDK path is not blocked for a core-first v0.1.0 RC: the package exports
`Obelisk::obelisk_sdk`, installs only `include/obelisk/ObeliskApi.h`, publishes the expected
CMake package files, and the installed consumer validation passes from a temporary install
root without source-tree include leakage.

The original example packaging/usability gap is now mostly closed by installed-SDK
examples under `examples/`. Remaining limitations are v1 surface blockers, not package
shape.

## Evidence Checked

- `CMakeLists.txt:47-51` defines `obelisk_sdk` as an installable interface target with
  build/install include directories.
- `CMakeLists.txt:459-497` installs runtime and SDK components, including
  `ObeliskTargets.cmake`, `ObeliskConfig.cmake`, and `ObeliskConfigVersion.cmake`.
- `cmake/ObeliskConfig.cmake.in:3-13` exports development/release metadata and public ABI
  version variables before including `ObeliskTargets.cmake`.
- `scripts/install_obelisk.sh:245-258` preflights runtime plus SDK package artifacts and
  allowlists the installed SDK files.
- `scripts/install_obelisk.sh:302-320` publishes staged SDK files with rollback snapshots.
- `scripts/test_install_obelisk_layout.sh` validates installed runtime/SDK layout, header
  allowlist, no source/build path leaks in package files, RUNPATH, reinstall backup,
  external installed SDK consumer builds, and installed-SDK builds for
  `examples/sdk_minimal_plugin`, `examples/sdk_descriptor_catalog`, and
  `examples/sdk_timer_plugin`.
- `tests/sdk_installed_consumer/CMakeLists.txt:11-93` builds C and C++ plugins using
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED)` and `Obelisk::obelisk_sdk`.

Verification run:

```text
OBELISK_BUILD_DIR=/home/flowcommunity-ark/Obelisk/build \
  scripts/test_install_obelisk_layout.sh /tmp/obelisk-sdk-gap-audit.TCewnM
```

Result: passed. The script reported `Install layout and public SDK consumer validation
passed`.

## Findings

### 1. External example packaging was source-tree-shaped

Priority: mostly-resolved in later integration

At the time of this audit, the visible first-party examples were in-tree reference
plugins:

- `plugins/oBaseEvents/CMakeLists.txt:1-3`
- `plugins/oProcessTimer/CMakeLists.txt:1-3`
- `plugins/oDescriptorCatalog/CMakeLists.txt:1-3`

Each links the in-tree target name `obelisk_sdk`, not the installed package target
`Obelisk::obelisk_sdk`, and each adds `${PROJECT_SOURCE_DIR}/extern` for the vendored
`nlohmann/json.hpp`. The example sources include that private vendored header:

- `plugins/oBaseEvents/oBaseEvents.cpp:1-2`
- `plugins/oProcessTimer/oProcessTimer.cpp:1-2`
- `plugins/oDescriptorCatalog/oDescriptorCatalog.cpp:1-2`

This did not break the RC package because `tests/sdk_installed_consumer` already proved
external consumers could build against the installed SDK.

Closure now exists as release-supported seed examples:

- `examples/sdk_minimal_plugin`
- `examples/sdk_descriptor_catalog`
- `examples/sdk_timer_plugin`

They use `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and
`Obelisk::obelisk_sdk`, and the install-layout gate builds them from a temporary consumer
root against the installed package. `plugins/*` remain in-tree runtime reference plugins,
not external package scaffolds.

### 2. The README minimal plugin was stricter than the append-only ABI guidance

Priority: resolved in the integration that adopted this audit

`README.md:274-276` rejects any runtime whose `ObeliskApi::struct_size` is smaller than
`sizeof(ObeliskApi)`, even though the snippet only needs the base logging prefix. The ABI
guidance elsewhere says appended slots should be guarded by capability and terminal
`struct_size` checks, not by requiring the whole current table for minimal functionality.

This is acceptable for a same-ref v0.1.0 smoke example, but it is a poor v0.2-facing SDK
pattern because append-only evolution can make old/new examples look unnecessarily
incompatible. The installed consumer fixtures use more precise slot checks, so this was a
documentation/example debt rather than a packaging blocker.

Closure adopted: the README minimal plugin now validates the API metadata prefix before
reading `abi_version` and no longer requires `sizeof(ObeliskApi)` for a logging-only
example. Callback/timer examples remain responsible for terminal-slot checks before using
appended ABI fields.

## Non-Issues

- Installed SDK package layout is present and validated.
- Public header install is allowlisted to `include/obelisk/ObeliskApi.h`; no extra public
  headers were observed in the layout test.
- Installed CMake consumer validation covers both C and C++ plugin compilation through
  `Obelisk::obelisk_sdk`.
- ABI boundary types in `include/obelisk/ObeliskApi.h` are C-compatible POD/function-pointer
  surfaces; no STL or C++ ownership types cross the public header boundary.
