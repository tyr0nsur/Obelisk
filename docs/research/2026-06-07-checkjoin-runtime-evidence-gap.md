# CheckJoinInProgress Runtime Evidence Gap

Date: 2026-06-07

## Scope

This note began as a docs-only audit for the current `CheckJoinInProgress`
rejected-start gap. Later sections record both standing-authorized runtime follow-ups and
local offline code/tooling deltas made from that audit. The 2026-06-08 route-sampler,
02:15 planner/audit, and 02:19 drift-table guardrail follow-ups performed only local
code/tooling edits plus one 01:58 redacted process-list read to avoid stale handoff
state; they did not read live server logs, touch `/servidor/ark`, start or stop servers,
send Discord, deploy to servers, or mutate Git state.

It records non-authorizing research facts only. It does not claim approved runtime
evidence, runtime readiness, public SDK readiness, stable readiness, publication
authority, or progress against SDK/P0 counters.

## Audited Inputs

- `docs/research/2026-06-06-player-principal-lifecycle-evidence-feasibility.md`
  for the current operational digest, drift patch notes, and latest recorded runtime
  follow-up.
- `docs/research/player-identity-planning-sources/players-lifecycle-anchor-candidates-all-six-planning-gap.json`
  and
  `docs/research/player-identity-planning-sources/players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json`
  for planning-source boundaries and rejected FName-drift shortcuts.
- `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/players_lifecycle/ShooterGameMode.CheckJoinInProgress.snapshot.json`,
  `tests/fixtures/ufunction_snapshots/manifest.json`, and
  `tests/fixtures/ufunction_snapshots/README.md` for fixture shape and non-promotional
  lifecycle-root policy.
- `ue/PlayerPrincipalLifecycleReflection.cpp`,
  `hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp`,
  `hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp`, and
  `hooks/ProcessEventHook.cpp` for current reflection, copied-observer, applicator, and
  diagnostic split points.
- Python analyzer/bundle/checker tests and C++ lifecycle tests for accepted and rejected
  shapes. These were read as guardrail references only.

## Current Facts

- The committed `ShooterGameMode.CheckJoinInProgress` UFunction snapshot is
  candidate-only offline-core evidence for ARK binary SHA
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
  artifact SHA
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`,
  Obelisk commit `e55b75c`. Its shape is `ParmsSize=17`, `NumParms=3`,
  property order `bIsFromLogin`, `NewPlayer`, `ReturnValue`, and return offset `0x10`.
- The fixture policy treats `CheckJoinInProgress` only as the rejected-start observer
  triplet source. `HandleNewPlayer` and `OnLogout` are the static lifecycle anchor
  sources. `K2_PostLogin` and lifecycle delegate signatures remain chronology or
  guidance only.
- Current reflection code has a canonical `CheckJoinInProgress` spec and explicit
  observed Ragnarok drift alternatives for the three property names. These drift chains
  are recognizer inputs only; they are not second-source layout evidence or runtime
  evidence by themselves.
- The post-patch recognizer accepts the observed complete `CheckJoinInProgress` drift
  chains `{28512,28414,17719}` and `{28512,28414,17720}` for
  `bIsFromLogin`, `NewPlayer`, and `ReturnValue`, but only when the full target,
  outer, field order, classes, offsets, sizes, bool metadata, redaction, and copied bool
  gates also pass. Mixed canonical/observed chains and unapproved property names remain
  fail-closed.
- The runtime diagnostic patch changed rejected copied observations on accepted
  lifecycle targets to log as `reflection_status=matched copy_status=rejected` instead
  of implying a reflection/FName mismatch. This is clearer negative evidence only; it
  does not broaden accepted runtime evidence.
- The accepted copied observer event requires a post-original
  `ShooterGameMode.CheckJoinInProgress` line with role `session_start_rejected`,
  copied fields `bIsFromLogin,ReturnValue`, copied values `1,0`, redacted field
  `NewPlayer`, `principal_action=none`,
  `apply_status=session_start_rejected_noop`, and
  `correlation_status=not_applicable`.
- The diagnostic path is intentionally separate. A
  `PlayerPrincipalLifecycleDiagnostic candidate ... diagnostic_shape=CheckJoinInProgress`
  line can show that the recognizer saw a target shape, but it is logged with
  `copy_status=rejected` and `evidence_claim=none`; checker tests reject diagnostic
  candidate lines as substitutes for the accepted observer event.
- Applicator tests keep the `CheckJoinInProgress(1,0)` rejected-start path as a no-op
  for principal allocation: no registry change, no registry pointer exposure, and
  action `None`. Internal dispatch can carry the copied event view, but it still does
  not allocate a principal.
- Existing notes record observed lifecycle activity and diagnostic lines, including
  `CheckJoinInProgress(0,0)` diagnostic-only material and superseded
  `HandleNewPlayer(0,1)` rejected-start material. The required accepted fresh-window
  `session_start_rejected` event with target
  `ShooterGameMode.CheckJoinInProgress` and copied values `1,0` remains absent.
- Prior TheIsland material did emit an exact `CheckJoinInProgress(1,0)` line, but
  it is rejected because it was stale/order-mismatched against the required sibling-set
  runtime window. It is a useful stimulus clue only, not approved evidence.
- A prior Ragnarok fresh window emitted accepted start/end material, a duplicate
  start, diagnostic candidates, and `CheckJoinInProgress(0,0)`. That fresh window did
  not emit an accepted `CheckJoinInProgress(1,0)` observer event, so it also does not
  clear the checker route.
- The patched runtime was installed and exercised on TheIsland and Ragnarok in prior
  approved windows, but those windows still produced only stale/order-mismatched
  TheIsland `1,0` material or fresh Ragnarok start/end, duplicate-start, diagnostic,
  and `0,0` material. They did not produce a checker-accepted approved runtime
  principal lifecycle bundle.
- The strict route blocker remains `approved_runtime_evidence_missing`. Existing
  partial start/end material, passive summaries, diagnostic candidate lines, request
  packs, notice artifacts, status reports, and planning-source artifacts do not clear it.

## 2026-06-08 Offline Tooling Checkpoint

Lead integration round, 2026-06-08 `04:42 CEST`: six scoped agents completed and were
closed. The round did not touch live servers, `/servidor/ark`, RCON, Discord, markers,
env, deployment, GitHub, tags, or release refs.

The local SDK/evidence tooling now carries a stricter offline route toward the same
runtime blocker:

- `analyze_runtime_observer_log.py` emits
  `strict_lifecycle_triplet_candidate_summary` for exact copied triplet candidates. It
  requires `session_start`, exact
  `ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, matched
  `session_end`, no diagnostic/passive substitution, and keeps
  `approved_runtime_evidence=false`, `runtime_evidence_ready=false`, and
  approval authority `downstream_bundle_checker_only`.
