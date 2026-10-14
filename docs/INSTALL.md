# Installation

This guide describes the centralized LinuxGSM layout used by Obelisk.

## Build

```bash
cd <repo-root>
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

## Install Layout

Recommended root:

```text
<obelisk-root>/
  lib/
  include/obelisk/
  lib/cmake/Obelisk/
  plugins/
  config/<plugin-id>/<plugin-config-file>
  logs/<instance-id>/
  state/instances/<instance-id>/
```

Install the runtime and SDK package:

```bash
./scripts/install_obelisk.sh --backup-existing <obelisk-root>
```

A successful installer exit means the expected runtime files, public header, CMake package
files, and managed directories were published into the chosen central root. It is still
package-shape evidence only: no runtime readiness, live-ops approval, stable release, SDK
v1 completion, Plugin Hub readiness/publication, public module coverage, or support-tier
activation follows from that install. Current package/install accounting remains SDK
`0/12`, P0 `0/4`, stable `false`.
This install guide also grants no live/server access: the latest release-readiness pass,
release-readiness passes, `progress_normalization_trace`, source_overclaim diagnostics,
`source_overclaim_total_flag_count=0`, beta notice drafts/actions, beta notices, passive
waits/summaries/snapshots/triplets, the latest validation pass, six-agent closure notes,
`.codex` cleanup, passive monitor ticks, passive monitor output,
passive monitors, public reachability, Plugin Hub planning, historical
TheIsland/Ragnarok/Genesis2 names, historical live approvals/map names, historical
approvals/map names, prior approvals, package-shape installs, package installs,
explicit-version non-`EXACT`
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
package-shape install success, and side-lane accounting are
chronology only unless the exact current-turn approval and accepted checker evidence are
named. They do not move SDK/P0 progress. They are not runtime evidence/readiness,
live-op authorization, Discord authorization, not Plugin Hub readiness, not stable SDK
readiness, not stable SDK claims, not package-shape/public package readiness, and not
support-tier activation.

The install root must be supplied explicitly as a positional argument; the installer does
not default to the live root and does not use inherited `OBELISK_ROOT` when omitted. The
root must be a non-root absolute path and must not be a symlink. Managed subdirectories
must also be real directories, not symlinks: `lib`, `plugins`, `include`,
`include/obelisk`, `lib/cmake`, `lib/cmake/Obelisk`, `config`, `logs`, `state`, and
`state/instances`. The installer rejects empty, relative, `/`, symlink roots, existing
non-directory roots, existing non-directory managed paths, symlinked managed paths, and
existing symlink/non-regular managed runtime or SDK artifact destinations before creating
directories or publishing artifacts. The chosen root path must also not traverse symlink
path components.

The script copies:

```text
build/libobelisk.so                         -> lib/libobelisk.so
build/_deps/subhook-build/libsubhook.so     -> lib/libsubhook.so
include/obelisk/ObeliskApi.h                -> include/obelisk/ObeliskApi.h
build/ObeliskConfig.cmake                   -> lib/cmake/Obelisk/ObeliskConfig.cmake
build/ObeliskConfigVersion.cmake            -> lib/cmake/Obelisk/ObeliskConfigVersion.cmake
build-generated ObeliskTargets.cmake        -> lib/cmake/Obelisk/ObeliskTargets.cmake
```

It also creates the managed directories shown in the layout above.
Runtime libraries and SDK files are staged before publication. `libobelisk.so` is produced
through the CMake `Runtime` component in a temporary install root, then both
`libsubhook.so` and `libobelisk.so` are installed under temporary `.incoming.<pid>` names
and atomically renamed to their final paths. The SDK component is installed into a separate
temporary root first; only the expected public header and CMake package files are then
published into the live install root with rollback snapshots.

With `--backup-existing`, matching timestamped backups are created for both runtime
libraries before replacement. If runtime or SDK publication fails, temporary
`.incoming.<pid>` files plus temporary runtime/SDK install roots are removed by the
installer cleanup trap, and any already-published runtime or SDK files are restored.

Rollback should restore `libobelisk.so` and `libsubhook.so` as a compatible pair from the
same backup timestamp, then restart only the explicitly approved target instance and rerun
the stable posture check.

Release-readiness and install-layout validation are offline checks. Do not point
`OBELISK_BUILD_DIR`, second-source roots, second-source report directories, or release
statement inputs under a live-server root, including that root's offline workspace; the
release, RC-smoke, and install-layout checks reject both textual protected paths and paths
that resolve there through symlinks. Release-readiness second-source report directories
must also be new or empty and must not traverse symlink path components, so ignored
artifact roots cannot carry stale generated reports into a fresh gate run.

External plugin builds can consume the installed SDK package-shape through the exported
CMake package:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
target_link_libraries(MyPlugin PRIVATE Obelisk::obelisk_sdk)
```

