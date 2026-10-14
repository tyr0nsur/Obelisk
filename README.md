# Obelisk — native Linux ARK plugin prototype

This private repository contains the native Linux runtime and plugin API being
developed for **ARK: Survival Evolved**. The public project name is
**ObeliskNative**; Obelisk remains the internal source and ABI name.

## Verified milestone

On 14 October 2026, a real **Epic Games 361.8** client connected to the
**public-branch ASE native Linux dedicated server 361.7**. The `oPing` plugin
received `/ping` and the player confirmed the visible `pong` reply. Ordinary
chat and a disconnect/relogin were also confirmed. Copied native identity
observations were consistent across that relogin; this does not establish
storefront provenance, authentication or a durable player/session contract.

The prototype baseline passed **147 CTest checks** before the latest identity
and lifecycle extension. The current build now passes **156/156 CTest checks**,
including the new identity and lifecycle fixtures. Those automated checks
cover runtime and plugin behavior; the real-client observation establishes
the in-game command/reply path. Steam acceptance, reply separation between two
real players and the remaining session cases are still pending.

The current source appends copied player observations and typed lifecycle
notifications to the C API, extending `ObeliskApi` to **312 bytes on Linux
x86_64**. Their build and fixture checks pass. The Epic client also confirmed
the name and opaque native ID displayed by `/whoami`, and the plugin received
the new owner-validated login and logout observations. Typed relogin, interrupted
connections and two-player separation remain pending for this new path.

This is a working prototype, not a production-stable release or a complete
ArkApi-equivalent SDK. See [oPing implementation and acceptance status](docs/OPING_PROTOTYPE.md)
for the current target, evidence and remaining checks.

## Plugin lifecycle milestone

The installed native runtime now controls the cooperative `oPing` plugin through
an OS-local operator socket. Thirteen live requests covered status, pause,
resume, two reloads, stop and start while the game server PID remained unchanged.
Four plugin generations loaded; the final generation is running. Cleanup closes
admission and drains callbacks, registrations and user-data destruction before
Shutdown. Failed cleanup or lifecycle exceptions retain mapped code.

The directed reply now uses the independently verified private-chat RPC. Startup
checks its profile; visible chat presentation still needs real-client acceptance.
TheIsland uses the recovered gameplay configuration with 70 slots and retains the
current world/profile. No historical player saves were available to restore.
See [operator lifecycle](docs/PLUGIN_LIFECYCLE_OPERATIONS.md) and
[function stages](docs/research/NATIVE_LINUX_FUNCTION_STAGES.md).

## Current development

The immediate work is a small, useful Linux plugin demonstrated with real
clients. The operator-authorized scope is recorded in
[the October reboot review](docs/REBOOT_2026-10-13.md); its initial installation
and smoke-test details are historical, while `OPING_PROTOTYPE.md` tracks the
active public-branch target.

The runtime loads native `.so` plugins through a versioned C ABI. The current
command path preserves exact matching and adds opt-in verb matching with
arguments and ASCII case folding, runs on the invoking game thread and sends a
synchronous reply to that invocation. Registered commands are consumed;
ordinary chat continues through the original game implementation. UE pointers
and target-specific layouts stay in the private Linux adapter.

Next acceptance work:

- Verify `/ping` with a real Steam client.
- Connect two players and confirm each reply reaches only its intended player.
- Exercise disconnect/relogin and reject expired or previous invocation tokens.
- Corroborate the new copied player snapshot and lifecycle API with real sessions,
  including failed or interrupted connections.

The authorized product scope now includes an original administrative suite and
functional migration from ASE plugin workflows. First-party utility commands,
private offline permission/wallet foundations and migration inspection are being
verified separately. See [suite status](docs/SUITE_STATUS.md),
[functional catalog](docs/research/ARKAPI_PLUGIN_SUITE_PARITY.md),
[SDK parity requirements](docs/research/ARKAPI_API_PARITY.md),
[offline storage](docs/SUITE_STORAGE.md) and
[migration inspection](docs/ARKAPI_MIGRATION.md). Gameplay mutations require their
own native proof and client acceptance; complete parity has not been established.

The [beta tester guide](docs/BETA_TESTER_GUIDE.md) lists all 20 current chat
commands and 88 acceptance cases with expected results and a report template.
Cases remain pending until actual client observations are recorded. The
announcement publisher attaches the reviewed guide to the operator-selected
Discord channel; communication itself does not mark a gameplay case accepted.

## Build and test

Requirements:

- Linux x86_64, CMake 3.22+, Git, and a C/C++ compiler with C++20 support.
- OpenSSL Crypto development headers and library. On Debian/Ubuntu, install
  `libssl-dev` alongside `build-essential`, `cmake` and `git`.
- The pinned fmt, spdlog and subhook dependency sources. CMake fetches them on a
  fresh configure; the active laboratory build already retains them in `_deps`.

From the repository root, reuse the sibling build directory:

```bash
cmake -S . -B ../build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ../build -j2
ctest --test-dir ../build --output-on-failure
```

The active source is `/servidor/obelisk/Obelisk` and the sole laboratory build is
`/servidor/obelisk/build`. Its pinned dependency sources and manifest are retained
there. Use focused targets while iterating, then the relevant full build/tests.
Push/PR CI builds the current native prototype, runs CTest, the chat benchmark
and its operator/SDK/manager guardrails. The unchanged full historical script and
release checks run through the manual `legacy-research.yml` workflow. Seven old
planning-fixture failures currently depend on missing external offline artifacts;
they are still reported as pending, rather than treated as gameplay acceptance.
The full runner remains available as `scripts/run_script_tests.sh`.