- Status/runner tooling rejects stale/passive complete-role material and blocks checker
  or bundle actions unless the copied-log source boundary is safe.
- Copy, closure, and runtime-window tooling now carry ordered analyzer -> strict selector
  -> bundle preflight -> approved-evidence checker command sequences, but those command
  plans remain non-authorizing.
- The activation checker now allows the Discord bot `tester_status_workflow` editable
  embed/button metadata only on exact report paths as non-evidence metadata. Nested
  runtime, authorization, SDK, P0, readiness, or approved-evidence aliases inside that
  workflow still fail closed.
- Multi-surface beta capture packs reject SDK/P0/runtime-evidence/live-authorization
  status and progress aliases.

Read-only static orientation found candidate native registration evidence for the three
approved lifecycle source names under registrar `0x1ccc140`:
`CheckJoinInProgress` window `0x13cbc88` thunk `0x15ce900`,
`HandleNewPlayer` window `0x13cc203` thunk `0x15d04c0`, and `OnLogout` window
`0x13cc559` thunk `0x15d1500`. This is lifecycle orientation only; it does not promote
runtime evidence, SDK readiness, public identity, or public runtime APIs.

Validation passed in the lead integration round: activation preconditions `63 OK`,
runtime-window execution `25 OK`, analyzer `61 OK`, status/runner `73 OK`,
copy/closure `100 OK`, Discord beta/notice `54 OK`, multi-surface pack `48 OK`,
approved-evidence checker `194 OK`, evidence bundle builder `120 OK`, `git diff
--check`, and compact SDK status still reports `approved_runtime_evidence_missing`,
SDK `0/12`, P0 `0/4`, runtime/public/stable false, and source overclaims `0`.

## 2026-06-08 Static Triplet Orientation Checkpoint

Lead local follow-up, 2026-06-08 `04:54 CEST`: offline static tooling now records the
three runtime triplet source names together without changing the runtime evidence gate.
No live server, `/servidor/ark`, RCON, Discord, deployment, marker/env, GitHub, tag, or
release action occurred.

`check_player_identity_static_lifecycle_orientation.py` now byte-checks bounded native
registration orientation for:

- `ShooterGameMode.CheckJoinInProgress`: role hint `session_start_rejected`, ASCII name
  VMA `0x416ff3a`, class-load/window `0x13cbc88`, registration `0x13cbc8f`, thunk
  `0x15ce900`, registrar call target `0x1ccc140`.
- `ShooterGameMode.HandleNewPlayer`: role hint `session_start`, ASCII name VMA
  `0x4170122`, class-load/window `0x13cc203`, registration `0x13cc20a`, thunk
  `0x15d04c0`, registrar call target `0x1ccc140`.
- `ShooterGameMode.OnLogout`: role hint `session_end`, ASCII name VMA `0x417024f`,
  class-load/window `0x13cc559`, registration `0x13cc560`, thunk `0x15d1500`,
  registrar call target `0x1ccc140`.

`build_player_identity_lifecycle_anchor_static_report.py` preserves the old
`accepted_targets` lifecycle-anchor binding as `HandleNewPlayer` plus `OnLogout` only,
and adds `accepted_triplet_sources` plus `required_runtime_triplet_sources` for the full
`HandleNewPlayer` / `CheckJoinInProgress` / `OnLogout` runtime triplet. The new fields
explicitly keep `approved_runtime_evidence=false`, `runtime_evidence_ready=false`,
`counts_toward_sdk=false`, and `counts_toward_p0_dependency_chain=false`; a copied
runtime sibling-set checker acceptance is still required.

Validation passed: static lifecycle orientation `4 OK`, lifecycle anchor static report
`4 OK`, combined static report plus planning-source manifests `26 OK`, and scoped
`git diff --check` clean.

## Rejected Shortcuts

- `HandleNewPlayer` rejected-start tuples (`0,0`, `0,1`, `1,0`) are superseded
  non-evidence for the current route.
- `CheckJoinInProgress` copied bool tuples other than `1,0`, especially `0,0`, are not
  accepted rejected-start evidence.
- A stale or order-mismatched TheIsland `CheckJoinInProgress(1,0)` line is not reusable
  as the missing accepted runtime role, even though the tuple itself is exact.
- A fresh Ragnarok window with start/end, duplicate start, diagnostic candidates, and
  `CheckJoinInProgress(0,0)` does not prove the rejected-start role.
- Diagnostic `CheckJoinInProgress` lines, even if they include copied bool text, are not
  accepted observer events and do not satisfy the bundle/checker chain.
- `K2_PostLogin` drift or presence cannot fill `session_start`,
  `session_start_rejected`, or `session_end`.
- More offline layout comparison, broad FName/GObjects scanning, map/tester changes, or
  passive player-count context cannot by themselves answer the missing approved runtime
  event.

## Planning Hardening

The source-bound planning lane now exposes the rejected-start requirement as exact
`ShooterGameMode.CheckJoinInProgress(1,0)` only. `HandleNewPlayer` rejected-start
tuples, passive snapshots, and diagnostic-only lines are recorded as non-evidence
substitutes in the readiness report and planning-source artifacts, and the all-six
planning-gap verifier rejects drift back to those substitutes.

The planning manifest verifier also checks the
`players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json` diagnostic
artifact against the committed sanitized `HandleNewPlayer` and `OnLogout` fixtures. It
binds the artifact's fixture property order and expected property FName indices to the
repo snapshots and rejects stale or promotional drift records. The later redacted-monitor
values reported for Ragnarok (`28411 -> 28422`, `28543 -> 28554`) are recorded only as
unbound passive diagnostic context with `approved_runtime_evidence=false`; they do not
change the exact `CheckJoinInProgress(1,0)` runtime role requirement.

