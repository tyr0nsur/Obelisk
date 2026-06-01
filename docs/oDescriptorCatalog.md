# oDescriptorCatalog

`oDescriptorCatalog` is a first-party reference plugin for metadata-only SDK discovery.
It demonstrates how a plugin can inspect promoted resource categories and gameplay policy
event kinds before deciding what copied events it wants to handle.

Support tier: release-supported seed.

Boundary: this is a release-supported SDK example, not active Plugin Hub work and not v1
SDK completion evidence.

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

The plugin reads this safe-disabled config before requiring the optional descriptor API
slots, so discovery/config-preparation can succeed when descriptor capabilities are not
advertised. When active, it requires both
`OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS` and
`OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS`, a sufficient
`ObeliskApi::struct_size` through `DescribeGameplayPolicyEventKind`, and non-null
descriptor function pointers before querying metadata. Missing capabilities, too-short
API tables, malformed config, unsafe allowlist entries, or incoherent descriptor metadata
fail closed without registering callbacks or timers.

`oDescriptorCatalog` has no owner-token runtime state because it does not register
callbacks or timers. Plugins that add callback or timer ownership on top of descriptor
discovery must follow the owner-token handle pattern used by the event and timer
examples.

## Output

When active, the plugin validates descriptor coherence and logs sanitized metadata:

- resource kind, stable name, supported event mask, supported field mask, descriptor flags;
- event kind, stable name, backing resource kind, event mask, field mask, event flags.

This metadata is for routing and configuration only. `resource_kind` is a category, not
object identity, inventory identity, player identity, lookup authority, mutation
authority, or proof that two events refer to the same in-game object.
Descriptor names and masks are copied metadata, not `FName`, `GNames`, `GObjects`,
`UObject`, or raw UE pointer access.
