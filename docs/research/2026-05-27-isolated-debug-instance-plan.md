# Isolated Debug Instance Plan

## Objective

Define an operational plan for creating or designating an ARK instance where Obelisk
debug captures can run without touching live `arkserver` / Ragnarok or public
`arkserver2` / TheIsland.

This is a documentation-only plan. It does not authorize editing `/servidor/ark`,
changing marker files, restarting servers, or killing processes.

## Environment

- Obelisk repo: `/home/flowcommunity-ark/Obelisk`
- Planning commit: `aac03cb`
- ARK live root observed by prior audit: `/servidor/ark`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256 from prior audit:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Current live/non-isolated instances from prior audit:
  - `arkserver` / `Ragnarok`, ports `7777`, `27015`, `27020`
  - `arkserver2` / `TheIsland`, ports `7780`, `27016`, `27021`

## Isolation Requirements

An instance is isolated enough for `ReflectionScanner` only when all of these are true:

- It has a dedicated LinuxGSM instance name, not `arkserver` or `arkserver2`.
- It uses ports that do not overlap live game, query, or RCON ports.
- It uses a save directory that is not `SavedRagnarok` or `SavedTheIsland`.
- It is not attached to the live cluster `MiClusterArk`.
- It has a non-public debug session name and, preferably, a server password or local-only
  bind/firewall rule.
- It writes Obelisk logs to a debug-only `OBELISK_LOG_DIR`, avoiding shared
  `Obelisk.log` and map-name log collisions.
- It loads Obelisk from the central root but disables plugins during scanner captures.
- It does not rely on current map-name marker files for debug-only behavior.

The marker caveat is important: current wrapper examples key markers by map name
(`ragnarok`, `theisland`). A second instance on the same map can inherit the same marker
posture and can also write the same `Obelisk-<Map>.log` unless `OBELISK_LOG_DIR` is
separated.

## Options

### Option A: New LinuxGSM Instance Sharing Existing Serverfiles

Create a third LinuxGSM instance, for example `arkserver-obelisk-debug`, that uses the
existing ARK install but has its own instance config, ports, save directory, session name,
RCON password, Obelisk log directory, and launcher wrapper.

Pros:

- Fastest clean path that does not repurpose live TheIsland.
- Avoids changing live instance configs and state markers.
- Uses the same ARK binary as live, so scanner evidence is relevant to the current binary.
- Keeps rollback simple: stop or disable only the debug instance.

Cons:

- Still shares the same serverfiles tree, so ARK updates/mod changes affect all instances.
- Requires operator permission to create LGSM files and start one new process.
- Needs port/firewall confirmation before first start.

Recommendation: use this option first.

### Option B: Fully Separate ARK Root

Install a separate debug ARK root, for example under `/servidor/ark-debug`, with its own
LinuxGSM install, serverfiles, saves, cluster directory, Obelisk wrapper, logs, and state.

Pros:

- Strongest isolation from live scripts, serverfiles, saves, updates, and logs.
- Allows destructive debug iteration without sharing the live tree.

Cons:

- Requires more disk, install time, and update management.
- The binary may drift from live unless the operator pins or verifies it before captures.
- More setup work before it can answer the current `ReflectionScanner` question.

Use this if Option A is rejected because sharing serverfiles is not acceptable.

### Option C: Repurpose `arkserver2` Only After Explicit Operator Confirmation

Stop treating `arkserver2` as live only if an operator confirms it is non-critical,
unadvertises it, detaches it from the live cluster, assigns separate saves/ports/logs, and
removes old binary-local Obelisk artifacts from its runtime path during a maintenance
window.

Pros:

- Least new LGSM scaffolding.
- Already has an instance slot and known ports.

Cons:

- Current evidence says it is public, named as FLOWCOM live, clustered with live saves, and
  has loaded old experimental plugin artifacts.
- It is unsafe as-is for scanner capture.
- Converting it risks touching a real player-facing map.

Use this only with explicit written operator confirmation that TheIsland is not live.

## Recommended Instance Shape

Suggested names and ports for Option A:

