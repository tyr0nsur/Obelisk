# Isolated Second Core Runbook

## Objective

Define the next safe second-source core capture for Obelisk reflection research without
using `arkserver` / Ragnarok.

This is preparation only. It does not authorize restarts, marker changes, ptrace/gcore,
text logging, or server launches.

## Target Priority

Preferred target:

- `arkserver-obelisk-debug`, a dedicated isolated debug instance with separate ports,
  saves, cluster/log posture, and wrapper-level Obelisk environment.

Fallback target:

- `arkserver2` / TheIsland only if the operator explicitly approves using that instance
  for the core window.

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
- wrapper/env scoped to the debug instance, not shared map markers:
  - `LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so`;
  - `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1`;
  - `OBELISK_DISABLE_PLUGINS=1`;
  - `OBELISK_PE_TRACE_LIMIT=0`;
  - no `OBELISK_ENABLE_NATIVE_EXEC_PROBES`.

## Preconditions

- The operator explicitly opens a core window for `arkserver-obelisk-debug`, or explicitly
  names `arkserver2` / TheIsland as the fallback target.
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

For dedicated debug, use only that instance's marker/env path:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/allow-ptrace
# restart only arkserver-obelisk-debug through its approved control script
```

For TheIsland fallback only:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver2/allow-ptrace
/servidor/ark/arkserver2 restart
```

After restart, confirm the PID belongs to the approved target. This is a debug posture, not
stable production posture.

## Capture

Use a timestamped target-specific output directory:

```bash
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target=arkserver-obelisk-debug   # or arkserver2 only if explicitly approved
out=/servidor/ark/obelisk/dumps/${target}-${stamp}
mkdir -p "${out}"/{core,pre,post,logs}
chmod 700 "${out}"

pid=<single approved target pid>
timeout 20m gcore -o "${out}/core/${target}-${stamp}" "${pid}" 2>&1 | tee "${out}/gcore.txt"
core_file="${out}/core/${target}-${stamp}.${pid}"
test -s "${core_file}"
chmod 600 "${core_file}"
sha256sum "${core_file}" | tee "${out}/core.sha256.txt"
ls -lh "${core_file}" | tee "${out}/core.ls.txt"
```

Do not use `kill -ABRT`. Do not retry repeatedly after a failed attach.

## Rollback

Remove ptrace posture and restart/stop only the approved target:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/allow-ptrace
# restart or stop only arkserver-obelisk-debug through its approved control script
```

For TheIsland fallback:

```bash
rm -f /servidor/ark/obelisk/state/instances/arkserver2/allow-ptrace
/servidor/ark/arkserver2 restart
cd /home/flowcommunity-ark/Obelisk
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map TheIsland --instance arkserver2
```

Preserve logs and proc snapshots under the dump directory. Do not commit raw artifacts.

## Offline Follow-Up

After the capture exists, run only offline tooling:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  --core "${core_file}" \
  --output-dir "/servidor/ark/obelisk/dumps/core-pack-${stamp}-fname-scan" \
  --scan-fname-tables \
  --fname-index None=0 \
  --fname-index ClientMessage=4884 \
  --fname-index ServerChat=9619 \
  --fname-index SetActiveMissionDebugFlags=9622

# Inspect the generated pack and choose a verified per-artifact FName root slot.
verified_fname_root_slot=<verified-slot-from-this-artifact>

python3 scripts/build_core_dump_evidence_pack.py \
  --binary /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer \
  --core "${core_file}" \
  --output-dir "/servidor/ark/obelisk/dumps/core-pack-${stamp}" \
  --gobjects-candidate gobjects=0x595b7e0 \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447 \
  --fname-root-slot verified_fname_root_slot="${verified_fname_root_slot}"

python3 scripts/verify_chat_reflection_constants.py \
  --core "${core_file}" \
  --fname-root-slot "${verified_fname_root_slot}" \
  --max-object-scan 30000
```

When regenerating UFunction or ScriptStruct snapshots from the second core, prefer passing
the generated evidence-pack manifest instead of manually retyping artifact identity:

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core "${core_file}" \
  --output-root <second-source-ufunction-snapshots> \
  --gobjects 0x595b7e0 \
  --evidence-pack-manifest "/servidor/ark/obelisk/dumps/core-pack-${stamp}/manifest.json" \
  --target PrimalItem.CanUse \
  --check-layout
```

If the manifest contains multiple FName roots, add
`--evidence-pack-fname-root-label verified_fname_root_slot`. The regenerators copy
`core.sha256`, `core.path`, the evidence-pack directory name, and the selected FName root
from the manifest, and reject CLI identity values that contradict it.

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
