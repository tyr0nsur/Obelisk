# Isolated Second Core Runbook

## Objective

Define the next safe second-source core capture for Obelisk reflection research without
using `arkserver` / Ragnarok.

This is a historical debug runbook template only. It does not authorize restarts, marker
changes, ptrace/gcore, text logging, runtime observation, tracing, scanner use,
beta/community notices, or server launches outside explicit current-turn operator approval
for the exact scoped run. `arkserver2` / TheIsland is an isolated fallback target, not a
standing approval.

## Target Priority

Preferred target:

- `arkserver-obelisk-debug`, a dedicated isolated debug instance with separate ports,
  saves, cluster/log posture, and wrapper-level Obelisk environment.

Fallback target:

- `arkserver2` / TheIsland under fresh current-turn scoped debug approval. Preserve
  evidence, restore stable posture, and shut it down afterward only when that scoped run
  requires it.

Protected target:

- `arkserver` / Ragnarok. Do not restart it, change markers, deploy runtime, attach,
  dump, scan, or enable tracing while player performance testing is active.

## Dedicated Instance Requirements

Before core capture, the dedicated instance should have:

- non-overlapping ports, for example `7790`, `7791`, `27025`, `27030`;
- isolated saves, for example `AltSaveDirectoryName=SavedObeliskDebug`;
- no live cluster, or a separate `ObeliskDebugCluster`;
- non-public session posture, password, firewall, or local-only access;
- separated logs, for example
  `OBELISK_LOG_DIR=/servidor/ark/obelisk/logs/isolated-debug`;
  this is a runtime log source only, not the final evidence location;
  copied log bundles for review must live in the external artifact workspace.
- wrapper/env scoped to the debug instance, not shared map markers:
  - `LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so`;
  - `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1`;
  - `OBELISK_DISABLE_PLUGINS=1`;
  - `OBELISK_PE_TRACE_LIMIT=0`;
  - no `OBELISK_ENABLE_NATIVE_EXEC_PROBES`.

## Preconditions

- The current-turn written run plan names the exact target, capture objective, allowed
  marker changes, start/restart/stop commands, ptrace/gcore command, rollback, external
  artifact workspace, and shutdown expectation. A new `arkserver-obelisk-debug` instance
  still needs separate current-turn approval until provisioned.
- Ragnarok is not touched.
- The target starts from quiet debug posture:
  - ProcessEvent hook enabled;
  - plugins disabled;
  - chat reflection disabled unless the window explicitly combines with the A/B runbook;
  - scanner/native-exec/debug-control disabled unless explicitly part of that window.

## Preflight

Record context before any invasive action:

```bash
cd /home/flowcommunity-ark/Obelisk
git rev-parse HEAD
git status --short
sha256sum /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
pgrep -af '^./ShooterGameServer'
df -h /servidor/ark
```

Copy the matching ARK binary into the external artifact workspace before offline intake
and record the copied file's SHA256. Offline tooling must use that copied binary, not the
live path under `/servidor/ark`.

For TheIsland fallback, also run:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
pgrep -af '^./ShooterGameServer TheIsland'
```

Abort if:

- the target does not have a single matching `ShooterGameServer` process;
- posture is not stable and quiet;
- Ragnarok would need to be changed;
- disk space is not comfortably above expected core size;
- scanner/native-exec/debug-control env is active unintentionally;
- logs/saves/cluster posture overlap a live public instance.

## Enable Temporary Ptrace

For dedicated debug, use only that instance's marker/env path after current-turn approval
names the exact ptrace/gcore run:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/allow-ptrace
# restart only arkserver-obelisk-debug through the control script named in current-turn approval
```

For TheIsland fallback only, and only when current-turn approval names this exact marker
edit and restart:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver2/allow-ptrace
/servidor/ark/arkserver2 restart
```

After restart, confirm the PID belongs to the current-turn approved exact target. This is a
debug posture, not stable production posture.

## Capture

Use a timestamped target-specific output directory outside `/servidor/ark` and outside the
repository only for the current-turn approved exact capture:

```bash
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target=arkserver2
out=/home/flowcommunity-ark/obelisk-artifacts/second-source/${target}-TheIsland-${stamp}
mkdir -p "${out}"/{raw,pre,post,logs,intake}
chmod 700 "${out}"

cp /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer "${out}/raw/ShooterGameServer"
sha256sum "${out}/raw/ShooterGameServer" | tee "${out}/raw/ShooterGameServer.sha256.txt"

pid=<single current-turn approved target pid>
timeout 20m gcore -o "${out}/raw/${target}-${stamp}" "${pid}" 2>&1 | tee "${out}/raw/gcore.txt"
core_file="${out}/raw/${target}-${stamp}.${pid}"
test -s "${core_file}"
chmod 600 "${core_file}"
sha256sum "${core_file}" | tee "${out}/raw/core.sha256.txt"
ls -lh "${core_file}" | tee "${out}/raw/core.ls.txt"
```

Do not use `kill -ABRT`. Do not retry repeatedly after a failed attach.

## Rollback

Remove ptrace posture and restart/stop only the current-turn approved exact target:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/allow-ptrace
# restart or stop only arkserver-obelisk-debug through the control script named in current-turn approval
```

For TheIsland fallback, only when current-turn rollback approval names these actions:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver2/allow-ptrace
/servidor/ark/arkserver2 restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
/servidor/ark/arkserver2 stop
```

Preserve logs and proc snapshots under the external artifact directory. Do not commit raw
artifacts. At the end of the window, `arkserver2` should be stopped, `allow-ptrace` absent,
scanner/native-exec/debug-control/broad-trace markers absent, plugins disabled, and no raw
artifact should exist under `/servidor/ark`.

## Offline Follow-Up

After the capture exists, first generate review plans only, using copied paths outside
`/servidor/ark`:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary "${out}/raw/ShooterGameServer" \
  --core "${core_file}" \
  --pack-dir "${out}/intake/pack" \
  --scan-only \
  --json-plan

python3 scripts/run_second_source_core_intake.py \
  --binary "${out}/raw/ShooterGameServer" \
  --core "${core_file}" \
  --pack-dir "${out}/intake/pack" \
  --snapshot-root "${out}/intake/ufunction-snapshots" \
  --verified-fname-root-slot <verified-slot-from-this-artifact> \
  --gobjects-candidate 0x595b7e0 \
  --target-set minimal-second-source-intake \
  --json-plan
```

Review the scan plan and full-intake plan before any `--execute`. Execution should write
phase outputs under `${out}/intake/pack/fname-scan`,
`${out}/intake/pack/gobjects-sampling`, and
`${out}/intake/pack/snapshot-comparison`, never under `/servidor/ark`. See
`docs/research/2026-05-28-second-source-core-intake-runbook.md` for the detailed intake
sequence and acceptance criteria.

Expected second-source result:

- same ARK binary hash or a recorded new hash;
- FName root/table is derived or scanned from this artifact and is not copied from the
  primary-core-only `0x5956f30` slot;
- `GObjects` object samples still round-trip through `InternalIndex`;
- chat `UFunction` target/class/outer/property membership checks pass;
- any mismatch is documented as binary/core-specific evidence, not patched live.

## Current Status

Read-only dump inventory on 2026-05-27 found only the existing Ragnarok-derived core and
packs. No second isolated core is currently available.