The next-action planner now records the latest rejected hypotheses as route-audit
metadata: stale/order-mismatched TheIsland `CheckJoinInProgress(1,0)` cannot be reused,
fresh Ragnarok `CheckJoinInProgress(0,0)` cannot satisfy the role, diagnostic candidate
lines cannot substitute for accepted copied observer events, and duplicate start/end-only
windows cannot clear `approved_runtime_evidence_missing`.

## Function-FName Near-Miss Diagnostic

Local offline patch, 2026-06-07 `22:59 CEST`: `ProcessEvent` can optionally emit a
metadata-only diagnostic when a UFunction shape matches one of the player-principal
lifecycle targets but the UFunction `FName` index differs from the exact accepted
target. This is intended to distinguish "wrong function name index" from "wrong copied
shape" without broad FName/GObjects scanning.

Activation requires all of the following gates:

- the normal player-principal lifecycle observer gate;
- candidate diagnostics enabled with
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1`;
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1`;
- a bounded
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=1..10000`.

The hook logs only diagnostic metadata, not params or player identity. Expected lines use
`PlayerPrincipalLifecycleDiagnostic candidate`, `diagnostic_shape=FunctionFNameNearMiss`,
`reflection_status=matched`, `read_status=ok`, `accepted_lifecycle_target=false`,
`params_logged=false`, `identity_logged=false`, and `evidence_claim=none`.

The accepted observer path remains exact: `TryIdentifyInvocation()` and
`TryObserveInvocation()` still reject the near-miss target as `NonLifecycleFunction`.
The analyzer accepts these diagnostic lines only as non-evidence. Copy/bundle/checker
paths must keep rejecting them for approved evidence, SDK/P0 progress, public identity
contract readiness, Plugin Hub readiness, publication, or stable SDK claims.

This diagnostic must not be enabled in a promotable evidence window. It is only for a
separate debug window when the route has player presence but no accepted lifecycle roles,
and it requires a later clean evidence window with diagnostics disabled before any
runtime evidence can be promoted.

## Compact Property FName Chain Diagnostics

Local offline patch, 2026-06-08 `00:38 CEST`: the TheIsland diagnostic window
showed that `HandleNewPlayer` property mismatch reasons could truncate before the
complete observed property FName chain was visible. The concrete truncated live clue
was a `HandleNewPlayer` diagnostic line that reached `position_4`/`ReturnValue`, but
the reason spent most of its 768-byte budget on per-property metadata and cut off
before the fifth property name could be confirmed.

The reflection and hook diagnostics now put a compact
`observed_property_fname_chain` summary near the start of diagnostic reasons. This
is intended to preserve a complete chain such as the current TheIsland/Ragnarok
candidate shape before verbose `prop_*` metadata is truncated. The change keeps the
same safety boundary:

- no params, raw player text, player identity, secrets, or UE pointers are logged;
- diagnostic lines remain `evidence_claim=none` and are non-promotable;
- the incomplete/current `HandleNewPlayer` chain remains reject-only until complete
  runtime evidence is observed and independently accepted;
- accepted runtime evidence still requires a clean sibling-set window with
  diagnostics disabled and the exact `session_start`, `CheckJoinInProgress(1,0)`
  `session_start_rejected`, and matched `session_end` triplet.

Analyzer tooling now treats compact property/FName chains from explicit diagnostic
fields or sanitized `reason` tokens as `diagnostic_property_fname_chain_non_evidence`.
Approved-evidence checker tooling rejects copied logs containing
`PlayerPrincipalLifecycleDiagnostic` lines and allows only safe analyzer-produced
diagnostic chain metadata as non-evidence context. This prevents complete-looking
diagnostic chain metadata from satisfying lifecycle roles, complete triplets,
SDK/P0 progress, public readiness, or stable claims.

Validation in the lead/integration round:

- `ctest --test-dir build -R 'PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure`
  passed `2/2`;
