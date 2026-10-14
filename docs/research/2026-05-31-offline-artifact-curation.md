# Offline Artifact Curation Snapshot

Current status: superseded for artifact-root inventory by
`docs/research/2026-05-31-offline-artifact-inventory-audit.md`. This note remains the
planning-only target-set boundary and curation snapshot.

This note records the current non-protected artifact root triage for
`/home/flowcommunity-ark/obelisk-artifacts`. It is a routing aid only. It does not
promote public SDK APIs, runtime readiness, object identity, lookup, mutation, return
override, `ResourceHandle`, player identity, or cross-binary support.

Commands run:

```bash
find /home/flowcommunity-ark/obelisk-artifacts -name artifact-pack.manifest.json -print |
while IFS= read -r p; do
  python3 scripts/normalize_artifact_pack.py --check --json "$(dirname "$p")"
done

python3 scripts/check_reflection_inventory_pack_readiness.py \
  --root /home/flowcommunity-ark/obelisk-artifacts
```

## Current Routing

Planning-only target-set artifact packs are consume-mode planning evidence only. The
planning-only target sets are `command-chat-response-route-planning`,
`mission-copied-bool-policy-slice`, `players-identity-lifecycle-intake`,
`players-lifecycle-anchor-candidates`, `structure-aggregate-census-planning`, and
`structure-build-policy-offline-intake`; their packs, container manifests, and child
evidence must not be cited as release-readiness roots, public SDK promotion evidence, or
`v1.0` completion signals. The
`inventory-custom-filter-array-boundary` target set is also planning-only and does not
promote Inventory SDK, mutation, public ABI, release readiness, or `v1.0` completion. The
`players-lifecycle-anchor-candidates` target set is layout-planning only and carries no
runtime lifecycle ordering claim. The `structure-build-policy-offline-intake` target set
has accepted planning-layout second-source accounting through the pinned offline intake
checker, but remains planning-only: no public SDK, runtime hook, mutation, enforcement,
return override, identity, lookup, release readiness, or v1 completion claim.

Primary current planning inputs:

- minimal redacted signatures:
  `rc-minimal-redacted-signatures-strict-20260530T000000Z`;
- item return-only: `item-return-only-second-source-20260530T084918Z` and
  `item-return-only-bool-tail-refresh-20260530T172552Z`;
- Mission copied bool: `mission-copied-bool-tail-policy-slice-20260530T090211Z`;
- Structure planning: `structure-aggregate-census-policy-slice-20260531T034715Z`
  and `structure-return-only-policy-slice-20260530T093002Z`;
- Structure build-policy planning: no current accepted artifact pack for
  `structure-build-policy-offline-intake`;
- Transfer planning: `transfer-baccept-only-policy-slice-20260530T073308Z` and
  `transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack`;
- ResourceHandle/UObject blocker context only:
  `resourcehandle-identity-complete-failclosed-20260530T165521Z`,
  `resourcehandle-post-callback-contract-20260530T171910Z`,
  `resourcehandle-serial-policy-20260530T190642Z`,
  `uobject-4000-set-call-clear-20260530T000000Z`, and
  `uobject-flag-policy-refresh-20260530T071436Z`;
- richer ResourceHandle/UObject blocker context:
  `uobject-flag-policy-rich-inputs-20260530T071436Z`,
  `uobject-flag-sample-refresh-20260530T112500Z`,
  `uobject-flag-transition-matrix-20260529T154634Z`,
  `uobject-flag-100-clear-correlation-*`, `uobject-flag-semantic-*`, and
  `weak-helper-static-polarity-regenerated-20260529T180011Z`.

