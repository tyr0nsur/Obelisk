# Core GUObjectArray Candidate

## Objective

Validate a stronger `GUObjectArray`/`GObjects` candidate from the existing authorized
`arkserver` core dump, using the already confirmed FName table from the same core.

## Environment

- Instance: `arkserver`
- Map: `Ragnarok`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Evidence artifact:
  `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z/gdb-gobjects-candidate-0x595b7e0.txt`
- Confirmed FName table in this core: `0x5956f30 -> 0x2ae5c660`

## Hypothesis

The current binary contains a `GUObjectArray`-shaped global at or near `0x595b7e0`.
Unlike chat string/object leads, this should validate through object-array structure:
chunk pointer, object count, object item, `UObjectBase` fields, and FName-resolved object
names.

## Evidence

GDB core inspection of `0x595b7e0`:

```text
chunks=0x2c6f2cc0 count=1243796 max=12648448 serial=45862
chunk0=0x2d10e000
obj0=0x79b62f8ff000
obj0 flags=0x400081 internal=0 class=0x2b1dd8c0 name_index=2866 name_number=0 outer=(nil)
obj0 name ... header=0x1664 string="/Script/CoreUObject"
class0 flags=0xc7 internal=516 class=0x2b1dda80 name_index=207 name_number=0 outer=0x79b62f8ff000
class0 name ... header=0x19e string="Package"
```

The FName headers match `index * 2`:

- `2866 * 2 = 0x1664`
- `207 * 2 = 0x19e`

This confirms that at least the first object item points to a plausible `UObjectBase`, and
the object's name and class name resolve through the same FName table previously validated
from the core.

## Result

`0x595b7e0` is promoted to `GUObjectArray research-candidate` for this ARK binary hash.
It is not yet a stable runtime offset.

The current best model from this core is:

- `GUObjectArray`-shaped root/struct: `0x595b7e0`
- chunk pointer field: `0x595b7f0`
- count-like field: `0x595b804`
- serial-like field: `0x595b838`
- first chunk: `0x2d10e000`

## Rejected Paths

- Do not continue treating chat UObject globals as direct GNames roots.
- Do not promote `0x5956f30` as a stable runtime slot from one core session. A later
  post-start debug-control probe rejected it with `table=0x13733660` and
  `implausible_num_elements`.
- Do not extend bootstrap sleeps as the main research strategy.

## Risks

- GDB warned that the currently installed `libobelisk.so` build id does not match the core.
  The ARK binary hash still matches the target executable, and this evidence reads ARK/core
  data, not Obelisk symbols.
- This validates item 0 only. Promotion beyond `research-candidate` requires validating
  multiple object indices, class/outer relationships, and static xrefs.
- `0x595b7e0` is binary-hash-specific evidence.

## Next Steps

1. Extend core tooling to validate several `FUObjectItem` indices from a candidate
   `GUObjectArray`.
2. Resolve each object's `NamePrivate` through the confirmed FName table.
3. Check that `InternalIndex` matches the array index for sampled objects.
4. Check that `ClassPrivate` and non-null `OuterPrivate` are plausible UObjects or appear
   in the object array.
5. Search static xrefs around the candidate to identify initialization and access paths.
6. After object enumeration works offline, enumerate `UClass`/`UFunction` candidates and
   only then return to chat command interception through reflected params.