- `python3 -m unittest scripts.test_analyze_runtime_observer_log` passed `59 OK`;
- Worker D ran
  `python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
  and reported `191 OK`; lead reran the previously failing evidence focal cases
  and got `4 OK`;
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.

This is an observability improvement for the next debug/tester window. It is not
approved runtime evidence and does not change SDK accounting.

## Clean Observer Runtime Follow-Up

Live follow-up, 2026-06-08 `00:48 CEST`: the patched build was installed to
`/servidor/ark/obelisk` and both active maps were restarted only after RCON
reported zero players. The current active maps are TheIsland (`arkserver2`) and
Ragnarok (`arkserver`); Genesis2 is off, preserving the two-server maximum. Both
processes show `ActiveEvent=Summer`.

The current run is a clean observer run, not a diagnostic run. Logs show the
ProcessEvent hook, plugins disabled, and `PlayerPrincipalLifecycleObserver`
enabled on both maps. Candidate diagnostics and function-FName near-miss envs
are not active in this run, so the compact property-chain patch is deployed but
will not emit diagnostic chain lines until a later diagnostics-enabled window.

TheIsland produced one accepted observer-shaped `session_end` line for
`ShooterGameMode.OnLogout` after a tester/player disconnect:
`apply_status=session_end_unresolved_noop` and `correlation_status=missing`.
That proves the current clean observer can still see logout traffic, but it is
not approved runtime evidence because it lacks a correlated `session_start` and
the exact `CheckJoinInProgress(1,0)` `session_start_rejected` sibling event.
It should be treated as a direction signal: keep improving/capturing the
`HandleNewPlayer`/start side, not as a bundle input.

RCON checks through `/home/flowcommunity-ark/dashboard/server/test_rcon.js`
reported zero players on TheIsland port `27021` and Ragnarok port `27020`.
The earlier attempted `scripts/rcon_command.py` path was invalid and should not
be interpreted as an RCON failure.

## Current HandleNewPlayer Drift Acceptance Fix

Local/runtime deploy follow-up, 2026-06-08 `00:57 CEST`: the clean observer
window exposed a plausible asymmetry: TheIsland emitted `session_end` through
`ShooterGameMode.OnLogout`, but no accepted `session_start` appeared for the
same player cycle. Offline audit found that constants for the complete current
runtime `HandleNewPlayer` property FName chain already existed:
`28422,21318,22972,28520,17727`, but that chain was not included in the approved
`HandleNewPlayer` drift-chain arrays. A current live `HandleNewPlayer` with the
complete chain could therefore reject before producing the copied
`session_start`, while `OnLogout` could still emit `session_end`.

The reflection and hook observer tables now include that exact five-field chain.
Acceptance remains narrow: the runtime still requires the full five-property
chain plus the existing UFunction shape, outer, flags, offsets, property class,
bool metadata, canonical copied bool, process-local subject-token, and
copied/redacted field checks. Mixed old/current chains, incomplete chains,
partial matches, and `K2_PostLogin` remain rejected. Diagnostics remain
non-evidence and do not log params, raw player text, identity, or UE pointers.

Validation before deploy:

- `cmake --build build --target player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests`
  passed;
- `ctest --test-dir build -R '^(PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests)$' --output-on-failure`
  passed `2/2`;
- full `cmake --build build -j2` completed and built `libobelisk.so`.

Deployment and runtime posture:

- RCON `ListPlayers` reported zero players on TheIsland and Ragnarok before
  restart;
- `SaveWorld` succeeded on both RCON ports;
- `/servidor/ark/obelisk` was updated through `scripts/install_obelisk.sh`
  as package-shape/install evidence only;
- TheIsland and Ragnarok were restarted sequentially, Genesis2 stayed off, and
  the two-server maximum was preserved;
- post-restart logs showed ProcessEvent hook installed, plugins disabled, and
  `PlayerPrincipalLifecycleObserver` enabled on both maps;
- post-restart observer-debug posture checks passed for both maps;
- candidate diagnostics and near-miss envs are off in the current clean observer
  run.

A new passive monitor was started for this corrected runtime window:
`/tmp/obelisk_passive_player_monitor_passive-20260607T225523Z-theisland-ragnarok-v3.log`.
The beta Discord active embed was updated in-place with buttons through the bot
channel, no webhook, no new message, and no repeat `@everyone`.

Follow-up in the same corrected runtime window: Ragnarok briefly showed one
player by RCON while Steam query still showed zero. The passive monitor captured
this as an RCON/query discrepancy and wrote passive snapshot
`/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260607T225732Z-arkserver-Ragnarok-27015-seq1-4104171/manifest.json`.
Lead sent a Ragnarok RCON broadcast asking testers to logout/rejoin once and use
the Discord embed buttons. The player later disappeared from RCON, and Ragnarok
emitted one `ShooterGameMode.OnLogout` observer line at
`2026-06-07T22:59:24Z`.

That line was still `apply_status=session_end_unresolved_noop` with
`correlation_status=missing`, so it remains invalid/non-evidence for the
approved route. `analyze_runtime_observer_log.py --allow-server-path
/servidor/ark/obelisk/logs/arkserver/Obelisk.log` reported
`approved_runtime_evidence=false`, `runtime_evidence_ready=false`, and missing
roles `session_start`, `session_start_rejected`, and `session_end`; the
unresolved logout outcome is counted as non-evidence. Do not copy this as an
approved bundle input.

This fix improves the chance that the next tester login emits the missing
accepted `session_start`. It is not approved runtime evidence. The SDK route
remains blocked until a clean copied sibling-set bundle contains accepted
`session_start`, exact `CheckJoinInProgress(1,0)` `session_start_rejected`, and
matched `session_end`, and the approved evidence checker accepts it.

## Hypotheses

- The current code path can build and check the exact accepted
  `CheckJoinInProgress(1,0)` observer event in tests, so the active gap is most likely
  runtime stimulus/evidence capture rather than an offline fixture-shape gap.
- The fastest current hypothesis is a clean fresh TheIsland window with diagnostic
  candidates disabled. TheIsland has already shown the exact `1,0` tuple, while the
  rejected material failed on staleness/order and the latest clean TheIsland retry did
  not reproduce the missing accepted role. Direct TheIsland is still the narrowest
  candidate-only next action because the alternative transfer/reconnect paths have worse
  duplicate/order risk and less exact `1,0` evidence. It still needs separate
  current-turn live-ops approval.
- The observed Ragnarok flow may not have exercised the specific join-in-progress branch
  that returns `false` with `bIsFromLogin=true`; it produced accepted starts, matched
  ends, duplicate start, diagnostic candidates, and `CheckJoinInProgress(0,0)`.
- Cluster transfer is not the fastest primary route on current evidence. The latest
  transfer-oriented Ragnarok attempt burned start/end budget, produced a duplicate start,
  and did not produce the accepted `CheckJoinInProgress(1,0)` event.
- Reconnect timing is a last-resort falsification path, not the primary evidence path,
  because reconnects naturally risk `session_end` before the rejected-start role,
  duplicate `session_start`, stale correlation, and sequence-budget loss.
- If a future approved window produces a new `CheckJoinInProgress` property-name drift
  chain, it should be treated as an explicit drift candidate requiring full shape,
  offset, class, bool-metadata, redaction, post-original, and checker coverage. It
  should not trigger broad name-table or GObjects rediscovery on the current binary.

## Route Sampler Diagnostic Follow-Up

Local development follow-up, 2026-06-08 `01:58 CEST`: current clean joins had shown
no accepted lifecycle route after observer enablement, while older triplet-like material
was historical or passive/non-promotable. The next useful local code target was therefore
not another immediate restart, but a bounded route sampler that can reveal which
non-reflected ProcessEvent FName routes are being hit when a player joins.

The runtime now supports a diagnostic-only sampler behind:

- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1`;
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1`;
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=1..10000`.

The sampler logs only: `PlayerPrincipalLifecycleDiagnostic route-sample sequence=<n>
fname_index=<n> fname_number=<n> post_original=true accepted_lifecycle_target=false
reflection_probe=false params_logged=false identity_logged=false evidence_claim=none`.
It does not read params, copy player identity, dispatch events, satisfy lifecycle roles,
or count toward runtime evidence. The analyzer records route samples as
`diagnostic_route_sample_non_evidence`; the passive monitor tails them as
diagnostic-only lines; the wrapper/posture checks require diagnostics and a bounded
limit; and activation preconditions reject all lifecycle diagnostic env keys from
approved evidence windows.

Validation:

- `python3 -m unittest scripts.test_analyze_runtime_observer_log scripts.test_monitor_ark_player_presence_passive`
  passed `97 OK`;
- `bash scripts/test_linuxgsm_wrapper_markers.sh` passed;
- `bash scripts/test_check_obelisk_server_posture.sh` passed;
- full `cmake --build build -j2` passed;
- `ctest --test-dir build -R 'PlayerPrincipalLifecycle|ProcessEventPlayerPrincipalLifecycle' --output-on-failure`
  passed `3/3`;
