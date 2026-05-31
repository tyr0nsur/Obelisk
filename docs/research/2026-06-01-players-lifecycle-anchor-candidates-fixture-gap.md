# Players Lifecycle Anchor Candidates Fixture Gap

Date: 2026-06-01

## Summary

`players-lifecycle-anchor-candidates` is reproducible offline for all six planning-only
targets across the two player-identity offline cores. The fixture gap identified during
the first pass has now been closed by adding all six base snapshots under
`tests/fixtures/ufunction_snapshots/7e7ded49e0c6/players_lifecycle/` and recording them
in `tests/fixtures/ufunction_snapshots/manifest.json`.

This remains candidate-only layout evidence. It does not claim login/logout runtime order,
stable player identity, public Player SDK readiness, object identity, lookup,
`ResourceHandle`, mutation, return override, runtime hooks, or release readiness.

## Fixture And Snapshot Coverage

Committed fixtures under `tests/fixtures/ufunction_snapshots`:

- `players_lifecycle/GameMode.K2_PostLogin.snapshot.json`
- `players_lifecycle/ShooterGameMode.CheckJoinInProgress.snapshot.json`
- `players_lifecycle/ShooterGameMode.HandleNewPlayer.snapshot.json`
- `players_lifecycle/ShooterGameMode.OnLogout.snapshot.json`
- `players_lifecycle/ShooterGameMode.OnPostLogin__DelegateSignature.snapshot.json`
- `players_lifecycle/ShooterGameMode.OnStartNewPlayer__DelegateSignature.snapshot.json`

Existing offline snapshots before this pass:

- `/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/lifecycle-anchor-snapshots/ShooterGameMode.HandleNewPlayer.snapshot.json`
- `/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/lifecycle-anchor-snapshots/ShooterGameMode.OnLogout.snapshot.json`
- `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/lifecycle-anchor-snapshots/ShooterGameMode.HandleNewPlayer.snapshot.json`
- `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/lifecycle-anchor-snapshots/ShooterGameMode.OnLogout.snapshot.json`

New scratch snapshots generated in this pass:

- `/tmp/obelisk-lifecycle-snapshot-probe/base/*.snapshot.json`
- `/tmp/obelisk-lifecycle-snapshot-probe/vanilla/*.snapshot.json`

The regenerated `HandleNewPlayer` and `OnLogout` scratch snapshots are byte-identical to
the existing offline lifecycle-anchor snapshots in both roots.

## Offline Evidence Inputs

Both roots use the same ARK binary:

- `ark_binary_sha256`: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- `fname_root_slot`: `0x5956f30`
- `gobjects`: `0x595b7e0`

Base identity core:

- Path: `/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/raw/core`
- `artifact_sha256`: `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`
- `capture_id`: `base-identity-core`
- `evidence_pack_id`: `player-identity-base-core-evidence-pack`
- `obelisk_commit`: `e55b75c`

Vanilla GDB core:

- Path: `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/raw/core`
- `artifact_sha256`: `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- `capture_id`: `vanilla-gdb-core`
- `evidence_pack_id`: `player-identity-vanilla-gdb-core-evidence-pack`
- `obelisk_commit`: `e55b75c`

## Layouts Observed

- `GameMode.K2_PostLogin`: `ParmsSize=8`, `NumParms=1`, `NewPlayer:ObjectProperty@0/8`.
- `ShooterGameMode.CheckJoinInProgress`: `ParmsSize=17`, `NumParms=3`,
  `bIsFromLogin:BoolProperty@0/1`, `NewPlayer:ObjectProperty@8/8`,
  `ReturnValue:BoolProperty@16/1`.
- `ShooterGameMode.HandleNewPlayer`: `ParmsSize=26`, `NumParms=5`,
  `NewPlayer:ObjectProperty@0/8`, `PlayerData:ObjectProperty@8/8`,
  `PlayerCharacter:ObjectProperty@16/8`, `bIsFromLogin:BoolProperty@24/1`,
  `ReturnValue:BoolProperty@25/1`.
- `ShooterGameMode.OnLogout`: `ParmsSize=8`, `NumParms=1`, `Exiting:ObjectProperty@0/8`.
- `ShooterGameMode.OnPostLogin__DelegateSignature`: `ParmsSize=8`, `NumParms=1`,
  `NewPlayer:ObjectProperty@0/8`.
- `ShooterGameMode.OnStartNewPlayer__DelegateSignature`: `ParmsSize=8`, `NumParms=1`,
  `NewPlayer:ObjectProperty@0/8`.

The two `BoolProperty` return/login fields observed here have canonical
`byte_mask=0x1`, `field_mask=0xff`, and `native_bool=false` in the base scratch snapshots.

## Comparison Results

Scratch base versus scratch vanilla:

- `scripts/compare_reflection_snapshots.py --base-root /tmp/obelisk-lifecycle-snapshot-probe/base --candidate-root /tmp/obelisk-lifecycle-snapshot-probe/vanilla --target-set players-lifecycle-anchor-candidates --json`
- Result: `accepted=6`, `inconclusive=0`, `rejected=0`.
- Output hash: `11974bcb4ef3fc1707a53d931e93b61f000e372db826468d13859547c151e352`
  for `/tmp/obelisk-lifecycle-snapshot-probe/all-six-compare.json`.

Scratch readiness report:

- `scripts/compare_reflection_snapshots.py --base-root /tmp/obelisk-lifecycle-snapshot-probe/base --candidate-root /tmp/obelisk-lifecycle-snapshot-probe/vanilla --target-set players-lifecycle-anchor-candidates --readiness-report --json`
- Result totals: `targets=6`, `comparable=6`, `second_source_accepted=6`, `blocked=0`.
- Output hash: `a4baa4822c8811759eab068447e4f1ee01285383025e6f7429017a01ede70d6c`
  for `/tmp/obelisk-lifecycle-snapshot-probe/all-six-readiness.json`.

Promotion-mode check:

- `scripts/compare_reflection_snapshots.py --base-root /tmp/obelisk-lifecycle-snapshot-probe/base --candidate-root /tmp/obelisk-lifecycle-snapshot-probe/vanilla --target-set players-lifecycle-anchor-candidates --readiness-report --fail-on-readiness-gaps --json`
- Exit: `1`.
- Expected blocker: `target_set_not_release_readiness`.
- Gate state: `layout_ready=true`, `promotion_ready=false`, `ready_scope=planning_only`.

Committed fixture readiness remains blocked:

- `scripts/compare_reflection_snapshots.py --base-root tests/fixtures/ufunction_snapshots --candidate-root /tmp/obelisk-lifecycle-snapshot-probe/vanilla --readiness-report --target-set players-lifecycle-anchor-candidates --json`
- First-pass result before fixture incorporation: `targets=6`, `blocked=6`, `comparable=0`,
  with blocker `missing_base_snapshot=6`.

After fixture incorporation:

- Direct compare against `/tmp/obelisk-lifecycle-snapshot-probe/vanilla`: `accepted=6`,
  `inconclusive=0`, `rejected=0`.
- Planning-layout intake readiness: `planning_layout_gate.ready=true`,
  `ready_scope=planning_only`.
- Promotion/readiness gate with `--fail-on-readiness-gaps`: expected exit `1` with
  `promotion_gate.ready=false` and blocker `target_set_not_release_readiness`.

## Incorporation

The six base snapshots were committed as fixture inputs only. They are useful for local
planning-layout comparisons and for consuming lifecycle-anchor candidate artifacts. They
must not be cited as second-source evidence by themselves and must not be used to promote
public player identity, runtime lifecycle ordering, lookup, `ResourceHandle`, mutation, or
return override. If this route needs to be regenerated for a new ARK binary hash, reuse
the exact offline recipe above and compare against a distinct second-source root before
updating fixture metadata.

## Checker Fixture Audit

The lifecycle-anchor candidate checker now has an explicit accepted-manifest helper for
the two reviewed lifecycle layout anchors:

- `ShooterGameMode.HandleNewPlayer` as `session_start`
- `ShooterGameMode.OnLogout` as `session_end`

The helper keeps the artifact `candidate_only`, marks promotion, public SDK, and runtime
readiness false, and leaves principal invalidation semantics unresolved. Object fields
remain `recognition_only`; scalar bools remain copied-candidate planning fields only.

Targeted checker coverage consumes this manifest successfully, reports the accepted start
and end targets, and verifies that `--promote` blocks on unresolved principal invalidation
semantics plus the candidate-only gate while keeping public/runtime readiness false. This
does not promote public player identity, UE pointer exposure, lookup, `ResourceHandle`,
mutation, return override, or any runtime ordering claim.
