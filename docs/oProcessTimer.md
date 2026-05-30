# oProcessTimer

`oProcessTimer` is a minimal first-party example for Obelisk process-local timers.

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

When enabled, the plugin validates the timer capability and owner token, registers one
one-shot timer with a 1000 ms delay, logs a fixed message when the callback fires, and
unregisters the handle on shutdown.

Callbacks must return quickly and must not call into UE/gameplay state.
