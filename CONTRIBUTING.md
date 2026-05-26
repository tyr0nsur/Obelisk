# Contributing

Obelisk is looking for contributors interested in Linux-native ARK server
modding, UE4 reflection, and safe runtime hooking.

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
- Keep experimental scanners behind explicit flags.
- Document every new signature or offset with how it was found.
- Avoid hardcoded offsets when reflection can be used.

## Build Check

Before opening a pull request:

```bash
git diff --check
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

Docs-only changes may skip the CMake build, but the PR should say why.

## Runtime Testing

Use one test map before enabling cluster-wide.

Recommended test posture:

```bash
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
./arkserver restart
```

Then remove `disable-plugins-ragnarok` only after the core hook is stable.

## Commit Style

Use short, direct commit messages:

```text
Add filtered ProcessEvent callbacks
Document centralized install layout
Harden chat plugin FString probing
```

## Current Priorities

1. Resolve `FName` indices to names.
2. Stabilize filtered chat interception.
3. Add safe plugin examples.
4. Add CI build checks.
5. Convert the experimental scanner into a documented offline/debug tool.

Use [docs/STATUS.md](docs/STATUS.md) before changing runtime behavior. It
defines which pieces are stable baseline, experimental, or not ready.

## Pull Request Checklist

The GitHub PR template contains the canonical checklist. At minimum, every PR
should answer:

- What subsystem or documentation area changed?
- Which validation ran, and what was intentionally skipped?
- Did the change affect live-server safety, research notes, or agent handoff?
- Are experimental probes still behind explicit gates?
