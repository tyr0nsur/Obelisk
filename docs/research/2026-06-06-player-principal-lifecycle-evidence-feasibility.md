# Player Principal Lifecycle Evidence Feasibility

Date: 2026-06-06

## Scope

This note records the current feasibility boundary for active
player-principal lifecycle evidence. It is offline research only and does not
authorize live ops, server/log reads, marker/env changes, `/servidor/ark` writes,
Discord sends, runtime capture, publication, public SDK work, lookup, mutation, or
return override.

Lead owns integration. The only owned durable change here is this research note.

## Operational Digest For Future Agents

Use this section before the historical updates below.

- Accepted lifecycle-anchor roles are now stricter: `ShooterGameMode.HandleNewPlayer`
  can fill only `session_start` with copied bools `bIsFromLogin=1,ReturnValue=1`.
  `session_start_rejected` must use the exact `ShooterGameMode.CheckJoinInProgress`
  copied observer alternative with `bIsFromLogin=1,ReturnValue=0`, redacted
  `NewPlayer`, `principal_action=none`,
  `apply_status=session_start_rejected_noop`, and
  `correlation_status=not_applicable`. `ShooterGameMode.OnLogout` is the only
  `session_end` anchor, and only with `apply_status=session_end_invalidated` plus
  `correlation_status=matched`. Current planning-smoke output must mirror this:
  `session_start_rejected.accepted_alternatives` contains only exact
  `CheckJoinInProgress(1,0)`, while historical `HandleNewPlayer` rejected tuples
  appear only as superseded non-evidence.
- Known Ragnarok FName drift for `HandleNewPlayer` and `OnLogout` is no longer rejected
  by the current recognizer by index mismatch alone. It is recognized only as an explicit
  recognizer-only drift-chain alternative after the full copied observer shape,
  target/outer, property order, bool metadata, redaction, post-original, apply-status, and
  correlation gates pass. The passive Ragnarok artifact remains planning context, not
  evidence.
- `GameMode.K2_PostLogin` FName drift stays rejected for lifecycle evidence. It can help
  explain join chronology, but it has no approved copied bool tuple, no
  `principal_action`, no lifecycle apply/correlation semantics, and cannot fill
  `session_start`, `session_start_rejected`, or `session_end`.
- The all-six `players-lifecycle-anchor-candidates` set is a planning gap, not a
  promotion result. Only `HandleNewPlayer`, exact `CheckJoinInProgress(1,0)`, and
  `OnLogout` participate in the approved copied triplet. `CheckJoinInProgress` remains
  an observer-only rejected-start alternative, not a public lifecycle anchor, and
  `K2_PostLogin` plus the lifecycle delegate signatures remain non-anchor guidance.
- Passive monitor lines, diagnostic candidate lines, copied passive snapshots, public
  query/player-count changes, notice artifacts, status reports, copied-log-only material,
  and passive complete triplets stay non-evidence. They cannot clear
  `approved_runtime_evidence_missing`; only a copied, approved sibling-set runtime bundle
  accepted by the consume-mode checker can do that.
- Passive player counting is now explicitly three-state. A monitor tick with GameDig
  `0/70` and RCON timeout/unknown must be treated as `presence_detected=false` plus
  `unknown_player_context=true`, not as confirmed no-users. Use
  `player_presence_context.no_users_confirmed=true` only when the query/RCON/observer
  signals all support that conclusion.
- There is now a narrowed start/end runtime evidence lane. It accepts copied/offline
  observer proof of `HandleNewPlayer(1,1)` `session_start` followed by matched
  `OnLogout` `session_end` for contract-review input only. It does not resolve the exact
  `CheckJoinInProgress(1,0)` rejected-start role, does not count as the approved runtime
  principal lifecycle evidence bundle, and contributes no SDK/P0/runtime/public readiness
  progress.
- When online beta evidence is scarce, do not idle on one proof path. Keep up to two ARK
  servers running as passive Obelisk debug windows when practical, restart only for
  Obelisk/gate updates, and prepare offline multi-surface capture so a single beta tester
  session can gather safe gated candidates across player principal, admin/list-player or
  kick path, commands/chat response, dino, tribe, buff, inventory, transfer, mission, and
  other checker-backed surfaces. These broader captures remain candidate/debug material
  until their own checkers accept and cannot replace the exact player-principal triplet.

## Multi-Surface Offline Capture Prep, 2026-06-07 05:19+ CEST

Operator policy was made durable for future compacted agents: keep up to two ARK servers
running as Obelisk debug windows when practical, restart only for Obelisk updates or gate
changes needed for SDK progress, broadcast first when players are connected, and prepare
offline capture across every safe checker-backed surface instead of waiting on one
player-principal proof path.

This was encoded as a candidate-only workflow, not as runtime evidence. The new
`scripts/plan_obelisk_multi_surface_beta_capture.py` helper emits an offline plan for
player-principal lifecycle, permissions/admin, command chat response, command replies,
dino scalar, tribe scalar, buff status, inventory/item copied signals, transfer
ScriptStruct, and mission copied-bool surfaces. Every surface carries false
evidence/progress/readiness flags, requires its own checker acceptance, and explicitly
cannot replace the strict `HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched
OnLogout` player-principal triplet.

The same hardening round closed all six spawned sub-agents with no standby agent left
open. It did not touch live servers, `/servidor/ark`, live logs, Discord, GitHub, tags,
publication, or server process state. Validation passed: multi-surface suite and plan
`402 OK`, public SDK focal queue/alias/blocker tests `6 OK`, same-turn player-principal
route suites `304 OK`, C++ `player_principal_registry_tests` passed, and touched-file
`git diff --check` passed. SDK state remained unchanged and intentionally blocked:
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable false,
source overclaims `0`.

## Multi-Surface Pack Guardrails, 2026-06-07 06:25+ CEST

The offline preparation path now has a concrete pack generator:
`scripts/prepare_obelisk_multi_surface_beta_capture_pack.py`. It writes a candidate-only
directory containing the multi-surface plan, checker matrix, non-claim manifest, operator
runbook, README, and pack manifest. It rejects protected live server roots, supports
dry-run, and records that the pack does not authorize live ops, Discord, runtime capture,
approved runtime evidence, SDK/P0 progress, public/stable readiness, Plugin Hub,
publication, or release claims.

Six supervised agents were collected and explicitly closed with no standby left open.
They strengthened fail-closed checks across player-principal runtime evidence,
permissions/admin, command chat response, command replies, dino, tribe, buff, mission,
inventory, and transfer surfaces. Candidate packs/plans/queues and debug material remain
visible only as candidate prep; they cannot replace
`HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout`, cannot clear
`approved_runtime_evidence_missing`, and cannot advance SDK/P0/runtime/public/stable
readiness by presence or naming alone.

Validation for this continuation: runtime approved-evidence suite `170 OK`; pack/plan
suite `7 OK`; permissions/admin plus command suites `265 OK`; dino/tribe/buff/mission/
inventory/transfer suite `145 OK`; public SDK focal multi-surface/runtime-alias tests
`4 OK`; touched-file `git diff --check` passed. No live server/log/Discord/GitHub/tag/
publication/process action occurred. SDK route remained `approved_runtime_evidence_missing`,
SDK `0/12`, P0 `0/4`, runtime/public/stable false, source overclaims `0`.

## Multi-Surface Pack Consumption Checker, 2026-06-07 06:55+ CEST

The offline pack now has a companion validator:
`scripts/check_obelisk_multi_surface_beta_capture_pack.py`. It verifies the expected pack
files, artifact hashes, schemas, target binding, candidate surface list, non-claim flags,
and runbook/README boundary language. The checker's scope is deliberately
`candidate_capture_pack_integrity_only`: a valid pack proves only that the candidate
capture checklist is internally coherent. It does not authorize live ops, read live logs,
send Discord, create runtime evidence, clear `approved_runtime_evidence_missing`, or
advance SDK/P0/runtime/public/stable readiness.

The pack generator's manifest hashing was corrected to avoid a self-referential hash:
`manifest_sha256` now means the SHA256 of the manifest payload without the
`manifest_sha256` field. Pack-family guardrails were also threaded through the runtime
approved-evidence checker, public SDK completion checker, runtime-window execution helper,
command route gate, public contract readiness checker, and window-manifest checker.
`check_permissions_admin_public_readiness.build_report()` now tolerates internal
`Namespace` callers that omit optional CLI-only beta/query artifact fields by treating the
missing fields as `None`.

Validation for this continuation: runtime approved-evidence suite `172 OK`; public
contract + window manifest + runtime-window execution suite `219 OK`; pack/route/
permissions focal suite `17 OK`; public SDK focal pack tests `3 OK`; command route gate
default returned `valid=True` and `accepted_for_planning=True`; touched-file
`git diff --check` passed. No live server/log/Discord/GitHub/tag/publication/process
action occurred. SDK route remained `approved_runtime_evidence_missing`, SDK `0/12`, P0
`0/4`, runtime/public/stable false, source overclaims `0`. The broader command-route
post-evidence suites still have unresolved identity-public-contract scenario failures and
must not be treated as complete SDK evidence.

## Offline Hardening Round, 2026-06-07 03:08Z

This round ran while no testers were available. It did not send Discord, activate a new
runtime window, restart servers, publish, tag, push, or claim SDK/runtime/public
readiness. Latest status remains `approved_runtime_evidence_missing`, next
`approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`.

Integrated facts:

- PluginManager now has player-principal parity for owner cleanup retry setup failure.
  The `plugin_manager_tests` target enables
  `OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS=1`, and
  `TestUnloadAllRetainsPlayerPrincipalDestroyRetryAfterOwnerCleanupSetupFailure` mirrors
  the existing chat/structure retry setup-failure behavior: first unload retains after
  `DestroyUserData` failure, second unload simulates retry setup failure without rerunning
  destroy or closing, third unload retries destroy and then closes with no live
  player-principal subscription.
- Player-principal registry bounded-retention behavior is protected by both C++ behavior
  tests and a Python guardrail that keeps the focused C++ test wired through CMake/CTest.
- Owner-token SDK consumer contract checks now reject direct positive
  permissions/admin and identity lookup wording while still allowing blocked/internal
  fixture language.
- Runtime evidence status reporting treats `arkserver2` / TheIsland as an allowed
  operator-context target under the recorded standing authority, but still classifies all
  such target data as non-evidence until an accepted copied sibling bundle exists.
- Future passive monitors now create and tee the requested `--snapshot-monitor-log`
  before the first session line. This fixes a robustness gap observed in a pre-patch
  monitor root where launcher logs existed but the requested passive monitor path did not.

Rejected shortcut:

- A read-only offline route audit re-confirmed that `HandleNewPlayer(0,1)`,
  `CheckJoinInProgress(0,0)`, `K2_PostLogin`, passive snapshots, query/RCON presence,
  copied-log-only summaries, and more broad static/layout discovery cannot substitute for
  exact `CheckJoinInProgress(1,0)` `session_start_rejected`.

Validation:

- `cmake --build build --target plugin_manager_tests`
- `./build/plugin_manager_tests`
- `ctest --test-dir build -R
  'PluginManagerTests|PlayerPrincipalEventDispatcherTests|PlayerPrincipalRegistryTests'
  --output-on-failure`
- `python3 -m unittest scripts.test_monitor_ark_player_presence_passive`
- `python3 -m unittest scripts.test_player_principal_runtime_guardrails
  scripts.test_report_player_principal_lifecycle_runtime_evidence_status
  scripts.test_check_player_identity_owner_token_sdk_consumer_contract`
- `scripts/report_obelisk_sdk_status.py --compact`
- `git diff --check`

## Offline Hardening Follow-Up, 2026-06-07 03:19Z

This follow-up also ran while no testers were available. It did not touch live servers,
live logs, `/servidor/ark`, Discord, GitHub, tags, or publication. All six delegated
agents were closed; no standby sub-agent remains.

