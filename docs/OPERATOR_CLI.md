# Operator CLI

Obelisk is gaining a server-side operator CLI. The first version is intentionally
read-only and safe to run on shared clusters:

```bash
scripts/obelisk.py --root /servidor/ark/obelisk status
scripts/obelisk.py --root /servidor/ark/obelisk instances list
scripts/obelisk.py --root /servidor/ark/obelisk plugins list
scripts/obelisk.py --root /servidor/ark/obelisk plugins show oBaseEvents
```

The CLI reads the central install root, plugin publication state, plugin config summaries,
and per-instance marker directories. It does not edit config, markers, plugin binaries, or
LinuxGSM state.

`instances list` includes a `persistent_posture` column derived only from marker files:

- `stable`: `enable-process-event-hook` and `disable-plugins` are regular files and no
  forbidden experimental marker entry is present.
- `incomplete`: one of the stable markers is missing or malformed.
- `experimental`: a debug/reflection/callback marker entry is present and would affect a
  future restart.
- `experimental+incomplete`: both conditions are true.
- `invalid`: the instance marker entry itself is unsafe, such as a symlinked instance
  directory.

This is a restart-posture summary, not proof that a currently running process has the same
environment. Use `scripts/check_obelisk_server_posture.sh --expect-stable --map <map>
--instance <instance-id>` for live process validation.

`status` reports valid instance directories separately from `invalid_instance_entries` so
unsafe marker entries are visible even before listing per-instance details.

## Post-Stable Lifecycle TODO

The first stable Obelisk line should not depend on mutable lifecycle commands. Keep the
CLI read-only until the runtime/API/plugin config contract is stable enough for external
modders and operators.

After the first stable production version, the target operator shape is:

```text
obelisk start <instance>
obelisk stop <instance>
obelisk restart <instance>
obelisk plugins list
obelisk plugins show <plugin>
obelisk plugins install <PluginName.so>
obelisk plugins enable <plugin> --instance <id>
obelisk plugins disable <plugin> --instance <id>
obelisk plugins rollback <plugin>
obelisk plugins restart <plugin> --instance <id>
```

Until Obelisk has a validated in-process plugin unload/reload system, plugin restart must
mean an operational restart of the target ARK instance after safely changing plugin
publication or config. It must not imply hot reload inside a running ShooterGameServer
process.

Lifecycle commands should be implemented as wrappers around explicit LinuxGSM instance
commands and Obelisk's staged installers. They must:

- require a named instance id;
- show the exact LinuxGSM command before execution;
- refuse broad cluster restarts by default;
- preserve the stable posture gates from `docs/INSTALL.md`;
- use `scripts/install_obelisk_plugin.sh` for plugin publication;
- keep plugin activation scoped by `instance_allowlist` or explicit `allow_all_instances`;
- reject per-instance disable when `allow_all_instances=true` unless the operator chooses
  a clearly global operation;
- use dry-run output, backups, symlink rejection, and destination-local atomic writes for
  shared plugin configs;
- run `scripts/check_obelisk_server_posture.sh` after restart when the instance is expected
  to run with Obelisk.

## Hot Reload Boundary

Hot plugin reload is a separate runtime feature, not a CLI shortcut. It needs proven
shutdown ordering, callback cleanup, thread/socket drain, and state ownership for every
plugin before the CLI can expose it as a normal operation.
