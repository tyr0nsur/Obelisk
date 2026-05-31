# ARK Server Restore Notes

Use this when SteamCMD, LinuxGSM, or the ARK app install rewrites server files and the two
LinuxGSM instances need to be restored quickly.

Operator-only runbook: these commands are not contributor authorization. They require
current-turn approval before any `/servidor/ark` read/write, stop/start/restart, backup,
or restore.

## Current Instances

- `arkserver`: Ragnarok, `OBELISK_INSTANCE_ID=arkserver`
- `arkserver2`: TheIsland, `OBELISK_INSTANCE_ID=arkserver2`
- Shared ARK root: `/servidor/ark`
- Shared serverfiles: `/servidor/ark/serverfiles`
- Shared cluster id currently observed: `MiClusterArk`

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

Ragnarok gameplay config note:

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

## Post-Restore Checks

Before starting servers:

```bash
sha256sum /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
sha256sum /servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
ls -la /servidor/ark/lgsm/config-lgsm/arkserver/
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/state
```

After starting:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
tail -n 100 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
tr '\0' '\n' < /proc/$(pgrep -f '^./ShooterGameServer TheIsland' | head -n1)/environ | rg 'OBELISK_INSTANCE_ID|OBELISK_ROOT|OBELISK_LOG_DIR'
```

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
