# SDK Offline Start/End Noncompletion Hardening

## Objective

Close the remaining offline false-positive route where a clean `session_start` plus
matched `session_end` could be mistaken for the approved three-role runtime lifecycle
evidence bundle.

## Environment

- Date: 2026-06-08 11:13 CEST
- Scope: offline repo tests and checkers only
- Live/server operations: none
- Discord/RCON/GitHub/release operations: none
- Active SDK status before and after: `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`

## Evidence

- C++ observer budget now has a regression proving `HandleNewPlayer(1,1)` plus
  `OnLogout` reserves only role bits `session_start|session_end`; it does not infer the
  missing `session_start_rejected` bit and is distinguishable from the full triplet.
- C++ applicator budget now has a matched-correlation regression proving a valid start and
  matched logout can be individually loggable while still remaining incomplete without the
  exact `ShooterGameMode.CheckJoinInProgress(1,0)` rejected-start sibling.
- The start/end evidence checker now emits explicit zero-credit/non-replacement flags and
  rejects nested overclaims that try to mark start/end-only evidence as approved runtime,
  SDK/P0, public, runtime, or exact-triplet replacement evidence.
- The runtime evidence status reporter now classifies start/end-only, diagnostic triplets,
  beta notices, request/window artifacts, and copied-log presence as non-evidence until
  the approved bundle checker accepts the exact copied sibling set.
- Player identity promotion certificate and post-runtime bridge now require the reviewed
  identity public contract decision record to be hash-bound to the same approved runtime
  evidence binding and reject stale runtime pairing or digest drift.

## Agent Results

- Euler: read-only C++ audit identified missing start+end noncompletion regressions.
- Curie: implemented start/end checker non-counting and overclaim tests.
- Confucius: implemented runtime-binding digest checks for identity promotion certificate
  and post-runtime bridge.
- Mencius: implemented runtime evidence status non-evidence classes and sibling-set gate
  metadata.
- Kepler and Lovelace: closed by lead while still running; no changes integrated.

## Validation

- `cmake --build build --target player_principal_lifecycle_applicator_tests process_event_player_principal_lifecycle_observer_tests -j 2`
- `ctest --test-dir build -R 'PlayerPrincipalLifecycleApplicatorTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure`: 2/2 passed
- `python3 -m unittest scripts/test_check_player_identity_runtime_principal_start_end_evidence.py`: 12 OK
- `python3 -m unittest scripts/test_report_player_principal_lifecycle_runtime_evidence_status.py`: 37 OK
- `python3 -m unittest scripts.test_build_player_identity_promotion_certificate scripts.test_build_player_identity_post_runtime_bridge`: 14 OK
- `python3 -m unittest scripts/test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py`: 197 OK
- Focused `git diff --check` for touched C++/Python paths passed
- `python3 scripts/report_obelisk_sdk_status.py --compact` remained blocked with
  `source overclaims: total=0`

## Result

Confirmed: start+end-only runtime material can be accepted only as narrow, non-counting
context. It does not clear `approved_runtime_evidence_missing`, does not satisfy runtime
readiness, does not advance SDK/P0, and cannot replace the exact same-run copied sibling
set containing `session_start`, `CheckJoinInProgress(1,0)` `session_start_rejected`, and
matched `session_end`.

## Next Steps

- Keep preparing offline gates and post-runtime contract tooling.
- When beta/runtime evidence is available, capture/copy/check the full sibling set before
  changing any SDK/P0 accounting.