The numeric package version is the SDK compatibility floor for the current pre-release
line, not a claim that a stable `v0.1.0` tag exists. Exact stable-looking CMake version
requests such as `find_package(Obelisk 0.1.0 EXACT CONFIG ...)` are rejected until a
stable SDK claim is explicitly authorized. The installed package also exposes
`Obelisk_*ABI_VERSION` CMake variables that mirror the `OBELISK_*ABI_VERSION` macros in
`ObeliskApi.h`; plugin source should continue to check the header macros and runtime
`struct_size`/capability fields before using appended ABI slots.
The explicit non-`EXACT` numeric version plus `COMPONENTS SDK` request is package-shape
evidence only. It does not imply stable SDK readiness, Plugin Hub readiness/publication,
public package readiness, runtime readiness, support-tier activation, or v1 completion.
`Obelisk::obelisk_sdk` is a public-header C ABI target only. It does not grant access to
implementation headers, private runtime symbols, `libobelisk.so` as a plugin link
dependency, public module SDK coverage, or support-tier activation.
Finding or linking this target is a build/package boundary check only; do not describe it
as runtime readiness, public SDK completion, stable release evidence, or Plugin Hub
readiness.
It also exports non-claim package metadata:
`Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS=package-shape-evidence-only`,
`Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED=FALSE`,
`Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED=FALSE`,
`Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED=FALSE`,
`Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED=FALSE`,
`Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED=FALSE`,
`Obelisk_V1_COMPLETION_CLAIM_ALLOWED=FALSE`,
`Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED=FALSE`, and
`Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED=FALSE`.
These package-shape markers do not resolve route completion for the current complete SDK
track: SDK blocker promotion remains `0/12`, the P0 dependency chain remains `0/4`,
`stable_claim_allowed=false`, and the active route blocker is
`approved_runtime_evidence_missing`; in short, SDK `0/12`, P0 `0/4`, stable `false`.

Plugins loaded from `plugins/` are expected to own their config defaults. The preferred
directory for plugin config is:

```text
<obelisk-root>/config/<plugin-id>/
```

The runtime loads every `.so` directly inside `<obelisk-root>/plugins/` on restart.
If a plugin should not load, do not place it in `plugins/`.
Install plugin `.so` files with `scripts/install_obelisk_plugin.sh <PluginName.so>
<obelisk-root>`; it stages the copy under a non-`.so` name and publishes it with an
atomic rename inside the shared plugin directory. The plugin installer also rejects a
missing positional root, ignores inherited `OBELISK_ROOT` as an install target, and rejects
a symlinked `plugins` directory. Do not copy plugins directly into the active directory
while ARK instances may restart.

Plugin Hub seed work is parked until the complete SDK blocker chain is resolved.
The plugin installer only publishes an already-built `.so`; it does not validate Plugin Hub
scope, ArkApi compatibility, public SDK promotion, or release readiness. If archived
Plugin Hub planning is explicitly requested, read the parked Plugin Hub docs as boundaries
only: `docs/PLUGIN_HUB_FOUNDATION_V1.md` and
`docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`; keep support-tier classification separate from
installation, keep ArkServerApi/AseApi/NextGen inputs as names and demand signals only,
and run the plugin installer with `--dry-run` as an offline/package-shape check before any
current-turn approved copy into a shared `plugins/` root. A dry-run, package-shape install,
or copied `.so` remains non-authorizing/non-evidence and does not create Plugin Hub
readiness/publication, public SDK promotion, support-tier activation, release readiness, or
runtime readiness.

Useful installer flags:

```text
--dry-run
--backup-existing
```

## LinuxGSM Wrapper

Versioned wrapper templates live in:

```text
packaging/linuxgsm/ObeliskRun.sh
packaging/linuxgsm/ObeliskRunDebug.sh
packaging/linuxgsm/arkserver-obelisk-debug.cfg.example
```

Place the production wrapper in:

```text
ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Before any maintenance restart, verify that the installed wrapper still matches the
versioned template:

```bash
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed <ark-root>/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Then configure LinuxGSM:

```ini
executable="./ObeliskRun.sh"
```

Do not restart, change markers, run runtime observations, or run Obelisk tests on shared
or player-facing instances without explicit operational approval for the exact target,
marker/env delta, restart expectation, rollback plan, evidence capture, notice path when
applicable, and shutdown expectations. Keep current instance posture and notification
routing in operator-owned deployment notes outside the public SDK docs.

## Instance Identity

`OBELISK_INSTANCE_ID` identifies the LinuxGSM instance, not the ARK map. Configure stable
instance identifiers per server process and keep current map-to-instance routing in
operator-owned deployment notes:

```text
<map-or-role> -> <instance-id>
<map-or-role> -> <instance-id>
<debug-role>  -> <debug-instance-id>
```

Operators can override it before launching the wrapper.

## Multi-Server And Cluster Layout

Obelisk is designed to support multiple ARK server processes sharing one central Obelisk
root, including clustered map setups. The stable layout is:

```text
${OBELISK_ROOT}/lib/                         shared runtime libraries
${OBELISK_ROOT}/plugins/                     shared plugin binaries
${OBELISK_ROOT}/config/<plugin-id>/          shared plugin configuration
${OBELISK_ROOT}/logs/<instance-id>/          per-server logs
${OBELISK_ROOT}/state/instances/<id>/        per-server markers and runtime state
```

Each ARK server process must have a unique `OBELISK_INSTANCE_ID`, even when several maps
share the same ARK cluster id, save cluster directory, plugin binaries, and Obelisk config.
The id must be non-empty and use only letters, digits, `_`, or `-`; plugin loading fails
closed when the id is missing or unsafe.
Use `instance_allowlist` in plugin config to select which maps/servers may activate a
plugin from the shared config. An enabled plugin with a missing or empty
`instance_allowlist` does not activate by default; set `allow_all_instances=true` only when
the plugin is intentionally safe to run on every process sharing that config.

Shared config is intentional; shared mutable plugin state is not the default. Plugins that
write runtime state should write under an instance-scoped path, or document and implement
their own locking/atomic-write strategy before using a shared state file across multiple
server processes.
Plugin config directories and `config.json` files must be regular filesystem entries under
`${OBELISK_ROOT}/config`; the runtime rejects symlinked plugin config directories and
symlinked or non-regular config files. `OBELISK_CONFIG_DIR` itself must be an absolute,
non-symlink directory when it exists; missing absolute roots may be created for safe
default configs, but relative or symlinked config roots fail closed before plugin
discovery.

## Feature Flags

For operator-approved operations, wrappers consume instance marker files:

```bash
# Current-turn approved exact debug window only. Do not run from an ordinary install or
# debug run.
# mkdir -p <obelisk-root>/state/instances/<current-turn-approved-instance-id>
# touch <obelisk-root>/state/instances/<current-turn-approved-instance-id>/<current-turn-approved-marker>
```

Do not create, remove, or refresh markers on shared or player-facing instances from
ordinary install or debug rounds. Treat the live marker list as observed baseline unless
the operator opens an explicit maintenance window for that instance in the current turn.
Experimental module markers, scanners, ReflectionScanner, ptrace/gcore, broad tracing,
runtime observation, player-facing notices, and restarts require explicit current-turn
operator approval for the exact scoped run.

