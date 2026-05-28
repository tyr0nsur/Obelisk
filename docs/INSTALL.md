# Installation

This guide describes the centralized LinuxGSM layout used by Obelisk.

## Build

```bash
cd /home/flowcommunity-ark/Obelisk
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

## Install Layout

Recommended root:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  config/<plugin-id>/<plugin-config-file>
  logs/<instance-id>/
  state/instances/<instance-id>/
```

Install the runtime:

```bash
./scripts/install_obelisk.sh --backup-existing /servidor/ark/obelisk
```

The install root must be supplied explicitly as a positional argument; the installer does
not default to the live root and does not use inherited `OBELISK_ROOT` when omitted. The
root must be a non-root absolute path and must not be a symlink. Managed subdirectories
must also be real directories, not symlinks: `lib`, `plugins`, `include`, `config`, `logs`,
`state`, and `state/instances`. The installer rejects empty, relative, `/`, symlink roots,
and symlinked managed paths before creating directories or publishing artifacts.

The script copies:

```text
build/libobelisk.so                         -> lib/libobelisk.so
build/_deps/subhook-build/libsubhook.so     -> lib/libsubhook.so
include/obelisk/*.h                         -> include/obelisk/
build/ObeliskConfig*.cmake                  -> lib/cmake/Obelisk/
```

It also creates `plugins`, `config`, `logs`, and `state/instances`.
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
same backup timestamp, then restart only the approved target instance and re-run the stable
posture check.

External plugins can consume the installed SDK through the exported CMake package:

```cmake
find_package(Obelisk CONFIG REQUIRED)
target_link_libraries(MyPlugin PRIVATE Obelisk::obelisk_sdk)
```

Plugins loaded from `plugins/` are expected to own their config defaults. The preferred
directory for plugin config is:

```text
/servidor/ark/obelisk/config/<plugin-id>/
```

The runtime loads every `.so` directly inside `/servidor/ark/obelisk/plugins/` on restart.
If a plugin should not load, do not place it in `plugins/`.
Install plugin `.so` files with `scripts/install_obelisk_plugin.sh <PluginName.so>
/servidor/ark/obelisk`; it stages the copy under a non-`.so` name and publishes it with an
atomic rename inside the shared plugin directory. The plugin installer also rejects a
missing positional root, ignores inherited `OBELISK_ROOT` as an install target, and rejects
a symlinked `plugins` directory. Do not copy plugins directly into the active directory
while ARK instances may restart.

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
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Then configure LinuxGSM:

```ini
executable="./ObeliskRun.sh"
```

Current instance posture is tracked in `docs/agent-handoff/CURRENT.md`. Do not restart,
change markers, or run Obelisk tests on shared or player-facing instances without explicit
operator approval for the target, rollback plan, and shutdown expectations.

## Instance Identity

`OBELISK_INSTANCE_ID` identifies the LinuxGSM instance, not the ARK map. The production
wrapper sets known defaults:

```text
Ragnarok  -> arkserver
TheIsland -> arkserver2
Debug     -> arkserver-obelisk-debug
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
symlinked or non-regular config files.

## Feature Flags

Instance marker files are preferred for production operations:

```bash
# Approved debug window only. Do not run from an ordinary install or agent round.
# mkdir -p /servidor/ark/obelisk/state/instances/<approved-instance-id>
# touch /servidor/ark/obelisk/state/instances/<approved-instance-id>/<approved-marker>
```

Do not create, remove, or refresh `arkserver` / Ragnarok markers from install or debug
rounds. Treat the Ragnarok marker list as observed baseline unless the operator opens a
Ragnarok maintenance window in the current turn. Experimental module markers, scanners,
ptrace/gcore, broad tracing, and restarts require explicit run-window approval.

Useful flags:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
state/instances/<instance-id>/allow-experimental-observers  # required with observer markers below
state/instances/<instance-id>/enable-chat-reflection  # experimental
state/instances/<instance-id>/enable-inventory-reflection  # experimental, metadata-only
state/instances/<instance-id>/enable-structure-reflection  # experimental, metadata-only
```

Experimental observer markers do nothing unless `allow-experimental-observers` is also
present for the same instance. Use that marker only inside an approved debug window and
remove it before returning the instance to stable posture.

`enable-chat-reflection` makes the wrapper set:

```text
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_CHAT_REFLECTION_LOG_LIMIT=0
```

The chat log limit is also the observation budget and defaults to `0`, matching the other
experimental observers. A short debug window must set an explicit non-zero budget before
chat reflection reads or logs fields.

`enable-structure-reflection` makes the wrapper set:

```text
OBELISK_ENABLE_STRUCTURE_REFLECTION=1
OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0
```

The structure log limit is also the observation budget and defaults to `0`, so the marker
alone does not read reflected structure fields. A short debug window must set an explicit
non-zero budget, and stable posture checks reject these variables.

`enable-inventory-reflection` follows the same policy:

```text
OBELISK_ENABLE_INVENTORY_REFLECTION=1
OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0
```

Inventory reflection is internal metadata observation only. It must not expose item ids,
contents, player identity, or gameplay-authoritative overrides.

Decoded chat text logging is not enabled by the marker. It requires an additional explicit
environment gate:

```text
OBELISK_CHAT_REFLECTION_LOG_TEXT=1
```

Rollback is removing the marker and restarting the instance. The stable production posture
is still process-event hook enabled, plugins disabled for debug, and chat reflection off
unless a development validation run explicitly needs it.

Map markers such as `enable-process-event-hook-ragnarok` are obsolete and are not read by
the release wrapper.

## Logs

Runtime logs are written to:

```text
/servidor/ark/obelisk/logs/arkserver/Obelisk.log
/servidor/ark/obelisk/logs/arkserver/Obelisk-Ragnarok.log
/servidor/ark/obelisk/logs/arkserver2/Obelisk.log
/servidor/ark/obelisk/logs/arkserver2/Obelisk-TheIsland.log
/servidor/ark/obelisk/logs/isolated-debug/
```

The LinuxGSM wrapper sets `OBELISK_INSTANCE_ID`. Custom launchers should set it explicitly
before loading Obelisk and keep it to the safe token form described above.

## Current Safe Production Posture

For live servers, the safest known posture is:

```text
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/disable-plugins
```

This validates the core ProcessEvent hook without loading experimental plugins.

Use `arkserver2` / TheIsland for debug/development markers and validation windows only
after explicit operator approval. It starts from powered off and must be stopped again
after the scoped test. Keep `arkserver` / Ragnarok protected while users are active.