| Artifact root | Schema/status | Current use | Non-claims |
| --- | --- | --- | --- |
| `item-return-only-policy-slice-20260530T072255Z` | normalized artifact pack, check OK | Item return-only copied `ReturnValue` policy evidence. | No Items SDK, Inventory SDK, identity, mutation, or return override. |
| `item-return-only-second-source-20260530T084918Z` | normalized artifact pack, check OK | Second-source companion for item return-only evidence. | No public item/inventory module promotion. |
| `item-return-only-bool-tail-refresh-20260530T172552Z` | accepted consume gate, compare readiness layout-only | Item return-only bool-tail refresh input. | No public item/inventory module promotion or return override. |
| `mission-copied-bool-policy-slice-20260530T072912Z` | normalized artifact pack, check OK | Internal Mission copied-bool planning evidence. | No public Mission SDK, arrays, identity, mutation, runtime hook, or return override. |
| `mission-copied-bool-tail-policy-slice-20260530T090211Z` | normalized artifact pack, check OK | Mission bool-tail metadata planning evidence. | No public Mission SDK or runtime dispatch. |
| `rc-minimal-redacted-signatures-strict-20260530T000000Z` | accepted consume gate, strict redacted signatures | Minimal second-source intake signature coverage input. | No public SDK promotion, identity, mutation, or runtime hook. |
| `structure-aggregate-census-policy-slice-20260531T034715Z` | normalized artifact pack, check OK | Structure aggregate/census planning evidence. | No StructureEvents SDK, structure identity, mutation, runtime validation, or public census API. |
| `structure-return-only-policy-slice-20260530T093002Z` | normalized artifact pack, check OK; contains a zero-byte `normalize-artifact-pack.json` summary artifact | Structure return-only planning evidence. | No build-policy SDK, return override authority, mutation, or runtime validation. |
| `transfer-baccept-only-policy-slice-20260530T073308Z` | normalized artifact pack, check OK | Transfer `bAccept` internal bool-layout fixture. | No Transfer SDK, payload identity, cross-map semantics, or public API. |
| `transfer-scriptstruct-bool-tail-refresh-20260530T163945Z/inventory-pack` | nested ScriptStruct inventory pack | Internal ScriptStruct bool-tail input for transfer planning. | Not a UFunction reflection inventory pack; no Transfer SDK or public API. |

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

Known caution: some child manifests record provenance paths under
`/servidor/ark/workspace-offline`. That offline workspace is approved for captured
artifact provenance, but this curation note is about the local
`/home/flowcommunity-ark/obelisk-artifacts` root. Do not dereference protected server
paths during read-only artifact audits.

2026-06-06 gate hardening: a valid sidecar does not allow a generic JSON artifact with an
unknown schema through the consume gate. Sidecars and embedded provenance are checked for
protected-root strings and relative paths that resolve into the protected root. Candidate
ResourceHandle, GObjects, and weak-helper artifacts remain consume-valid only while they
avoid positive public/runtime aliases such as lookup availability, public identity,
mutation support, or return-override support. Named target-set coverage must match the
current `scripts/reflection_target_sets.py` revision hash, and duplicate or mismatched
manifest/direct target-set declarations are blockers rather than silently deduplicated.
Nested arrays/maps are part of that claim scan: unsupported child schemas and redacted
UFunction signature reports now emit explicit wording blockers for positive
`ResourceHandle`, lookup, public SDK, runtime hook, mutation, or return-override text.
Named redacted UFunction signature artifacts also inherit
`scripts/reflection_target_sets.py` catalog hygiene blockers, so duplicate catalog entries
or mixed UFunction/ScriptStruct target-set definitions cannot be hidden by deduped
coverage helpers. The artifact sidecar gate now scans provenance for positive
public/runtime/ResourceHandle/object-identity aliases, including underscore/camel-case
forms, while preserving blocked or planning-only ResourceHandle research wording.

2026-06-06 supervised offline alias follow-up: the shared target-set catalog alias guard
now also rejects `mutation`, `return_override`, and `stable_sdk` promotion surfaces,
including compact/camel-case spellings such as `ResourceHandle`, `ObjectLookup`,
`ReturnOverride`, and `StableSDK`. Redacted UFunction signature validation now scans
schema/provenance/catalog fields for those non-promoted aliases without treating ordinary
`v1` schema syntax or accepted planning target sets as promotion claims.

## Player Identity Status

Historical status, superseded by the source-bound planning manifests recorded in
`docs/research/player-identity-planning-sources/` and the route audit. Do not use this
section to rerun player-identity offline pack discovery or reopen closed fixture gaps; the
current blocker is `approved_runtime_evidence_missing`.

At the time of this curation pass, readiness preflight found no accepted
`obelisk.reflection-inventory-pack.v1` under the artifact root:

- `status=blocked`;
- `accepted_pack=null`;
- `reason=missing_reflection_inventory_pack`;
- `reason=artifact_pack_container_not_reflection_inventory` for normalized
  `artifact-pack.manifest.json` containers;
- `reason=scriptstruct_pack_not_reflection_inventory` for ScriptStruct inventory packs;
- `reason=schema_mismatch` for other non-reflection manifests when present;
- the required target set is `players-identity-lifecycle-intake` with 12 expected targets;
- historical snapshot gaps included `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`; those gaps are now closed by later
  source-bound planning manifests, and accepted planning anchors are
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`.

Do not use the normalized artifact packs above, their container manifests, or the nested
ScriptStruct inventory pack as substitutes for player-identity reflection inventory
coverage. The next identity step still requires a non-protected UFunction reflection
inventory pack with its own `manifest.json` that explicitly records
`players-identity-lifecycle-intake` coverage.
