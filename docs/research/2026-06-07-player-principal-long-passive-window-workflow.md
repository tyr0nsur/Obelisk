# Player Principal Long Passive Window Workflow

Date: 2026-06-07

## Scope

This note records the current player-principal runtime workflow clarification for broad
passive observer windows. It is durable workflow memory and negative-evidence context
only.

It does not claim approved runtime evidence, readiness, SDK/P0 progress, stable
readiness, publication authority, Plugin Hub readiness, or live-ops authorization. It
does not include raw logs.

## Facts

- Standing launch/debug authority exists for the current runtime workflow, but authority
  is not evidence and does not make the route ready.
- Accepted player-principal lifecycle evidence still requires the exact copied triplet
  in one valid sibling-set window:
  `HandleNewPlayer(1,1)`,
  `CheckJoinInProgress(1,0)`, and a matched `OnLogout` with only safe copied fields.
- The first TheIsland window for run `20260607T132020Z` produced start/end lifecycle
  material only. The copy dry-run remained blocked because `session_start_rejected` was
  missing.
- The user clarified that broad passive windows should stay open while players may enter,
  instead of closing early and repeatedly restarting when the first join does not produce
  the rejected-start role.
- Follow-up clarification: if players are already connected, do not restart merely to
  widen observer coverage or add side-lane logging. Capture with the active gates and
  prepare broader candidate packs offline for the next necessary deploy/restart window.
- Tooling now intends broad observer windows to use a minimum of 15 minutes and a maximum
  of 2 hours.
- Ragnarok diagnostic candidate drift observed after the forced restart is useful for
  debugging only, not promotion: `HandleNewPlayer` first property name index `28416` and
  `OnLogout` property name index `28548` do not have a reviewed full drift-chain evidence
  source, so they stay rejected/non-evidence. Tests now pin that `28416` cannot reserve
  evidence budget or build copied lifecycle evidence.
- A later operator-forced restart of both active servers on 2026-06-07 at about
  `15:12Z`/`15:13Z` reloaded Obelisk without code/marker/env changes. Post-restart
  Ragnarok observed `HandleNewPlayer` property-name drift
  `28419/21315/22969/28517...`; this remains diagnostic-only for the same reason.
- Analyzer handling now records safe truncated partial lifecycle FName mismatch chains as
  diagnostic summaries only. For the live `28419/21315/22969/28517...` shape it reports
  `truncated=true` and `observed_name_indices_complete=false`, preserving
  `approved_runtime_evidence=false` and all readiness gates false.
- Approved-evidence checker guardrails allow safe diagnostic mismatch-summary keys in
  source summaries, but still reject real player/UE internal leakage inside those
  summaries. This fixes fixture false positives without promoting diagnostic material.