Useful flags:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins  # wrapper input
state/instances/<instance-id>/allow-experimental-observers  # required with observer markers below
state/instances/<instance-id>/enable-chat-events  # experimental ChatMessageEvent producer
state/instances/<instance-id>/enable-chat-reflection  # experimental
state/instances/<instance-id>/enable-inventory-reflection  # experimental, metadata-only
state/instances/<instance-id>/enable-structure-reflection  # experimental, metadata-only
state/instances/<instance-id>/enable-item-return-events  # experimental, copied ReturnValue-only
state/instances/<instance-id>/enable-player-principal-lifecycle-observer  # experimental, exact lifecycle observer
```

`disable-plugins` is a supported LinuxGSM wrapper marker, not an independent runtime
gate. The wrapper translates it into `OBELISK_DISABLE_PLUGINS=1`; custom launchers must
set that environment variable themselves when plugin loading should be disabled.

The normal LinuxGSM wrapper is protected by default. If any experimental observer marker,
runtime debug/scanner marker, callback escape marker, active debug request marker, or
observer/debug environment is present for the selected instance, stable profile launch
fails closed. A current-turn approved observer window must use
`OBELISK_WRAPPER_PROFILE=observer-debug` and the same instance must have
`allow-observer-debug-window`; do not persist that profile in the service environment.
When `OBELISK_INSTANCE_ID` is set, the wrapper requires the safe token form
`[A-Za-z0-9_-]+`; if `state/instances/<instance-id>` already exists, it must be a real
non-symlink directory so marker checks cannot escape through path traversal or symlinks.
The wrapper also refuses an `observer-debug` profile that has only the approval marker and
no scoped observer/debug marker. Experimental observer markers still do nothing unless
`allow-experimental-observers` is also present for the same instance. Use those markers
only inside a current-turn approved exact debug window and remove them before returning
the instance to stable posture.

The player-principal lifecycle observer is exact for first evidence windows:

```text
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=<supported ARK SHA256>
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
```

It also requires `enable-process-event-hook`, `disable-plugins`,
`allow-observer-debug-window`, `allow-experimental-observers`, and
`enable-player-principal-lifecycle-observer` as regular non-symlink markers on the same
instance. Other observer/debug markers are incompatible with that lifecycle window.

The player-principal lifecycle diagnostic candidate gate is not an install, package-shape,
or SDK-readiness signal. `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1`
may be used only inside a current-turn approved exact observer-debug diagnostic window
that also enables the player-principal lifecycle observer gate. Diagnostic output is
candidate-only FName target evidence; it must not read params, log identity, dispatch
callbacks, satisfy approved runtime evidence, or promote runtime/public SDK readiness.

`enable-chat-events` makes the wrapper set the minimal copied `ChatMessageEvent`
producer:

```text
OBELISK_ENABLE_CHAT_EVENTS=1
OBELISK_CHAT_EVENTS_BINARY_SHA256=<supported ARK SHA256>
OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=<positive dispatch budget>
```

This is the marker/env path for the copied `ChatMessageEvent` producer. Copied
plugin-facing delivery for all four known chat send modes has accepted copied-log
validation; use this path only for current-turn approved exact regression/beta windows,
after a current-turn operator-approved notice, with a short observer-debug window and
explicit rollback.
Do not use `enable-chat-reflection` as delivery evidence.

`enable-chat-reflection` makes the wrapper set the historical chat observer:

```text
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_CHAT_REFLECTION_LOG_LIMIT=0
```

The chat log limit is also the observation budget and defaults to `0`, matching the other
experimental observers. A current-turn approved short debug window must set an explicit
non-zero budget before chat reflection reads or logs fields.

`enable-structure-reflection` makes the wrapper set:

```text
OBELISK_ENABLE_STRUCTURE_REFLECTION=1
OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0
OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=0
```

Structure log and internal-dispatch budgets are separate and both default to `0`, so the
marker alone does not read reflected structure fields or dispatch copied internal events.
A current-turn approved short debug window must set an explicit non-zero budget for the
intended path, and stable posture checks reject these variables.

`enable-inventory-reflection` follows the same policy:

```text
OBELISK_ENABLE_INVENTORY_REFLECTION=1
OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0
OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=0
```

Inventory log and inventory-backed `GameplayPolicyEvent` dispatch budgets are separate and
both default to `0`, so the marker alone does not read reflected inventory fields or
dispatch copied internal events. A current-turn approved short debug or beta window must
set an explicit non-zero budget for the intended path.

Inventory reflection may feed copied, redacted inventory-backed `GameplayPolicyEvent`
signals when dispatch is explicitly budgeted and subscribed. It must not expose item ids,
contents, player identity, gameplay-authoritative overrides, a public Inventory or Items
SDK, `ResourceHandle`, lookup, mutation, raw UE pointers/params, or return override.

`enable-item-return-events` follows the stricter copied event policy for the three
promoted item return-only `GameplayPolicyEvent` kinds:

```text
OBELISK_ENABLE_ITEM_RETURN_EVENTS=1
OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=<supported ARK SHA256>
OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=<positive dispatch budget>
OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT=0
```

The marker is accepted only in an approved `observer-debug` window with
`allow-observer-debug-window` and `allow-experimental-observers`. Dispatch budget must be
explicitly positive; log budget defaults to `0`. The producer copies only `ReturnValue`
for `AllowEquipItem`, `CanRepair`, and `UseItemOntoItem`. It must not expose item ids,
inventory identity, player identity, lookup, mutation, raw UE pointers/params, or return
override. Stable posture checks reject this marker and all `OBELISK_ITEM_RETURN_EVENTS_*`
variables.

Decoded chat text logging is not enabled by the marker. It requires an additional explicit
environment gate:

```text
OBELISK_CHAT_REFLECTION_LOG_TEXT=1
```

Rollback is removing the observer/debug-window markers and restarting the instance only
when those actions are named by the current-turn approval. The stable production posture is
still process-event hook enabled, plugin loading disabled through
`OBELISK_DISABLE_PLUGINS=1`, and all experimental observers off.

Map markers such as `enable-process-event-hook-ragnarok` are obsolete and are not read by
the release wrapper.

## Logs

Runtime logs are written to:

```text
<obelisk-root>/logs/<instance-id>/Obelisk.log
<obelisk-root>/logs/<instance-id>/Obelisk-<map>.log
<obelisk-root>/logs/isolated-debug/
```

The LinuxGSM wrapper sets `OBELISK_INSTANCE_ID`. Custom launchers should set it explicitly
before loading Obelisk and keep it to the safe token form described above. Explicit
`OBELISK_LOG_DIR` values must be absolute, non-symlink directories; when logs are derived
from `OBELISK_ROOT`, both `${OBELISK_ROOT}` and `${OBELISK_ROOT}/logs` must be
non-symlink directories. Per-instance log directories are also rejected when symlinked, so
log writes cannot escape the central root through an inherited environment.

## Stable Validation Posture

For a live or live-like validation instance, the stable posture is:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
```

