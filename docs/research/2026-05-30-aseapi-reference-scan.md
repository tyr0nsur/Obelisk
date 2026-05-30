# AseApi Reference Scan

## Objective

Assess whether `ArkServerApi/AseApi` can accelerate Obelisk without importing unsafe
Windows/MSVC assumptions into the Linux runtime.

## Environment

- Source: `https://github.com/ArkServerApi/AseApi`
- Local inspection clone: `/tmp/aseapi-inspect`
- Inspected commit: `f13b85979254b6b19c8d9255a0fc11c128978b8b`
- Obelisk scope: research/reference only; no server or runtime experiment performed.

## Result

Useful, but only as a dictionary and behavior map.

Use AseApi for:

- ARK/UE name vocabulary such as `AShooterPlayerController.ServerSendChatMessage`,
  `AShooterGameState.bAllowCaveBuildingPvP`, item/inventory/structure/tribe class names,
  and broad plugin-facing capability areas.
- Compatibility taxonomy for future Obelisk primitives: chat commands, console/RCON
  commands, tick callbacks, timers, plugin lifecycle commands, logging/config helpers,
  permissions, and common ArkApi-style plugin expectations.
- Candidate target discovery before running Obelisk's own snapshot/second-source checks.

Do not use AseApi for:

- Memory offsets, vtable definitions, direct `GetNativePointerField` accessors, direct
  `NativeCall` wrappers, or copied C++ struct layouts.
- `.lib` artifacts, MSVC calling conventions, Windows headers, or Windows hook/ABI design.
- Public Obelisk SDK exposure of raw UE pointers, object identity, mutation, return
  override, or direct internal function invocation.

## Evidence

The repo includes Ark/Atlas public headers and implementation code under
`version/Core/Public/API` and `version/Core/Private`. The scan found:

- 149 files under `version/Core/Public`.
- 13,151 direct `NativeCall`, `GetNativePointerField`, and `BitFieldValue`-style accessors
  in the Ark public headers.
- Command/timer concepts in `version/Core/Private/Commands.*` and
  `version/Core/Private/Tools/Timer.cpp`.
- Chat hook naming around
  `AShooterPlayerController.ServerSendChatMessage_Implementation`.

Those are valuable for naming and product compatibility, but the implementation strategy is
not portable to Obelisk's Linux safety model.

## Obelisk Rule

Every AseApi-derived target must be revalidated through Obelisk:

1. Confirm the `UFunction` or `UProperty` name from offline reflection/snapshot evidence.
2. Confirm owner/class, property chain, sizes, flags, and bounded parameter layout.
3. Require second-source/static/readiness gates before promotion.
4. Route runtime access through `ReflectionScanner`, `RuntimeReflection`, and
   `ProcessEventHook` copied-data paths.
5. Expose only Obelisk-owned copied POD through an append-only C ABI.

## Next Steps

- Build a small ArkApi compatibility matrix from AseApi names only:
  commands, timers, permissions, chat, players, tribes, dinos, items/inventory,
  structures, admin, storage/config.
- Start with non-UE-dependent Obelisk primitives, especially owner-token timers, then
  layer command routing once chat identity/permission requirements are clear.
- For gameplay modules, use AseApi names only as candidate seeds for the existing Item,
  Mission, Transfer, and later broader module recognizer flow.