- The approved-evidence closure path should be validated serially: run
  `scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle` and
  `scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
  one after the other. Running them concurrently produced false failures from shared
  fixture cleanup, not a runtime evidence problem.

## Workflow

For future approved broad windows, keep observer and passive monitors open while waiting
for natural player entry, and continue offline development while the passive window is
running. Do not treat a start/end-only window as readiness, and do not copy or promote it
unless the exact required triplet is present.

Restart only when the target instance is empty, or when a restart is strictly necessary
after broadcast and transfer guidance has been followed. Avoid repeated restart loops as
the default response to missing `CheckJoinInProgress(1,0)` evidence.

If the active runtime lacks a desired optional observer while players are inside, keep the
current capture running and treat the missing observer as next-window preparation unless
the absent gate is a strict blocker for ObeliskSDK progress. Candidate-only
multi-surface packs can be prepared offline so the next beta session captures more than
one surface without cutting the current player session.

Diagnostic lifecycle FName mismatches should be summarized and reviewed as negative
evidence. A reviewed full property-name drift chain can only become a recognizer input;
it does not promote observer output unless the exact copied triplet passes the approved
bundle/checker path.

## 2026-06-07 17:50 CEST Balance Restart And Window Closure

The operator requested a five-minute global restart timer for active maps after
PVP-Raideo balance changes. The lead sent RCON `Broadcast` countdowns to Ragnarok and
TheIsland at 5/4/3/2/1 minutes plus 30/10 seconds, ran `SaveWorld` successfully on both
maps before restart, and restarted `arkserver` then `arkserver2` sequentially. No
Obelisk code, marker, or env change was mixed into that restart.

Post-restart state: exactly two ARK servers are running, Ragnarok PID `2840693` and
TheIsland PID `2844057`, both with `-ActiveEvent=Summer`; RCON revalidated Ragnarok
`players=2` and TheIsland `players=0`. Obelisk reloaded on both maps through
`LD_PRELOAD`, installed the ProcessEvent hook, disabled plugins, and enabled the
player-principal lifecycle observer with SHA
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

The broad TheIsland window `20260607T134929Z-player-principal-lifecycle` closed without
approved evidence. The final passive monitor lines keep TheIsland at observer-gate only
with no lifecycle roles; Ragnarok produced diagnostic/rejected drift outside the approved
TheIsland sibling set. The live TheIsland `Obelisk.log` is now post-restart and outside
the original window, so the copy dry-run correctly blocks with
`blocked_observer_enable_outside_fresh_window`. Runtime status remains
`approved_runtime_evidence=false`, `ready=false`, and SDK/P0 progress `0`.

## 2026-06-07 18:16 CEST Fresh TheIsland Direct-Join Window

A fresh TheIsland runtime window was prepared as
`20260607T161643Z-player-principal-lifecycle`, from `2026-06-07T16:16:43Z` to
`2026-06-07T18:16:43Z`, using the approved standing runtime/debug authority and the
guarded beta-test notice path. The dry-run notice required exactly one selected tester to
direct-join TheIsland, avoid cluster transfer/reconnect/logout churn, and wait for
instructions. The guarded helper then sent the beta Discord notice with `@everyone`.
Ragnarok also received an RCON broadcast with the same direct-join/no-churn instruction.

Before activating the window, TheIsland RCON reported `players=0`; `SaveWorld` returned
`ok=true`; only `arkserver2` was restarted. This kept the two-server cap intact and left
Ragnarok online for normal cluster continuity. TheIsland restarted at `16:17:16Z`;
Obelisk loaded at `16:17:15Z`; the player-principal lifecycle observer enabled at
`16:17:48Z`, inside the approved window, with SHA
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`, log limit `10`,
dispatch limit `0`, plugins disabled, ProcessEvent enabled, and diagnostic candidates
disabled.

Runtime monitoring is intentionally passive while waiting for a tester. The monitor under
`/servidor/ark/workspace-offline/live-validation-logs/20260607T161643Z-player-principal-lifecycle/passive-monitor.log`
reports TheIsland query/RCON `0` players and observer gate only so far. The companion
operator watcher records only control markers: if exact `CheckJoinInProgress(1,0)` is
observed, it sends a one-time RCON logout instruction to TheIsland; if a matched
`OnLogout` appears afterward, it marks the session-end capture. Until the copied sibling
set and approved bundle checker accept the exact triplet, all monitor, notice, RCON, and
watcher material remains non-evidence and contributes no SDK/P0 progress.

Six agents were closed in this round. Reusable workflow deltas: fresh retry windows must
use their own run id, sibling set, notices, and start/end; copy/bundle checkers must
revalidate copied logs against the fresh window and reject `ready_to_copy` without an
exact triplet; after accepted runtime evidence the next route is only
`identity_public_contract_gate_missing`; multi-surface beta candidates may be captured as
status-only side lanes but never replace player-principal evidence; the clean tester flow
is one direct-join tester, no cluster transfer/reconnect, logout only after exact
CheckJoin.

## 2026-06-07 19:08 CEST Cancelled Restart And Route-Lock Fix

The lead briefly started a PVP-Raideo restart countdown after misreading the operator's
restart context. The operator corrected scope: Obelisk work must not adjust or schedule
PVP-Raideo unless that server operation is explicitly requested. The countdown process
was terminated before `SaveWorld` or any lead restart, and both active maps received RCON
cancellation broadcasts. Later passive checks showed fresh ARK processes/log bootstrap on
both maps outside that cancelled countdown: TheIsland loaded Obelisk at `17:01:59Z`, and
Ragnarok loaded Obelisk at `17:03:28Z`. Treat those restarts as operator/external or
autorestart unless later evidence proves otherwise.