- `git diff --check` passed.

The full activation-precondition suite still has the preexisting failure
`test_accepts_real_standing_beta_notice_report_without_standing_send_coverage`; the new
route-env rejection coverage passed inside that run. Strict status remains
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable false.

## Post-Patch Runtime Plan

This plan is not live-ops authorization by itself. A future agent still needs either the
recorded standing launch authority bound to this same ObeliskSDK debug/evidence purpose
and safety limits, or exact delegated current scope, before reading server logs, touching
`/servidor/ark`, restarting, sending Discord, running RCON, or capturing runtime
evidence. That authority remains authorization only and never promotes evidence.

Candidate-only experiment target, once approved:

1. Prefer a clean fresh TheIsland (`arkserver2`) window with diagnostic candidates
   disabled, because the stale/order-mismatched TheIsland material already showed the
   exact `CheckJoinInProgress(1,0)` tuple. This is a candidate-only recommendation and
   does not grant scope.
2. Use a patched observer runtime on the named approved instance only. Historical
   context used TheIsland (`arkserver2`) and Ragnarok (`arkserver`), with Genesis2 kept
   off and a two-server maximum; do not infer that those names grant current scope.
3. Capture one copied, post-original `PlayerPrincipalLifecycleObserver event` for each
   role in the same approved sibling-set bundle:
   `HandleNewPlayer(1,1)` as `session_start`,
   `CheckJoinInProgress(1,0)` as `session_start_rejected`, and matched `OnLogout` as
   `session_end`.
4. Require the CheckJoin line to contain target
   `ShooterGameMode.CheckJoinInProgress`, copied bool fields
   `bIsFromLogin,ReturnValue`, copied values `1,0`, redacted field `NewPlayer`,
   `principal_action=none`, `apply_status=session_start_rejected_noop`, and
   `correlation_status=not_applicable`.
5. Feed only the copied log, completed approval receipt, window manifest, stable final
   posture, and sidecars through the analyzer, bundle builder, approved manifest builder,
   and approved runtime evidence checker. Use `--post-window-replay` for any
   post-window or promotion-route consumption.
6. If the post-patch run produces stale/order-mismatched `CheckJoinInProgress(1,0)`,
   `CheckJoinInProgress(0,0)`, diagnostic candidates, duplicate start/end-only material,
   or accepted start/end only, record it as negative runtime context and leave
   `approved_runtime_evidence_missing` active.

## Tester Choreography Ranking

Fastest candidate-only tester plan, once separately approved:

1. Primary route: clean TheIsland direct join, no diagnostics. Use one approved
   `arkserver2` / `TheIsland` observer window with diagnostic candidates disabled,
   plugins disabled, dispatch limit `0`, log limit `10`, and no unrelated observer
   families. Start from a quiet target with no scripted reconnects or queued testers.
   Have one tester join TheIsland directly from outside the cluster path, then remain
   connected. If the approved scope includes accepted-event tail monitoring, wait for
   the exact `CheckJoinInProgress(1,0)` `session_start_rejected` line before asking that
   same tester to leave once for the matched `OnLogout` end. If no accepted CheckJoin
   line appears during the approved window, close it as missing-role evidence instead of
   adding retries inside the same capture.
2. Budget guard: do not mix direct join, cluster transfer, and reconnect in one window.
   The checker rejects duplicate accepted role lines in the actual capture window, and
   the analyzer flags sequence or log-limit overruns. A second successful join, early
   logout, reconnect loop, or transfer after the anchor start can turn otherwise useful
   material into duplicate-role or order-mismatched non-evidence.
3. Cluster-transfer fallback: run only as a separate fresh window after the direct
   TheIsland attempt is closed. If approved, make transfer into the target the first
   player action for that window; do not first create a direct `HandleNewPlayer` anchor
   and then transfer, because that repeats the latest Ragnarok failure mode. Current
   evidence demotes TheIsland-to-Ragnarok transfer because it produced start/end,
   duplicate start, diagnostics, and `CheckJoinInProgress(0,0)`, not the required
   `1,0`.
4. Reconnect fallback: use only as a separate single-attempt negative test if direct
   join and transfer both fail under approved scope. Do not use rapid reconnects in the
   primary evidence window. The expected failure modes are `session_end` before
   `session_start_rejected`, duplicate `session_start`, stale/duplicate logout
   correlation, or another unsupported `CheckJoinInProgress` tuple.
5. Stop conditions: stop the evidence attempt after the first matched `session_end`,
   after any duplicate accepted role appears, after an unsupported CheckJoin tuple
   appears, or when the approved window expires without the `session_start_rejected`
   role. Preserve the result as negative runtime context and do not relax the `1,0`
   gate.

## Stale TheIsland Lines

Future agents should read old and stale TheIsland lines as historical diagnostics or
stimulus clues, not as a partial bundle to rescue. The older-runtime sequence had
`HandleNewPlayer(1,1)`, a `CheckJoinInProgress` copied-observation rejection, a
superseded `HandleNewPlayer(0,1)` rejected-start shortcut, matched `OnLogout`, and
another start. Prior TheIsland material improved the tuple clue by emitting an
exact `CheckJoinInProgress(1,0)` line, but dry-run copy/order checks still reject it
because it is stale/order-mismatched against the required fresh sibling-set window.

Use those old lines only to explain why the diagnostic and drift patches were needed.
Do not treat them as approved runtime evidence, second-source evidence, public SDK
readiness, a reason to relax the bool tuple, a reason to enable diagnostics for the
fastest candidate, or a reason to duplicate beta notices just to recreate a missing
sidecar.

## Next Experiments And Code Targets

Future work still needs the recorded standing launch authority or exact delegated
current scope before any server/log read or runtime observation. Within that boundary,
the useful evidence target is narrow:

1. Candidate-only fastest path: request a clean fresh TheIsland window with diagnostic
   candidates disabled. The candidate target is only a planning hypothesis; it does not
   authorize reading logs, restarting, RCON, Discord, marker/env changes, or runtime
   capture.
2. Capture one copied, post-original, accepted `HandleNewPlayer(1,1)` `session_start`,
   one copied, post-original, accepted `CheckJoinInProgress(1,0)`
   `session_start_rejected`, and one matched `OnLogout` `session_end` in the same
   approved sibling-set bundle.