Integrated facts:

- Window request/preflight now names the strict rejected-start copied bool contract:
  `ShooterGameMode.CheckJoinInProgress` with fields `bIsFromLogin,ReturnValue` and values
  `1,0`. The checker rejects packs whose runtime triplet contract mutates those fields or
  values, and the operator-request markdown mirrors the copied-bool shape.
- Evidence-closure diagnostics now expose `strict_rejected_start_*` fields for observed
  invalid shapes such as `CheckJoinInProgress(0,0)` without counting them as approved
  runtime evidence.
- Public contract readiness derives `approved_runtime_evidence_binding` only from a
  checker-accepted approved runtime manifest. A reviewed/current identity decision record
  plus start/end-only runtime evidence remains fail-closed and cannot activate the
  post-approved-runtime gate.
- The next-actions runner rejects positive standing-authority evidence/progress aliases
  and blocks actions with unresolved exact copied lifecycle triplet blockers before they
  can become runner-eligible.
- PluginManager static guardrails now keep player-principal retry setup-failure parity
  wired through the dispatcher test hook.

Validation:

- `python3 -m unittest scripts.test_prepare_player_principal_lifecycle_window_request
  scripts.test_check_player_principal_lifecycle_window_request`: `110 OK`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q
  scripts.test_prepare_player_principal_lifecycle_evidence_closure_request
  scripts.test_run_player_principal_lifecycle_next_actions
  scripts.test_plugin_manager_guardrails scripts.test_report_obelisk_sdk_status`: `179 OK`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q
  scripts.test_prepare_player_principal_lifecycle_window_request
  scripts.test_check_player_principal_lifecycle_window_request
  scripts.test_check_player_identity_public_contract_readiness
  scripts.test_prepare_player_principal_lifecycle_evidence_closure_request
  scripts.test_run_player_principal_lifecycle_next_actions
  scripts.test_plugin_manager_guardrails scripts.test_report_obelisk_sdk_status`: `394 OK`.
- `git diff --check` on touched current files: OK.

Status remains `approved_runtime_evidence_missing`, next
`approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`. The next
runtime window still needs real testers to produce the exact `HandleNewPlayer(1,1)`,
`CheckJoinInProgress(1,0)`, and matched `OnLogout` copied triplet.

## Ragnarok Start/End Evidence And Narrowed Contract Input, 2026-06-07 02:03Z

Runtime facts:

- Target: `arkserver` / Ragnarok, current log window from `2026-06-07T02:03:34Z`.
- Obelisk runtime loaded at `2026-06-07T02:03:34Z`; ProcessEvent hook address
  `0x1d34e20`; lifecycle observer enabled at `2026-06-07T02:04:01Z`.
- The window produced repeated accepted `ShooterGameMode.HandleNewPlayer(1,1)`
  `session_start` events and matched `ShooterGameMode.OnLogout` `session_end` events.
- `ShooterGameMode.CheckJoinInProgress` matched reflection with the newer drift chain,
  but the copied bool observation in this runtime was `(0,0)`, so it remained
  `copy_status=rejected` diagnostic material. No exact approved
  `CheckJoinInProgress(1,0)` rejected-start line was captured.

Copied/offline evidence:

- Evidence root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T020334Z-ragnarok-start-end-evidence`
- `runtime-observer-summary.json`: copied/analyzed observer summary.
- `principal-start-end-evidence.check.json`: `ready=true`,
  `ready_scope=principal_start_end_runtime_evidence_only`, resolves only
  `runtime.lifecycle_start_end_evidence`, and explicitly does not resolve
  `runtime.lifecycle_rejected_start_evidence` or
  `approved_runtime_principal_lifecycle_evidence_bundle`.
- `player-identity-public-contract-start-end-readiness.check.json`: public-contract
  readiness accepts the narrowed input with `ready=true`,
  `ready_scope=contract_review_input_only`, and
  `runtime_contract_input.kind=principal_start_end_runtime_evidence`, while keeping
  `approved_runtime_evidence_present=false`, `runtime_ready=false`,
  `public_sdk_ready=false`, and all SDK/P0/progress claims false.

Reusable conclusion:

- Rejected hypothesis: the current live join/disconnect flows reliably produce exact
  `CheckJoinInProgress(1,0)`. Current evidence shows `CheckJoinInProgress(0,0)`
  diagnostics and safe start/end anchors instead.
- Accepted design adjustment: use the narrowed start/end lane to unblock public-contract
  review work that only needs principal creation/invalidation proof, while leaving the
  strict approved runtime bundle as the blocker for SDK/runtime/public readiness.
- `scripts/report_obelisk_sdk_status.py --compact` intentionally remains strict:
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`.

## Worker 6 Offline Route Audit, 2026-06-07

This audit was offline-only. It did not read live server paths or logs, perform server
operations, run RCON, send Discord, publish, tag, push, or claim runtime/public/SDK
readiness.

Audited answer: waiting for the exact copied
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected` line remains the
fastest valid route. Extra broad diagnostic shape logging is not the primary next action
because current local planning already distinguishes accepted-target copied-observation
rejections from evidence, and newer local runtime/reflection work already records a
bounded `CheckJoinInProgress` drift chain. A different map/tester flow is not justified
by offline evidence alone; any map or tester change remains a lead/operator-scoped
runtime choice, not a planning shortcut. More offline layout/static discovery is also
not the route blocker for the current binary.

The concrete offline planning change from this audit is to make the non-claiming route
preference machine-readable: `plan_player_principal_lifecycle_next_actions.py` and
`check_player_principal_lifecycle_planning_blocker_smoke.py` now emit a
`route_audit` block with `current_blocker=approved_runtime_evidence_missing`, the exact
missing runtime shape, and explicit false flags for diagnostic-first, map/tester-first,
and offline-layout-first priority. This is planning metadata only; it does not authorize
runtime work or convert copied-observation rejection material into evidence.

Recommended next action remains route-blocked and narrow: under a separately approved
player-backed runtime window, obtain accepted `HandleNewPlayer(1,1)` `session_start`,
exact copied `CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`OnLogout` `session_end` in an accepted sibling-set bundle. If the exact rejected-start
role is missing or only diagnostic/passive material exists, stop at the missing-role
result.

## Ragnarok Restart, 2026-06-07 00:31Z

The operator requested restarting Ragnarok so testers could move from TheIsland to
Ragnarok and test the installed runtime. The lead verified the cluster stayed at two ARK
servers, broadcast a 60-second warning on Ragnarok after RCON reported one redacted
player, restarted only `arkserver` / Ragnarok, and broadcast on TheIsland after Ragnarok
returned. TheIsland stayed running; Genesis2 was not started and no three-server condition
occurred.

Facts observed after restart:

- ARK processes: TheIsland PID `2994420` and Ragnarok PID `3238306`, both with
  `-ActiveEvent=Summer`.
- Ragnarok RCON responded after warm-up with zero redacted players.
- Ragnarok log shows Obelisk loaded at `2026-06-07T00:31:40Z`, ProcessEvent absolute x64
  hook installed, ReflectionScanner disabled, plugins disabled, and
  `PlayerPrincipalLifecycleObserver enabled` at `2026-06-07T00:32:07Z` with binary SHA
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, log limit `10`,
  and dispatch limit `0`.
- No new runtime install, backup, publication, tag, push, Plugin Hub action, or readiness
  claim occurred in this restart step.
- After restart, Ragnarok emitted a fresh `HandleNewPlayer(1,1)` `session_start` at
  `2026-06-07T00:33:08Z` plus the expected non-anchor `K2_PostLogin` diagnostic
  rejection. RCON reported one redacted player, the lead broadcast an instruction to
  disconnect once from Ragnarok rather than cluster-transfer, and a recheck at
  `2026-06-07T00:37:07Z` still showed one redacted player with no `session_end` yet.

Runtime signal before this restart was useful but still non-evidence. The `00:14Z`
Ragnarok run captured `HandleNewPlayer(1,1)` `session_start`, a
`CheckJoinInProgress` accepted-target copied-observation rejection logged as
`copy_status=rejected`, a superseded/non-approved `HandleNewPlayer(0,1)` rejected-start
shortcut, matched `OnLogout` `session_end`, and another start. This validates that the
observer can see the lifecycle edges, but it still cannot clear
`approved_runtime_evidence_missing`: the accepted bundle path requires exact
`CheckJoinInProgress(1,0)` `session_start_rejected` in a valid
`<YYYYMMDDTHHMMSSZ-player-principal-lifecycle>` evidence root with sibling sidecars.

## Supervised Route Audit And Ragnarok Follow-Up, 2026-06-07 00:54Z

A six-worker supervised round kept the route blocked and improved guardrails around the
same blocker. The analyzer now accepts the hook's safe accepted-target
`CheckJoinInProgress` copied diagnostic shape only as `copy_status=rejected`
diagnostic-only material. Evidence copy/bundle/checker fixtures now reflect that
diagnostic-only material and the current approved rejected-start shape. Public-contract
readiness scanning blocks lookup/resource-handle/ownership/permissions/commands terms in
the public-header review path. Package-shape wording now consistently distinguishes the
allowed explicit-version non-`EXACT` CMake request from forbidden `EXACT` stable-readiness
claims. The route audit conclusion is unchanged: exact copied
`CheckJoinInProgress(1,0)` remains the fastest valid route, while broad diagnostics,
map/tester changes, and more offline layout discovery are not primary next actions.

Live follow-up facts:

- Old pre-fix passive monitor timeout parents `3125910` and `3151001` were stopped.
- New passive monitor root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T004139Z-ragnarok-postrestart-monitor`.
  Timeout PID `3297045`, child PID `3297046`.
- The monitor logged per-target snapshot policy and captured Ragnarok passive snapshots
  `seq1` at `2026-06-07T00:41:51Z` and `seq2` at `2026-06-07T00:43:54Z`; these are
  passive non-evidence and do not count toward SDK/P0/runtime readiness.
- Ragnarok emitted `HandleNewPlayer(1,1)` `session_start` at `2026-06-07T00:33:08Z`,
  matched `OnLogout` `session_end` at `2026-06-07T00:43:14Z`, and another
  `HandleNewPlayer(1,1)` `session_start` at `2026-06-07T00:43:36Z`.
- RCON at `2026-06-07T00:54:40Z` still reported one redacted Ragnarok player.

Analyzer summary for the live Ragnarok log remains blocked: accepted roles are
`session_start,session_end`, missing role is `session_start_rejected`, malformed lines
`0`, approved runtime evidence `false`. The status helper still reports
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable false.

## Ragnarok Runtime Refresh, 2026-06-07 00:14Z

The operator explicitly requested restarting Ragnarok so testers can transfer from
TheIsland to Ragnarok and test the new runtime. The lead used the standing launch
authorization plus this current-turn request, broadcast the transfer instruction through
RCON, stopped only `arkserver` / Ragnarok, verified TheIsland stayed alive, and restarted
Ragnarok in observer-debug mode. No Genesis2 start occurred and no three-server condition
occurred.

Facts observed:

- Current ARK processes after restart: TheIsland PID `2994420` and Ragnarok PID
  `3102370`, both with `-ActiveEvent=Summer`.
- Ragnarok ports were listening after start: game UDP `7777`, query UDP `27015`, and
  RCON TCP `27020`.
- The current built runtime had been installed to `/servidor/ark/obelisk` without
  `--backup-existing`; installed runtime SHA256
  `e9a4bee9807f33e7993ca7bd1adbe296de25232e1a66f90a9720086a641ace2a`.
- Ragnarok log shows runtime loaded at `2026-06-07T00:14:51Z`, ProcessEvent absolute x64
  hook installed, ReflectionScanner disabled, plugins disabled, and
  `PlayerPrincipalLifecycleObserver enabled` at `2026-06-07T00:15:19Z` with binary SHA
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, log limit `10`,
  and dispatch limit `0`.
- Posture check passed in `player-principal-lifecycle-observer-debug` mode.
- RCON broadcasts were accepted on TheIsland and Ragnarok. Raw `ListPlayers` output must
  not be quoted; use only redacted counts.
- A two-hour passive monitor was started at
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T001703Z-ragnarok-runtime-monitor/passive-monitor.log`
  with snapshots under
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T001703Z-ragnarok-runtime-monitor/snapshots`.
  First tick saw Ragnarok `0/70` by query/RCON and TheIsland one redacted RCON player,
  then copied passive non-evidence snapshot
  `passive-detect-20260607T001737Z-arkserver2-3125911`.

Runtime-diagnostic patch deployed for this run: accepted lifecycle targets whose copied
observation is rejected now log `reflection_status=matched copy_status=rejected` rather
than suggesting reflection/FName drift. This keeps copied-evidence acceptance fail-closed;
it only makes the diagnostic channel less misleading. Validation passed for the lifecycle
build target, analyzer tests, lifecycle CTest, the player-principal guardrail/analyzer/
passive monitor Python suite, and `git diff --check` on touched files.

Evidence status is still blocked. TheIsland's prior candidate sequence on the old runtime
contained `HandleNewPlayer(1,1)`, a copied-observation rejection for
`CheckJoinInProgress`, a superseded/non-approved `HandleNewPlayer(0,1)` rejected-start
shortcut, matched `OnLogout`, and another session start. Copy dry-runs still reject it:
the full window is ambiguous/duplicate and the narrow window lacks exact approved
`CheckJoinInProgress(1,0)` `session_start_rejected`. Therefore SDK/P0 progress remains
`0/12` and `0/4`, route `approved_runtime_evidence_missing`.

## Ragnarok Drift Refresh, 2026-06-06 23:32Z

During the current-window beta flow for
`20260606T232745Z-player-principal-lifecycle`, Ragnarok produced a safe diagnostic
rejection for `ShooterGameMode.HandleNewPlayer`:

- target: `ShooterGameMode.HandleNewPlayer`
- FName index: `2170`
- copied params/identity: not logged
- evidence claim: none
- rejection reason: `lifecycle_property_FName_mismatch`
- observed complete property-name chain:
  `{28414,21310,22964,28512,17720}`

This was useful diagnosis, not accepted runtime evidence. The runtime/reflection patch
now whitelists that chain only as a complete chain alongside prior known Ragnarok
chains; mixed variants still reject. The server was then rebuilt, installed to
`/servidor/ark/obelisk` without `--backup-existing`, and only `arkserver` / Ragnarok was
restarted after GameDig reported `0/70` and no observer `session_start` was present.
TheIsland and Genesis2 were not started, so no three-server condition occurred.

Post-restart facts:

- Ragnarok PID `2790453`, `-ActiveEvent=Summer`.
- Runtime loaded at `2026-06-06T23:32:08Z`.
- ProcessEvent absolute x64 hook installed.
- Plugins disabled.
- `PlayerPrincipalLifecycleObserver enabled` at `2026-06-06T23:32:30Z` with binary SHA
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, log limit `10`,
  dispatch limit `0`.
- Posture check passed in `player-principal-lifecycle-observer-debug` mode.
- Beta notice dry-run and confirmed send completed for the current window; the notice is
  a required player action, not evidence.

Validation: lifecycle C++ build targets passed; CTest for
`ProcessEventPlayerPrincipalLifecycleObserverTests`,
`PlayerPrincipalLifecycleApplicatorTests`, and `PlayerPrincipalLifecycleReflectionTests`
passed `3/3`; analyzer/passive-monitor focal Python tests passed `79 OK`; `git diff
--check` on touched runtime/reflection files passed. SDK status remains blocked at
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.

Player-connected restart rule retained for future turns: restart a server with connected
players only when it is 100% necessary to advance ObeliskSDK; if unavoidable, broadcast
with a prudent timer and keep one cluster server available for transfer while preserving
the two-server maximum.

Follow-up without restart, 2026-06-06 `23:33Z`-`23:38Z`: the post-patch Ragnarok
observer accepted `ShooterGameMode.HandleNewPlayer` as `session_start` at
`23:33:22Z`, then saw `ShooterGameMode.OnLogout` at `23:37:23Z` but rejected it with a
safe diagnostic-only `lifecycle_property_FName_mismatch` because the observed `Exiting`
property name index was `28546` instead of the exact expected `28543`. A second
`session_start` was accepted at `23:38:02Z`. This is useful runtime progress but not
approved evidence: the copied approved triplet is still missing exact
`CheckJoinInProgress(1,0)` `session_start_rejected` and matched `session_end` proof.

The lead added a local, not-yet-deployed recognizer patch for the exact
`OnLogout` drift `28546`, alongside prior known `OnLogout` drift indices `28550` and
`28549`; unapproved indices still reject. Lifecycle build targets passed, CTest for
`ProcessEventPlayerPrincipalLifecycleObserverTests`,
`PlayerPrincipalLifecycleApplicatorTests`, and `PlayerPrincipalLifecycleReflectionTests`
passed `3/3`, and `git diff --check` on the touched runtime/reflection paths passed.
The operator then instructed not to restart and to continue another front, so the patch
remains local until a future restart is 100% necessary for ObeliskSDK progress. A focal
search did not find a real runtime `CheckJoinInProgress` drift line, so no speculative
`CheckJoinInProgress` whitelist was added.

## Ragnarok Runtime Refresh, 2026-06-06 23:09Z

After the operator reported no users, the lead used the recorded standing launch
authorization to deploy the current runtime and restart only `arkserver` / Ragnarok. This
was a debug-runtime preparation step, not approved lifecycle evidence.

Facts observed:

- `cmake --build build --target obelisk` linked `libobelisk.so`; the build emitted
  third-party `fmt/spdlog` GCC warnings but completed successfully.
- `scripts/install_obelisk.sh --build-dir build /servidor/ark/obelisk` ran with
  `OBELISK_ALLOW_SERVER_ROOT_WRITES=1` and without `--backup-existing`, leaving no new
  `.bak` or `.install-*` files under the Obelisk root.
- The active LinuxGSM wrapper was updated from `packaging/linuxgsm/ObeliskRun.sh`; its
  SHA matched after deployment:
  `cacde0d4e296436abb7c7275d9e179057defe3494c27eb8f2bbbb36deaf8439c`.
- Only Ragnarok was restarted through LinuxGSM with the tmux environment unset; TheIsland
  and Genesis2 were not started, and no three-server condition occurred.
- Post-restart PID `2658353` was observed for Ragnarok with `-ActiveEvent=Summer`.
- Posture JSON passed in `player-principal-lifecycle-observer-debug` mode for
  `arkserver`, with ProcessEvent hook enabled, plugins disabled, observer markers/env
  active, and all runtime/public/evidence readiness claims false.
- `Obelisk.log` showed runtime loaded at `2026-06-06T23:09:35Z`, ProcessEvent absolute
  x64 hook installed, plugins disabled, and `PlayerPrincipalLifecycleObserver enabled` at
  `2026-06-06T23:10:11Z` with binary SHA
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, limit `10`, and
  dispatch limit `0`.
- Passive monitor after the restart reported GameDig `0/70`, RCON timeout/unknown,
  observer enable/diagnostic lines only, no lifecycle roles, `approved_runtime_evidence=false`,
  and `player_presence_context unknown_player_context=true`.
- No beta Discord notice was sent for this refresh. A dry-run against the historical
  `20260606T203359Z` request produced an `@everyone` payload, but its embedded time window
  was stale, so it was not suitable for current tester recruitment.

Validation in the same lead round: lifecycle/public/planning/passive Python suite
`224 OK`, downstream P0 suite `252 OK`, MOTD normalizer `4 OK`, C++/ABI CTest `6/6`,
`bash -n` and touched Python `py_compile` passed. SDK status remained blocked at
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable false.

## Genesis2 Runtime Window Attempt, 2026-06-06 16:29Z

Standing operator authority was bound for run
`20260606T162929Z-player-principal-lifecycle` on `arkserver3` / Genesis2. The evidence
directory was
`/servidor/ark/workspace-offline/live-validation-logs/20260606T162929Z-player-principal-lifecycle`;
the preparation report directory was
`/servidor/ark/workspace-offline/live-validation-logs/runtime-window-prep-report-arkserver3-20260606T162420Z`.

Facts observed:

- The guarded beta testers notice was dry-run checked and then sent before activation.
- Genesis2 started under the observer-debug profile inside the requested window.
- `PlayerPrincipalLifecycleObserver enabled` appeared in-window with the expected binary
  SHA, `limit=10`, and `dispatch_limit=0`.
- Query stayed `0/70`, and the operator later reported no users online.
- No accepted `session_start`, `session_start_rejected`, or `session_end` roles appeared.
- `copy_player_principal_lifecycle_ready_log.py` wrote `ready-log-copy.json` with
  `copy_readiness=blocked_missing_lifecycle_roles`, `copied=false`, and all three roles
  missing. No copied `Obelisk.log` was produced.
- Genesis2 was stopped afterward, observer markers were removed, and only Ragnarok was
  observed running.

Tooling lesson promoted from this attempt:

- `ready-log-copy.json` and generated `operator-approval-receipt.template.json` are
  auxiliary non-evidence sidecars, not invalid unexpected JSON sidecars.
- Closure-generated copy commands must include
  `--json-output <evidence_dir>/ready-log-copy.json`.
- A valid confirmed beta notice JSON should complete the notice requirement for the
  current window and must not cause closure/status tooling to request another Discord
  send. The notice remains context only and does not authorize runtime work or count as
  evidence.

Validation after the tooling fix: closure/status unittest `63 OK`; evidence bundle
unittest `98 OK`. Actual closure/status reports still block on missing lifecycle roles
and missing copied/bundled artifacts; no approved runtime evidence or SDK progress is
claimed.

## Evidence Files Inspected

- `scripts/analyze_runtime_observer_log.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_evidence.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
- `scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`
- `scripts/monitor_ark_player_presence_passive.sh`
- `scripts/test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
- `scripts/test_build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`
- `scripts/test_monitor_ark_player_presence_passive.py`
- `hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp`
- `hooks/ProcessEventPlayerPrincipalLifecycleApplicator.cpp`
- `hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.cpp`
- `ue/PlayerPrincipalLifecycleReflection.cpp`
- `tests/core/ProcessEventPlayerPrincipalLifecycleObserverTests.cpp`
- `tests/core/PlayerPrincipalLifecycleApplicatorTests.cpp`
- `docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md`
- `docs/research/2026-06-01-player-principal-runtime-observer-brief.md`
- `docs/research/2026-06-01-player-principal-runtime-capture-plan.md`
- `docs/research/2026-06-01-player-identity-runtime-capture-readiness-checklist.md`
- `docs/research/2026-06-01-player-identity-lifecycle-route-audit.md`
- `docs/research/2026-06-04-lifecycle-anchor-fname-drift-delta.md`
- `docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md`
- `docs/player_identity_public_contract_decisions.json`

## Required Lifecycle Roles

The accepted runtime lifecycle evidence shape is exactly the ordered observer
role triplet:

```text
session_start -> session_start_rejected -> session_end
```

The strict Genesis2 evidence strategy requires these role-specific proofs. A
line counts only when the copied observer event, analyzer summary, bundle
builder, and approved-evidence checker all accept the same ordered role;
hook-side diagnostics or partial tool acceptance stay non-evidence.

- `session_start`: `ShooterGameMode.HandleNewPlayer`, copied bool fields
  `bIsFromLogin,ReturnValue`, copied bool values `1,1`,
  redacted fields `NewPlayer,PlayerData,PlayerCharacter`,
  `principal_action=candidate_created`,
  `apply_status=session_start_created`,
  `correlation_status=not_applicable`.
- `session_start_rejected`: the only approved copied-observer alternative is the exact
  post-original `ShooterGameMode.CheckJoinInProgress` observer line with
  `bIsFromLogin=true`, `ReturnValue=false`, redacted field `NewPlayer`,
  `principal_action=none`, `apply_status=session_start_rejected_noop`, and
  `correlation_status=not_applicable`. `HandleNewPlayer` rejected tuples (`0,1`,
  `1,0`, or `0,0`) are now rejected by the approved checker as ambiguous shortcuts.
  `CheckJoinInProgress` is an observer alternative only, not a promoted lifecycle
  anchor. The line is evidence only if the analyzer, bundle builder, and approved
  checker all accept it as the ordered `session_start_rejected` role; otherwise it
  remains candidate-only.
- `session_end`: `ShooterGameMode.OnLogout`, no copied bool fields or values,
  redacted field `Exiting`,
  `principal_action=candidate_invalidated`,
  `apply_status=session_end_invalidated`,
  `correlation_status=matched`.

All accepted event lines must be post-original, redacted, and free of player
identifiers, UE pointers, raw params, FName/GObjects indices, `ResourceHandle`,
commands, chat text, permissions/admin state, or plugin subscriber state.

## Passive Ticks Are Non-Evidence

Passive monitor output can report player presence, observer tails, diagnostic
candidate lines, or even a complete role triplet candidate, but it is explicitly
classified as non-evidence:

- the passive monitor emits `process_control=none`,
  `approved_runtime_evidence=false`, `ready=false`, and
  `evidence_classification=passive_*_non_evidence`;
- passive snapshots are copy/analyze-only and record
  `snapshot_counts_as_approved_runtime_evidence=false`;
- `analyze_runtime_observer_log.py` keeps runtime observer summaries
  `approved_runtime_evidence=false` and `runtime_evidence_ready=false`;
- the approved-evidence checker rejects passive monitor logs, passive snapshots,
  passive activity triage, diagnostic-only material, and copied monitor metadata
  as approved runtime evidence shortcuts.

The 2026-06-04 passive-drift note records connected Ragnarok players with copied
passive diagnostics. Its old "drift equals diagnostic/non-evidence" wording is
stale for current recognizer behavior: known `HandleNewPlayer` and `OnLogout`
FName drift chains are now recognized only as recognizer-only alternatives under the full
copied lifecycle shape and observer gates. The passive Ragnarok artifact itself still
remains non-evidence until an approved sibling-set bundle is built and accepted.

Rejected hypothesis: passive monitor ticks, public-query activity, copied passive
snapshots, or a passive complete triplet can clear `approved_runtime_evidence_missing`.
They cannot.

## Accepted Analyzer And Bundle Requirements

`check_player_identity_runtime_principal_lifecycle_evidence.py` is only a
synthetic/redacted shape-fixture guard. It does not approve runtime evidence.

`analyze_runtime_observer_log.py` can summarize a copied log and identify the
role triplet, but its summary is observational-only. For later approval, the
summary must have one `player_principal_lifecycle` module, one observer gate,
current binary SHA
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
observer limit `10`, dispatch limit `0`, `delivery_claim=none`,
`principal_claim=none`, expected hook/runtime posture, quality counters at zero,
no passive metadata, no diagnostics, no rejected-only material, no unapproved
detail keys, and exactly the three required accepted event cases in order.
For Genesis2/Ragnarok, `session_start_rejected` must be filled by exact
`CheckJoinInProgress(1,0)` as an observer-only alternative. `HandleNewPlayer`
rejected tuples are no longer approved runtime evidence. `CheckJoinInProgress`
is not promoted lifecycle-anchor evidence; it must be accepted here and then
survive bundle generation and consume-mode checker validation. Analyzer-only or
bundle-only recognition is not enough.

`check_player_identity_runtime_principal_lifecycle_approved_evidence.py` can
accept consume-only runtime evidence only when the manifest binds that clean
summary to an approved operational window and sibling artifact set. It also
requires fail-closed consumer boundary cases for `stale_after_logout` and
`malformed_or_unsupported_evidence`, a privacy boundary that allows only copied
opaque principal evidence, and false public/runtime/promotion readiness flags.
Even accepted consume mode advances only to
`identity_public_contract_gate_missing`; promote, public-readiness, and
runtime-readiness modes still fail closed.

`build_player_identity_runtime_principal_lifecycle_evidence_bundle.py` requires
the copied log under an approved offline workspace path shaped like
`live-validation-logs/<run-id>/Obelisk.log`, exact sibling sidecars
(`window-request.json`, `observer-window.env`, `operator-approval-request.md`,
completed `operator-approval-receipt.json`, `preflight-pre.json`,
`preflight-post.json`, `window-manifest.env`), and the approved output manifest at
`approved-bundle/approved-runtime-principal-lifecycle-evidence.json`. Required
sidecars and generated bundle reports must not carry readiness, authorization,
publication, public SDK, or progress overclaims.

## Likely Function Anchors

The approved bundle path is still narrower than the local hook-side recognizer.
For the current binary hash, treat the following as binary-scoped anchors, not
portable SDK constants:

- `ShooterGameMode.HandleNewPlayer` (`fname_index=2170`): accepted start
  anchor. The strict `session_start` case is
  `bIsFromLogin=1,ReturnValue=1` with
  `apply_status=session_start_created` and
  `correlation_status=not_applicable`. Current recognition also accepts known
  `HandleNewPlayer` FName drift chains for the accepted start case only. Rejected-start
  bool tuples (`0,1`, `1,0`, `0,0`) are not approved runtime evidence and must not be
  used to satisfy `session_start_rejected`.
- `ShooterGameMode.OnLogout` (`fname_index=2384`): only approved end anchor.
  Current recognition also accepts known `OnLogout` FName drift chains, but an
  `OnLogout` sighting is not enough; accepted evidence requires
  `apply_status=session_end_invalidated` and `correlation_status=matched` from
  the private process-local correlation path.
- `ShooterGameMode.CheckJoinInProgress` (`fname_index=1845`):
  `session_start_rejected` observer alternative only. The only candidate shape
  for this function is the exact post-original copied line
  `CheckJoinInProgress(bIsFromLogin=true,ReturnValue=false)` with no principal
  creation and `session_start_rejected_noop/not_applicable`. It counts only if
  the analyzer, bundle builder, and approved checker accept that copied line;
  otherwise preserve it as candidate evidence and keep the bundle incomplete.
  Do not promote it into lifecycle anchor binding.
- `GameMode.K2_PostLogin`, `ShooterGameMode.OnPostLogin__DelegateSignature`,
  and `ShooterGameMode.OnStartNewPlayer__DelegateSignature`: diagnostic or
  guidance-only anchors. They can help explain organic join chronology, but they
  copy no approved principal lifecycle evidence and cannot clear any required
  role.

Admin/listing surfaces such as `ServerListPlayers` and `ServerKickPlayer`,
public query state, player counts, and `ShooterPlayerController` or
`ShooterPlayerState` activity remain non-anchors for this blocker.

## Genesis2 Organic Capture Strategy

This strategy applies to Genesis2 runtime work only while the recorded
2026-06-06 standing debug authority remains unretracted, or under a future
exact current-turn approval with the same safety limits. This note itself does
not create or widen approval to read live logs, edit markers/env, restart, wait
on players, send notices, or capture runtime evidence.

The practical ordering target is:

```text
accepted HandleNewPlayer session_start while the player remains present
-> accepted CheckJoinInProgress(true,false) session_start_rejected line
-> matched OnLogout session_end for the accepted start subject
```

That order matches the checker-required
`session_start -> session_start_rejected -> session_end` sequence and gives
`OnLogout` a chance to match the process-local subject token bound by the prior
accepted start. A logout before the accepted start, a logout for an uncorrelated
subject, or a process/restart boundary cannot become `session_end` evidence.

For a player-backed window, the applicable standing or current-turn authority
must name the player policy and notice path. If beta/user notice is required,
the approved dry-run-checked notice must be sent before activation or waiting
begins. Notice artifacts prove communication only; they do not count as runtime
evidence.

Recommended capture posture for the future window:

- Keep the first-window budget at `10`, dispatch limit at `0`, plugins
  disabled, scanner/native-exec/ptrace/gcore/broad tracing off, and unrelated
  observer families off.
- Capture one accepted Genesis2 `HandleNewPlayer` start first. Do not let the
  start player leave until the rejected-start role has been attempted, because
  an early logout can consume the only correlated end signal before the required
  rejected role exists.
- Try to obtain the strict `CheckJoinInProgress(bIsFromLogin=true,
  ReturnValue=false)` rejected-start line organically, without RCON, admin
  mutation, synthetic fixtures, forced server state changes, or broad
  ProcessEvent tracing. If any analyzer, bundle, or checker stage rejects that
  copied line, preserve it as candidate evidence only and do not claim the
  approved bundle is complete.
- After the rejected-start role is observed, have the accepted start subject
  leave cleanly only within the approved runbook. The required end line is
  valid only if the copied log reports `session_end_invalidated/matched`;
  unresolved, missing, duplicate, or stale logout correlation stays
  non-evidence.
- If the rejected-start role or any later role is missing, stop at a
  missing-role result. Do not extend the window, switch maps, start another
  server, deploy a different build, or use
  passive waiting as a shortcut unless the recorded standing authority or a new
  current-turn approval explicitly scopes that work.

Genesis2-specific prior passive context is useful only as risk evidence:
Genesis2 passive material has shown start and rejected-start activity but still
lacked `session_end`, while Ragnarok has historical passive complete-triplet
diagnostics. Both remain non-evidence until the approved sibling-set bundle
passes.

## Standing-Authority Runner Posture

As of the 2026-06-06 local handoff, the operator posture is Obelisk-debug-first:
the cluster servers are debug targets until ObeliskSDK is ready, but the safety
floor remains no secrets, no raw player text, warn/schedule before restarts with
connected players, rollback preserved, ARK concurrency at two or fewer, and
never three ARK servers.

The current Genesis2 posture is passive wait on the same run id,
`20260606T051057Z-player-principal-lifecycle`: `arkserver3` / Genesis2 is the
only observed ARK server in the latest handoff, the player-principal lifecycle
observer is active, the extended monitor is passive/read-only, latest query was
`players=0/70`, and no accepted lifecycle roles were present. The status remains
`blocked_missing_lifecycle_roles`, missing `session_start`,
`session_start_rejected`, `session_end`, `window-manifest.env`,
`preflight-post.json`, and the approved bundle manifest.

Next runner action under standing authority is narrow: continue the exact
Genesis2 lifecycle window for missing roles, keep the beta notice path as an
operator action rather than evidence, then complete checked sibling artifacts
for the same copied run only after the required role triplet exists. No evidence
claim is valid until the copied `Obelisk.log`, approval receipt, pre/post
preflight, window manifest, and generated approved bundle pass the approved
evidence checker in consume mode. Even that result would answer only
`approved_runtime_evidence_missing`; it would not be SDK readiness, stable
readiness, public readiness, Plugin Hub readiness, publication authority, or a
public/stable SDK claim.

## Machine Next-Actions Runner Boundary

The new machine-next-actions path is a planner/normalizer for lead review. Its
design assumptions are:

- Inputs are already-produced offline JSON reports from the runtime-window
  executor, activation preconditions, beta notice prep, runtime status, and
  closure request tools.
- Output is a deterministic action queue with `runner_contract`,
  `runner_command`, and `runner_operation` payloads, all carrying
  `execute_by_default=false` and non-authorization text.
- The offline normalizer does not send Discord, operate ARK, read live logs,
  edit marker/env files, copy `Obelisk.log`, build approved bundles, or convert
  passive/status output into evidence.
- Recorded standing authority is treated as scope provenance for the lead-runner
  path. It is not a command to auto-execute side effects from a generated JSON
  report.

Current live blocker for the active Genesis2 run remains two-part: there is no
copied approved-sibling `Obelisk.log` for the run, and the lifecycle role triplet
is still missing (`session_start`, `session_start_rejected`, `session_end`).
The latest passive state also reported `players=0/70`, so no player-backed
missing-role capture is available to consume.

Before player lifecycle evidence exists, executable work is limited to
offline/report-only actions: regenerate or review request packs, dry-run notice
prep, activation-precondition reports, route/status/closure reports, machine
next-action normalization, and repo-local checker or fixture validation against
sanitized inputs or copied offline artifacts. If a notice path is later executed
under exact lead/operator scope, the notice remains communication proof only.

Work that must wait on the copied lifecycle role triplet includes copying and
binding the run's `Obelisk.log`, writing checked post-window sidecars, building
the approved bundle, running consume-mode approved-evidence checks for the
bundle, advancing to public identity contract review, and unblocking downstream
permissions/admin, command response, commands/replies, SDK/P0, publication, or
Plugin Hub work. Generated machine actions may name those follow-ups, but the
generated plan is not their execution.

## Rejected Hypotheses And Non-Evidence Boundaries

Rejected hypotheses to keep future workers from repeating dead ends:

- Passive Genesis2 start/rejected-start lines plus a public query showing player
  count changes can substitute for a copied approved bundle. They cannot.
- A Ragnarok passive complete triplet can stand in for Genesis2 missing roles.
  It cannot; it is diagnostic-only and map/window scoped.
- Any `OnLogout` line proves `session_end`. It does not; only
  `session_end_invalidated` with `correlation_status=matched` is accepted.
- `CheckJoinInProgress(1,0)` by itself is approved rejected-start evidence. It
  is not; it must be copied post-original and accepted by the analyzer, bundle
  builder, and approved checker as the ordered `session_start_rejected` role.
- `K2_PostLogin`, lifecycle delegate signatures, admin/listing calls, public
  reachability, query-player counts, beta notice receipts, passive monitor
  ticks, closure requests, copied diagnostics, package metadata, Plugin Hub
  aliases, status aliases, or old-format observer lines without
  `apply_status`/`correlation_status` can clear
  `approved_runtime_evidence_missing`. They cannot.
- Recording raw player data, player names, platform ids,
  controller/player-state identity, UE pointers, FName/GObjects indices, raw
  params, chat/command text, `ResourceHandle`, or hashes of redacted identity
  values would strengthen the bundle. It would not; such material must not be
  logged, copied into Git, or used as evidence for this route.

Exact non-evidence boundary: an artifact is not approved runtime evidence unless
the copied offline log, post-window manifest, approval receipt, pre/post
preflight sidecars, and generated approved bundle all satisfy the approved
checker in consume mode while promote, public-readiness, and runtime-readiness
modes still fail closed.

## Offline And Static Evidence To Gather Next

The next offline/static work should be bounded to capture feasibility. It should
not restart broad FName/GObjects/core discovery for the current binary hash.

- Confirm the `CheckJoinInProgress` acceptance chain before relying on it in a
  Genesis2 plan. The local hook/applicator path supports
  `CheckJoinInProgress(bIsFromLogin=true,ReturnValue=false)` as a no-principal
  rejected-start observation, but strict evidence requires the analyzer, bundle
  builder, and approved checker to accept the copied observer line. If any
  stage rejects it, keep the line candidate-only and do not claim bundle
  completion.
- Build a small static anchor table for `HandleNewPlayer`, `OnLogout`,
  `CheckJoinInProgress`, `K2_PostLogin`, and the two lifecycle delegate
  signatures from a non-protected offline binary artifact. Record binary SHA,
  commands/tool versions, string/name registration evidence, function flags,
  `ParmsSize`, `NumParms`, property order, bool metadata, and why each target is
  accepted, candidate-only, or rejected.
- Add or preserve analyzer fixtures for the failure modes that matter to
  Genesis2: accepted start with no later matched logout, rejected-start-only
  material, `CheckJoinInProgress` candidate material, unsupported copied
  `CheckJoinInProgress` bool tuples other than `true,false`, old-format event
  lines, `session_end_unresolved_noop`, `session_end_duplicate_noop`, and
  `session_end_stale_noop`.
- Before any approved runtime window, rerun only repo-local shape and checker
  commands against sanitized fixtures or copied offline artifacts to confirm the
  required observed-event set, target-set revision, binary SHA, and sidecar
  bundle contract are still current.

## Feasibility Risk

The route is feasible only through a current-turn approved runtime window that
captures the exact copied lifecycle triplet and accepted sibling-set bundle.
The risky role is `session_start_rejected`: the likely strict Genesis2 path is
`CheckJoinInProgress(bIsFromLogin=true,ReturnValue=false)`, but partial observer
recognition is not enough and the repository has no accepted artifact proving a
safe deterministic organic way to obtain the checker-accepted rejected role on
demand. Prior organic/passive observations include missing roles, diagnostic
FName drift, historical old-format candidate material, Genesis2 missing
`session_end`, and Ragnarok passive complete-triplet non-evidence.

Do not answer that risk with passive waiting alone, stale prior approval, broad
FName/GObjects scans, live-log reads, extra servers, or server operations outside
an exact current-turn approval. If the future window is player-backed, the
approved dry-run-checked notice must be sent before activation, restart, capture,
or player-backed waiting begins; notice artifacts still are communication proof
only, not runtime evidence.

## Current Conclusion

The active blocker remains `approved_runtime_evidence_missing`. The next useful
evidence is not more offline layout discovery; it is a consume-only copied
runtime lifecycle evidence bundle whose ordered roles are accepted
`HandleNewPlayer` `session_start`, analyzer/bundle/checker-accepted
`CheckJoinInProgress(true,false)` `session_start_rejected`, and matched
`OnLogout` `session_end`, followed by separate public identity contract review.
This note makes no runtime, public SDK, promotion, or readiness claim.

## 2026-06-06 10:33 CEST Update

The debug-first path now has a mechanical copied-log readiness bridge:

- `scripts/copy_player_principal_lifecycle_ready_log.py` checks the live/candidate
  `Obelisk.log` for observer enable plus accepted `session_start`,
  `session_start_rejected`, and `session_end` role proofs before copying into the
  approved evidence directory. It is dry-run by default, requires explicit live-log-read
  and evidence-dir-write flags for execution, and still makes no evidence/readiness
  claim.
- Closure/status now emit the copied-log action before `window-manifest.env`,
  `preflight-post.json`, and approved-bundle actions. The current plan has
  `action_count=8`; with evidence writes allowed the first eligible action is
  `closure_missing_obelisk_log`, but the helper currently reports
  `blocked_missing_lifecycle_roles`.
- The next-action runner now invokes repo `.py` and `.sh` actions through
  `python3`/`bash`, so planned actions do not depend on script executable bits.
  Evidence-dir writes require `--allow-evidence-dir-writes`.
- The approved-evidence checker allows analyzer lifecycle metadata fields only under
  `$.source_summary.modules.player_principal_lifecycle`; the same route remains
  fail-closed for status/passive/notice/shortcut aliases.

Runtime state at this checkpoint: only `arkserver3`/Genesis2 is running, the passive
monitor is active, latest tick is `2026-06-06T08:31:43Z`, players are `0/70`, the
observer enable line is present, and no lifecycle roles have appeared. No
`Obelisk.log` was copied and no approved runtime evidence was produced.

## 2026-06-06 14:26 CEST Post-Reboot Window Update

After host reboot, the debug posture was restored under the recorded standing launch
authorization with exactly two ARK servers running: `arkserver3` / Genesis2 PID `45046`
and `arkserver` / Ragnarok PID `48047`; `arkserver2` / TheIsland remains off. Both
running commands include `-ActiveEvent=Summer`.

The current passive monitor is intentionally longer than the requested 2-hour wait:
`timeout 21600` with PIDs `72760`/`72761`, log
`/servidor/ark/workspace-offline/live-validation-logs/20260606T051057Z-player-principal-lifecycle/post-reboot-passive/monitor.log`,
and snapshots under the sibling `snapshots/` directory. Latest checked tick
`2026-06-06T12:25:34Z` reports Genesis2 and Ragnarok query OK, both `0/70`, observer
enabled, and no lifecycle roles. The confirmed beta tester notice JSON is
`/tmp/obelisk-beta-notice-confirmed-post-reboot.json`.

Reporter and closure tooling now preserve the post-reboot monitor path and confirmed beta
notice path as non-evidence operator context through status and machine-next-action
reports. A real status report remains `blocked_missing_lifecycle_roles`, missing
`session_start`, `session_start_rejected`, `session_end`, `window-manifest.env`,
`preflight-post.json`, and
`approved-bundle/approved-runtime-principal-lifecycle-evidence.json`. This update makes
no runtime evidence, SDK readiness, stable readiness, publication, Plugin Hub, tag, or
push claim.

## 2026-06-06 14:45 CEST SDK Acceleration Update

The current round tightened the offline path around the same missing runtime evidence:

- `copy_player_principal_lifecycle_ready_log.py` now exposes top-level
  `copy_readiness`; live dry-run on Genesis2 reports
  `blocked_missing_lifecycle_roles`, copied=false, and missing
  `session_start`, `session_start_rejected`, and `session_end`.
- `plan_player_principal_lifecycle_next_actions.py` and
  `run_player_principal_lifecycle_next_actions.py` now carry post-reboot monitor/beta
  context as non-evidence and block live/log actions in the offline runner; the real
  current plan is `eligible_count=0`, `blocked_count=7` until roles appear.
- Analyzer acceptance remains strict: copied `CheckJoinInProgress(1,0)` is the only
  rejected-start candidate shape; unsupported tuples such as `1,1` are rejected as
  `unsupported_check_join_in_progress_bool_tuple`.
- Identity gates, SDK status, package-shape checks, and release-statement tooling now
  explicitly preserve monitor/beta/status/copied-log/package-shape artifacts as
  non-evidence/non-progress until a copied approved runtime bundle exists.

Runtime state at this checkpoint is unchanged: Genesis2 and Ragnarok are both up with
Summer event, both query `0/70`, observer enable lines are present, and no lifecycle roles
have appeared. This update makes no approved runtime evidence, SDK readiness, stable
readiness, Plugin Hub, publication, tag, or push claim.

## 2026-06-06 16:00 CEST Runtime UTC/MOTD Update

Genesis2 was updated under the recorded standing launch authorization after a beta
notice and in-game broadcast told testers to stay on Ragnarok. Only `arkserver3` /
Genesis2 was restarted; `arkserver` / Ragnarok stayed up and `arkserver2` / TheIsland
stayed off, preserving the two-server limit. Fresh Genesis2 Obelisk logs were truncated
before restart so the next capture starts from the newly installed runtime format rather
than old `[HH:MM:SS]` local-time lines.

Current live posture after restart:

- `arkserver3` / Genesis2 PID `765327`, query `27017`, `-ActiveEvent=Summer`.
- `arkserver` / Ragnarok PID `48047`, query `27015`, `-ActiveEvent=Summer`.
- Genesis2 file log now begins with UTC ISO lines such as
  `[2026-06-06T13:55:55Z] [info] ...`.
- Genesis2 observer line is present at `2026-06-06T13:56:33Z` with
  `limit=10`, `dispatch_limit=0`, `delivery_claim=none`, and
  `principal_claim=none`.
- Latest Genesis2 passive query after warm-up is `current_map=Gen2`,
  `players=0/70`; no fresh lifecycle roles have appeared yet.
- Local redacted RCON `ListPlayers` remains unreliable (`timeout`/command failure), so
  player presence must be inferred from multiple signals: GameDig, redacted RCON when it
  works, and the latest Obelisk lifecycle observer event.

The dashboard MOTD writer was audited by delegated agent Boole
`019e9d36-e5bc-7763-9644-4cde2977d8eb` and patched so all dashboard
`GameUserSettings.ini` mutation routes normalize `[MessageOfTheDay] Message=` to one
physical line with literal `\n` separators. The live
`/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini`
MOTD was repaired in place without creating a new backup under `/servidor/ark`.

Validation for this update: full Obelisk build passed, `ctest` passed `145/145`,
passive monitor tests passed `25 OK`, dashboard syntax passed, dashboard focal tests
passed `19/19`, and PM2 `ark-dashboard` restarted online. This update still makes no
approved runtime evidence, SDK readiness, stable readiness, Plugin Hub, publication, tag,
or push claim; the active blocker remains `approved_runtime_evidence_missing`.

## 2026-06-06 17:05 CEST MOTD Follow-Up

Delegated read-only follow-up agent Kepler
`019e9d70-f800-72b0-813a-0fde4daee78f` completed and was closed. The lead repaired the
live `GameUserSettings.ini` MOTD again in place so `Message=` is one physical line with
literal `\n` separators and a closed French RichColor block. The dashboard normalizer was
hardened to stop multiline MOTD collection before any next INI key, not only `Duration=`,
then PM2 `ark-dashboard` was restarted online as PID `1068057`.

Validation for the follow-up: dashboard `node --check server.js` passed, focused
`bootstrap.test.js` passed `20/20`, and dashboard `git diff --check` for touched files was
clean. No new `/servidor/ark` backup was created. Kepler confirmed dashboard-managed
`GameUserSettings.ini` writers are covered; remaining non-dashboard suspects are direct
top-level scripts (`fix_configs.py`, `apply_fibercraft_settings.py`), historical scratch
scripts, restore/LinuxGSM default install copies, manual edits, and runtime RCON/admin
`SetMessageOfTheDay`.

Latest process recheck during this follow-up observed only Ragnarok `arkserver` PID
`48047` as a live `ShooterGameServer`; Genesis2 was not observed as a live process or
listening on expected ports, TheIsland remained off, and no ARK server start/stop/restart
was performed for this MOTD repair. The existing passive monitor PIDs `72760`/`72761`
therefore have a stale Genesis2 target until Genesis2 is started again under the standing
debug authority. This follow-up still makes no approved runtime evidence, SDK readiness,
stable readiness, Plugin Hub, publication, tag, or push claim.

## 2026-06-06 18:07 CEST MOTD External Writer Re-Audit

The live `GameUserSettings.ini` `[MessageOfTheDay]` section was rechecked after the user
reported the MOTD kept breaking. Current state is valid: one physical `Message=` line,
literal `\n` separators, `Duration=20` as the next key, and `orphan_lines=0`. The byte
check confirms the separators are literal backslash-n bytes (`5c 6e`), not physical
newlines inside the INI value.

Dashboard-managed writes remain covered by `normalizeGameUserSettingsContent`, and PM2
`ark-dashboard` is online as PID `1068057`. The two top-level legacy external writers
identified in the prior follow-up, `/home/flowcommunity-ark/fix_configs.py` and
`/home/flowcommunity-ark/apply_fibercraft_settings.py`, now normalize any physical
multiline MOTD before writing `GameUserSettings.ini`. They were syntax-checked with
`python3 -m py_compile`; the generated `__pycache__` was removed. The scripts were not
executed because execution would mutate live ARK config.

No ARK start, stop, restart, RCON command, Discord send, or `/servidor/ark` backup was
created for this re-audit. Remaining ways the MOTD can still be reintroduced broken are
manual edits, restore/LinuxGSM default install copies, historical scratch scripts, and
runtime RCON/admin `SetMessageOfTheDay`.

## 2026-06-06 17:44 CEST Contract Binding And Mission Boundary Update

The identity public-contract review path is now explicitly two-step and fail-closed:
accepted runtime lifecycle evidence can resolve only `runtime.lifecycle_evidence`, then
the reviewed identity public-contract decision record must bind itself to that exact
accepted runtime manifest through `approved_runtime_evidence_binding`. The committed
default reviewed record remains source-hash-current and contract-review-only, but it is
not accepted for contract review until that binding exists and matches the accepted
runtime manifest. This prevents monitor, beta notice, status, copied-log-only, request,
preflight/window, receipt, sidecar, certificate, simulation, mock, or fixture artifacts
from opening the public identity contract gate.

The gap report now exposes the binding audit fields so future agents can distinguish a
valid-but-unbound reviewed record from a bound accepted record without running a second
checker. A bound record can remove only the reviewed identity-contract decision keys from
the post-runtime gate; it still leaves the broader evidence/privacy/lifetime/ABI decision
keys unresolved and cannot claim public header/API/ABI readiness, runtime readiness, SDK
readiness, P0 progress, permissions/admin, command/chat response, commands/replies,
Plugin Hub, publication, tag, or push.

Mission copied-bool also remains an internal side-lane. `hooks/ProcessEventMissionReflection.cpp`
was removed from the `obelisk` runtime target because the mission readiness checker
correctly rejects mission ProcessEvent hook wiring in a runtime/shared target before that
lane is promoted. The mission reflection tests still build the hook in test-only targets,
so offline validation remains available without exposing mission runtime behavior.

Validation for this update:

- Identity gap/decision suite: `74 OK`.
- Integrated identity/header/first-evidence/planning suite: `159 OK`.
- Public-contract readiness plus approved-runtime-evidence suite: `257 OK`.
- Full public-SDK status/completion suite after focal fixes: `351 OK`.
- `check_command_permission_route_gate.py --json`: valid/planning-only.
- `check_mission_copied_bool_readiness.py --json`: ready for internal planning only.
- `check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json`: ready, with
  P0 and complete-SDK claim contribution still false.
- `obelisk`, `process_event_mission_reflection_tests`, and
  `mission_copied_bool_event_dispatcher_tests` build; CTest for the two mission focal
  targets passes `2/2`.

This update still makes no approved runtime evidence, SDK readiness, stable readiness,
Plugin Hub, publication, tag, or push claim. The active route remains
`approved_runtime_evidence_missing`.

## 2026-06-06 18:10 CEST Runtime Evidence Checker Parity

Superseded by the 2026-06-06 21:59 CEST hardening checkpoint below. This section records
the older parity problem and its interim fix. Do not use it as current routing for
`session_start_rejected`: current approved evidence rejects `HandleNewPlayer`
rejected-start tuples and requires exact `CheckJoinInProgress(1,0)`.

Read-only audit agent Hume `019e9da9-b8eb-7310-82fd-9ac5298ac04d` found a historical
false-negative risk before later hardening: older hook/analyzer routing could treat
`ShooterGameMode.HandleNewPlayer` rejected-start tuples as recognizable current-route
candidates, while the checker accepted only one of those tuples. That route is now
superseded. Treat all `HandleNewPlayer` rejected-start tuples (`0,1`, `1,0`, and `0,0`)
as false-positive history and non-evidence, not accepted alternatives.

Historical interim action: the checker was temporarily widened for those
`HandleNewPlayer` rejected-start tuples. That interim acceptance is superseded by the
exact `CheckJoinInProgress(1,0)` route and must not be reproduced in current planning
smoke or runtime-window guidance. Tests from that interim round preserved the
no-public-SDK/no-runtime-readiness flags.

Read-only audit agent Hooke `019e9da8-f877-7993-999f-d1879e31bf58` also identified an
operational closure blocker: `prepare_player_principal_lifecycle_evidence_closure_request.py`
could emit the `copy_player_principal_lifecycle_ready_log.py` command without the
required `--fresh-window-start-utc` and `--fresh-window-end-utc` flags. The closure
request now reads those values from `window-request.json` when present and valid,
includes them in the not-executed copy command, and marks window issues as explicit
blockers otherwise.

Validation for this update: `python3 -m unittest
scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
scripts.test_analyze_runtime_observer_log` passed `212 OK`, and
`python3 -m unittest scripts.test_prepare_player_principal_lifecycle_evidence_closure_request`
passed `47 OK`. This update still makes no approved runtime evidence, SDK readiness,
stable readiness, Plugin Hub, publication, tag, or push claim.

## 2026-06-06 18:20 CEST MOTD Current-State Recheck

After the user reported the MOTD kept breaking after manual edits, the live
`/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini`
section was parsed directly again. The current file is not physically broken:
`[MessageOfTheDay]` contains exactly one `Message=` line, that line contains literal
`\n` separators, `Duration=20` remains the next key, and there are no orphan non-key
lines inside the section.

Dashboard validation passed with `node --test
/home/flowcommunity-ark/dashboard/server/test/bootstrap.test.js` (`20/20`), including
the three MOTD normalizer tests. The two top-level legacy writers were syntax-checked
with `python3 -m py_compile /home/flowcommunity-ark/fix_configs.py
/home/flowcommunity-ark/apply_fibercraft_settings.py`; both already normalize physical
multiline MOTD input before writing `GameUserSettings.ini`.

The remaining plausible breakage sources are outside the covered writers: manual raw
edits that insert physical newlines inside `Message=`, restore/LinuxGSM default install
copies, historical scratch scripts, or runtime RCON/admin `SetMessageOfTheDay`.
No ARK start/stop/restart and no `/servidor/ark` backup was created for this check.

## 2026-06-06 Worker E Offline Lifecycle Candidate Audit

Superseded by the 2026-06-06 21:59 CEST hardening checkpoint below for
`session_start_rejected` acceptance. This section remains useful as historical audit
context only.

This audit was repo-local and offline-only. It read the lifecycle feasibility note,
research README, player-identity planning-source JSON, committed lifecycle UFunction
snapshots, and the analyzer/checker/planning-smoke scripts. It did not touch live
servers, `/servidor/ark`, Discord, GitHub, handoff files, runtime markers, or runtime
logs.

Audit result: no missed offline-only lifecycle anchor was found. The six committed
`players-lifecycle-anchor-candidates` fixtures remain a planning/guidance set, not a
promotion set. `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` remain
the only durable source-bound lifecycle anchors. `ShooterGameMode.CheckJoinInProgress`
remains only the observer alternative for `session_start_rejected`, and
`GameMode.K2_PostLogin` plus the lifecycle delegate signatures remain chronology or
diagnostic guidance only.

Current false-positive risk to preserve for the next runtime window:
`scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json` is useful
for blocker status only when its `session_start_rejected.accepted_alternatives` list has
exactly one entry: copied `ShooterGameMode.CheckJoinInProgress(1,0)`. Historical
`HandleNewPlayer` rejected tuples must appear only as superseded non-evidence and no
longer satisfy approved runtime evidence. A future runner must wait for exact copied
`CheckJoinInProgress(1,0)` for `session_start_rejected`.

Rejected hypotheses from this audit:

- The all-six lifecycle fixture set hides a better offline lifecycle anchor. It does
  not; without distinct non-`/tmp` candidate snapshots and approved runtime ordering, it
  remains planning-layout intake only.
- `K2_PostLogin`, `OnPostLogin__DelegateSignature`, or
  `OnStartNewPlayer__DelegateSignature` can fill a required lifecycle role because they
  contain `NewPlayer`. They cannot; they carry no accepted copied bool tuple,
  `principal_action`, apply status, or correlation contract.
- `CheckJoinInProgress` copied bool tuples other than `1,0`, old-format lifecycle event
  lines without `apply_status`/`correlation_status`, diagnostic candidate lines mixed
  beside complete events, or unmatched/duplicate/stale `OnLogout` outcomes can complete
  the bundle. They cannot.

Exact current runtime candidate guidance: after observer enable, capture an accepted
`HandleNewPlayer(1,1)` `session_start`; then capture exact copied
`CheckJoinInProgress(1,0)` for `session_start_rejected`; then capture `OnLogout` only
when it reports `apply_status=session_end_invalidated` and `correlation_status=matched`
for the private process-local correlation path. If any role is missing or only
diagnostic/passive material exists, stop at the missing-role result.

Offline validation during this audit:

- `python3 scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json`
  returned ready/planning-only with next blocker `approved_runtime_evidence_missing`.
- `python3 scripts/compare_reflection_snapshots.py --list-target-guidance --target-set
  players-lifecycle-anchor-candidates --json` returned guidance-only/non-evidence
  status.
- `python3 scripts/compare_reflection_snapshots.py --base-root
  tests/fixtures/ufunction_snapshots --target-set players-lifecycle-anchor-candidates
  --readiness-report --planning-layout-intake --json` failed closed with
  `missing_candidate_root`, as expected for a base-only audit.
- `python3 scripts/build_player_identity_planning_source_manifests.py --output-dir
  /tmp/obelisk-worker-e-planning-sources --snapshot-root
  tests/fixtures/ufunction_snapshots --json` returned `valid=true` and produced the same
  lifecycle/principal planning-source hashes as the repo copies.

## 2026-06-06 21:59 CEST CheckJoinInProgress Hardening

This update is repo-local/offline plus read-only live status checks. It did not start,
stop, restart, deploy, send Discord, run RCON, publish, tag, push, or claim SDK/runtime
readiness.

Integrated result:

- `analyze_runtime_observer_log.py` accepts `ShooterGameMode.CheckJoinInProgress` only
  as `session_start_rejected` when the copied bool tuple is exactly
  `bIsFromLogin,ReturnValue=1,0`, `NewPlayer` is redacted, `principal_action=none`, and
  `apply_status/correlation_status` are `session_start_rejected_noop/not_applicable`.
- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now requires
  the approved triplet `HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> OnLogout`
  with matched end correlation. `HandleNewPlayer` rejected-start tuples are rejected as
  ambiguous shortcuts for approved evidence.
- `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py` and
  `build_player_identity_runtime_principal_lifecycle_approved_manifest.py` require the
  `check_join_in_progress_rejected_start` alternative before writing an approved
  manifest and preserve exact sibling sidecar/hash binding.
- `check_public_sdk_v1_completion.py` and `report_obelisk_sdk_status.py` keep offline
  CheckJoinInProgress/session-start-rejected aliases non-public, non-stable, non-v1, and
  blocked at `approved_runtime_evidence_missing` until a real accepted bundle exists.
- No-users planning now prefers passive wait plus a next diagnostic window with
  `--restart-expectation none` and `--diagnostic-candidates`, keeping player warnings
  and broadcast recommendations as non-authorizing metadata.

Validation:

- `python3 -m unittest` for lifecycle analyzer, approved checker, bundle/manifest, and
  next-action/window execution suites: `355 OK`.
- `python3 -m unittest scripts.test_check_public_sdk_v1_completion
  scripts.test_report_obelisk_sdk_status`: `355 OK`.
- CTest `PlayerPrincipalLifecycleReflectionTests` and
  `ProcessEventPlayerPrincipalLifecycleObserverTests`: `2/2`.
- Final status remains blocked at `approved_runtime_evidence_missing`, SDK `0/12`, P0
  `0/4`, runtime/public/stable false.

Live read-only check: only Ragnarok `arkserver` PID `1744812` was running, GameDig
reported `0/70`, and the active `Obelisk.log` had only runtime load, ProcessEvent hook,
plugin-disabled, lifecycle observer enable, and diagnostic enable lines. No lifecycle
roles were logged during this pass.

## 2026-06-06 Worker F Planning Smoke Current-Route Cleanup

This update is repo-local/offline-only and only removes stale planning guidance. It does
not authorize runtime work, server/log reads, Discord sends, GitHub publication, tags,
commits, release documentation, or handoff documentation.

Current planning-smoke output now renders `session_start_rejected.accepted_alternatives`
with exactly one entry: copied `ShooterGameMode.CheckJoinInProgress(1,0)`. Historical
`ShooterGameMode.HandleNewPlayer` rejected-start tuples (`0,1`, `1,0`, and `0,0`) are
reported only under `superseded_non_evidence_alternatives` and cannot satisfy approved
runtime evidence.

Validation:

- `python3 -m unittest scripts.test_check_player_principal_lifecycle_planning_blocker_smoke`:
  `8 OK`.
- `python3 -m unittest scripts.test_research_doc_guardrails`: `46 OK`.
- `python3 -m py_compile` on the planning-smoke script and focal unittest: passed.
- `python3 scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json`:
  `ready=true`, `planning_sources_ready=true`, `next_blocker=approved_runtime_evidence_missing`,
  and the current rejected-start alternative list contains only `CheckJoinInProgress(1,0)`.

Final status remains blocked at `approved_runtime_evidence_missing`, SDK `0/12`, P0
`0/4`, runtime/public/stable false.

## 2026-06-06 23:01 CEST No-User Window Closure

This update records the latest standing-authorized Ragnarok observer window after the
operator reported no users. It did not restart, deploy, send Discord, run RCON actions,
publish, tag, push, or claim SDK/runtime readiness.

Window and posture:

- Evidence dir:
  `/servidor/ark/workspace-offline/live-validation-logs/20260606T203359Z-player-principal-lifecycle`.
- Approved window: `2026-06-06T20:33:59Z` to `2026-06-06T20:48:59Z`.
- Runtime load: `2026-06-06T20:33:52Z`; lifecycle observer enabled:
  `2026-06-06T20:34:12Z`.
- Binary SHA matched:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- Live snapshot at `2026-06-06T21:00:35Z`: only Ragnarok `arkserver` PID `1943280`,
  `-ActiveEvent=Summer`, observer-debug env, plugins disabled, GameDig `0/70`, RCON
  `ListPlayers` timeout/unknown, and observer tail lines only for observer/diagnostic
  enable.

Result:

- `ready-log-copy.json` reports `copy_readiness=blocked_missing_lifecycle_roles`,
  `copied=false`, `approved_runtime_evidence=false`, roles present `[]`, and missing
  `session_start`, `session_start_rejected`, and `session_end`.
- Runtime status was written to
  `/tmp/obelisk-20260606T203359Z-runtime-evidence-status.json` because the helper rejects
  status output under protected server paths. It reports route
  `approved_runtime_evidence_missing`, missing exact labels `HandleNewPlayer(1,1)`,
  `CheckJoinInProgress(1,0)`, and `OnLogout matched`, plus missing approved sidecars and
  bundle files.
- No copied `Obelisk.log` or approved evidence bundle exists for this window.

Conclusion: this was a valid observer window with no player lifecycle invocations, not an
approved runtime evidence result and not an analyzer/checker failure. Continue offline
SDK work while keeping the runtime path ready for the next real player-backed window.

## 2026-06-06 23:25 CEST Runtime Evidence Hardening Round

This was an offline six-agent plus lead integration round after the no-user window. It
did not restart, deploy, send Discord, run RCON actions, publish, tag, push, or claim
SDK/runtime readiness.

Integrated hardening:

- Copied lifecycle triplet consumers now require the same safe copied-event shape before
  follow-up: post-original execution, exact redaction fields/counts, expected
  `principal_action`, hidden principal id/generation, and `delivery_claim=none`.
- C++ player-principal lifecycle applicator now fails closed for accepted
  `session_start` without nonzero `EventSequence` and `ServerProcessEpoch`, preventing an
  uncorrelatable live principal allocation.
- The next-action runner rejects non-string structured argv items and missing output flag
  values before a helper can be considered executable.
- Permissions/command and side-lane guardrails reject newly covered shortcut aliases
  including package-shape/package-install, Plugin Hub, source provenance splits,
  `allowed`, `unblocked`, `unlocked`, and numeric credit claims.
- Install/compatibility docs now state that the non-`EXACT`
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` request is a
  package-shape compatibility-floor check only, not stable SDK readiness.

