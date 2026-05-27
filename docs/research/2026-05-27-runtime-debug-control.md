# Runtime Debug Control

> Historical Ragnarok capture note. Do not enable debug-control on `arkserver` / Ragnarok
> while player performance testing is active. Future debug-control runs should prefer a
> dedicated `arkserver-obelisk-debug` instance; use `arkserver2` / TheIsland only during an
> explicitly approved fallback window.

## Why this exists

The static FName root experiments proved that bootstrap-time probing is not a
good source of truth. The server can already be online while the startup scanner
still sees an early or wrong table state.

Obelisk now has a debug-only runtime control path so probes can be triggered
after the ARK process is alive.

## Enablement

This is not stable posture. Enable it only for a short approved debug window on the
dedicated debug instance:

```bash
instance=arkserver-obelisk-debug
touch /servidor/ark/obelisk/state/instances/${instance}/enable-debug-control
# Restart only the approved isolated/debug instance control script.
```

Expected Obelisk log line:

```text
Debug control enabled. Watching /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug for marker requests.
```

Stable posture must reject `OBELISK_ENABLE_DEBUG_CONTROL=1`.

## Static FName probe request

Write one or more candidate slot addresses to:

```text
/servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/request-static-fname-probe
```

Example:

```bash
printf '0x5956f30\n' > /servidor/ark/obelisk/state/instances/${instance}/request-static-fname-probe
```

The debug control thread polls every two seconds, runs the static FName root
probe, then renames the request to `request-static-fname-probe.done.<ms>`.

## Rollback

```bash
rm -f /servidor/ark/obelisk/state/instances/${instance}/enable-debug-control
# Restart only the approved isolated/debug instance control script.
/home/flowcommunity-ark/Obelisk/scripts/check_obelisk_server_posture.sh --expect-stable \
  --map TheIsland --instance "${instance}"
```

This keeps the default harness clean while allowing targeted post-start memory
inspection without waiting through blind bootstrap retries.

## First live result

Environment:

- Instance: `arkserver`
- Map: `Ragnarok`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Runtime posture: ProcessEvent hook enabled, plugins disabled,
  `OBELISK_ENABLE_DEBUG_CONTROL=1`

Request:

```text
0x5956f30
```

Observed log:

```text
Debug control running static FName probe for 1 slot(s)
StaticFNameRoot FName static-root reject: slot=0x5956F30 table=0x13733660 reason=implausible_num_elements readable_clues=0/3 matched_clues=0/3 header_index_ok=0/3 num_elements=0 num_chunks=0
```

Result:

- The on-demand trigger works.
- Waiting longer for bootstrap retries is not a coherent strategy.
- `0x5956f30` must not be treated as a stable runtime offset from the previous
  core dump alone. The next investigation should scan live readable data
  mappings for FName-table-shaped pointers or derive the root from code/data
  references instead of pinning this single slot.
