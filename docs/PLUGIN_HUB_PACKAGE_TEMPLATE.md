# Plugin Hub Package Template

Use this template for Plugin Hub RC candidate packages. Keep the package README and
metadata scoped to one support tier and one supported surface.

## Package Metadata

```text
plugin_id:
display_name:
plugin_version:
minimum_obelisk_sdk: 0.1.x
Support tier: <release-supported seed | experimental pattern | blocked backlog>
used_capabilities:
config_path:
exported_abi_entry_points:
shutdown_exported: <yes | no>
shutdown_reason:
```

Use exactly one `Support tier:` line. Do not describe the package as v1-ready, full SDK,
production SDK, ArkApi-compatible, AseApi-compatible, or portable from ArkApi plugins.

## Supported Surface

Choose one narrow surface:

- `release-supported seed`: lifecycle/config/logging, descriptor/catalog reads, or
  process-local owner-token timers using the installed Obelisk SDK.
- `experimental pattern`: passive copied `ChatMessageEvent` parsing or copied
  `GameplayPolicyEvent` auditing only, clearly labeled experimental and plugin-local.
- `blocked backlog`: the package needs unpromoted surfaces and must remain a design,
  evidence, or guardrail package instead of a public Plugin Hub module.

Name the exact capabilities and callbacks used. If a feature needs commands, replies,
send-chat, permissions, identity, lookup, persistence, storage, inventory/item mutation,
structure enforcement, return overrides, raw UE pointers, raw params, or cross-instance
state, classify it as `blocked backlog`.

## Explicit Non-Claims

Include these statements in the package README:

```text
This package is not evidence that Obelisk v1 or a full public SDK is complete.
This package is not ArkApi/AseApi compatible and does not port ArkApi plugin behavior.
This package does not expose commands, replies, send-chat, permissions, identity, storage,
inventory, structure, mutation, return override, or raw UE pointer support outside the
declared support tier.
```

For `experimental pattern`, also state:

```text
This is an experimental copied-data pattern, not a production Plugin Hub module or a
general chat, command, policy, inventory, structure, identity, mutation, or enforcement
SDK.
```

## Install And Package Evidence

Record the review evidence with the package:

```text
obelisk_install_prefix:
build_command:
build_result:
compile_commands_check:
linked_target: Obelisk::obelisk_sdk
private_header_check:
defined_symbols_check:
package_files:
```

Minimum evidence:

- builds with `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`;
- links only `Obelisk::obelisk_sdk`;
- uses hidden default symbol visibility;
- includes no private Obelisk headers, ArkApi/AseApi headers, raw UE types, raw
  `ProcessEvent` params, `GetNativePointerField`, `NativeCall`, or `ResourceHandle`;
- exports only the required Obelisk plugin entry points for the declared tier;
- ships README, license text, plugin shared object, and config example or schema when
  config is read.

## README Review Checklist

Before publishing an RC candidate package, verify:

- exactly one support tier is declared;
- supported surface matches the capability matrix;
- install evidence uses the installed SDK, not repository-local plugin wiring;
- config defaults are safe-disabled when config exists;
- `abi_version`, `struct_size`, capability bits, function pointers, and owner tokens are
  checked fail-closed where applicable;
- shutdown is idempotent when callbacks, timers, retained catalog state, or partial init
  cleanup are possible;
- README and metadata contain no ArkApi compatibility, v1 readiness, full SDK, complete
  SDK, commands, permissions, identity, send-chat, mutation, storage, inventory, or
  structure claims outside the declared tier.
