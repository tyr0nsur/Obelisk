# Contributing

Obelisk is looking for contributors interested in Linux-native ARK server
modding, UE4 reflection, and safe runtime hooking.

## Branch Model

The canonical development branch is `main`.

Use short-lived topic branches for work:

```text
feature/<area>-<summary>
fix/<area>-<summary>
docs/<area>-<summary>
research/<topic>
```

Open pull requests back to `main`. Keep PRs focused on one subsystem or one
documentation/research topic. Do not keep long-running integration branches
unless the team lead explicitly creates one for a release or migration.

Internal coordination notes are separate from the public contributor workflow,
which should stay focused on branch scope, validation, and PR review.

## Repository Map

```text
include/obelisk/      Public SDK headers and ABI surface
api/                  Transitional include wrappers
core/                 Plugin manager, event manager, config, lifecycle
hooks/                Runtime hook implementations and ProcessEvent observers
loader/               LD_PRELOAD bootstrap
runtime/              Logging, marker helpers, runtime services
ue/                   UE4 memory/reflection helpers and recognizers
plugins/oBaseEvents/  First official example plugin
tests/                C++ ABI/runtime/SDK tests and fixtures
scripts/              Install, validation, and offline reversing tooling
packaging/            LinuxGSM and harness wrapper templates
docs/                 Architecture, status, install, release, research notes
```

Public plugin contracts live under `include/obelisk/`. ARK/LinuxGSM files are
validation adapters, not the product API.

## Useful Areas

- Linux ELF and x86_64 detours.
- Unreal Engine 4 reflection internals.
- ARK dedicated server behavior.
- C ABI plugin design.
- CMake, packaging, and CI.
- Documentation and reproducible test setups.

## Development Rules

- Keep `ShooterGameServer` stability first.
- Prefer filtered callbacks over global `ProcessEvent` callbacks.
- Do not let C++ exceptions cross plugin boundaries.
- Do not expose STL types in the public plugin ABI.
- Keep experimental scanners and observers behind env plus per-instance markers.
- Document every new signature or offset with how it was found.
- Avoid hardcoded offsets when reflection can be used.
- Follow [docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md) before
  adding or promoting plugins.

## Build Check

Before opening a pull request:

```bash
git diff --check
cmake -S . -B build
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
scripts/run_script_tests.sh
```

Docs-only changes may skip the CMake build, but the PR should say why.
Changes to install layout, CMake package exports, public headers, or SDK
packaging should also run:

```bash
scripts/test_install_obelisk_layout.sh
```

## Runtime Testing

Runtime validation requires an operator-approved window for the named instance.
Do not restart servers, edit live server roots, or change markers from a PR
unless the work explicitly owns live-ops for that window.

For an approved validation target, confirm stable posture with explicit map and instance
values:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Experimental debug/scanner work must use explicit env plus instance markers and
rollback to stable posture. Use only an operator-approved debug or development
target for a scoped test, then return it to the requested operational state.

## Commit Style

Use short, direct commit messages:

```text
Add filtered ProcessEvent callbacks
Document centralized install layout
Harden reflected event parameter decoding
```

## Current Priorities

1. Build the general UE4 reflection pipeline: `FName`, `GNames`, `GObjects`,
   `UObject`, `UFunction`, and property-chain validation.
2. Keep runtime hooks, marker gates, plugin lifecycle, and C ABI behavior stable.
3. Expand offline snapshot tooling and second-source comparison before promoting
   public SDK module APIs.
4. Add safe plugin examples only after the relevant promotion gates are met.
5. Reduce operational and documentation debt that can mislead new contributors.

Use [docs/STATUS.md](docs/STATUS.md) before changing runtime behavior. It
defines which pieces are stable baseline, experimental, or not ready.

## Pull Request Checklist

The GitHub PR template contains the canonical checklist. At minimum, every PR
should answer:

- What subsystem or documentation area changed?
- Which validation ran, and what was intentionally skipped?
- Did the change affect live-server safety, research notes, or public status docs?
- Are experimental probes still behind explicit gates?
