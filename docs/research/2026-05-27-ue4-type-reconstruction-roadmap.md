# UE4 Type Reconstruction Roadmap

## Objective

Define the shortest verifiable path from `FName` resolution to `GObjects` and `UFunction`
metadata without returning to chat heuristics or unbounded runtime scans.

This note is a planning/evidence model only. It does not accept offsets, change runtime
behavior, or require touching `/servidor/ark`.

## Current Baseline

- `ProcessEvent` hook installation is separate from reflection and already guarded.
- `ReflectionScanner` can rank candidate globals from copied isolated logs.
- Analyzer evidence packs can record Obelisk commit, binary SHA256, copied log path,
  objdump path, candidate counts, reject markers, and GNames promotion gate.
- Core evidence for this binary confirms a legacy FName table for the captured process and
  promotes `0x595b7e0` to `GUObjectArray research-candidate`.
- Offline UObject enumeration now finds real chat-related `Function` objects through
  `GObjects` and FName-backed names. `UFunction` metadata, property chain, and parameter
  layout are not accepted yet.
- Old chat-related clue mapping `9619 -> ClientMessage` and `9622 -> ServerChat` is stale.
  Current core evidence has `4884 -> ClientMessage`, `9619 -> ServerChat`, and
  `9622 -> SetActiveMissionDebugFlags`.

## P0: Accept A Bounded FName Resolver

Goal: turn validated `FName` indices into strings on one exact binary.

Fields or structures to validate:

- `FName` object layout:
  - `ComparisonIndex` offset and signed 32-bit width.
  - `Number` offset and signed 32-bit width.
- Name storage model:
  - older indirect `GNames` chunks, or
  - compact `FNamePool` style storage.
- Entry header:
  - string encoding flag or inferred encoding,
  - string length,
  - ANSI/UTF variant,
  - safe max entry length.
- Table metadata:
  - element count or pool bounds,
  - chunk count or block count,
  - valid index range.

Evidence required:

- Analyzer evidence pack with binary SHA256 and Obelisk commit.
- `matched_clues=3/3` for `None`, `ClientMessage`, and `ServerChat`.
- Repeat confirmation through distinct `source_global` values or distinct targets, or a
  second independent static path.
- Static xref explanation for the source global or pool access path.
- Rejection examples for wrong previews, implausible counts, unreadable chunks, and
  single-source rows.

Reject when:

- index `0` is not exactly `None`;
- `ClientMessage` or `ServerChat` are swapped, truncated, empty, or unrelated;
- counts are negative or impossible for the clue indices;
- only one chat-derived global points at the table;
- the conclusion depends on live/shared server evidence;
- the entry reader accepts arbitrary printable memory without table bounds.

What `ReflectionScanner` should eventually log:

```text
[ReflectionScanner] FName resolver candidate: model=<GNames|FNamePool> root=<ptr> source=<addr> score=<n>/<m> binary_index_bits=<n> bounds=<ok|reject> clues=None,ClientMessage,ServerChat status=<candidate|reject> reason=<text>
```

Do not implement yet:

- public SDK name APIs;
- global name caching;
- broad index sweeps;
- chat event decoding.

## P0: Identify GUObjectArray/GObjects Shape

Goal: find a bounded object array/root that can validate candidate `UObject*` values.

Fields or structures to validate:

- Global root pointer or static accessor path.
- Object array model:
  - chunked `FUObjectArray` / `FChunkedFixedUObjectArray`, or
  - older flat/indirect `GObjects`-like shape.
- Object item shape:
  - object pointer field,
  - flags/serial fields if present,
  - element size and chunk size.
- Array metadata:
  - object count,
  - max object count,
  - chunk count,
  - readable chunk pointers.
- Cross-checks against candidate objects:
  - candidate `InternalIndex` maps back to the same object pointer;
  - object vtable first entry points to executable ShooterGameServer mapping;
  - object `ClassPrivate`, `OuterPrivate`, and `NamePrivate` are readable/plausible;
  - `NamePrivate` resolves through the accepted FName resolver.

Evidence required:

- Static xref or decompiler evidence showing a global/root access path.
- At least two object candidates whose `InternalIndex` maps back through the array.
- Names resolved through accepted `FName`, not raw numeric index assumptions.
- Reject logs for wrong element size, out-of-bounds index, unreadable chunk, and object
  mismatch.

Reject when:

- `InternalIndex` does not map back to the object;
- high `UObject validation` score is the only evidence;
- class/outer pointers are merely readable but cannot be resolved as objects;
- candidate array size is implausibly small, huge, or mutable noise;
- validation requires scanning arbitrary writable memory without a root candidate.

What `ReflectionScanner` should eventually log:

```text
[ReflectionScanner] GObjects candidate: root=<ptr> model=<chunked|flat|unknown> object_count=<n> max=<n> chunks=<n> element_size=<n> source=<addr> status=<candidate|reject> reason=<text>
[ReflectionScanner] GObjects object check: object=<ptr> internal_index=<n> array_object=<ptr> name='<resolved>' class=<ptr> class_name='<resolved>' status=<ok|reject> reason=<text>
```

Do not implement yet:

- object iteration exposed to plugins;
- object lookup by name in the SDK;
- object lifetime caching across frames;
- gameplay mutation from discovered objects.

## P0: Identify UClass/UStruct Enough For UFunction

Goal: validate that candidate function objects are real `UFunction` instances through
class and struct metadata, not executable-field proximity.

Fields or structures to validate:

- `UObject` base fields already confirmed:
  - vtable,
  - flags,
  - internal index,
  - class,
  - name,
  - outer.
