# ARK Server Restore Notes

Use this when SteamCMD, LinuxGSM, or the ARK app install rewrites server files and the two
development instances need to be restored quickly.

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

## Backup Already Created

Latest backup symlink:

```text
/home/flowcommunity-ark/backups/ark-config-latest
```

Concrete backup created before further experiments:

```text
/home/flowcommunity-ark/backups/ark-config-20260527-015805
```

It contains:

- `Game.ini`
- `GameUserSettings.ini`
- LinuxGSM `arkserver/*.cfg`
- `MANIFEST.txt` with SHA256 hashes and running server command lines at backup time

## Create A Fresh Backup

Run before risky updates:

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
tr '\0' '\n' < /proc/$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)/environ | rg 'OBELISK_INSTANCE_ID|OBELISK_ROOT|OBELISK_LOG_DIR'
```

Expected safe Obelisk posture for development baseline:

- Ragnarok: ProcessEvent hook enabled, plugins disabled; currently reserved for player
  performance testing.
- TheIsland: designated Obelisk debug/development target as `arkserver2`; still require
  explicit run-window approval for scanner/native-exec/ptrace or broad tracing.
- ReflectionScanner disabled unless an isolated/debug run is intentionally authorized.
- Native exec probes disabled.

## Do Not Restore Blindly

- Do not restore while a server is writing config.
- Do not copy old binary-local `libobelisk.so` or `ObeliskPlugins/` back into the ARK
  binary directory.
- Do not restore legacy map markers as the source of truth.
- Do not reuse live cluster flags for a future isolated debug instance.
- Do not activate raw discovery probes or ReflectionScanner as part of config recovery.
