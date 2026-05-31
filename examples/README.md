# Examples

This directory contains creator-facing examples that build against the installed Obelisk
SDK package. These examples are separate from `plugins/`, which contains first-party
in-tree reference plugins used by Obelisk's own build and tests.

- `sdk_minimal_plugin/`: smallest external C plugin using `find_package(Obelisk 0.1.0
  CONFIG REQUIRED)` and `Obelisk::obelisk_sdk`.

Examples must stay inside public `include/obelisk/ObeliskApi.h` contracts. Do not use
private headers, raw UE pointers, `ProcessEvent` internals, identity, lookup, mutation,
return overrides, new gameplay APIs, chat replies/send-chat, or ArkApi implementation
patterns in creator-facing examples.
