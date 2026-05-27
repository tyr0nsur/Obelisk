# UFunction Membership Back-References

## Objective

Strengthen offline `UObject`/`UFunction`/`UProperty` validation so readable memory is not
accepted merely because it has plausible FName-backed fields.

## Environment

- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- FName root slot in this core: `0x5956f30 -> 0x2ae5c660`
- `GUObjectArray` research-candidate: `0x595b7e0`

## Change

`scripts/inspect_core_ufunctions.py` now validates membership without broad scans:

1. Read the candidate `UObjectBase.InternalIndex`.
2. Confirm the index is in bounds for the current `GObjects` count.
3. Read exactly `GObjects[InternalIndex]`.
4. Require the slot to point back to the candidate object.

The same check is applied to:

- inspected target objects;
- target `ClassPrivate`;
- target `OuterPrivate`;
- every property object in a `UStruct.Children` chain;
- each property's `ClassPrivate` and `OuterPrivate`.

The JSON and text output now expose membership fields such as `object_membership_status`,
`class_membership_status`, `outer_membership_status`, and per-property
`membership_status`/`class_membership_status`/`outer_membership_status`.

## Evidence

Command:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --index 25447 --index 26281 \
  --window-size 0xc0 \
  --max-object-scan 30000 \
  --json
```

Observed summary:

```text
ServerChat candidate candidate-uobject 25447 candidate-uobject 518 candidate-uobject 400
  prop MessageText candidate-uobject 25448 candidate-uobject 547 candidate-uobject 25447
SendServerChatMessage candidate candidate-uobject 26281 candidate-uobject 518 candidate-uobject 411
  prop MessageText candidate-uobject 26286 candidate-uobject 547 candidate-uobject 26281
  prop MessageColor candidate-uobject 26285 candidate-uobject 548 candidate-uobject 26281
  prop bIsBold candidate-uobject 26284 candidate-uobject 532 candidate-uobject 26281
  prop ReceiverTeamId candidate-uobject 26283 candidate-uobject 539 candidate-uobject 26281
  prop ReceiverPlayerID candidate-uobject 26282 candidate-uobject 539 candidate-uobject 26281
```

This confirms that the inspected functions and their properties are not just readable
memory windows: their object, class, and outer pointers round-trip through the current
`GObjects` candidate.

## Result

Offline `UFunction` property-chain evidence is stronger for this core and binary hash.
This still does not promote a public SDK contract or a runtime-stable offset.

## Risks

- The evidence still depends on one core and one ARK binary hash.
- This check confirms object-array membership, not object lifetime safety in a running
  server.
- A second isolated core is still required before promotion beyond candidate-only evidence.

## Next Steps

1. Keep runtime chat recognition gated to exact validated metadata.
2. Repeat `GObjects -> UObject -> UFunction -> property chain` inspection on a second
   isolated core.
3. Continue static classification of `0x595b7e0` init/reset/destructor/lookup anchors.