3. Feed the copied log, window manifest, approval receipt, and sidecars through the
   analyzer, bundle builder, approved manifest builder, and approved runtime evidence
   checker. Do not count raw logs, passive summaries, or diagnostic lines as evidence.
4. If stale/order-mismatched TheIsland `1,0`, Ragnarok `0,0`, duplicate start/end-only
   material, or diagnostic-only lines recur, keep them as negative evidence and inspect
   the accepted-event split in
   `hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp`,
   `hooks/ProcessEventHook.cpp`, and
   `scripts/analyze_runtime_observer_log.py` without relaxing the `1,0` gate.
5. If property-name drift changes, review
   `ue/PlayerPrincipalLifecycleReflection.cpp` and the corresponding C++ observer and
   reflection tests. Add only exact drift-chain alternatives with full copied-shape
   guardrails.
6. Keep checker targets strict:
   `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py`,
   `scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`, and
   `scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py`
   should continue rejecting diagnostic candidates, stale `HandleNewPlayer` rejected
   tuples, and unsupported `CheckJoinInProgress` bool tuples.

## Non-Claims

- No accepted `CheckJoinInProgress(1,0)` runtime event was found by this audit.
- No blocker was cleared; `approved_runtime_evidence_missing` remains active.
- No public player identity, public Player SDK, permission/admin, command/reply,
  runtime-readiness, stable-readiness, mutation, lookup, `ResourceHandle`, or return
  override claim is made.

## 2026-06-08 Runtime/Tooling Follow-Up

Scope: lead-owned integration and live debug under the recorded standing launch
authorization. This section records non-promotable runtime/debug facts and local tooling
deltas only. It does not claim approved runtime evidence, SDK/P0 progress, public SDK
readiness, stable readiness, publication, Plugin Hub readiness, or support-tier
activation.

Observed runtime facts:

- The tester cycle before this follow-up produced only unresolved `session_end` lines on
  Ragnarok and TheIsland. Both had
  `apply_status=session_end_unresolved_noop` and `correlation_status=missing`, so they
  are invalid lifecycle evidence and do not satisfy `session_end`.
- TheIsland diagnostic logs showed current-runtime property FName drift for
  `HandleNewPlayer`, `CheckJoinInProgress`, and diagnostic-only `K2_PostLogin`. The
  `CheckJoinInProgress` chain was complete enough to capture exact observed property
  name indices `28520,28422,17729`. The `HandleNewPlayer` line was truncated before the
  full fifth property metadata was visible, so its synthetic tail must remain
  reject-only.
- Superseded historical note: an earlier diagnostic-only section said the current
  `HandleNewPlayer` candidate chain `28422,21318,22972,28520,17727` was intentionally
  not accepted. That is no longer current. The later drift acceptance fix accepts that
  exact complete five-field chain only under strict function shape, outer, flags,
  offsets, property class, bool metadata, copied/redacted shape, and safety checks.
- The `FunctionFNameNearMiss` diagnostic was expanded offline to report delegate-name,
  unapproved-property-chain, and outer-mismatch near misses as metadata-only diagnostic
  candidates. Exact accepted lifecycle names remain excluded from near-miss promotion.
- Analyzer tooling now accepts
  `PlayerPrincipalLifecycleDiagnostic function-FName near-miss logging enabled` as
  diagnostic gate metadata, not as a malformed player-principal line. Passive monitor
  tooling also tails that line as diagnostic-only non-evidence.
- Posture tooling now allows and validates the near-miss env pair only in observer-debug:
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1` and
  `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=1..10000`.
  Stable posture still rejects both env vars.
- Discord beta coordination was converted to a single active bot embed with buttons.
  The active message is updated in-place in channel `1513238083741683934`, so routine
  updates do not repeat `@everyone` pings.

Live state after deployment:

- Current central install `/servidor/ark/obelisk` was updated from the local build after
  focused validation.
- TheIsland `arkserver2` was restarted only after RCON reported `0` players. Ragnarok
  stayed running, preserving the hard maximum of two ARK servers.
- TheIsland PID `3819911` loaded the ProcessEvent hook at `0x1d34e20`, disabled plugins,
  enabled player-principal observer, enabled candidate diagnostics, and enabled
  function-FName near-miss diagnostics with scan limit `10000`. This is explicitly
  non-promotable because diagnostics are active.
- Passive monitor PID `3909098`/`3909099` writes to
  `/tmp/obelisk_passive_player_monitor_passive-20260607T221440Z-theisland-ragnarok-v2.log`
  with snapshots under `/tmp/obelisk-passive-evidence-snapshots`. Its first tick saw
  TheIsland and Ragnarok at `0` players and no accepted lifecycle roles.

Validation recorded:

- `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_prepare_player_principal_lifecycle_beta_notice`
  passed `51` tests.
- `python3 -m unittest scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_permissions_admin_public_readiness`
  passed `191` tests.
- Multi-surface beta pack tests passed `47` tests.
- Approved manifest, evidence bundle, and approved evidence checker tests passed
  `31`, `118`, and `189` tests respectively.
- Analyzer suite passed `56` tests.
- C++ lifecycle reflection/observer CTest passed `2/2`.
- LinuxGSM wrapper marker tests, posture tests, and passive-monitor focal tests passed.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable
  false, and source overclaims `0`.

Next useful runtime step:

When testers enter TheIsland during this diagnostic window, inspect copied logs for a
complete `HandleNewPlayer` property chain and for whether the newly accepted
`CheckJoinInProgress` drift emits a copied `session_start_rejected` observer event. If
the complete `HandleNewPlayer` chain appears, add it only with full-shape tests and then
restart into a clean non-diagnostic evidence window before attempting an approved bundle.

## Offline Planner And Regression Audit Follow-Up

Scope: lead integration at 2026-06-08 `02:15 CEST`. No live server, `/servidor/ark`,
RCON, Discord, deploy, marker/env, restart, or live-log operation occurred.

Read-only regression audit result:

- The current "logout-only" symptom is not currently classified as a code regression.
  The likelier cause is contract/window/flow mismatch: older material allowed or
  documented superseded `HandleNewPlayer` rejected-start shortcuts, while the current
  strict contract requires one clean copied sibling-set window containing
  `HandleNewPlayer(1,1)`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`, and matched
  `OnLogout`.
