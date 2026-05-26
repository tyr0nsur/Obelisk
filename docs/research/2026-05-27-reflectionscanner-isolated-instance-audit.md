# ReflectionScanner Isolated Instance Audit

## Objective

Determine, without changing server state, whether this host has an isolated/debug ARK
instance suitable for running `ReflectionScanner` without touching live Ragnarok.

## Environment

- Obelisk repo: `/home/flowcommunity-ark/Obelisk`
- Starting commit observed: `1870682`
- ARK root inspected read-only: `/servidor/ark`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`

## Method

Read-only inspection only:

- LinuxGSM instance scripts and configs under `/servidor/ark/arkserver*` and
  `/servidor/ark/lgsm/config-lgsm/arkserver/`.
- Running `ShooterGameServer` command lines and Obelisk-related environments from
  `/proc/<pid>/cmdline` and `/proc/<pid>/environ`.
- Obelisk wrapper `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh`.
- Obelisk and console logs under `/servidor/ark/obelisk/logs/`,
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/`, and
  `/servidor/ark/log/console/`.
- Marker files under `/servidor/ark/obelisk/state/`.

No servers were restarted, no marker files were changed, no variables were activated, and
no processes were killed.

## Evidence

Observed running ARK processes:

- `arkserver` / `Ragnarok`:
  - map/save: `Ragnarok?AltSaveDirectoryName=SavedRagnarok`
  - session: `[ES] FLOWCOM | Fibercraft x1000 | Ragnarok | Epic+Steam`
  - ports: game `7777`, query `27015`, RCON `27020`
  - public advertising flags: `-Crossplay -PublicIPForEpic=79.116.87.223`
  - cluster flags: `-clusterid=MiClusterArk -ClusterDirOverride=/servidor/ark/serverfiles/ShooterGame/Saved -NoTransferFromFiltering`
  - environment includes central `LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so`
    and `LD_LIBRARY_PATH=/servidor/ark/obelisk/lib:`
  - Obelisk state markers present:
    `/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok` and
    `/servidor/ark/obelisk/state/disable-plugins-ragnarok`
  - `/servidor/ark/obelisk/logs/Obelisk-Ragnarok.log` reports ProcessEvent hook
    installed, `ReflectionScanner disabled`, and plugin loading disabled.

- `arkserver2` / `TheIsland`:
  - map/save: `TheIsland?AltSaveDirectoryName=SavedTheIsland`
  - session: `[ES] FLOWCOM | Fibercraft x1000 | TheIsland | Epic+Steam`
  - ports: game `7780`, query `27016`, RCON `27021`
  - public advertising flags: `-Crossplay -PublicIPForEpic=79.116.87.223`
  - cluster flags: `-clusterid=MiClusterArk -ClusterDirOverride=/servidor/ark/serverfiles/ShooterGame/Saved -NoTransferFromFiltering`
  - observed process environment has `LD_PRELOAD=./libobelisk.so`
  - no `/servidor/ark/obelisk/state/enable-process-event-hook-theisland` or
    `/servidor/ark/obelisk/state/disable-plugins-theisland` marker was present.
  - `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/Obelisk-TheIsland.log`
    reports ProcessEvent hook disabled, `ReflectionScanner disabled`, scanning
    `ObeliskPlugins`, and loading `ChatPlugin.so`.
  - `/proc/<pid>/maps` shows the old binary-local `libobelisk.so` and
    `ObeliskPlugins/ChatPlugin.so` mapped as deleted files.

LinuxGSM config evidence:

- Only these instance config files were found:
  - `/servidor/ark/lgsm/config-lgsm/arkserver/arkserver.cfg`
  - `/servidor/ark/lgsm/config-lgsm/arkserver/arkserver2.cfg`
- `arkserver.cfg` defines live Ragnarok with FLOWCOM public session name and shared
  cluster.
- `arkserver2.cfg` defines public TheIsland with FLOWCOM public session name and the same
  shared cluster.
- No `arkserver3`, `debug`, `dev`, or `isolated` instance config was found in the
  LinuxGSM config tree.

Wrapper evidence:

- `ObeliskRun.sh` has map-specific marker handling only for `Ragnarok*` and `TheIsland*`.
- The wrapper does not translate any marker into `OBELISK_ENABLE_REFLECTION_SCANNER=1`;
  the scanner still requires an explicit environment variable at launch time.

## Result

No confirmed isolated/debug ARK instance was found.

`TheIsland` is a candidate only in the weak sense that it is not Ragnarok, but it is not a
safe ReflectionScanner target from the observed evidence: it is publicly named, crossplay
enabled, tied to the same cluster/save root, lacks the required hook/plugin-disable marker
posture, and has an existing plugin-loaded runtime state. Treat it as live/non-isolated
until an operator confirms otherwise.

## Blockers

- No dedicated debug or isolated LinuxGSM instance was present.
- No non-public session name, separate cluster id, separate save root, or local-only bind
  was observed for any instance.
- `ReflectionScanner` cannot be enabled by current marker files; it requires launch
  environment changes and therefore a controlled restart/start operation.
- TheIsland currently has evidence of old binary-local Obelisk artifacts and `ChatPlugin`
  loaded, which conflicts with the scanner runbook's plugin-disabled requirement.

## Safe Commands Proposed After Explicit Permission

These are proposed for a future authorized maintenance/debug window; do not run them as
part of this audit:

```bash
git -C /home/flowcommunity-ark/Obelisk rev-parse --short HEAD
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
pgrep -af '^./ShooterGameServer'
ls -la /servidor/ark/obelisk/state /servidor/ark/lgsm/config-lgsm/arkserver
```

If an operator designates or creates a genuinely isolated instance, start only that
instance with the runbook flags:

```bash
export OBELISK_ENABLE_REFLECTION_SCANNER=1
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
unset OBELISK_CHAT_DISCOVERY
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
export OBELISK_PE_TRACE_LIMIT=0
```

Then collect copied logs offline with:

```bash
rg "ReflectionScanner|NativeExecProbe|ChatPlugin|ProcessEvent" /path/to/isolated/Obelisk.log
rg "UObject validation|FName indirect-table probe|delayed global resolved" /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/isolated/Obelisk.log
```

## Risks

- Enabling `ReflectionScanner` on Ragnarok would violate the runbook and touch live
  Ragnarok.
- Enabling it on TheIsland without operator confirmation may still touch a live public
  cluster map.
- Leaving plugins enabled during scanner capture can mix unrelated plugin behavior into
  the evidence and violates the capture criteria.
- Changing marker files or restarting either current instance without a maintenance plan
  can affect active players.

## Next Steps

1. Ask the operator to identify whether `arkserver2` is live or non-critical; current
   read-only evidence says to treat it as live.
2. If no existing instance is isolated, plan a separate debug instance with a distinct
   session name, save directory, cluster id or no cluster, non-public/local binding where
   possible, and plugin-disabled Obelisk posture.
3. Only after that confirmation, run the existing isolated capture runbook on the debug
   instance and analyze copied logs offline.