Validation:

- Integrated Python focal suite: `515 OK`.
- C++/ABI/SDK-consumer build targets: passed.
- CTest for lifecycle, ABI, and SDK consumer tests: `112/112`.
- Route gate: valid/planning-only at `approved_runtime_evidence_missing`, blockers `[]`.
- SDK status remains SDK `0/12`, P0 `0/4`, runtime/public/stable false.
- `check_public_sdk_v1_completion.py --json` exits `1` as expected with
  `status=blocked`, `current_route_blocker=approved_runtime_evidence_missing`.

Live passive check during the round still reported Ragnarok `0/70` with only observer
enable/diagnostic log lines. No new runtime lifecycle evidence exists.

## 2026-06-06 23:42 CEST No-User SDK Accounting Hardening

The operator reported no users, so this round stayed offline. No restart, deployment,
RCON, Discord, publication, tag, push, Plugin Hub action, or readiness claim occurred.

Applied findings:

- Manual runtime-window follow-up steps now state in machine-readable fields that they are
  external-only and do not authorize action, approved runtime evidence, runtime readiness,
  public SDK readiness, or v1 completion.
- Runtime-window execution and SDK status/completion/first-evidence checkers now reject
  newly observed aliases that could otherwise overclaim progress: `unblocked`, `allowed`,
  SDK/P0 credit fields, package exact/non-exact reports, Plugin Hub, passive/beta notices,
  provenance/source sidecars, and lifecycle sidecar material.
