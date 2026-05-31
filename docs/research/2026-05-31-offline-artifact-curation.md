# Offline Artifact Curation Snapshot

This note records the current non-protected artifact root triage for
`/home/flowcommunity-ark/obelisk-artifacts`. It is a routing aid only. It does not
promote public SDK APIs, runtime readiness, object identity, lookup, mutation, return
override, `ResourceHandle`, player identity, or cross-binary support.

Commands run:

```bash
for p in /home/flowcommunity-ark/obelisk-artifacts/*/artifact-pack.manifest.json; do
  python3 scripts/normalize_artifact_pack.py --check --json "$(dirname "$p")"
done

python3 scripts/check_reflection_inventory_pack_readiness.py \
  --root /home/flowcommunity-ark/obelisk-artifacts
```

## Current Routing

Primary current planning inputs:

- item return-only: `item-return-only-second-source-20260530T084918Z`;
- Mission copied bool: `mission-copied-bool-tail-policy-slice-20260530T090211Z`;
- Structure planning: `structure-aggregate-census-policy-slice-20260531T034715Z`
  and `structure-return-only-policy-slice-20260530T093002Z`;
- Transfer planning: `transfer-baccept-only-policy-slice-20260530T073308Z` and
  `transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack`;
- ResourceHandle/UObject blocker context only:
  `resourcehandle-identity-complete-failclosed-20260530T165521Z`,
  `resourcehandle-post-callback-contract-20260530T171910Z`,
  `resourcehandle-serial-policy-20260530T190642Z`,
  `uobject-4000-set-call-clear-20260530T000000Z`, and
  `uobject-flag-policy-refresh-20260530T071436Z`.

| Artifact root | Schema/status | Current use | Non-claims |
| --- | --- | --- | --- |
| `item-return-only-policy-slice-20260530T072255Z` | normalized artifact pack, check OK | Item return-only copied `ReturnValue` policy evidence. | No Items SDK, Inventory SDK, identity, mutation, or return override. |
| `item-return-only-second-source-20260530T084918Z` | normalized artifact pack, check OK | Second-source companion for item return-only evidence. | No public item/inventory module promotion. |
| `mission-copied-bool-policy-slice-20260530T072912Z` | normalized artifact pack, check OK | Internal Mission copied-bool planning evidence. | No public Mission SDK, arrays, identity, mutation, runtime hook, or return override. |
| `mission-copied-bool-tail-policy-slice-20260530T090211Z` | normalized artifact pack, check OK | Mission bool-tail metadata planning evidence. | No public Mission SDK or runtime dispatch. |
| `structure-aggregate-census-policy-slice-20260531T034715Z` | normalized artifact pack, check OK | Structure aggregate/census planning evidence. | No StructureEvents SDK, structure identity, mutation, runtime validation, or public census API. |
| `structure-return-only-policy-slice-20260530T093002Z` | normalized artifact pack, check OK | Structure return-only planning evidence. | No build-policy SDK, return override authority, mutation, or runtime validation. |
| `transfer-baccept-only-policy-slice-20260530T073308Z` | normalized artifact pack, check OK | Transfer `bAccept` internal bool-layout fixture. | No Transfer SDK, payload identity, cross-map semantics, or public API. |

## Legacy Or Blocked Roots

These roots exist in the artifact directory, but the current normalizer/check path rejects
them or treats them as legacy/candidate-blocked evidence:

- `minimal-second-source-intake-offline-20260530T075501Z`: legacy
  `obelisk.artifact-pack-manifest.v1` spelling; do not use as a current normalized pack
  without a deliberate migration note.
- `resource-handle-flag4000-reconciliation-primary-20260530T000000Z`: legacy
  `obelisk.artifact-pack-manifest.v1`; ResourceHandle remains blocked.
- `resource-handle-serial-scan-primary-20260530T000000Z`: legacy
  `obelisk.durable-artifact-pack.v1` and `candidate_blocked`; not public handle evidence.
- `structure-nonpin-copied-scalar-policy-slice-20260530T100717Z`: legacy
  `obelisk.artifact-pack-manifest.v1`; cite the dated research note instead of treating
  this as a current normalized pack.
- `uobject-4000-set-call-clear-20260530T000000Z`: legacy
  `obelisk.durable-artifact-pack.v1` and `candidate_blocked`; not public UObject
  identity evidence.
- `uobject-flag-policy-refresh-20260530T071436Z`: legacy
  `obelisk.artifact-pack-manifest.v1`; not public `ResourceHandle` or lookup evidence.
- `static-global-preflight-20260529`: static preflight manifest, not an artifact-pack
  container. It can guide static refresh work, but it is not a current normalized pack.
- `transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack`: nested
  ScriptStruct inventory pack; useful only within its documented internal-layout scope.
- `resourcehandle-identity-complete-failclosed-20260530T165521Z`: aggregated
  ResourceHandle blocker reports without a root artifact-pack container; useful for
  blocker context only.
- `resourcehandle-post-callback-contract-20260530T171910Z`: internal rejection-contract
  candidate; it does not unlock post-callback lookup.
- `resourcehandle-serial-policy-20260530T190642Z`: candidate policy note; it does not
  prove runtime serial reuse or wraparound safety.
- `offline-binaries`: copied binary storage for reproducibility only; it is not evidence
  by itself.

Known caution: `structure-nonpin-copied-scalar-policy-slice-20260530T100717Z` contains
legacy schema state and invalid or empty gate JSON outputs in this snapshot. Cite the
dated research note or regenerate a current normalized pack before using it as current
accepted evidence.

## Player Identity Status

Current readiness preflight found no accepted `obelisk.reflection-inventory-pack.v1`
under the artifact root:

- `status=blocked`;
- `accepted_pack=null`;
- `reason=missing_reflection_inventory_pack`;
- `reason=schema_mismatch`;
- required targets remain `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`.

Do not use the normalized artifact packs above as substitutes for player-identity
reflection inventory coverage. The next identity step still requires a non-protected
UFunction reflection inventory pack that explicitly records
`players-identity-lifecycle-intake` coverage.
