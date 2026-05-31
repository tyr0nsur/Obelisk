# Dino Scalar-Only Policy Planning

## Purpose

Plan the next internal copied-data lane after Mission for the compact Dino target pair.
This note is planning-only. It does not authorize server access, runtime observation,
hook wiring, public SDK work, ABI changes, mutation, return overrides, identity exposure,
or compatibility claims.

Scope is limited to scalar-only owned copies from the compact Dino evidence already
recorded in `2026-05-29-dino-compact-second-source-readiness.md`.

## Candidate Lane

Internal target family:

```text
PrimalDinoCharacter.AddPassenger
PrimalDinoCharacter.AllowCarryCharacter
```

Copied scalar candidates:

```text
AddPassenger.PassengerSeatIndex -> int32 copied value
AddPassenger.bForcePassenger -> bool copied value
AddPassenger.bAllowFlyersAndWaterDinos -> bool copied value
AddPassenger.bSkipLineTrace -> bool copied value
AddPassenger.ReturnValue -> bool copied value, only if post-call capture is separately approved
AllowCarryCharacter.ReturnValue -> bool copied value, only if post-call capture is separately approved
```

The first lane should prefer pre-call scalar inputs only. Return values require a separate
capture timing decision because they are output semantics, not passive input metadata.

## Redacted References

The following object references are recognition-only and must not be copied, logged, used
as identity, or exposed through plugin callbacks:

```text
AddPassenger.ACharacter
AllowCarryCharacter.CanCarryPawn
```

Redaction expectation:

- use object properties only to prove the exact reflected shape;
- do not persist raw pointers, `InternalIndex`, FName indices, GObjects indices, names,
  actor labels, rider/player/dino identity, resource handles, or lookup keys;
- fail closed if exact metadata recognition depends on an unreadable, missing, or
  implausible object field.

## Blockers

Do not promote beyond planning until these are resolved:

- exact recognizer tests cover accepted shapes and near-name/property collision rejects;
- copied-data builder tests prove all exported fields are Obelisk-owned scalars;
- redaction tests prove object fields cannot leave the recognizer boundary;
- dispatcher ownership and callback lifecycle are reviewed for a Dino-internal event
  family;
- observer-profile, supported-SHA, budget, and instance-marker gates exist for any later
  runtime observation;
- operator rollback and no-mutation posture are documented for the separately approved
  observation run.

## Consume Expectations

Internal consumers may only consume immutable scalar snapshots. They must treat absent
fields, unsupported hashes, unrecognized metadata, redacted object fields, and missing
post-call return capture as non-events.

Consumers must not infer dino identity, rider/passenger identity, tame state, carry
permission policy, server compatibility, or gameplay outcome from this lane. The lane is
metadata copied from a narrow reflected function shape, not a public behavior contract.

## Promotion Expectations

Promotion can be considered only after a follow-up note or patch demonstrates:

- exact compact target recognition from reflected metadata;
- synthetic fixture coverage for positive and negative cases;
- scalar-only copy ownership with object redaction enforced by tests;
- no public Dino SDK, public C ABI, public capability bit, public resource kind, or
  installed SDK consumer change;
- no mutation, return override, UE function call, broad scan, or identity lookup;
- separately approved runtime validation plan if observation becomes necessary.

Until those gates pass, Dino remains an internal copied-data planning lane behind Mission,
not an externally consumable module surface.