- PluginManager cleanup progress now survives partial public-gameplay cleanup failure so
  retry is possible without stale tracking.
- Exact-path server posture checks, complete reflection artifact identities, and
  ResourceHandle/object-identity/owner-token fail-closed aliases were hardened.

Validation completed before final status rerun:

- Python focal suites: `216 OK`.
- Completion/status/first-evidence suite: `403 OK`.
- Wrapper/posture/install-layout shell checks: passed.
- `plugin_manager_tests` build and CTest `PluginManagerTests|ChatEventDispatcherTests|StructureEventDispatcherTests`: passed.
- Handoff/operational/research/plugin guardrails: `142 OK`.
- `py_compile` and `git diff --check` for touched paths: passed.

Final status remains non-evidence until the approved runtime bundle checker accepts a
real player-backed triplet. The blocker is still `approved_runtime_evidence_missing` with
SDK `0/12`, P0 `0/4`, runtime/public/stable false, and completion JSON exits `1` as the
expected blocked result.

## 2026-06-07 02:03 CEST RCON Helper Fix And CheckJoin Drift Patch

Runtime diagnosis:

- RCON itself was healthy. The dashboard helper
  `/home/flowcommunity-ark/dashboard/server/test_rcon.js` printed valid RCON responses
  but stayed alive, so `timeout` wrappers reported false failures. The helper now exits
  `0` after successful `main()` completion. Redacted checks confirmed Ragnarok `27020`
  and TheIsland `27021` return `ListPlayers` status `ok` once ARK finishes loading.