This validates the core ProcessEvent hook without loading experimental plugins when the
supported LinuxGSM wrapper is used. The runtime itself disables plugin loading only when
`OBELISK_DISABLE_PLUGINS=1` is present; the `disable-plugins` marker is the wrapper input
that sets that environment variable.

Keep current instance names, maps, validation windows, deployment communication, and
debug-instance startup/shutdown rules in operator-owned deployment notes, not in public
SDK install docs. For any approved exact server-side feature window, use the approved
operator notice path when applicable, enable only the required markers, avoid raw player
text or identity logging, preserve copied logs, and remove experimental markers before
returning to stable posture.

Stable production posture also requires a non-symlink Obelisk root and managed
subdirectories, a non-symlink runtime library, and no forbidden experimental marker
entries for the instance, including observer, scanner, debug-control, native-exec,
ptrace, global callback, or public `CallProcessEvent` markers. Offline posture checks
must use `--proc-root` fixtures whose root, `environ`, and `maps` files do not resolve
into live `/proc`; pass `--pid` for fixture checks so process discovery does not call
`pgrep` against live `/proc`. Fixture roots under a live-server root are rejected even when
`--allow-protected-root` is supplied; use a copied fixture under `/tmp` or another
approved offline artifact workspace instead. Reading live `/proc` or validating a
protected ARK server root also requires separate current-turn approval; the explicit
flags below acknowledge that scope but do not grant it. Prove the running process with:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --allow-live-procfs-read --allow-protected-root \
  --map <map> --instance <instance-id>
```

During a current-turn approved passive observer-debug wait, do not treat a stable-posture
failure as a stopped server. Do not chain LinuxGSM `monitor`, `start`, `stop`, or
`restart` calls just because the expected player-dependent signal has not arrived yet.
Wait with read-only player-presence checks or copied log tails inside the approved window,
and prove that live posture separately with:

```bash
scripts/check_obelisk_server_posture.sh --expect-observer-debug \
  --allow-live-procfs-read --allow-protected-root \
  --map <map> --instance <instance-id>
```

Return to the `--expect-stable` check after the observer window is rolled back.
