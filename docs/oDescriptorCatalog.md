# oDescriptorCatalog

`oDescriptorCatalog` is a first-party reference plugin for metadata-only SDK discovery.
It demonstrates how a plugin can inspect promoted resource categories and gameplay policy
event kinds before deciding what copied events it wants to handle.

The plugin uses only:

- `DescribeResourceKind`
- `DescribeGameplayPolicyEventKind`

It does not register callbacks, timers, chat handlers, threads, HTTP endpoints, raw
`ProcessEvent` callbacks, resource identities, lookup handles, mutations, or return
overrides.

## Config

Default config is safe-disabled:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "descriptor_catalog": {
    "enabled": false,
    "log_catalog": true
  }
}
```

To activate on one instance, set both `enabled=true` and
`descriptor_catalog.enabled=true`, and include the current `OBELISK_INSTANCE_ID` in
`instance_allowlist`.

## Output

When active, the plugin validates descriptor coherence and logs sanitized metadata:

- resource kind, stable name, supported event mask, supported field mask, descriptor flags;
- event kind, stable name, backing resource kind, event mask, field mask, event flags.

This metadata is for routing and configuration only. `resource_kind` is a category, not
object identity, inventory identity, player identity, lookup authority, mutation
authority, or proof that two events refer to the same in-game object.