- Do not quote raw `ListPlayers` output in reports; it can contain player names or IDs.

Runtime finding:

- TheIsland/Ragnarok logs showed exact `ShooterGameMode.CheckJoinInProgress` FName drift
  at `BIsFromLogin 28509 -> 28512`. The inferred full current chain, matching the
  adjacent `HandleNewPlayer` drift family, is `{28512,28414,17720}` for
  `BIsFromLogin`, `NewPlayer`, and `ReturnValue`.
- The patch accepts only that complete `CheckJoinInProgress` chain with exact field
  shape, classes, offsets, sizes, and copied bool semantics. Mixed canonical/observed
  variants and unapproved names remain fail-closed.

Validation:

- Build targets: `obelisk`, `process_event_player_principal_lifecycle_observer_tests`,
  `player_principal_lifecycle_reflection_tests`, and
  `player_principal_lifecycle_applicator_tests` passed.
- CTest for
  `ProcessEventPlayerPrincipalLifecycleObserverTests|PlayerPrincipalLifecycleApplicatorTests|PlayerPrincipalLifecycleReflectionTests`
  passed `3/3`.
- Python analyzer/passive-monitor focal suite passed `79 OK`.
- `git diff --check` passed for touched Obelisk paths and the dashboard RCON helper.

Live window:

- A new TheIsland request pack was prepared at
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T000000Z-player-principal-lifecycle`
  for `2026-06-07T00:00:00Z` through `00:15:00Z` UTC with standing-authority receipt.
- Guarded beta testers Discord notice was sent with `@everyone`, but its stdout report
  was not saved as `beta-notice.confirmed.json`; avoid duplicate sends solely to create
  that sidecar unless a checker explicitly requires it.
- The patched runtime was installed to `/servidor/ark/obelisk`; only TheIsland
  (`arkserver2`) was restarted after RCON confirmed zero TheIsland players. Ragnarok
  stayed running as the transfer/play target and got an RCON broadcast. No Genesis2 and
  no three-server condition occurred.
- Current post-patch TheIsland posture: PID `2994420`, `-ActiveEvent=Summer`,
  observer-debug passed, runtime loaded at `2026-06-07T00:01:20Z`, observer enabled at
  `2026-06-07T00:01:42Z`, query/RCON `ok`, `0/70` players, passive monitor active from
  `2026-06-07T00:02:56Z`.

No approved runtime evidence exists yet after this patch. A valid bundle still needs a
post-patch player-backed triplet: `HandleNewPlayer` `session_start`, exact
`CheckJoinInProgress(1,0)` `session_start_rejected`, and matched `OnLogout`
`session_end`. The SDK route remains `approved_runtime_evidence_missing`, SDK `0/12`,
P0 `0/4`, runtime/public/stable false.

## 2026-06-07 00:11 CEST Runtime-Evidence Readiness Hardening

This round stayed offline and did not mutate live ARK state, send Discord, run RCON,
publish, tag, push, or claim readiness. The work focused on making the next player-backed
runtime window harder to misinterpret.

Findings and changes:

- Beta notice preparation can now include `@everyone` in the dry-run payload for the beta
  testers channel, but that remains a guarded notice action only. The report still grants
  no Discord authorization by itself, no server authority, no evidence, and no SDK
  progress. The request validator rejects `unblocked` and SDK/P0 credit aliases.
- Evidence bundle/checker regressions now cover missing canonical siblings and aliases:
  `window-manifest.env`, copied `Obelisk.log`, `preflight-post.json`, and partial
  lifecycle triplets cannot be promoted through alternate fields.
- Live tooling now fails closed on observer-debug marker/env mismatch and more than two
  ARK servers in proc fixtures; valid GameDig JSON without a numeric player count remains
  unknown/non-evidence.
- Reflection comparison now treats nested ArrayProperty/StructProperty candidates without
  nested identity as inconclusive, not accepted.
- Package-shape ABI guard now rejects Plugin Hub/runtime/support-tier readiness markers.

Validation completed before the final completion rerun:

- Beta notice suite: `26 OK`.
- Snapshot/package-shape focal suite: `175 OK`.
- Evidence bundle/checker suite: `265 OK`.
- Live tooling tests: shell tests passed and passive monitor `27 OK`.
- PluginManager build/guardrails/CTest passed.
- Public SDK completion/status suite passed `355 OK`.
- Route/status still report `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`,
  runtime/public/stable false.

No new approved runtime evidence exists. The next evidence-producing step remains a real
player-backed accepted bundle containing `session_start`, exact
`CheckJoinInProgress(1,0)` `session_start_rejected`, and matched `session_end` with safe
`apply_status`/`correlation_status` fields.

## 2026-06-07 00:54 CEST No-User Offline SDK Hardening

The operator reported no users. This round stayed offline: no server start/stop/restart,
deployment, marker/env mutation, Discord send, RCON action, live-log read, publication,
tag, push, Plugin Hub action, or readiness claim occurred. Read-only process posture
earlier in the round showed only Ragnarok active.

Durable findings and changes:

- Player availability is now explicit operator context only. `players_detected`,
  `no_players_currently_detected`, unknown player counts, and absent player context do not
  count as activation, runtime capture, evidence, SDK/P0 progress, public SDK readiness,
  runtime readiness, stable readiness, or v1 completion.
- `observer-debug` LinuxGSM starts now reject debug/scanner/callback/CallProcessEvent/
  blocking/static-probe escape markers before exec unless the scoped observer marker set
  is the only active experimental set.
- First-evidence artifacts now carry both top-level false readiness/progress fields and a
  plural `first_evidence_boundary.non_claims` list, so checked-in planning artifacts cannot
  be mistaken for evidence.
- Header-gate policy now shares the canonical reviewed identity public contract hash policy
  instead of a stale local string. This keeps passive/runtime-presence, no-users,
  runtime-window planning, status-json, copied-log-only, package-shape/support-tier, and
  historical-handoff aliases non-counting.
- Command/chat response and commands/replies scanners skip `non_evidence_artifacts` as
  context, while still flagging positive readiness/progress claims elsewhere.
- Route-gate claim scanning now distinguishes blocker aliases
  `approved_runtime_evidence_missing` / `approved_runtime_evidence_required...` from
  positive `approved_runtime_evidence_ready` / `approved_runtime_evidence_accepted`
  aliases. The former are allowed blockers; the latter remain forbidden claims.

Delegation outcome:

- Singer completed and was integrated for live-tooling hardening.
- Lorentz, Newton, Ptolemy, Jason, and Mendel were closed after timeout/shutdown without
  integrated final reports.
- Huygens completed a header-gate diagnosis after the lead had already aligned the checker
  and was closed. No standby sub-agent remains.

Validation:

- Runtime availability report `17 OK`; activation/preconditions `55 OK`.
- Wrapper/posture/passive tooling passed; passive monitor `27 OK`.
- Reflection/first-evidence `199 OK`; public header/permissions `267 OK`.
- Command/public-contract/generator suite `348 OK`; route gate `76 OK` plus direct JSON
  `valid=true`, `planning_only=true`, blockers `[]`.
- Docs guardrails `89 OK`; touched Python `py_compile` passed.
- `report_obelisk_sdk_status.py --compact`: route `approved_runtime_evidence_missing`,
  SDK `0/12`, P0 `0/4`, runtime/public/stable false.
- `check_public_sdk_v1_completion.py --json` exits blocked as expected with the route gate
  accepted and current blocker `approved_runtime_evidence_missing`.

No approved runtime evidence, SDK readiness, stable readiness, Plugin Hub readiness,
publication, tag, push, or v1 completion claim is made by this update.

## 2026-06-07 03:05 CEST Ragnarok New-Runtime Restart

The operator explicitly requested a Ragnarok restart so testers could transfer from
TheIsland to Ragnarok and test the new runtime. Under the standing live-ops authorization,
the lead rebuilt target `obelisk`, installed to `/servidor/ark/obelisk` without
`--backup-existing`, and restarted only `arkserver` / Ragnarok after RCON reported one
redacted Ragnarok player and both active maps received a 60-second transfer warning.
TheIsland stayed running as the transfer server, Genesis2 stayed off, and the two-server
maximum was preserved.

Observed runtime facts:

- Current ARK processes after restart: TheIsland PID `2994420`, Ragnarok PID `3410463`,
  both with `-ActiveEvent=Summer`.
- Installed runtime SHA256:
  `107d2031da6446b71b4b25348c71b4c2f780dbc818682bcb28cbbd26e0d67d42`.
- Ragnarok loaded Obelisk at `2026-06-07T01:01:12Z`, installed ProcessEvent hook at
  `0x1d34e20`, kept ReflectionScanner disabled, and kept plugins disabled.
- `PlayerPrincipalLifecycleObserver enabled` appeared at `2026-06-07T01:01:43Z` with
  binary SHA `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, log
  limit `10`, dispatch limit `0`, and diagnostic candidates enabled.
