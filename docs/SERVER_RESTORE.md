# ARK Server Restore Notes

Use this when SteamCMD, LinuxGSM, or the ARK app install rewrites server files and the ARK
LinuxGSM instances need to be restored quickly. Never run more than two ARK servers at
once; an approved posture transition must confirm one instance is off before another is
brought online.

Operator-only runbook: these commands are not contributor authorization. They require
current-turn approval before any `/servidor/ark` read/write, stop/start/restart, backup,
restore, runtime observation, or live log read.
Current-turn exact scope is required for live server/log reads, marker/env changes,
Discord sends, and runtime capture; passive/read-only observations and beta tester
notices are not exceptions, and this restore note does not create that scope.
Historical approvals, release-readiness/package-shape/install success, Plugin Hub or
support-tier labels, public reachability, passive monitor output, passive monitors,
`progress_normalization_trace`, source_overclaim diagnostics,
`source_overclaim_total_flag_count=0`, the latest validation pass, six-agent closure
notes, `.codex` cleanup, exact-version
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
package installs, historical live approvals/map names, historical approvals/map names,
and beta notices are chronology only. They do not create live-op authorization, Discord
authorization, runtime evidence/readiness, SDK/P0 progress, public SDK readiness,
publication authority, Plugin Hub readiness, support-tier activation,
package-shape/public package readiness, stable SDK readiness, or stable SDK claims.
Treat every live read of server state or logs as scoped operator work; copied offline
artifacts may be reviewed without expanding that scope.

## Current Instances

- `arkserver`: Ragnarok, `OBELISK_INSTANCE_ID=arkserver`
- `arkserver2`: TheIsland, `OBELISK_INSTANCE_ID=arkserver2`
- `arkserver3`: Genesis2, `OBELISK_INSTANCE_ID=arkserver3`; game UDP `7783`,
  raw UDP `7784`, Steam query UDP `27017`, RCON TCP `27022`
- Shared ARK root: `/servidor/ark`
- Shared serverfiles: `/servidor/ark/serverfiles`
- Shared cluster id currently observed: `MiClusterArk`

Genesis2 public reachability note: local health is not enough after router/NAT/firewall
or port-forwarding work. After any approved router/NAT/firewall or port-forwarding
change, verify Genesis2 public Steam/GameDig query from outside the LAN; local health does
not prove public reachability. If Genesis2 is healthy locally but absent from public
query, treat missing forwarding for UDP `7783`/`7784`/`27017` as the likely network-scope
cause until operator/network evidence says otherwise. This is operator knowledge only; it
does not authorize starts, stops, restarts, router/NAT/firewall edits, port forwarding, or
any other network changes without current-turn approval.

## Configs To Preserve

The two main gameplay config files are:

```text
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
```

LinuxGSM instance config also matters:

```text
/servidor/ark/lgsm/config-lgsm/arkserver/arkserver.cfg
/servidor/ark/lgsm/config-lgsm/arkserver/arkserver2.cfg
/servidor/ark/lgsm/config-lgsm/arkserver/arkserver3.cfg
/servidor/ark/lgsm/config-lgsm/arkserver/common.cfg
/servidor/ark/lgsm/config-lgsm/arkserver/secrets-*.cfg
```

Obelisk runtime files live outside the Steam app tree and should remain under:

```text
/servidor/ark/obelisk/
```

If a reinstall rewrites the ARK binary directory, also verify the launcher/wrapper under:

```text
/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Use the read-only drift check before restarting any restored instance:

```bash
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

## Backup Already Created

Latest backup symlink:

```text
/home/flowcommunity-ark/backups/ark-config-latest
```

Concrete backup created before further experiments:

```text
/home/flowcommunity-ark/backups/ark-config-20260527-190558
```

It contains:

- `Game.ini`
- `GameUserSettings.ini`
- LinuxGSM `arkserver/*.cfg`
- `MANIFEST.txt` with SHA256 hashes and running server command lines at backup time

Historical Ragnarok gameplay config note, not current authorization:

- `AllowCaveBuildingPvP=True` was applied in
  `GameUserSettings.ini` on 2026-05-27 after explicit operator approval, then
  `arkserver` was restarted successfully. The latest restore symlink was refreshed to
  `/home/flowcommunity-ark/backups/ark-config-20260527-190558`; Ragnarok remained up.
- The pre-change file backup is
  `/home/flowcommunity-ark/backups/ark-config-manual/GameUserSettings.ini.allow-cave-20260527-184547.bak`.

## Create A Fresh Backup