- `UStruct` fields enough to walk ownership:
  - super struct,
  - children/property list root,
  - struct size,
  - min alignment if visible.
- Class identity:
  - candidate object's class resolves to `Function`/`UFunction` equivalent, or
  - outer/class chain proves the object is a function owned by a class.

Evidence required:

- Candidate function name resolves through FName.
- Candidate object exists in GObjects.
- Candidate class/outer chain resolves through GObjects.
- At least one known function clue, such as `ServerChat` or `ClientMessage`, appears as a
  real object with plausible ownership.

Reject when:

- only a field inside the object points to executable memory;
- class pointer is readable but not found in GObjects;
- name resolves but object is not reachable from object array;
- outer chain loops, leaves readable memory, or cannot be bounded.

What `ReflectionScanner` should eventually log:

```text
[ReflectionScanner] UFunction object candidate: object=<ptr> name='<resolved>' class='<resolved>' outer='<resolved>' gobjects_index=<n> status=<candidate|reject> reason=<text>
```

Do not implement yet:

- function invocation helpers;
- event routing by string name in production;
- plugin-visible `UObject*` wrappers.

## P1: Validate UFunction Metadata

Goal: read enough of `UFunction` to bound parameter decoding.

Fields to validate:

- `FunctionFlags`.
- `NumParms`.
- `ParmsSize`.
- `ReturnValueOffset`.
- native function pointer only as metadata, not as a hook target.
- property/children chain root for params.

Evidence required:

- Field offsets supported by UE4 source comparison and binary-specific object examples.
- `ParmsSize` is plausible for known functions and never used beyond readable param buffer.
- `NumParms` matches the number of discovered parameter properties.
- Function flags contain plausible UE function flag bits and reject impossible values.

Reject when:

- `ParmsSize` is zero for a function expected to have params without another explanation;
- `ParmsSize` is huge or points scanner toward broad memory reads;
- `NumParms` and property chain disagree;
- candidate tail offsets are inferred from one qword window only.

What `ReflectionScanner` should eventually log:

```text
[ReflectionScanner] UFunction metadata: object=<ptr> name='<resolved>' flags=0x<hex> num_parms=<n> parms_size=<n> return_offset=<n> property_root=<ptr> status=<candidate|reject> reason=<text>
```

Do not implement yet:

- param decoding from hardcoded offsets;
- manual construction of params for `ClientMessage`;
- native exec probes.

## P1: Validate Property Chain And Params

Goal: decode `ProcessEvent` parameters through metadata.

Fields to validate:

- property node class/type tag.
- property name `FName`.
- property offset inside params.
- element size.
- array dimension.
- next property pointer.
- string property layout for this binary before decoding `FString`.

Evidence required:

- Property chain is bounded by known function metadata.
- Every param read is inside `[params, params + ParmsSize)`.
- Type decoder rejects unknown or unsupported property classes.
- `FString` layout is validated separately with known length/max/data semantics.

Reject when:

- the chain loops;
- a property offset falls outside `ParmsSize`;
- property count exceeds `NumParms` without explanation;
- string decoding accepts arbitrary pointer/length pairs;
- decoding is triggered by every ProcessEvent rather than filtered known functions.

What `ReflectionScanner` should eventually log:

```text
[ReflectionScanner] UFunction params: function='<resolved>' parms_size=<n> properties=<n> status=<candidate|reject> reason=<text>
[ReflectionScanner] UProperty param: function='<resolved>' name='<resolved>' type='<resolved>' offset=<n> element_size=<n> array_dim=<n> status=<ok|reject> reason=<text>
```

Do not implement yet:

- `OnChatMessage`;
- command interception;
- outbound chat send helpers;
- generic script VM or Blueprint-like invocation.

## Recommended Shortest Path

1. Keep FName/GObjects evidence binary-hash-scoped until second-source validation exists.
2. Use offline `GObjects` enumeration to inspect known chat `Function` objects.
3. Add `UFunction` metadata logs or offline evidence for `FunctionFlags`, `NumParms`,
   `ParmsSize`, and property root candidates.
4. Add property chain logs.
5. Decode params only for one known function in a copied/isolated capture.

## Risks

- ARK's UE4 fork may use a name storage model that differs from upstream assumptions.
- Static xrefs from chat strings may point to generated statics, not global UE reflection
  roots.
- High-scoring `UObject` shapes are easy false positives without GObjects back-reference.
- `UFunction` tail windows can look plausible while being unrelated object data.
- Dynamic instrumentation tools would add noise before we have isolated-debug discipline.
- A binary update can invalidate all candidate offsets; evidence packs must include hashes.

## Files Reviewed

- `docs/agent-handoff/CURRENT.md`
- `docs/agent-handoff/COMPACT_CONTEXT.md`
- `agent-skills/obelisk-ue4-type-reconstruction/SKILL.md`
- `agent-skills/obelisk-ue4-reflection/SKILL.md`
- `agent-skills/obelisk-reversing-research/SKILL.md`
- `agent-skills/obelisk-static-binary-analysis/SKILL.md`
- `agent-skills/obelisk-tooling-discipline/SKILL.md`
- `ue/Reflection.h`
- `ue/ReflectionScanner.cpp`
- `scripts/analyze_reflectionscanner_capture.py`
- `docs/research/2026-05-27-gname-evidence-pack-workflow.md`
- `docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md`

## Result

The next implementation should not add chat features. It should add narrowly gated
scanner/analyzer support only when the previous layer has evidence:

- accepted `FName` resolver before `GObjects`;
- accepted `GObjects` before `UFunction`;
- accepted `UFunction` metadata before params;
- accepted params before gameplay events.
