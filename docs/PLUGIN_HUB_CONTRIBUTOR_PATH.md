# Plugin Hub Contributor Path

This is the short path for adding a Plugin Hub foundation example without widening the
SDK. It starts from the current installed SDK package and stops before identity,
permissions, mutation, or complete v1 claims.

## 1. Decide The Tier

Classify the idea before copying code:

- `release-supported seed`: lifecycle/config/logging, descriptor/catalog reads, or
  process-local timers using the current C ABI.
- `experimental pattern`: passive copied `ChatMessageEvent` parsing or copied
  `GameplayPolicyEvent` auditing, clearly labeled as experimental and plugin-local only.
- `blocked backlog`: anything that needs commands, replies, send-chat, permissions,
  identity, lookup, persistence, storage services, inventory/item mutation, structure
  enforcement, return overrides, raw UE pointers, raw params, or cross-instance state.

The supported seed set is intentionally small: lifecycle/config/logging minimal plugins,
descriptor/catalog readers, and process-local timer utilities. Passive copied chat
parsing and copied policy auditing are experimental examples only. Permissions/admin,
commands/replies/send-chat/broadcast, economy, kits, homes, teleport, and item grants
remain blocked until Obelisk promotes the required identity/principal, permissions/admin,
command routing, response path, persistence/storage, and safe mutation/grant surfaces.

Names from ArkApi, AseApi, or popular plugin families can justify demand notes, but they
do not change the tier and must not be copied as implementation patterns.

## 2. Copy The Closest Example

For a release-supported installed-SDK seed, start from `examples/`:

- copy `examples/sdk_minimal_plugin` for lifecycle/config/logging;
- copy `examples/sdk_minimal_plugin` for descriptor/catalog readers, then add only
  metadata-only `DescribeResourceKind` or `DescribeGameplayPolicyEventKind` calls behind
  `struct_size`, capability-bit, and non-null function-pointer checks;
- copy `examples/sdk_timer_plugin` for owner-token process-local timer work.

Use `plugins/oDescriptorCatalog` as a behavior reference for descriptor validation and
bounded logging, not as the external package scaffold. Keep the external package on
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` and
`Obelisk::obelisk_sdk`.

Keep external examples on the installed SDK contract:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
target_link_libraries(<plugin-target> PRIVATE Obelisk::obelisk_sdk)
```

Do not start from `plugins/` when writing the minimum external package. The `plugins/`
tree contains first-party runtime reference plugins and may use repository-local wiring.

## 3. Validate The Installed SDK

Build from the external plugin source root with an installed Obelisk prefix:

```bash
cmake -S . -B build \
  -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build -j"$(nproc)"
```

Check that the package consumed installed headers and linked only the installed SDK
target:

```bash
rg -n '/path/to/obelisk-install-root/include' build/compile_commands.json
! rg -n '/path/to/Obelisk/include' build/compile_commands.json
rg -n 'find_package\(Obelisk 0\.1\.0 CONFIG REQUIRED COMPONENTS SDK\)|Obelisk::obelisk_sdk' CMakeLists.txt
```

The public source check should return no matches:

```bash
rg -n --glob '!README.md' --glob '!build/**' \
  '#include .*(core/|plugins/|private|ArkApi|AseApi)|ProcessEvent|UObject|UFunction|FString|GObjects|GetNativePointerField|NativeCall|ResourceHandle' .
```

For a narrow lifecycle/config/logging package, `nm -D --defined-only build/<plugin>.so`
should expose only the Obelisk plugin entry points.

## 4. Package Metadata

Before review, the package must state:

- `plugin_id`
- display name
- plugin version
- minimum Obelisk SDK line
- exactly one `Support tier: <tier>` declaration using release-supported seed,
  experimental pattern, or blocked backlog
- used capabilities
- config path
- exported ABI entry points
- whether shutdown is exported and why

Treat the minimum Obelisk SDK line as the installed package floor the example was built
and reviewed against. Do not present it as `v1` readiness, general Plugin Hub
compatibility, ArkApi/AseApi compatibility, or support for surfaces outside the declared
tier.

Review must fail if README, package metadata, or public seed docs claim v1 readiness,
ArkApi/AseApi compatibility, commands, permissions, identity, send-chat/replies, mutation,
storage, inventory, or structure support outside that one declared tier.

Ship safe-disabled default config when config is present:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
```

## 5. When To Stop

Stop at release-supported seed when the example builds against the installed SDK,
checks `abi_version`, `struct_size`, capability bits, non-null function pointers, and
owner tokens, cleans up registrations in idempotent shutdown, and documents package
metadata.

Stop at experimental pattern when the example passively observes copied chat or policy
data and the README clearly says it is not a production module, command SDK, permissions
SDK, identity SDK, send-chat API, moderation API, policy-enforcement SDK, inventory SDK,
structure SDK, mutation API, or v1 completion evidence.

Stop as blocked backlog when the idea needs any unpromoted surface. Write a design or
research note instead of adding wrappers, compatibility shims, private headers, raw
`ProcessEvent` access, raw UE pointers, identity assumptions, permission checks, storage
services, mutation, or return overrides.

Plugin Hub foundation examples help contributors learn the current C ABI. They do not
declare a complete v1 SDK and do not create identity, permissions, command, chat reply,
storage, inventory, structure, or gameplay mutation support.

Do not split a blocked module into a "seed" by using only its timer, logging, or passive
parser pieces. If the user-visible feature needs permissions/admin checks, command
routing, replies, send-chat, broadcast, economy/kits/homes state, teleport, item grants,
or other gameplay mutation, the package stays blocked until the required identity,
permissions, commands, response path, persistence, and mutation surfaces exist.