After the observed restart, exactly two ARK servers were running: TheIsland PID `3224523`
and Ragnarok PID `3235261`, both with `-ActiveEvent=Summer`, ProcessEvent enabled,
plugins disabled, and the player-principal lifecycle observer SHA
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`. TheIsland had
query/RCON `0/70`, observer gate only, no lifecycle roles, and no copied approved
evidence. A new passive monitor was started for the same run under
`passive-monitor-restarted-20260607T1704Z.log`; this is monitor metadata only.

Offline development fixed a route-lock integration bug: after accepted runtime evidence,
`check_command_permission_route_gate.py` now quarantines only the expected post-runtime
`player_identity_public_contract_gap` child while keeping the route locked at
`identity_public_contract_gate_missing`. The fix explicitly keeps permissions/admin,
command response, commands/replies, SDK/P0 progress, runtime readiness, and public SDK
readiness false/non-counting. Validation passed: route gate `82 OK`, bound route `53 OK`,
gap report `65 OK`, focal integration `1135 OK`, and `git diff --check` clean.

## 2026-06-07 19:41 CEST Exact-Triplet And Multi-Surface Offline Round

Six delegated agents were closed with no standby left open. This was an offline
integration round only: no live server, `/servidor/ark`, RCON, Discord, marker/env,
restart, GitHub, commit, tag, push, Plugin Hub, or publication action occurred.

Reusable technical changes:

- Approved player-principal evidence now requires exactly one copied lifecycle triplet:
  `session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
  `session_start_rejected`, and `session_end`.
- Duplicate start/end context, stale ready-log-copy context, non-exact rejected-start
  context, and non-exact bundle/manifest inputs fail closed before approved manifests are
  written.
- Pruned or stale terminal logout proof downgrades to non-evidence
  `SessionEndStaleNoop`; it may clear private correlation but must not dispatch a
  validated lifecycle event.
- RCON/ListPlayers/ServerListPlayers/ServerKickPlayer/static thunk/source-ready/status/
  route/command aliases remain admin or operational metadata only. They cannot unlock
  permissions/admin, command response, commands/replies, SDK/P0 progress, runtime
  readiness, or public SDK readiness.
- Chat/RCON/broadcast/send source aliases, including `sendSourceReady`, `send_status`,
  split `send_source`, and text variants, are rejected as downstream command-response or
  commands/replies authority.
- The multi-surface beta capture tooling can now prepare one tester session with primary
  player-principal plus admin, commands, dino, tribe, buff, inventory, item, and transfer
  side lanes. The pack remains redacted-metadata-only, no-restart, no-Discord,
  candidate-only, non-evidence, non-progress, and cannot clear
  `approved_runtime_evidence_missing`.

Validation passed: approved-evidence `187 OK`, approved-manifest builder `29 OK`,
evidence-bundle builder `115 OK`, C++ lifecycle focal tests plus CTest/runtime guardrails,
identity contract/preflight suite `351 OK`, permissions/admin plus command/response plus
multi-surface suite `416 OK`, global route/status guardrails `391 OK`, and
`git diff --check` clean. Strict SDK status remains
`approved_runtime_evidence_missing`, next
`approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
runtime/public/stable false, source overclaims `0`. `check_public_sdk_v1_completion.py`
still exits `1` as expected; it treats the multi-surface pack as a visible candidate
queue only, not approved evidence.

No Obelisk restart is pending from these offline changes. Restart only for a required
Obelisk deploy/gate change or a current operator request; do not restart merely to
broaden logging or because guardrails were hardened offline.

## Next Step

Keep the observer/passive monitor posture open only under the active authority/window and
continue offline development while waiting. When a candidate event set appears, run the
normal copy dry-run/checker path and leave `approved_runtime_evidence_missing` active
unless the exact copied triplet passes.
