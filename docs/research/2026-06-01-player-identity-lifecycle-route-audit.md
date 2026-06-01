# Player Identity Lifecycle Route Audit

Date: 2026-06-01

## Scope

This is a read-only/offline audit of the current player identity lifecycle route. It
summarizes what existing docs and scripts already accept for the narrow
`ShooterGameMode.HandleNewPlayer` / `ShooterGameMode.OnLogout` route, and what is still
missing before runtime capture can satisfy the player-principal blocker.

This note does not authorize server access, marker/env changes, restarts, runtime
capture, scanners, debug attachment, `ptrace`, `gcore`, broad `ProcessEvent` tracing,
Discord/community notices, Git actions, public SDK work, lookup, `ResourceHandle`,
mutation, return override, or release claims.

## Inputs Reviewed

- `docs/agent-handoff/CURRENT.md`
- `docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md`
- `docs/research/2026-06-01-player-principal-runtime-capture-plan.md`
- `docs/research/2026-06-01-player-principal-runtime-observer-brief.md`
- `docs/research/2026-06-01-player-principal-policy-route.md`
- `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`
- `docs/research/2026-05-31-player-identity-first-evidence.md`
- `docs/research/2026-05-30-player-identity-lifecycle-plan.md`
- `scripts/reflection_target_sets.py`
- `scripts/check_player_identity_first_evidence_readiness.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_evidence.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
- `scripts/analyze_runtime_observer_log.py`
- `scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py`
- `scripts/check_player_principal_lifecycle_preflight.sh`

## Accepted Route

The accepted route is narrow and already documented:

```text
reviewed FName root 0x5956f30
-> reviewed GObjects candidate 0x595b7e0
-> complete player identity reflection inventory
-> focal HandleNewPlayer / OnLogout snapshots
-> candidate-only lifecycle anchor and principal policy manifests
-> approved private runtime consume-only observer evidence
-> later, separate public ABI and promotion review
```

For the current reviewed ARK Linux binary SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, existing notes
accept the FName root and GObjects candidate as reusable offline reflection inputs only.
They are not public object identity, runtime-stable public GObjects, lookup, or
`ResourceHandle`.

`players-identity-lifecycle-intake` remains a 12-target planning-only intake set.
`players-lifecycle-anchor-candidates` is also planning-only and contains six lifecycle
candidate targets. Of those six, only these two are accepted as the first narrow runtime
ordering candidates:

- `ShooterGameMode.HandleNewPlayer`
- `ShooterGameMode.OnLogout`

The accepted focal shapes are exact:

- `ShooterGameMode.HandleNewPlayer`: `ParmsSize=26`, `NumParms=5`,
  `NewPlayer:ObjectProperty@0/8`, `PlayerData:ObjectProperty@8/8`,
  `PlayerCharacter:ObjectProperty@16/8`, `bIsFromLogin:BoolProperty@24/1`,
  `ReturnValue:BoolProperty@25/1`.
- `ShooterGameMode.OnLogout`: `ParmsSize=8`, `NumParms=1`,
  `Exiting:ObjectProperty@0/8`.

Offline fixture/layout evidence is accepted as candidate-only planning evidence.
`HandleNewPlayer` may become a private candidate start observation only after original
`ProcessEvent` returns and copied bool bytes are canonical
`bIsFromLogin=1,ReturnValue=1`. Other canonical bool combinations are rejected starts
with `principal_action=none`. Non-canonical bool bytes reject the record.

`OnLogout` is only an invalidation-shaped private event. It does not prove complete
logout ordering, reconnect behavior, transfer/download behavior, controller replacement,
or public principal invalidation semantics by itself.

## Existing Checker Route

The current scripts already encode the split between shape-only fixtures, approved
runtime evidence, and later public-contract work:

- `check_player_identity_runtime_principal_lifecycle_evidence.py` accepts only
  synthetic/redacted shape fixtures and keeps `approved_runtime_evidence_present=false`.
  Its next blocker remains `approved_runtime_evidence_missing`.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` validates the
  future secret-free observer window manifest and copied-log path/SHA posture. It is not
  evidence by itself.
