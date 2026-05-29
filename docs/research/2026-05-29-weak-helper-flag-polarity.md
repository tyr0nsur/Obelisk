# Weak Helper Flag Polarity

## Objective

Refine the `uobject_flags_validity_semantics_unproven` blocker by reviewing the static
weak-handle helper family around `0x1d56a30..0x1d56cf8` for the current Linux
`ShooterGameServer` hash.

## Environment

- Binary: `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- SHA256: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Objdump: GNU Binutils 2.42
- Workspace: `/servidor/ark/workspace-offline/weak-helper-flag-polarity-20260529`
- Key artifacts:
  - `objdump/weak-helper-family.objdump.txt`
  - `objdump/caller-windows.objdump.txt`
  - `objdump/direct-call-counts.txt`
  - `ghidra/ghidra-headless-java.stdout`

## Hypothesis

The helpers implement UE4 weak-object validation over `{index, serial}` pairs backed by
the accepted `GObjects` candidate. `UObject+0x8` flags `0x100` and `0x4000` are consulted
as validity filters, but the public meaning and safe lifetime contract remain unpromoted.

## Evidence

The helper family repeatedly validates:

- object index is non-negative and below `0x595b804`
- chunk lookup goes through `0x595b7f0`
- `FUObjectItem+0x8` matches the weak-handle serial
- `FUObjectItem+0x0` resolves the `UObject*`
- `UObject+0x8` is tested for `0x100` and/or `0x4000`

Static helper observations:

| Helper | Observed return shape | Flag polarity |
| --- | --- | --- |
| `0x1d56ae0` | boolean-like validity result | returns false if serial mismatches, object pointer is null, `flags & 0x100`, or `flags & 0x4000` |
| `0x1d56c00` | object pointer or null | returns null if serial mismatches, object pointer is null, or `flags & (0x100 | 0x4000)` |
| `0x1d56c70` | object pointer or null | always rejects `flags & 0x100`; rejects `flags & 0x4000` only when its boolean mode parameter is false |
| `0x1d56a30` | boolean-like multi-mode result | same serial/object checks; mode parameters affect whether an already-null object path or `0x4000` is tolerated |
| `0x1d56b60` | boolean-like multi-mode result | related checks, but caller polarity still needs tighter review before using it as accepted evidence |

Caller windows provide useful polarity context:

- `0x3522bc0` calls `0x1d56ae0`; only when it returns true does the caller invoke
  `0x1d56c00` and pass the resolved object onward.
- `0x83a2ad` calls `0x1d56c00`; a non-null returned object gates a later call using that
  object pointer.
- `0x83a358` calls `0x1d56c70` with `esi=1`; the returned object controls whether the
  surrounding array element is removed.

This is stronger than prior broad core scans because the flag checks appear in executable
helper code and at least two bounded caller windows use true/non-null as the valid path.

## Result

Partially confirmed for internal research:

- `FUObjectItem+0x8` is serial-backed weak-handle state for this binary hash.
- `UObject+0x8 & 0x100` behaves as invalid in the reviewed helper variants.
- `UObject+0x8 & 0x4000` behaves as invalid in strict helper variants and may be
  optionally tolerated by at least one helper mode.

This refines the blocker but does not close it for public `ResourceHandle` promotion.
The missing piece is a named lifecycle semantic and a safe runtime policy for when an
opaque handle may be resolved or rejected across hook frames, plugin callbacks, and object
destruction.

## Risks

- Function names are Ghidra placeholders; do not use them as semantic proof.
- The conclusion is scoped to the ARK binary hash above.
- Do not expose `UObject*`, object indices, serials, class/name/outer pointers, or
  GObjects offsets through the public SDK.
- Do not use this evidence for mutation, return override, or post-callback lookup.

## Next Steps

1. Add a small evaluator mode that treats `0x100` as hard-invalid and `0x4000` as
   strict-invalid unless a helper mode explicitly allows it, then test against existing
   redacted samples.
2. Review more bounded callers of `0x1d56c70` and `0x1d56b60` to name the mode parameter
   more defensibly.
3. Keep public `ResourceHandle` blocked until the runtime design can guarantee
   process-local lifetime, fail-closed revalidation, and no UE internals exposure.
