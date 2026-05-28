# Versioning Policy

Obelisk uses SemVer-style names, but the project is still pre-release research and SDK
formation work. Version numbers are coordination markers first; they are not stability
promises until a tag is explicitly cut.

## Current Line

Current development line:

```text
0.1.0-dev
```

This means the repository is moving toward a future `v0.1.0`, but no `v0.1.0` release is
promised yet. The current tree may break plugin ABI, install layout, scanner output, or
debug-harness assumptions when that is the correct engineering tradeoff.

The CMake package version is intentionally numeric during this line:

```text
project(Obelisk VERSION 0.1.0)
```

`ObeliskConfigVersion.cmake` and installed SDK consumers use the numeric compatibility
floor, for example `find_package(Obelisk 0.1.0 CONFIG REQUIRED)`. That numeric package
version is not a release claim by itself; the release claim exists only when a matching
Git tag is cut after the release checklist passes.

The installed package also exports:

- `Obelisk_DEVELOPMENT_LINE`
- `Obelisk_RELEASE_CHANNEL`
- `Obelisk_API_ABI_VERSION`
- `Obelisk_PLUGIN_METADATA_ABI_VERSION`
- `Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION`

Consumers can inspect those CMake variables when they need to distinguish a dev package
from a tagged release or pin against a specific public C ABI.

## Allowed Version Labels

Use these labels consistently:

| Label | Meaning | Git tag? |
| --- | --- | --- |
| `0.1.0-dev` | Active development toward the first minor baseline. APIs can break. | No |
| `0.1.0-alpha.N` | A named preview for contributors when a specific checkpoint is useful to test. | Optional |
| `0.1.0-rc.N` | A release candidate after scope freeze and validation checklist pass. | Yes |
| `0.1.0` | First stable baseline for the documented runtime/SDK scope only. | Yes |
| `0.2.0-dev` | Development after `0.1.0`, likely reflection/event API work. | No |

Do not tag every useful commit. Prefer commits, research notes, and handoff updates until
there is a reason for external testers to compare against a named checkpoint.

## When Not To Tag

Do not create a version tag when:

- The work is primarily reverse-engineering evidence.
- ReflectionScanner behavior changed but `GNames`, `GObjects`, or `UFunction` candidates
  are not independently validated.
- The change only improves README, handoff, skills, or research notes.
- The runtime was not validated by the standard local test suite.
- The change depends on `/servidor/ark` state that is not reproduced in repo docs.
- The plugin ABI changed without ABI layout tests and migration notes.

## Breaking Changes Before 1.0

Before `1.0.0`, breaking changes are allowed, but they must be explicit. A breaking change
is any change that can make a previously valid plugin, wrapper, install layout, config, or
research workflow fail.

Record breaking changes in `CHANGELOG.md` under `0.1.0-dev` until a real release branch or
tag exists. Include:

- What changed.
- Who is affected.
- Whether migration is required now or only before enabling a feature.
- The commit or document that explains the reason.

Public ABI rules:

- Removing, retyping, or reordering public C ABI fields is an ABI break.
- Appending fields behind `abi_version` and `struct_size` can be compatible only when old
  plugins are rejected or handled deliberately.
- A future ABI-major redesign should be documented before implementation, not discovered
  through plugin crashes.

## Progress Tracking Without Stability Claims

Use this order of confidence:

1. `docs/research/YYYY-MM-DD-topic.md` for evidence, hypotheses, rejected paths, and risks.
2. `docs/agent-handoff/CURRENT.md` for concise active facts and next steps.
3. `docs/STATUS.md` for contributor-facing stability classification.
4. `CHANGELOG.md` for user-visible changes that matter across commits.
5. A pre-release tag only when external testing needs a fixed reference.

Avoid calling a feature stable because it compiled once. Stable baseline means the repo
contains enough tests, docs, gates, and rollback posture to reproduce the claim.

## Suggested Milestones

`0.1.0-dev` should remain active until these are true:

- Runtime/SDK tests cover PluginManager, EventManager, ABI layout, plugin config, and a
  minimal external SDK consumer.
- Install/package validation proves a clean install exposes headers, runtime libraries,
  and example plugin layout without relying on the source tree.
- `oBaseEvents` remains small and demonstrates only validated API surfaces.
- `docs/STATUS.md`, `docs/RELEASE.md`, and `CHANGELOG.md` agree on scope.
- The numeric CMake package version remains documented as a compatibility floor, not as
  proof that a stable tag exists.

`0.1.0-alpha.1` is reasonable when:

- The above baseline is mostly complete.
- Known missing features are clearly marked experimental or not ready.
- A contributor can build, test, install dry-run, and compile the SDK consumer from docs.

`0.1.0` should wait until:

- Release scope is frozen.
- CI is green.
- The release checklist passes.
- No known critical crash path exists in the documented default posture.

Reflection and chat should not block `0.1.0` unless they are advertised as part of the
stable scope. They should instead drive later `0.2.0-dev` or `0.3.0-dev` lines.
