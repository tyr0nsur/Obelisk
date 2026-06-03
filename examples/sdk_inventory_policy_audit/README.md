# Copied Inventory Policy Audit Example

This creator-facing example builds outside the Obelisk source tree and uses only the
installed SDK package:

Support tier: experimental pattern.

- `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`
- `Obelisk::obelisk_sdk`
- `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS`
- `OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS`
- `RegisterGameplayPolicyEventWithOwnerTokenHandle`
- `UnregisterGameplayPolicyEventWithOwnerToken`
- `DescribeGameplayPolicyEventKind`

This is an experimental copied-data pattern for observing copied inventory-backed
`GameplayPolicyEvent` categories. It counts callback-scope scalar fields from promoted
event kinds and logs only process-local aggregate counts during shutdown.

The example does not provide an Inventory SDK, Items SDK, identity, lookup, mutation,
return override, commands, permissions, chat replies/send-chat, storage, ArkApi
compatibility, Windows/MSVC portability, or implementation patterns from other
frameworks. It does not make policy decisions and does not retain callback payloads after
the callback returns.

The `find_package` version is a compatibility floor for the current pre-release SDK line,
not a complete SDK claim and not a claim that a stable `v0.1.0` release tag exists.
This example is a foundation/contributor-readiness sample, not ArkApi portability
guidance and not Obelisk SDK v1 evidence.

## Build

Install Obelisk into a test root first, then point CMake at that install:

```bash
cmake -S examples/sdk_inventory_policy_audit -B /tmp/obelisk-sdk-inventory-policy-audit-build \
  -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root
cmake --build /tmp/obelisk-sdk-inventory-policy-audit-build -j"$(nproc)"
```

The output is `obelisk_sdk_inventory_policy_audit.so`. Install plugins into a local
Obelisk root with `scripts/install_obelisk_plugin.sh`; do not copy a partially built
`.so` into a shared runtime `plugins/` directory.
