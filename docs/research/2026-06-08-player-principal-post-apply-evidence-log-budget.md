# Player Principal Approved Evidence Log Budget

Date: 2026-06-08 08:09 CEST

## Summary

The approved runtime player-principal lifecycle observer must not spend the bounded
approved-evidence log budget when it only sees a canonical function shape. The budget is
now reserved after the copied observation has been applied to the principal registry and
the final apply/correlation status is known.

This fixes a runtime-window false-negative risk: an unrelated canonical `OnLogout` could
previously reserve the single `session_end` approved-evidence role before correlation
proved that it matched the started beta-player principal. The later matched logout could
then be suppressed, leaving the copied log without the checker-required triplet.

## Durable Facts

- `ProcessEventPlayerPrincipalLifecycleObserver::TryObserveInvocation` leaves
  `observationNumber=0` for approved-runtime evidence mode until the hook applies the
  copied observation.
- `ProcessEventPlayerPrincipalLifecycleApplicator::IsApprovedRuntimeEvidenceLoggableApplyResult`
  permits approved evidence logging only for:
  - `session_start_created`,
  - `session_start_rejected_noop`,
  - `session_end_invalidated` with a valid resolved logout correlation.
- A canonical but unmatched `OnLogout` remains observable/applicable state, but it is not
  approved runtime evidence and must not reserve the `session_end` log slot.
- The strict route is unchanged: accepted evidence still requires one copied sibling-set
  triplet with `HandleNewPlayer(1,1)`, exact `CheckJoinInProgress(1,0)`, and matched
  `OnLogout`.

## Offline SDK Guardrails Added In Same Checkpoint

- Public SDK completion now strips the surface-specific promotion certificate key when
  hashing an active promoted surface record, so downstream self-bound certificates do not
  fail only because their own binding is attached.
- Player-identity promotion certificates are now required by completion to carry the same
  reviewed-surface hash policy fields already emitted by the real builder.
- Permissions/admin and command/chat-response public-header scans now include the same
  future ABI/capability aliases guarded by the C ABI layout tests.

## Validation

- `cmake --build build -j$(nproc)`
- `ctest --test-dir build -R 'PlayerPrincipalLifecycleApplicatorTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure`
- `python3 -m unittest scripts.test_check_command_permission_route_gate`
- `python3 -m unittest scripts.test_build_command_chat_response_promotion_certificate scripts.test_check_command_chat_response_public_readiness`
- `python3 -m unittest scripts.test_check_permissions_admin_public_readiness`
- `python3 -m unittest scripts.test_report_obelisk_sdk_status`
- `python3 -m unittest scripts.test_check_public_sdk_v1_completion` (`340 OK`)
- `python3 scripts/report_obelisk_sdk_status.py --compact`

The compact status remains strict: `approved_runtime_evidence_missing`, SDK `0/12`, P0
`0/4`, runtime/public/stable false, approved runtime evidence false, source overclaims
`0`.

No live server, RCON, Discord, deploy, marker/env, GitHub, tag, or release operation was
run in this checkpoint.

## Next Step

Use the next approved runtime window to capture a copied sibling-set log after this
post-apply reservation fix is deployed. The fastest valid unblock remains a
checker-accepted approved runtime principal lifecycle evidence bundle.