- The reflection and observer code still contain the accepted TheIsland
  `CheckJoinInProgress` drift chain `28520,28422,17729` and the current
  `HandleNewPlayer` drift chain `28422,21318,22972,28520,17727`. Seeing
  `session_end_unresolved_noop` with `correlation_status=missing` means no accepted
  start principal was created in that same valid window, not that logout alone is usable.
- Route sampler output remains diagnostic-only. It can point to which FName indices are
  traversing `ProcessEvent`, but it does not read params, copy identity, satisfy roles, or
  promote approved evidence.

Integrated local tooling:

- `scripts/plan_player_principal_lifecycle_next_actions.py` now accepts copied/sanitized
  analyzer JSON with schema `obelisk.runtime-observer-log-summary.v1`.
- When the analyzer reports `diagnostic_route_sample_*` fields for
  `player_principal_lifecycle`, the planner emits one offline action
  `review_player_principal_lifecycle_route_samples` and a
  `route_sample_plan_summary`.
- Known lifecycle FName indices are mapped only as planning metadata:
  `1845 -> ShooterGameMode.CheckJoinInProgress`, `2170 -> ShooterGameMode.HandleNewPlayer`,
  `2384 -> ShooterGameMode.OnLogout`, and `4943 -> GameMode.K2_PostLogin`.
- The new route-sample action preserves `approved_runtime_evidence=false`,
  `runtime_ready=false`, `public_sdk_ready=false`, and SDK/P0 progress `0`.

Validation:

- `python3 -m unittest scripts.test_plan_player_principal_lifecycle_next_actions scripts.test_check_player_principal_lifecycle_activation_preconditions`
  passed `75` tests.
- `python3 -m unittest scripts.test_analyze_runtime_observer_log scripts.test_monitor_ark_player_presence_passive scripts.test_report_player_principal_lifecycle_runtime_evidence_status scripts.test_run_player_principal_lifecycle_next_actions`
  passed `164` tests.
- `python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails`
  passed `91` tests.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable false.

## Drift-Table Consistency Guardrail

Scope: local static guardrail at 2026-06-08 `02:19 CEST`. No live/server operation was
performed.

The accepted drift constants and chain arrays are duplicated in
`ue/PlayerPrincipalLifecycleReflection.cpp` and
`hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp`. A static guardrail now compares
the observed lifecycle drift constants and the `HandleNewPlayer` /
`CheckJoinInProgress` drift-chain blocks across both files. This directly covers the
offline audit recommendation to catch divergence before a deployment or evidence window.

The same guardrail suite also now verifies the observation-budget recheck after the
metadata-only recognition pass by checking ordering before the final
`ProcessLocalSubjectTokenMode::Assign` pass, rather than depending on one exact
condition string. This preserves the intended fail-closed behavior without making the
test brittle to a safe compound condition.

Validation:

- `python3 -m unittest scripts.test_player_principal_runtime_guardrails` passed `25`
  tests.

## Event-Split And Post-Runtime Contract Prep

Scope: offline integration round on 2026-06-08 after compaction/resume. No live server
logs were read, no `/servidor/ark` paths were modified, and no server, RCON, Discord,
deploy, marker/env, GitHub, commit, tag, or release action occurred.

The player-principal lifecycle tooling now carries a clearer event split through the
offline pipeline:

- `copy_player_principal_lifecycle_ready_log.py` emits
  `ready_log_evidence_split` with schema
  `obelisk.player-principal-lifecycle-ready-log-copy-evidence-split.v1`. It distinguishes
  exact-triplet-ready, start/end-only missing exact rejected start, rejected
  `CheckJoinInProgress` candidate with non-`1,0` bools, shape-unapproved observer
  events, and diagnostic-only material.
- `analyze_runtime_observer_log.py` emits
  `player_principal_lifecycle_event_split_summary` for accepted observer events,
  `copy_status=rejected`, route samples, diagnostic candidates,
  `session_end_unresolved_noop/missing`, and the synthetic missing exact
  `CheckJoinInProgress(1,0)` gap.
- `report_player_principal_lifecycle_runtime_evidence_status.py` and
  `run_player_principal_lifecycle_next_actions.py` consume the split defensively,
  preserve it as non-executable context, and point the next manual action at the missing
  `session_start_rejected` / `ShooterGameMode.CheckJoinInProgress(1,0)` role when
  start/end-only material is present.

These fields are diagnostic and routing aids only. They keep
`approved_runtime_evidence=false`, `runtime_evidence_ready=false`,
`public_sdk_ready=false`, SDK/P0 progress `0`, and do not authorize runtime work,
Discord, marker/env edits, publication, or stable SDK claims. A copied log with
diagnostic lines or start/end-only material still cannot be bundled/promoted.

The post-runtime public-contract lane was also prepared offline:

- `check_player_identity_public_contract_readiness.py` and
  `check_player_identity_public_contract_gap_report.py` now report
  `post_runtime_contract_gap_diagnostic` so that, once the approved runtime principal
  lifecycle bundle exists, the next blocker is explicit:
  `reviewed_identity_public_contract_decision_record` and its reviewed/header keys.
- The diagnostic rejects readiness aliases and keeps public identity, lookup,
  permissions/admin, command/chat surfaces, public SDK/API/ABI/header readiness,
  v1 completion, Plugin Hub, ResourceHandle, mutation, return override, SDK progress,
  and P0 progress fail-closed.

Validation in this round:

- `python3 -m unittest scripts.test_copy_player_principal_lifecycle_ready_log` passed
  `37 OK`.
- `python3 -m unittest scripts.test_analyze_runtime_observer_log` passed `61 OK`.
- `python3 -m unittest scripts.test_report_player_principal_lifecycle_runtime_evidence_status scripts.test_run_player_principal_lifecycle_next_actions`
  passed `71 OK`.
- `python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report`
  passed `182 OK`.
- `python3 -m unittest scripts.test_player_principal_runtime_guardrails` passed `26 OK`.
- `python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails`
  passed `91 OK`.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
  runtime/public/stable false, approved runtime/in-game evidence false, and source
  overclaims `0`.

## Approved Checker Split Metadata Guardrail Fix

Scope: offline checker/builder fix on 2026-06-08 `03:12 CEST`. No live server logs were
read, no `/servidor/ark` paths were modified, and no server, RCON, Discord, deploy,
marker/env, GitHub, commit, tag, or release action occurred.

