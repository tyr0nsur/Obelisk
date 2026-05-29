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

## Build And Release Checks

Before opening a normal development pull request, run the focused fast checks
that match your change:

```bash
git diff --check
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
scripts/run_script_tests.sh
```

Docs-only changes may skip the CMake build, but the PR should say why.

Release-candidate, installer, SDK package, CMake export, public-header, or
first-stable scope changes must use the core-first release gate instead of
hand-picking equivalent commands:

```bash
scripts/check_release_readiness.sh
```

That gate requires a clean worktree by default and runs the build, CTest,
script tests, install-layout validation, operator CLI status check, install
dry-runs, plugin install dry-run, and whitespace checks with one set of
defaults.

PRs that promote reflected gameplay or module surfaces must run the same gate
with second-source readiness enabled and explicitly name every promoted target
set:

```bash
scripts/check_release_readiness.sh --require-second-source-readiness \
  --ufunction-second-source-root <candidate-snapshot-root> \
  --ufunction-second-source-target-set <target-set>
```

Add `--scriptstruct-second-source-root` only with an explicitly named
`--scriptstruct-second-source-target-set`. If readiness reports are kept, write
them under an ignored report directory with `--second-source-report-dir`.

Changes on the `ProcessEvent` hot path, including chat/reflection observer work,
should also run the local benchmark checker before review:

```bash
cmake --build build --target chat_reflection_benchmark
./build/chat_reflection_benchmark 20000 > /tmp/obelisk-chat-reflection-benchmark.txt
python3 scripts/check_chat_reflection_benchmark.py /tmp/obelisk-chat-reflection-benchmark.txt
```

This benchmark is synthetic local regression coverage. It does not promote chat
or any gameplay module to SDK scope, and it does not replace an operator-approved
runtime validation window when a change requires one.

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

1. Close the core-first `v0.1.0-rc` surface around stable runtime hooks, marker
   gates, plugin lifecycle, C ABI behavior, `GameplayPolicyEvent`, and
   `DescribeResourceKind`.
2. Keep additional gameplay/module APIs out of public scope until their copied
   payloads, callback lifetime, SDK consumer coverage, and explicitly named
   second-source gates are complete.
3. Expand offline snapshot tooling and second-source comparison before promoting
   public SDK module APIs.
4. Build the general UE4 reflection pipeline (`FName`, `GNames`, `GObjects`,
   `UObject`, `UFunction`, and property-chain validation) as research/tooling
   work unless a scoped RC task requires it.
5. Add safe plugin examples only after the relevant promotion gates are met.
6. Reduce operational and documentation debt that can mislead new contributors.

Use [docs/STATUS.md](docs/STATUS.md) before changing runtime behavior. It
defines which pieces are stable baseline, experimental, or not ready.

## Pull Request Checklist

The GitHub PR template contains the canonical checklist. At minimum, every PR
should answer:

- What subsystem or documentation area changed?
- Which validation ran, and what was intentionally skipped?
- Did the change affect live-server safety, research notes, or public status docs?
- Are experimental probes still behind explicit gates?
