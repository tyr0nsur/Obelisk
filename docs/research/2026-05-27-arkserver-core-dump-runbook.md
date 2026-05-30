# Historical Arkserver Core Dump Runbook

> Historical runbook. Do not execute this against `arkserver` / Ragnarok while player
> performance testing is active. The executable workflow for future second-source cores is
> `docs/research/2026-05-27-isolated-second-core-runbook.md`: prefer
> `arkserver-obelisk-debug`; use `arkserver2` / TheIsland only as an explicit
> operator-approved fallback.

## Objective

Preserve the original Ragnarok core-dump procedure as historical evidence and a source of
metadata requirements. Future captures must be ported to an isolated/debug target before
execution. This runbook is for authorized maintainer review only; do not run `gdb`,
`gcore`, restart servers, or modify `/servidor/ark` without an approved capture window.

## Preconditions

- Operator has explicitly designated `arkserver-obelisk-debug` as the debug target for
  this capture, or explicitly approved `arkserver2` / TheIsland as fallback.
- The lead owns the invasive command window and is ready to abort if posture is wrong.
- The preferred path uses the per-instance `allow-ptrace` marker and a restart into debug
  posture. Root/sysctl changes are a fallback, not the normal path.
- Large artifacts are written under `/servidor/ark/obelisk/dumps` because that filesystem
  has the required space.

## Preflight

```bash
set -euo pipefail

repo=/home/flowcommunity-ark/Obelisk
server_bin=/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer
stamp=$(date -u +%Y%m%dT%H%M%SZ)
instance=arkserver-obelisk-debug
map=TheIsland
out=/servidor/ark/obelisk/dumps/${instance}-${stamp}

mkdir -p "${out}"/{pre,post,logs}
chmod 700 "${out}"

git -C "${repo}" rev-parse --short HEAD | tee "${out}/obelisk-commit.txt"
git -C "${repo}" status --short | tee "${out}/git-status.txt"
sha256sum "${server_bin}" | tee "${out}/ShooterGameServer.sha256.txt"
file "${server_bin}" | tee "${out}/ShooterGameServer.file.txt"
cat /proc/sys/kernel/yama/ptrace_scope | tee "${out}/pre/yama-ptrace-scope.txt"

pgrep -af "^./ShooterGameServer ${map}" | tee "${out}/pre/pgrep.txt"
pid_count=$(wc -l < "${out}/pre/pgrep.txt")
test "${pid_count}" -eq 1
pid=$(awk '{print $1}' "${out}/pre/pgrep.txt")
test -n "${pid}"
echo "${pid}" | tee "${out}/pid.txt"

"${repo}/scripts/check_obelisk_server_posture.sh" --expect-stable --pid "${pid}" \
  --map "${map}" --instance "${instance}" \
  | tee "${out}/pre/posture.txt"

tr '\0' '\n' < "/proc/${pid}/cmdline" | tee "${out}/pre/cmdline.txt"
tr '\0' '\n' < "/proc/${pid}/environ" | sort \
  | rg '^(OBELISK_|LD_PRELOAD=|LD_LIBRARY_PATH=)' \
  | tee "${out}/pre/obelisk-env.txt" || true
cp "/proc/${pid}/"{status,limits,maps,smaps_rollup} "${out}/pre/"
readlink -f "/proc/${pid}/exe" | tee "${out}/pre/exe.txt"
readlink -f "/proc/${pid}/cwd" | tee "${out}/pre/cwd.txt"

rss_kb=$(awk '/^Rss:/ {print $2}' "/proc/${pid}/smaps_rollup")
df -h /servidor/ark | tee "${out}/pre/df-ark.txt"
df -Pk /servidor/ark | tee "${out}/pre/df-ark-kb.txt"
echo "rss_kb=${rss_kb}" | tee "${out}/pre/rss.txt"
```

Abort before attaching if:

- `pid` is empty, or multiple plausible `ShooterGameServer ${map}` processes exist.
- `check_obelisk_server_posture.sh --expect-stable` fails before enabling debug ptrace.
- `OBELISK_ENABLE_NATIVE_EXEC_PROBES` is present.
- Scanner/static-root env is present unless the lead intentionally accepts that posture.
- Free space under `/servidor/ark` is not comfortably larger than process RSS
  plus room for compression and logs.

## Enable Debug Ptrace

With Yama `ptrace_scope=1`, `gcore` cannot attach to an existing sibling process unless
Obelisk opts in or root changes the kernel setting. The preferred Obelisk path is:

```bash
touch /servidor/ark/obelisk/state/instances/${instance}/allow-ptrace
# Restart only the approved isolated/debug instance control script.
```

After restart, the process env should include `OBELISK_DEBUG_ALLOW_PTRACE=1`, and Obelisk
should log:

```text
Debug ptrace attach enabled by OBELISK_DEBUG_ALLOW_PTRACE=1.
```

Do not treat this as stable posture. It is a temporary dump posture and must be removed
after the dump:

```bash
rm -f /servidor/ark/obelisk/state/instances/${instance}/allow-ptrace
# Restart only the approved isolated/debug instance control script.
```

## Dump

`gcore`/`gdb` will briefly stop the process while writing the dump. Run only during the
approved window:

```bash
core_base="${out}/core/${instance}-${stamp}"
mkdir -p "${out}/core"
chmod 700 "${out}/core"

timeout 20m gcore -o "${core_base}" "${pid}" 2>&1 | tee "${out}/gcore.txt"
core_file="${core_base}.${pid}"
test -s "${core_file}"
chmod 600 "${core_file}"
sha256sum "${core_file}" | tee "${out}/core.sha256.txt"
ls -lh "${core_file}" | tee "${out}/core.ls.txt"
```

If `gcore` is unavailable, the equivalent lead-owned fallback is:

```bash
timeout 20m gdb -q -batch \
  -ex "set pagination off" \
  -ex "attach ${pid}" \
  -ex "gcore ${core_base}.${pid}" \
  -ex "detach" \
  -ex "quit" 2>&1 | tee "${out}/gdb-gcore.txt"
```

Do not use `kill -ABRT` for this workflow; it intentionally terminates the server.

If Obelisk has not been restarted with `allow-ptrace`, `gcore` is expected to fail with
Yama/ptrace errors. Do not keep retrying against the same process.

## Posture Check

```bash
if kill -0 "${pid}" 2>/dev/null; then
  "${repo}/scripts/check_obelisk_server_posture.sh" --pid "${pid}" \
    | tee "${out}/post/debug-posture.txt"
  cp "/proc/${pid}/"{status,limits,maps,smaps_rollup} "${out}/post/"
else
  echo "pid ${pid} no longer exists after dump" | tee "${out}/post/process-gone.txt"
fi

cp -a "/servidor/ark/obelisk/logs/${instance}/." "${out}/logs/" 2>/dev/null || true
rg -n "Obelisk Runtime Loaded|ProcessEvent|ReflectionScanner|NativeExecProbe|Plugin loading|ERROR|Fatal|Signal" \
  "${out}/logs" | tee "${out}/log-markers.txt" || true
```

If the process is gone or hung, preserve artifacts and stop. The lead decides any restart
or rollback.

After removing `allow-ptrace` and restarting, stable posture must pass:

```bash
"${repo}/scripts/check_obelisk_server_posture.sh" --expect-stable \
  --map "${map}" --instance "${instance}" \
  | tee "${out}/post/stable-posture-after-rollback.txt"
```

## Evidence Pack Contents

Preserve the whole `${out}` directory, including:

- `core/<instance>-*.${pid}` and `core.sha256.txt`
- `obelisk-commit.txt` and `git-status.txt`
- `ShooterGameServer.sha256.txt` and `ShooterGameServer.file.txt`
- `pid.txt`
- `pre/` and `post/` procfs snapshots
- `pre/posture.txt`, `post/debug-posture.txt`, and
  `post/stable-posture-after-rollback.txt` when available
- `logs/` copied from `/servidor/ark/obelisk/logs/arkserver/`
- `gcore.txt` or `gdb-gcore.txt`
- `log-markers.txt`

Do not commit the core, logs, proc snapshots, or generated evidence artifacts to Git.

## Risks

- `gcore`/`gdb` pauses all target threads while dumping; players may see a freeze or
  timeout if the dump is large.
- Core files can include secrets, player data, memory-resident tokens, and proprietary
  server state. Keep permissions `600` for the core and `700` for the directory.
- Dump size can exceed RSS because mapped regions and allocator state may be large.
- Disk pressure on the host can degrade or crash other services.
- A failed attach can still perturb timing. Do not chain additional runtime probes after a
  failed dump.
- Leaving `allow-ptrace` enabled after the dump is a security/debug posture leak; stable
  posture checks intentionally reject `OBELISK_DEBUG_ALLOW_PTRACE=1`.