Main outputs:

```text
../build/libobelisk.so
../build/_deps/subhook-build/libsubhook.so
../build/plugins/oPing/oPing.so
../build/plugins/oBaseEvents/oBaseEvents.so
../build/plugins/oProcessTimer/oProcessTimer.so
../build/plugins/oDescriptorCatalog/oDescriptorCatalog.so
```

`plugins/oPing/` is the current command/reply example and is built by default.
`OBELISK_BUILD_EXPERIMENTAL_PLUGINS` controls the additional historical examples.

## Repository layout

```text
include/obelisk/       C API headers, command data and lifecycle event contracts
plugins/oPing/        Current /ping example and experimental /whoami/lifecycle work
core/                 Plugin manager, command dispatch, configuration and cleanup
hooks/                ProcessEvent and private native chat/lifecycle adapters
loader/               LD_PRELOAD bootstrap
runtime/              Logging, binary identity and runtime services
ue/                   Private UE memory, text and class validation helpers
plugins/              Other retained reference and experimental plugins
examples/             Installed SDK package examples
tests/               Offline C++, plugin, ABI and SDK consumer checks
docs/                Current prototype notes and historical research/planning
scripts/             Installation, analysis and validation helpers
packaging/           Harness and LinuxGSM wrapper templates
```

## Runtime and plugin contract

The isolated prototype uses `LD_PRELOAD`, a binary-verified private adapter and
one plugin, `oPing.so`. The active runtime is described in
[OPING_PROTOTYPE.md](docs/OPING_PROTOTYPE.md). Runtime libraries, plugin binaries,
configuration and logs belong under an operator-chosen runtime root:

```text
<runtime-root>/lib/libobelisk.so
<runtime-root>/lib/libsubhook.so
<runtime-root>/plugins/oPing.so
<runtime-root>/config/<plugin-id>/config.json
<runtime-root>/logs/<instance-id>/
<runtime-root>/state/instances/<instance-id>/
```

Plugin code includes `<obelisk/ObeliskApi.h>` and exports
`ObeliskPlugin_GetInfo`, `ObeliskPlugin_Init` and optionally
`ObeliskPlugin_Shutdown`. Check ABI versions, `struct_size`, capabilities and
function pointers before using appended slots. Copy the borrowed API/context
information needed after initialization into plugin-owned state.

Command invocation tokens expire when their callback returns. They authorize
only the current synchronous reply on the invoking thread and for the owning
plugin. Player snapshots and lifecycle strings are callback-scoped copied
observations; copy their bytes before retaining them. They provide no
permissions, authentication, durable session handle or subsequent reply rights.
See [command data](include/obelisk/ObeliskCommandApi.h) and
[lifecycle data](include/obelisk/ObeliskPlayerLifecycleApi.h) for exact lifetimes.

Keep worker-thread timers away from UE gameplay calls. Callback registrations
and plugin-owned resources must drain before unload. The native adapter remains
installed until process exit; hot reload/removal is outside this milestone.
Historical reflection scanners and unverified layouts remain disabled on the
current server.

## Retained history and reference material

The recovered work remains useful for architecture, ABI design, packaging and
research. Earlier complete-SDK plans and promotion counters describe a broader
release goal; they are not the acceptance criteria or authorization gates for
the current operator-requested prototype. Historical `0/12` SDK progress must
not be read as zero working gameplay or as a requirement to implement twelve
modules before improving `oPing`.

- [Initial reboot review](docs/REBOOT_2026-10-13.md): recovery, first smoke tests
  and the revised goal; superseded target paths are identified there.
- [Architecture](docs/ARCHITECTURE.md), [plugin architecture](docs/PLUGIN_ARCHITECTURE.md)
  and [contributor notes](CONTRIBUTING.md): retained design and implementation context.
- [Historical stability matrix](docs/STATUS.md), [versioning](docs/VERSIONING.md),
  [complete-SDK compatibility plan](docs/SDK_V1_COMPATIBILITY.md) and
  [release policy](docs/RELEASE.md): historical broader release tracking.
- [Installation reference](docs/INSTALL.md), [operator CLI](docs/OPERATOR_CLI.md)
  and [plugin examples](plugins/README.md): existing helpers; verify their target
  assumptions before applying them to the active laboratory instance.
- [Research archive](docs/research/): retained evidence and its original scope.
- [Plugin Hub foundation](docs/PLUGIN_HUB_FOUNDATION_V1.md) and
  [capability matrix](docs/PLUGIN_HUB_CAPABILITY_MATRIX.md): future planning,
  not delivered functionality.

Use recorded client behavior for gameplay claims, focused build/tests for
implementation changes and the current prototype document for active status.


## Native module suite milestone

Six cooperative plugins are running in the laboratory: oPing, oEssentials,
oShopKits, oAdvancedChat, oWorldTools and oHomes. Thirty-two live operator requests
exercised the four new packages without changing the game process. Their command
and lifecycle fixtures pass; their visible gameplay effects need client checks.

Shop/kits currently expose catalogs with fulfillment disabled, backed by a
private transactional receipt foundation. Chat adds observed-session list,
global messages and whispers with rate limits. World tools expose current
position, native tribe ID, mounted dino IDs and aimed structure ID. Homes are
session-only points with a guarded current-player teleport binding; reconnect
or reload clears them. See [suite status](docs/SUITE_STATUS.md) for the exact
native profile, acceptance state and remaining inventory/identity work.