- `analyze_runtime_observer_log.py` accepts only the private
  `player_principal_lifecycle` observer grammar for `HandleNewPlayer` and `OnLogout`.
- `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py` wires copied log
  analysis, window-manifest checking, approved manifest building, and the approved
  evidence checker.
- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py` can accept a
  reviewed copied runtime summary only as `runtime_evidence_only`; even then it keeps
  `promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`, with the
  next blocker becoming `identity_public_contract_gate_missing`.
- `check_player_identity_first_evidence_readiness.py` now treats accepted offline layout
  and principal policy as sufficient to stop more offline discovery, but still blocks on
  `approved_runtime_evidence_missing` until approved runtime evidence is supplied.

The approved-evidence checker also requires the three runtime cases to appear in the
documented lifecycle order:

```text
session_start -> session_start_rejected -> session_end
```

A bundle with the right shapes but logout/invalidation before the start anchor is not
accepted lifecycle evidence.

## Missing Before Runtime Evidence Acceptance

The active blocker is exactly:

```text
approved_runtime_evidence_missing
```

The missing artifact is a future, current-turn operator-approved, bounded,
consume-only `PlayerPrincipalLifecycleObserver` window that produces all of the
following from copied offline evidence:

- one accepted observer enable line for `players-lifecycle-anchor-candidates`, binary
  SHA `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
  log limit `10`, dispatch limit `0`, `delivery_claim=none`, and
  `principal_claim=none`;
- one post-original `HandleNewPlayer` accepted `session_start` event with copied bools
  `bIsFromLogin,ReturnValue=1,1`, redacted object fields, and
  `principal_action=candidate_created`;
- one post-original `HandleNewPlayer` `session_start_rejected` event with copied bools
  `0,1`, redacted object fields, and `principal_action=none`;
- one post-original `OnLogout` `session_end` event with `Exiting` redacted and
  `principal_action=candidate_invalidated`;
- fail-closed consumer boundary cases for stale-after-logout and malformed/unsupported
  evidence;
- a checked window manifest whose copied log path and SHA match the copied offline log;
- a built approved-evidence manifest accepted in consume mode while promotion,
  public-readiness, and runtime-readiness modes still fail closed;
- rollback and stable-posture evidence for the same approved instance and map.

The copied evidence must not contain player names, Steam/EOS/platform ids, IP-like
values, tribe ids, transfer ids, saved-player identifiers, object names, class names,
UE pointers, raw params, raw buffers, FName indices, GObjects indices, `ResourceHandle`,
map locations, chat text, command text, permissions/admin state, plugin subscriber state,
or hashes of redacted identity values.

## Not Needed For This Blocker

Do not spend the next round on any of these for the current binary hash unless a reviewed
artifact contradicts the existing evidence:

- broad FName discovery;
- broad GObjects discovery;
- more core scans;
- admin/listing snapshot discovery;
- lifecycle layout rediscovery;
- Ghidra/radare orientation for this same blocker;
- `ResourceHandle` serial, flag, or object-lifetime promotion;
- public GObjects or object lookup promotion.

The current SDK blocker is not missing FName/GObjects evidence. It is the absence of an
approved copied runtime observer summary for the accepted `HandleNewPlayer`/`OnLogout`
route.

## Non-Claims

This audit does not promote public player identity, permissions/admin, commands/replies,
chat sender authentication, economy/storage, persistence, cross-instance identity,
lookup, `ResourceHandle`, public GObjects, UE pointer validity, mutation, return
override, plugin delivery, public SDK readiness, runtime readiness, or v1 completion.

Even after the approved runtime evidence blocker is cleared, the next gate is a separate
public identity contract review. Runtime evidence acceptance should change the blocker to
`identity_public_contract_gate_missing`, not to public identity readiness.