Operators may run this during an approved maintenance window before risky updates:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
backup_root="/home/flowcommunity-ark/backups/ark-config-$stamp"
mkdir -p "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer"
mkdir -p "$backup_root/lgsm/config-lgsm/arkserver"
cp -a /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer/"
cp -a /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer/"
cp -a /servidor/ark/lgsm/config-lgsm/arkserver/*.cfg "$backup_root/lgsm/config-lgsm/arkserver/"
(cd "$backup_root" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$backup_root/MANIFEST.txt"
ln -sfn "$backup_root" /home/flowcommunity-ark/backups/ark-config-latest
```

## Restore Gameplay And LGSM Configs

Only run this when the servers are stopped or during a controlled maintenance window:

```bash
backup_root="/home/flowcommunity-ark/backups/ark-config-latest"
cp -a "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini" \
  /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
cp -a "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini" \
  /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
cp -a "$backup_root/lgsm/config-lgsm/arkserver/"*.cfg \
  /servidor/ark/lgsm/config-lgsm/arkserver/
```

When restoring `GameUserSettings.ini`, verify that `[MessageOfTheDay]` keeps
`Message=` on one physical line with literal `\n` separators. Restoring an older backup
can reintroduce a multiline MOTD that ARK/dashboards may parse as broken text.
The dashboard normalizes its managed `GameUserSettings.ini` writes, but direct scripts
such as `/home/flowcommunity-ark/fix_configs.py`,
`/home/flowcommunity-ark/apply_fibercraft_settings.py`, historical scratch scripts,
LinuxGSM default install copies, manual edits, and RCON/admin `SetMessageOfTheDay`
operations can still reintroduce or preserve a broken MOTD if their input is already
split or incomplete.

Use `scripts/normalize_ark_motd_ini.py` on an offline staged copy before copying
`GameUserSettings.ini` back to `/servidor/ark`:

```bash
backup_root="/home/flowcommunity-ark/backups/ark-config-latest"
staged_ini="/tmp/ark-GameUserSettings.ini"
cp -a "$backup_root/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini" "$staged_ini"
python3 scripts/normalize_ark_motd_ini.py "$staged_ini" --check --json
python3 scripts/normalize_ark_motd_ini.py "$staged_ini" --write --json
python3 scripts/normalize_ark_motd_ini.py "$staged_ini" --check --json
```

`--check` exits `1` when the staged file still needs normalization; use `--write` only on
the staged copy, then copy that staged file during the approved restore step. The
normalizer rejects direct or symlink-resolved paths under `/servidor/ark` unless
`--allow-protected-path` is passed. That flag is for an already approved maintenance
workflow only; it does not authorize live config reads/writes, server starts, restarts,
runtime observation, or validation. The tool edits only `[MessageOfTheDay]` `Message=`
continuation lines and leaves unrelated INI sections, keys, comments, and blank lines
unchanged.

## Post-Restore Checks

Before starting servers:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
sha256sum /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
ls -la /servidor/ark/lgsm/config-lgsm/arkserver/
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/state
```

After starting inside the same approved maintenance window:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
tail -n 100 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
tr '\0' '\n' < /proc/$(pgrep -f '^./ShooterGameServer TheIsland' | head -n1)/environ | rg 'OBELISK_INSTANCE_ID|OBELISK_ROOT|OBELISK_LOG_DIR'
```

These are live runtime/log observations, not offline receipts or copied-log review.
Skip them unless the current approval names the target instances, restart window,
marker/env gates when applicable, evidence paths, rollback, shutdown/posture expectation,
and any notice/send path required for player-facing validation.

Expected safe Obelisk posture for development baseline:

- Ragnarok: ProcessEvent hook enabled, plugins disabled; currently protected while users
  are active.
- TheIsland: `arkserver2` is powered off. Current Obelisk debug/development server work
  uses `arkserver2` only after explicit approval for a scoped test, rollback, and shutdown
  afterward; scanner/native-exec/ptrace or broad tracing still require explicit
  run-window approval and rollback.
- ReflectionScanner disabled unless an isolated/debug run is intentionally authorized.
- Native exec probes disabled.

## Do Not Restore Blindly

- Do not restore while a server is writing config.
- Do not copy old binary-local `libobelisk.so` or `ObeliskPlugins/` back into the ARK
  binary directory.
- Do not restore legacy map markers as the source of truth.
- Do not reuse live cluster flags for a future isolated debug instance.
- Do not activate raw discovery probes or ReflectionScanner as part of config recovery.