```text
LinuxGSM instance: arkserver-obelisk-debug
Map: TheIsland or another lightweight installed map, but not sharing live saves
Session name: [DEBUG] Obelisk isolated - do not join
AltSaveDirectoryName: SavedObeliskDebug
Game port: 7790
ARK peer/raw port expectation: reserve 7791 as adjacent game traffic
Query port: 27025
RCON port: 27030
RCON: enabled only with a debug-only password
Cluster: disabled preferred; if required, use clusterid=ObeliskDebugCluster
ClusterDirOverride: /servidor/ark/serverfiles/ShooterGame/SavedObeliskDebugCluster
Obelisk log dir: /servidor/ark/obelisk/logs/isolated-debug
Plugins: disabled
Native exec probes: unset
Chat discovery: unset
```

Cluster preference:

- Preferred: omit `-clusterid`, `-ClusterDirOverride`, and transfer flags entirely.
- Acceptable fallback: use `-clusterid=ObeliskDebugCluster` and a dedicated
  `ClusterDirOverride` outside the live cluster directory.
- Rejected: using `MiClusterArk`, `/servidor/ark/serverfiles/ShooterGame/Saved` as the
  live cluster root, or `-NoTransferFromFiltering` from the public cluster config.

## LinuxGSM Files To Create Or Copy

These are future authorized changes, not actions taken by this plan.

```text
/servidor/ark/arkserver
  copy to:
/servidor/ark/arkserver-obelisk-debug

/servidor/ark/lgsm/config-lgsm/arkserver/arkserver2.cfg
  copy or use as reference for:
/servidor/ark/lgsm/config-lgsm/arkserver/arkserver-obelisk-debug.cfg

/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
  copy or use as reference for:
/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRunDebug.sh
```

The debug wrapper should not depend on shared map markers for scanner behavior. It should
export the debug environment explicitly, then execute `ShooterGameServer`.

Candidate wrapper environment:

```bash
export OBELISK_ROOT="/servidor/ark/obelisk"
export OBELISK_PLUGIN_DIR="${OBELISK_ROOT}/plugins"
export OBELISK_CONFIG_DIR="${OBELISK_ROOT}/config"
export OBELISK_LOG_DIR="${OBELISK_ROOT}/logs/isolated-debug"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so"

export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_PE_TRACE_LIMIT=0

unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

# Set this only for the scanner capture start, not for normal debug idle.
export OBELISK_ENABLE_REFLECTION_SCANNER=1

exec ./ShooterGameServer "$@"
```

The LinuxGSM config should point only the debug instance at this wrapper:

```ini
executable="./ObeliskRunDebug.sh"
```

Do not change `arkserver.cfg`, `arkserver2.cfg`, or the production `ObeliskRun.sh` for the
first debug instance unless the operator explicitly chooses a shared-wrapper design.

## Safe Launch Arguments

The exact LinuxGSM variable names should be copied from the existing instance config, but
the resulting ARK command line should have this shape:

```text
TheIsland?listen?SessionName=[DEBUG] Obelisk isolated - do not join?AltSaveDirectoryName=SavedObeliskDebug?ServerPassword=<debug-password>?ServerAdminPassword=<debug-admin-password>?RCONEnabled=True?RCONPort=27030?Port=7790?QueryPort=27025
```

Required removals from the live configs:

- Remove public FLOWCOM session names.
- Remove `-Crossplay` unless the operator explicitly needs remote Epic/Steam joining.
- Remove `-PublicIPForEpic=79.116.87.223`.
- Remove live cluster flags.
- Remove `-NoTransferFromFiltering`.

If local-only binding is known to work in this LinuxGSM/ARK setup, prefer a local bind or
firewall rule before the first scanner run. If local bind is uncertain, use a server
password and keep the debug session name visibly non-public until firewall policy is
confirmed.

## Obelisk Capture Variables

For a `ReflectionScanner` capture on the debug instance:

```bash
export OBELISK_ENABLE_REFLECTION_SCANNER=1
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
export OBELISK_PE_TRACE_LIMIT=0
```

Base runtime variables:

```bash
export OBELISK_ROOT=/servidor/ark/obelisk
export OBELISK_PLUGIN_DIR=/servidor/ark/obelisk/plugins
export OBELISK_CONFIG_DIR=/servidor/ark/obelisk/config
export OBELISK_LOG_DIR=/servidor/ark/obelisk/logs/isolated-debug
export LD_LIBRARY_PATH=/servidor/ark/obelisk/lib:${LD_LIBRARY_PATH}
export LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so
```

`OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` is forbidden for this plan. Raw event discovery must
remain disabled for the scanner capture.

## Permission Checklist

Before any filesystem or server action, get explicit operator approval for each checked
item:

- [ ] Create `/servidor/ark/arkserver-obelisk-debug`.
- [ ] Create
  `/servidor/ark/lgsm/config-lgsm/arkserver/arkserver-obelisk-debug.cfg`.
- [ ] Create
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRunDebug.sh`.
- [ ] Reserve ports `7790`, `7791`, `27025`, and `27030`, or provide replacements.
- [ ] Confirm whether the debug instance may advertise publicly. Default answer should be
  no.
- [ ] Confirm whether local bind/firewall isolation is available.
- [ ] Confirm the debug session password and RCON/admin password handling.
- [ ] Confirm no live cluster flags will be used.
- [ ] Confirm the first start/restart window for only `arkserver-obelisk-debug`.
- [ ] Confirm where copied logs should be stored for offline analysis.

Pre-start checks after permission:

```bash
git -C /home/flowcommunity-ark/Obelisk rev-parse --short HEAD
git -C /home/flowcommunity-ark/Obelisk status --short
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
pgrep -af '^./ShooterGameServer'
ss -lunpt | rg '(:7790|:7791|:27025|:27030)\b'
```

Start only the debug instance:

```bash
cd /servidor/ark
./arkserver-obelisk-debug start
```

Do not run `restart` against `arkserver` or `arkserver2`.

## Validation After Debug Start

Expected Obelisk log path:

```text
/servidor/ark/obelisk/logs/isolated-debug/Obelisk.log
/servidor/ark/obelisk/logs/isolated-debug/Obelisk-TheIsland.log
```

The map-specific filename may still be `Obelisk-TheIsland.log`; isolation comes from the
debug-only `OBELISK_LOG_DIR`.

Expected log posture:

```text
Obelisk Runtime Loaded Native (LD_PRELOAD)
ProcessEvent absolute x64 hook installed successfully
Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1
[ReflectionScanner] Scanning ...
```

Reject the run if copied logs contain:

```text
[NativeExecProbe] installed
legacy plugin markers
```

Analyze only copied logs with the existing runbook commands:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/copied/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/copied/Obelisk.log
```

## Rollback

Rollback should affect only `arkserver-obelisk-debug`.

Immediate rollback:

```bash
cd /servidor/ark
./arkserver-obelisk-debug stop
```

Disable scanner but keep the debug instance available:

```bash
# In ObeliskRunDebug.sh or the debug-only LGSM env:
unset OBELISK_ENABLE_REFLECTION_SCANNER
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_PE_TRACE_LIMIT=0
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

cd /servidor/ark
./arkserver-obelisk-debug restart
```

Full cleanup after logs are copied and reviewed:

```text
Remove or archive:
- /servidor/ark/arkserver-obelisk-debug
- /servidor/ark/lgsm/config-lgsm/arkserver/arkserver-obelisk-debug.cfg
- /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRunDebug.sh
- /servidor/ark/obelisk/logs/isolated-debug/ only after log evidence is preserved
```

Do not remove or change live markers:

```text
/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
/servidor/ark/obelisk/state/disable-plugins-ragnarok
```

Post-rollback sanity checks:

```bash
pgrep -af '^./ShooterGameServer'
ss -lunpt | rg '(:7790|:7791|:27025|:27030)\b'
tail -n 80 /servidor/ark/obelisk/logs/Obelisk-Ragnarok.log
```

The live Ragnarok log should not show scanner activation, native exec probes, or plugin
loading changes from the debug run.

## Risks

- Sharing serverfiles means a debug process can still consume CPU/RAM/IO on the live host.
- If ports are already in use or firewall rules publish them, the debug server may become
  joinable.
- If `OBELISK_LOG_DIR` is not separated, debug logs can mix with live map logs.
- If map-name markers are reused, a debug map can inherit live map behavior or change live
  behavior later.
- If cluster flags are copied from live, the debug instance can touch transfer data or
  player expectations.
- If `arkserver2` is repurposed without explicit confirmation, the plan may disrupt a real
  public TheIsland instance.

## Result

No server changes were made. The recommended path is a new LinuxGSM instance named
`arkserver-obelisk-debug`, using isolated ports, saves, log directory, and wrapper-level
Obelisk environment variables instead of shared production markers.

## Next Steps

1. Ask the operator to approve Option A or choose Option B/C explicitly.
2. If Option A is approved, request permission for the specific file creations and port
   reservation listed in the checklist.
3. After the debug instance exists, run the existing isolated capture runbook only against
