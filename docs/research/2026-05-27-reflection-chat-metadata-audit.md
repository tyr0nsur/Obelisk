# Reflection Chat Metadata Audit

## Objective

Advance reflection/chat research without touching live servers or enabling ChatPlugin on a
production map. The concrete goal was to move the codebase a small step toward
`FName`/`GNames`/`GObjects`/`UFunction` metadata-backed decoding.

## Environment

- Workspace: `/home/flowcommunity-ark/Obelisk`
- Obelisk commit observed before edits: `223a036`
- Date: 2026-05-27
- Runtime servers: not touched
- Native exec probes: not used
- Live ChatPlugin: not enabled

## Hypothesis

The safest near-term improvement is to make the existing research code emit more structured
candidate object evidence, while keeping all scanner behavior behind its existing
`OBELISK_ENABLE_REFLECTION_SCANNER=1` gate and keeping ChatPlugin's runtime behavior
unchanged.

## Method

1. Audited `ue/ReflectionScanner.*`, `ue/Memory.*`, `ue/Reflection.h`, and
   `plugins/chat/ChatPlugin.cpp`.
2. Centralized the duplicated `FName`, `FString`, and `UObjectBase` probe layouts in
   `ue/Reflection.h`.
3. Updated ChatPlugin to consume the shared probe layouts while preserving its existing
   UTF-16/UTF-32 scoring and discovery gates.
4. Extended ReflectionScanner logging for already-discovered candidate globals:
   - bounded `UObject` header probe: vtable, flags, internal index, class pointer,
     `NamePrivate`, outer pointer
   - bounded `UFunction` tail window around `+0xA0..+0xC8` when an executable field is
     already found

## Evidence

- `cmake --build build` completed successfully.
- Built targets included `libobelisk.so` and `ChatPlugin`.
- The scanner remains gated by existing startup behavior; no new live experiment path was
  added.
- Native exec probe installation remains behind `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1`; this
  task did not use it.

## Result

This change does not claim any new offset as validated. It improves future offline/debug
captures by logging enough object-shape evidence to compare candidate globals against
`UObject` and `UFunction` expectations before accepting `GObjects`, `GNames`, or function
metadata hypotheses.

## Rejected Paths

- Did not add a new broad `ProcessEvent` scan in ChatPlugin.
- Did not activate ChatPlugin discovery on live Ragnarok.
- Did not use native exec probes.
- Did not hardcode `ServerChat`/`ClientMessage` metadata offsets as facts.
- Did not infer `GObjects` or `GNames` from string proximity alone.

## Risks

- `UFunction` tail logging is a candidate window only. Values around `+0xA0..+0xC8` can be
  false positives unless cross-validated against object enumeration and resolved names.
- `Memory::IsReadable` is still a coarse probe based on `write(/dev/null)`. It is acceptable
  for gated research logging, not for production metadata traversal.
- ChatPlugin still relies on raw FString parameter probing until property metadata is
  recovered.

## Next Steps

1. Run `ReflectionScanner` only on an isolated/debug instance with
   `OBELISK_ENABLE_REFLECTION_SCANNER=1` and plugins disabled.
2. For each candidate global, compare:
   - candidate `NamePrivate.ComparisonIndex` against observed chat indices `9619`/`9622`
   - candidate class pointer consistency across discovered objects
   - executable field offset consistency, especially whether `+0xA8` remains plausible
3. Use the logged object header evidence to design a `GUObjectArray` scan that requires
   repeated valid `UObjectBase` shapes rather than one string reference.
4. Only after `GObjects` and names are resolved, replace ChatPlugin's raw FString scan with
   reflected `UFunction` parameter offsets and `ParmsSize` bounds.

## Skill Updates Needed

No skill rule changed. Existing rules already say ReflectionScanner is offline/debug-only,
native exec probes are unsafe, and chat decoding should move to reflection metadata.
