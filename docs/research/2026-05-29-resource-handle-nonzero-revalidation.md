# ResourceHandle Nonzero Serial Revalidation

## Objective

Record the offline revalidation result for the
`resource-handle-nonzero-revalidation-20260529T060741Z` evidence pack and keep the
public `ResourceHandle` gate closed unless object validity semantics are proven.

## Environment

- Evidence source: approved offline workspace pack copy, identified by pack name above.
- Runtime posture: no live-server run, restart, marker change, or direct live path input.
- Scope: `FUObjectItem` serial-candidate revalidation and GObjects field coherence for
  the current ARK binary evidence chain.

## Hypothesis

Nonzero serial-backed `FUObjectItem` candidates can strengthen internal object-handle
evidence when they agree with coherent `GObjects` field access, but they do not prove safe
public identity handles without validated `UObject+0x8` lifetime/validity semantics.

## Evidence

- Revalidation accepted `32/32` sampled entries.
- All `32` accepted samples carried nonzero serial candidates.
- The sampled records were coherent with the accepted `GObjects` field interpretation,
  strengthening the internal field-window evidence.
- No contradictory sample in this pack resolves the remaining
  `uobject_flags_validity_semantics_unproven` blocker.

## Result

Confirmed as offline internal evidence: nonzero serial candidates are present across the
accepted sample set, and the `GObjects` coherent field interpretation is proven for this
pack.

Not promoted: public `ResourceHandle`, post-callback object identity, lifetime/reuse
semantics, mutation, and return overrides remain blocked by
`uobject_flags_validity_semantics_unproven`.

## Risks

- Nonzero serial agreement alone can still overstate handle safety if `UObject+0x8` flags
  include lifecycle states that invalidate an otherwise matching `{index, serial}` pair.
- Treat this pack as field and serial evidence only; do not expose it as a public SDK
  identity contract.

## Next Steps

- Resolve the named `UObject+0x8` validity and lifetime semantics before reconsidering
  public `ResourceHandle` promotion.
- Preserve future revalidation packs as offline evidence and keep live-server paths out of
  validator inputs.
