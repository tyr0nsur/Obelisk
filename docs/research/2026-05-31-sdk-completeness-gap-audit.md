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

## 2026-06-01 Follow-Up: ABI/Package Consumer Guardrail

Scope: audit whether ABI/package debt could block future complete-SDK surfaces, limited to
versioning append-only behavior, public header guardrails, installed SDK consumer tests,
and examples. No public header, runtime code, Plugin Hub claim, commit, tag, push, Discord,
or server action was used.

Decision: package-shape risk remains low for the current core SDK package, with one
guardrail improvement adopted.

Evidence checked:

- `include/obelisk/ObeliskApi.h` keeps public ABI structs POD/C-compatible, ABI version
  and `struct_size` metadata on public payload/context structs, and append-only
  `ObeliskApi` fields after the original function table.
- `tests/abi/AbiLayoutTests.cpp` and `tests/abi/CAbiLayoutTests.c` freeze x86_64 sizes,
  alignments, offsets, capability bits, enum values, and the current appended terminal
  slot.
- `scripts/test_public_sdk_guardrails.py` keeps the public header on the reviewed v0.1
  allowlist and blocks unpromoted identity, ResourceHandle, command, permission,
  mutation, return-override, and broad v1-complete wording.
- `scripts/test_install_obelisk_layout.sh` installs to a temporary root, confirms only
  `include/obelisk/ObeliskApi.h` is public, rejects source-tree include leakage, builds
  installed C/C++ consumers, and builds the release-supported installed-SDK examples from
  `examples/`.
- `cmake/ObeliskConfig.cmake.in` exports public ABI version variables derived from the
  header macros.

Adopted guardrail: `scripts/test_versioning_guardrails.py` now requires every public
`OBELISK_*ABI_VERSION` macro to be exported through the installed CMake package, passed as
an `OBELISK_CMAKE_*` compile definition in `tests/sdk_installed_consumer/CMakeLists.txt`,
and compared against the installed header in both C and C++ installed consumers. This
prevents future ABI-version macros from being package-visible but unvalidated by external
consumer fixtures.

Residual prioritized debt:

1. Future SDK surfaces still need promotion-specific ABI tests and installed-consumer
   fixtures before public header exposure; the current package scaffolding cannot replace
   copied-payload, ownership, privacy, and lifecycle gates.
2. `ObeliskApi` v1 keeps `abi_version` and `struct_size` appended for original table
   compatibility. That is guarded, but a later ABI-breaking v2 should use a front-loaded
   header after an explicit major-version design.
3. Example coverage intentionally validates release-supported installed-SDK seeds only.
   Experimental copied-data examples must remain clearly labeled and should not become
   release-supported package evidence without their own installed-consumer checks.
