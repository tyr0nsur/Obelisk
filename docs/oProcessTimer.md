# oProcessTimer

`oProcessTimer` is a minimal first-party example for Obelisk process-local timers.

Support tier: release-supported seed.

Release-scope caveat: this plugin and the timer ABI are part of the current
`v0.1.0-rc.2` core runtime surface. They remain process-local core primitives and do not
promote UE timers, gameplay/module timers, identity, command routing, or shared-cluster
state.

It demonstrates only the timer ABI:

- owner-token timer registration;
- one-shot callback registration with a zero-failure handle;
- explicit unregister during shutdown;
- safe-disabled config by default.

It does not use or imply UE timers, gameplay timers, `ProcessEvent`, `UObject`, `FName`,
`GObjects`, player/resource identity, permissions, commands, mutation, lookup, persistent
timer ids, cluster state, HTTP, sockets, file readers, or detached worker ownership.

## Config

Default config is fail-closed:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
```

To activate the example in an approved local test environment, set `enabled=true` and add
the current instance id to `instance_allowlist`. Do not store timer handles in config or
logs; timer ids are process-local runtime handles only.

## Runtime Behavior

On init, the plugin reads its safe-disabled config before requiring the optional timer API
slots, so discovery/config-preparation can succeed on instances where the timer feature is
not active. When enabled, it requires `OBELISK_API_CAPABILITY_TIMERS`, a sufficient
`ObeliskApi::struct_size` through `UnregisterTimerWithOwnerToken`, non-null timer
register/unregister function pointers, and a non-zero `plugin_owner_token` before any
registration. It then registers one one-shot timer with a 1000 ms delay, logs a fixed
message when the callback fires, and unregisters the handle on shutdown. Shutdown is
idempotent, and an init failure after an accepted timer registration unregisters the
process-local handle before state is reset. Timer callbacks use stable process-local user
data and do not read borrowed init context.

`UnregisterTimerWithOwnerToken` cancels future timer delivery for the handle, but plugin
authors should not treat individual timer unregister as a full quiescence barrier. The
runtime owner cleanup during plugin unload is the final barrier before plugin code and
owner state are released.

Callbacks must return quickly and must not call into UE/gameplay state.