- Posture check passed
  `scripts/check_obelisk_server_posture.sh --expect-observer-debug
  --allow-live-procfs-read --allow-protected-root --map Ragnarok --instance arkserver`.
- Passive monitor one-shot at `2026-06-07T01:03:48Z` reported Ragnarok query/RCON `ok`,
  zero redacted Ragnarok players, and one redacted TheIsland player. Broadcasts were
  accepted on TheIsland and, after warm-up, on Ragnarok.

Evidence state remains blocked. Analyzer on the new Ragnarok log sees only observer gate
and diagnostic-enable lines, with accepted count `0` and all three lifecycle roles
missing. Analyzer on the current TheIsland log sees accepted `session_start` and
`session_end`, but still misses the required exact `CheckJoinInProgress(1,0)`
`session_start_rejected`; superseded `HandleNewPlayer` rejected-start material remains
non-evidence. Route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`,
runtime/public/stable false.

Operational note: ad hoc Node `rcon-client` scripts can hang while awaiting socket close
after a valid ARK RCON response. Future live-ops snippets should use explicit RCON
timeouts plus process-level bounds or `process.exit()` after sanitized output, and should
not misclassify that close hang as failed RCON.

## 2026-06-07 01:14Z Handoff Continuity Audit

This was a docs-only continuity audit of the handoff/research state after the 03:05 CEST
Ragnarok restart. It did not read live server paths or logs, perform server operations,
run RCON, send Discord, publish, tag, push, touch Plugin Hub state, or claim runtime,
public SDK, stable SDK, or v1 readiness.

Continuity result:

- Standing launch authority remains recorded and transferable until revoked, with the
  two-server, no-secret, player-warning, and no-readiness-claim limits still attached.
- Active routing remains unchanged: `approved_runtime_evidence_missing`, SDK `0/12`, P0
  `0/4`, runtime/public/stable false, and source overclaims `0`.
- No checker-accepted approved runtime principal lifecycle bundle is recorded. Passive
  monitor output, RCON/player counts, package-shape install state, diagnostics, and
  copied-observation rejection lines remain non-evidence.
- Latest supervised workers are closed; no active sub-agent remains open.

## 2026-06-07 04:53 CEST Runtime Window Follow-Up

Ragnarok was restarted under the standing live-ops authority so testers could move from
TheIsland and exercise the new runtime. TheIsland stayed online as the transfer bridge,
Genesis2 stayed off, and the two-server maximum was preserved. Ragnarok loaded Obelisk at
`2026-06-07T02:39:03Z`; the lifecycle observer enabled at `2026-06-07T02:39:38Z` with the
expected binary SHA, log limit `10`, dispatch limit `0`, and diagnostic candidates on.

The new Ragnarok log captured only partial lifecycle evidence:

- `HandleNewPlayer(1,1)` `session_start` at `2026-06-07T02:40:31Z`.
- matched `OnLogout` `session_end` at `2026-06-07T02:42:15Z`.
- another `HandleNewPlayer(1,1)` `session_start` at `2026-06-07T02:42:29Z`.

The strict `CheckJoinInProgress(1,0)` `session_start_rejected` event remains absent.
`CheckJoinInProgress(0,0)` remains diagnostic-only `copy_status=rejected`, and superseded
`HandleNewPlayer(0,1)` remains non-evidence. Therefore the SDK route stays
`approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, with no runtime/public/stable
readiness claim.

Offline hardening from this follow-up:

- `PlayerPrincipalRegistry` now bounds retained invalidated principals and avoids reusing
  evicted handles, so long-running servers cannot accumulate invalidated principals
  indefinitely.
- The reviewed identity public-contract decision record now has the current SHA for
  `docs/player_identity_public_contract_decisions.json`, but still intentionally fails
  acceptance until `approved_runtime_evidence_binding` points at a checker-accepted
  approved runtime evidence bundle.
- Strict rejected-start diagnostics were added to the runtime evidence checker/bundle
  path without relaxing the `CheckJoinInProgress(1,0)` gate.

Validation for this checkpoint: runtime evidence checker/bundle suite `269 OK`, status/
monitor/public-contract/start-end suite `240 OK`, CTest for
`PlayerPrincipalRegistryTests|PlayerPrincipalEventDispatcherTests|PluginManagerTests`
`3/3`, direct `player_principal_registry_tests` passed, and touched-file `git diff --check`
passed.