The approved runtime evidence checker was rejecting
`player_principal_lifecycle_event_split_summary` as
`forbidden_identity_or_ue_internal_leakage` because the privacy detector matches `ip`
inside `principal`. That made a checker-accepted bundle vulnerable to a false blocker
once the analyzer-provided event split was present.

The fix is a narrow path allowlist for the split metadata container and its
`evidence_classification` leaf. The recursive scan still descends into the split, so
unsafe nested fields remain forbidden. Tests now cover accepted safe split metadata and
rejection of `player_name`, `ue_pointer`, and `raw_params` under the split.

The evidence-bundle builder preflight expectation was also updated to include
`session_end_missing_correlation_diagnostics=None` in the empty
`copy_readiness_context`, matching the builder's current output contract.

Validation:

- `python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
  passed `193 OK`.
- `python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`
  passed `119 OK`.
- `git diff --check` passed.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
  runtime/public/stable false, approved runtime/in-game evidence false, and source
  overclaims `0`.

This fix does not supply runtime evidence, approve a bundle, move SDK/P0 counters, or
authorize publication. It removes a false offline rejection so a future real copied
sibling-set triplet can be judged by the intended contract.

## Status-Layer Strict Triplet Guardrail

Scope: offline status/builder integration fix on 2026-06-08 `03:28 CEST`. No live server
logs were read, no `/servidor/ark` paths were modified, and no server, RCON, Discord,
deploy, marker/env, GitHub, commit, tag, or release action occurred.

A read-only pipeline audit found that the strict triplet was well enforced by the
approved checker and bundle builder, but the final SDK status layer could still advance
from `approved_runtime_evidence_missing` to `identity_public_contract_gate_missing` when a
public SDK container only supplied bare aliases such as
`approved_runtime_evidence_accepted`, `evidence_bundle_accepted`, and a readiness/presence
boolean. That was too weak because it did not prove the checker schema, input schema, or
strict selected sibling set.

`report_obelisk_sdk_status.py` now requires a checker-contract report before treating the
runtime evidence blocker as cleared. The accepted container must include:

- the approved checker report schema and approved-evidence input schema;
- `ready_scope=runtime_evidence_only`;
- public/runtime/stable readiness and complete-SDK claim flags false;
- `strict_lifecycle_triplet_selected=true`;
- strict selected roles `session_start`, `session_start_rejected`, `session_end`;
- zero non-counting context events and roles;
- `strict_rejected_start_expected_shape=ShooterGameMode.CheckJoinInProgress(1,0)`;
- observed rejected-start target `ShooterGameMode.CheckJoinInProgress`,
  bool fields `bIsFromLogin,ReturnValue`, bool values `1,0`,
  `apply_status=session_start_rejected_noop`, and
  `correlation_status=not_applicable`.

Tests now cover both directions:

- bare accepted-runtime booleans without strict-triplet proof keep
  `approved_runtime_evidence_missing`, SDK `0/12`, and P0 `0/4`;
- a faithful checker report advances only to `identity_public_contract_gate_missing`,
  still with public/runtime/stable readiness false and SDK/P0 progress `0`;
- the evidence-bundle builder's generated checker output can feed the aggregate status
  smoke and route only to the identity public contract gate.

Validation:

- `python3 -m unittest scripts.test_report_obelisk_sdk_status` passed `58 OK`.
- `python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`
  passed `120 OK`.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
  runtime/public/stable false, approved runtime/in-game evidence false, and source
  overclaims `0`.

This status-layer guardrail does not create runtime evidence. It prevents a generic or
invalid "accepted evidence" alias from bypassing the approved checker contract.

## Post-Runtime Public Contract Binding Hardening

Scope: offline SDK/public-contract hardening on 2026-06-08 `04:07 CEST`. No live server
logs were read by the lead, no `/servidor/ark` paths were modified, and no server, RCON,
Discord, deploy, marker/env, GitHub, commit, tag, or release action occurred.

Six scoped agents were spawned and later explicitly closed. The round hardened the route
after approved runtime evidence without claiming that such evidence exists:

- reviewed identity public-contract decision records now require a strict approved-runtime
  checker report reference with matching path and sha256;
- identity public-contract readiness/gap reports reject status/report-shaped runtime
  placeholders and bare `accepted_for_contract_review` aliases;
- command permission route, bound identity sources, and command principal authz bridge
  treat `requires_*`, `must_*`, and `does_not_*` metadata as requirements/negative
  guardrails rather than readiness;
- public SDK completion treats public-contract review/readiness artifacts as
  non-approved runtime evidence and keeps SDK/P0 counters at zero until the identity gate
  is actually satisfied;
- status aggregation rejects a public-contract review artifact even if it carries
  runtime-evidence booleans, unless it is the strict approved-runtime checker contract;
- handoff guardrails now machine-check that standing launch authority survives compaction
  only as authorization and never as runtime evidence, SDK/P0 progress, or readiness.

Read-only candidate audit found no current strict candidate in existing copied material.
Known copied/passive logs remain near-misses or diagnostic/non-evidence: some are
start/end only, older complete-role material uses a superseded rejected-start shape, and
passive Ragnarok material is ambiguous/non-promotable. Do not bundle those files as
approved evidence.

Validation:

- `python3 -m unittest scripts.test_check_player_identity_public_contract_decision_record scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report`
  passed `251 OK`.
- `python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_command_permission_route_gate_bound_identity_sources scripts.test_check_command_principal_authz_response_bridge`
  passed `166 OK`.
- `python3 -m unittest scripts.test_report_obelisk_sdk_status` passed `59 OK`.
- `python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails`
  passed `93 OK`.
- `python3 -m unittest scripts.test_check_public_sdk_v1_completion` ran `334` tests and
  found one stale expected-list failure after new non-evidence reasons were introduced;
  after an expectation-only test update, the affected completion subset passed `4 OK`.
- `git diff --check` passed.
- `scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
  runtime/public/stable false, approved runtime/in-game evidence false, and source
  overclaims `0`.

This is not runtime evidence and does not unblock public identity. It narrows the
post-runtime review path so that once a real strict copied sibling-set bundle exists, the
next blocker is exactly `identity_public_contract_gate_missing` instead of a collection
of ambiguous placeholders.
