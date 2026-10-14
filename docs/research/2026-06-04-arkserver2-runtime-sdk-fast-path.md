# arkserver2 Runtime SDK Fast Path

## Scope

Initial 2026-06-04 operator update, now historical: `arkserver2` on `TheIsland` was approved as the
debug/development target for necessary ObeliskSDK runtime work and launch acceleration.
The immediate SDK blocker remains approved copied runtime principal lifecycle evidence.

Historical correction recorded later on 2026-06-04: routing had moved from TheIsland to the two-server
Ragnarok+Genesis2 posture. Only `arkserver` / `Ragnarok` PID `1848240` and `arkserver3` /
`Genesis2` PID `1989133` are running; `arkserver2` / `TheIsland` is off. Never keep three
ARK servers running. The then-current passive monitor watched `arkserver:Ragnarok` plus
`arkserver3:Genesis2:27017` and writes
`/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log`. After the operator opened
ports, public GameDig query to `79.116.87.223:27017` returned map `Gen2`,
`connect=79.116.87.223:7783`, `queryPort=27017`, `numplayers=0`, `maxplayers=70`, and
ping about `13ms`; the earlier public-query/NAT blocker is resolved. This is not approval
for new marker/env changes, deploys, restarts, runtime capture, or chained restarts while
waiting.

Scope F offline correction: the active/passive wording above is historical routing
context only for this research note. The current supervised offline round authorizes no
live operations, server/log reads, `/servidor/ark` reads or writes, marker/env changes,
RCON, Discord, GitHub, publication, tags, or SDK/runtime/stable claims.
Interpret every old `active`, `current`, or `then-current` server/map phrase in this note
as timestamped historical context, not standing authorization. It does not grant
current-turn live reads, marker/env changes, process control, runtime capture,
publication, or SDK/P0 progress.

Passive monitor output and passive snapshots are diagnostic-only and remain
`ready=false`, `approved_runtime_evidence=false`, and non-evidence until the approved
evidence checkers accept a copied `PlayerPrincipalLifecycleObserver event` triplet plus
safe `apply_status`/`correlation_status` proof fields. The SDK remains
non-complete: route blocked at `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`,
and `stable_claim_allowed=false`.

Neither the initial approval, the then-current passive-wait posture, nor this offline
round grants Discord publication, GitHub publication, broad ProcessEvent tracing, raw
player text/gameplay payload logging, ReflectionScanner, native-exec probes, ptrace/gcore,
Frida/rr, public SDK readiness, runtime readiness, or v1 completion claims.

## 2026-06-04 Offline Completion Checker and Status-Proof Hardening

Latest offline integration at local `22:55` did not touch live ARK processes, server
markers, env, RCON, Discord, GitHub, or `/servidor/ark` writes. The delegated audit round
found the public SDK completion test was slow rather than stuck: quiet `unittest` runs hide
hundreds of checker/helper subprocesses. The checker now has a fail-closed helper
subprocess timeout controlled by
`OBELISK_PUBLIC_SDK_V1_COMPLETION_HELPER_TIMEOUT_SECONDS`, and the top-level test harness
fails explicitly if a checker subprocess exceeds its timeout.

The approved-evidence lane was tightened with synthetic offline negatives:

- old-format `PlayerPrincipalLifecycleObserver event` lines without
  `apply_status`/`correlation_status` are malformed and non-evidence;
- logout variants with unresolved, duplicate, stale, or missing correlation status remain
  non-evidence;
- approved manifests that mutate only observed-case or function-detail status proof fields
  are rejected and leave `approved_runtime_evidence_present=false`.

Plugin/runtime guardrails now also keep player-principal identity/event alias tokens out of
PluginManager public ABI wiring and assert that
`PlayerPrincipalEventDispatcher::Get().Register(` remains test-only until player identity
promotion adds public ABI, owner cleanup, and SDK consumer tests.

Validation from this offline round:

- focal tests: 24 OK;
- analyzer, approved-evidence, bundle, and approved-manifest suites: 244 OK;
- PluginManager, player-principal runtime, handoff, research, and operational guardrails:
  130 OK;
- full `scripts.test_check_public_sdk_v1_completion`: 282 OK in 242.223 seconds under a
  420 second timeout;
- `scripts/report_obelisk_sdk_status.py`: still blocked at
  `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`;
- `git diff --check -- .`: OK.

This hardening improves false-positive resistance only. It does not produce approved
runtime evidence, public player identity ABI, runtime readiness, public SDK readiness, or a
complete SDK claim.

## 2026-06-04 Supervised Offline SDK Round

Latest supervised offline round at local `23:11` used six scoped agents and closed all six
before integration. It did not perform live operations, server reads/writes, marker/env
changes, RCON, Discord, GitHub publication, tags, or readiness claims.

Integrated findings and changes:

- Player identity public decision records now require explicit false flags for
  `live_ops_authorized`, `server_operations_authorized`, `workspace_writes_authorized`,
  `runtime_capture_authorized`, and `reads_live_logs`, plus a matching no-authorization
  non-claim. The aggregate public-contract readiness report propagates those false flags.
- The player identity public-header gate rejects neutral free-form overclaims such as a
  ready public header or approved runtime evidence unlocking public header work, and it
  rejects adjacent public identity/lookup-style symbols beyond the exact proposal.
- Approved runtime evidence intake rejects additional analyzer quality counters and adds
  regressions for old-format lifecycle lines plus copied-log mutations of
  `apply_status`/`correlation_status`.
- Inventory copied-signal stability now pins public-header numeric ABI values for the
  five copied inventory/item `GameplayPolicyEvent` signals, their masks, the relevant
  field masks, and `OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM`.
- Status reporting and docs guardrails preserve source overclaims but normalize passive
  complete triplets, missing Genesis2 `session_end`, and historical TheIsland sidecars
  back to non-authorizing/non-evidence.

Read-only agent conclusions:

- Runtime/C ABI audit found no public player-principal/player-identity ABI leak, missing
  owner-cleanup decision, process-lifetime registry issue, or lifecycle callback cleanup
  gap.
- Static/reversing audit found no new no-live artifact worth adding for the active blocker.
  The semantic `HandleNewPlayer`/`OnLogout` snapshot-root check is already accepted as
  layout/planning evidence only. More offline drift analysis would be explanatory and would
  not move `approved_runtime_evidence_missing`.

Validation:

- public identity contract/header suites: 123 OK;
- inventory/status/handoff suites: 64 OK;
- approved-evidence and bundle suites: 185 OK;
- public/runtime guardrails: 257 OK;
- full public SDK completion checker: 282 OK in 241.604 seconds under a 420 second timeout.

Status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`,
`stable_claim_allowed=false`. The only artifact that can move the blocker is a
checker-accepted, copied approved runtime principal lifecycle evidence bundle with the
required sibling sidecars and status-proof fields.

## Original Fastest Safe Route (Superseded)

This initial route was superseded by the later active diagnostic window, organic
TheIsland candidate capture, and passive wait posture below. Do not treat this section as
the current restart/install instruction.

1. Commit the current validated hardening checkpoint so runtime evidence can bind to a
   reviewed 40-character Obelisk commit.
2. Rebuild `libobelisk.so`.
3. Refresh `/servidor/ark/obelisk` with `scripts/install_obelisk.sh --backup-existing`.
4. Refresh `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh` from
   `packaging/linuxgsm/ObeliskRun.sh`; read-only preflight found wrapper drift.
5. Prepare a fresh player-principal lifecycle request pack for a short future window on
   `arkserver2` / `TheIsland`.
6. Use only the player-principal lifecycle observer markers/env, plugins disabled,
   dispatch limit `0`, log limit `10`, and no scanner/debug/callback escape markers.
7. Start or restart `arkserver2` only inside the scoped window, copy `Obelisk.log` to the
   run evidence directory, rollback observer markers/env to stable posture, then run the
   post-window checks.
8. Build the approved runtime principal lifecycle evidence bundle and route proof. The
   expected route transition is from `approved_runtime_evidence_missing` to locked
   `identity_public_contract_gate_missing`, with all public/runtime/promotion/v1 flags
   still false.

## Initial Observed Preflight (Superseded)

This preflight describes the state before the later install/restart/debug window. Later
runtime posture for that historical sequence is recorded in subsequent sections; it is
not current authorization.

- `scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --map
  TheIsland --mode stable --expected-binary-sha256
  7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 --allow-stopped
  --json` failed on LinuxGSM wrapper drift before any marker/runtime changes.
- `scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance
  arkserver2` reported no running `ShooterGameServer` process for `TheIsland`.
- `scripts/install_obelisk.sh --build-dir build --dry-run /servidor/ark/obelisk` printed
  the expected staged runtime/SDK install plan without changing files.

## 20260603T233330Z Runtime Window Result

Artifacts:

```text
/servidor/ark/workspace-offline/live-validation-logs/20260603T233330Z-player-principal-lifecycle/
```

Window:

- approved start: `2026-06-03T23:33:30Z`
- approved end: `2026-06-03T23:41:30Z`
- actual observer capture: `2026-06-03T23:33:54Z` to `2026-06-03T23:40:00Z`
- rollback completed: `2026-06-03T23:40:23Z`; manifest rollback end recorded as
  `2026-06-03T23:40:50Z` to include the stable post-check sidecar.

Accepted operational facts:

- LinuxGSM wrapper matched the versioned template before the run.
- Pre-window observer preflight passed with `offline_only=false` and `allow_stopped=false`.
- Runtime log showed native LD_PRELOAD load, ProcessEvent candidate count `1`, candidate
  address `0x1d34e20`, absolute hook patch size `18`, ReflectionScanner disabled, plugins
  disabled, and a single player-principal lifecycle observer gate:
  `limit=10`, `dispatch_limit=0`, `delivery_claim=none`, `principal_claim=none`.
- Post-window manifest replay is accepted with verified completed operator receipt.
- Stable rollback left only `disable-plugins` and `enable-process-event-hook` markers on
  `arkserver2`; stable posture/preflight passed and the new server process has no observer
  env.

Rejected evidence result:

```text
analyze_runtime_observer_log failed with exit 1:
runtime observer summary has quality blockers:
player_principal_lifecycle: no_accepted_or_rejected_observer_lines
```

No approved runtime-principal lifecycle evidence manifest was produced. The route remains
`approved_runtime_evidence_missing`.

Reason: no ARK client/player was available during the window, so startup produced the
observer gate but no `HandleNewPlayer` or `OnLogout` lifecycle events. Accepted evidence
requires real lifecycle activity in the copied log: `session_start_created/not_applicable`,
`session_start_rejected_noop/not_applicable`, and `session_end_invalidated/matched`.

## Passive Wait Correction

After additional short windows, the operator correctly pointed out that repeated restarts
make it unlikely for organic players to join. The live-ops posture changed from timed
window chaining to passive presence detection:

- stop scheduled player-principal window controllers instead of allowing another
  automatic rollback/restart while waiting for players;
- leave running ARK processes alone;
- remove future observer markers from `arkserver2` so a future normal restart does not
  inherit the observer window;
- monitor player count with local Steam query only, not LinuxGSM `monitor`;
- open the next bounded observer/evidence window only after real player presence is
  detected or the operator gives a fresh exact instruction.

Integrated helper:

```bash
scripts/monitor_ark_player_presence_passive.sh --interval 30 \
  arkserver:Ragnarok arkserver2:TheIsland
```

Implementation facts:

- `arkserver` / `Ragnarok` query port: `27015`
- `arkserver2` / `TheIsland` query port: `27016`
- this installed GameDig catalog uses type `ase`; old alias `arkse` returns
  `{"error":"Invalid game: arkse"}` and must be treated as a query error, not as
  `0` players
- the helper never calls LinuxGSM `monitor`, `start`, `stop`, or `restart`, and never
  edits markers
- the earlier detached monitor log/PID were placed outside `/servidor/ark`:
  `/tmp/obelisk-player-presence-monitor.log` and
  `/tmp/obelisk-player-presence-monitor.pid`
  (superseded by the active
  `/tmp/obelisk-passive-player-monitor-20260604.log` monitor in the current handoff)

Observed passive check at `2026-06-04T00:21:07Z`: both `Ragnarok` and `TheIsland` were
queryable with `players=0/70`, maps matched expected values, and both current server
processes carried `-ActiveEvent=Summer`.

## 2026-06-04 Organic Player Negative Result

Passive monitoring later observed a real organic player on `arkserver2` / `TheIsland`:

- `2026-06-04T00:34:44Z`: GameDig reported `players=1/70`, name `TITAN 654`.
- `2026-06-04T00:36:11Z` through `2026-06-04T00:38:28Z`: repeated read-only queries still
  reported `players=1/70`, name `TITAN 654`.
- `2026-06-04T00:38:44Z`: GameDig reported `players=0/70`; the player had left.

During that whole connect/disconnect interval, `/servidor/ark/obelisk/logs/arkserver2/Obelisk.log`
contained only the player-principal lifecycle observer enable line:

```text
PlayerPrincipalLifecycleObserver enabled binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 target_set=players-lifecycle-anchor-candidates limit=10 dispatch_limit=0 delivery_claim=none principal_claim=none.
```

It did not contain `PlayerPrincipalLifecycleObserver event` lines for `session_start`,
`session_start_rejected`, or `session_end`.

Interpretation: player presence is no longer the immediate blocker. The current accepted
observer targets, `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`, did
not fire for this observed join/leave path, or the path did not pass through the
post-original `ProcessEvent` route. This is a negative runtime result, not approved
principal lifecycle evidence.

Follow-up implemented offline: the runtime now has an opt-in candidate-only diagnostic
gate, `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1`, under the same
player-principal lifecycle observer gate. It logs at most the normal bounded log limit for
known `players-lifecycle-anchor-candidates` UFunction indices:

- `ShooterGameMode.CheckJoinInProgress` (`1845`)
- `ShooterGameMode.HandleNewPlayer` (`2170`, still the accepted start target)
- `ShooterGameMode.OnLogout` (`2384`, still the accepted end target)
- `GameMode.K2_PostLogin` (`4943`)
- `ShooterGameMode.OnPostLogin__DelegateSignature` (`28545`)
- `ShooterGameMode.OnStartNewPlayer__DelegateSignature` (`28555`)

Diagnostic lines use the prefix `PlayerPrincipalLifecycleDiagnostic` and log only
candidate target, `fname_index`, `post_original=true`, and explicit non-claims. They do
not read params, log identity, dispatch callbacks, satisfy approved runtime evidence, or
promote public player identity/SDK readiness.

Operator instruction captured on `2026-06-04`: when necessary, scoped passive server tests
may be activated and left waiting for player logs while offline development continues in
parallel. This does not authorize repeated restarts while waiting, broad tracing, raw
payload logging, scanner/native-exec/ptrace tools, publication, or SDK readiness claims.

## 2026-06-04 Active Diagnostic Window

After the candidate-only diagnostic gate was implemented and the documentation guardrail
was restored, the rebuilt runtime/SDK was installed to `/servidor/ark/obelisk` without
creating backup copies, and the installed LinuxGSM wrapper was refreshed from
`packaging/linuxgsm/ObeliskRun.sh`. `scripts/check_linuxgsm_wrapper_drift.sh` then
reported the installed wrapper matched the versioned template
(`sha256=e9c72bba7dd2ab86d0ae21e09d1881808f4c4ed5d9555bdaef4c73d9590b1b4b`).

Historical diagnostic window note, now superseded: this earlier run used both approved
debug/development targets:

- `arkserver` / `Ragnarok`
- `arkserver2` / `TheIsland`

Both instances were restarted once at about `2026-06-04T01:54Z`, after GameDig reported
`players=0/70` on both maps. The exact marker set was:

- `enable-process-event-hook`
- `disable-plugins`
- `allow-observer-debug-window`
- `allow-experimental-observers`
- `enable-player-principal-lifecycle-observer`

The exact observer env included `OBELISK_WRAPPER_PROFILE=observer-debug`,
`OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10`,
`OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0`, and
`OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1`. It did not enable scanner,
native exec, ptrace, global/filtered callbacks, ProcessEvent blocking, or payload/identity
logging.

Post-restart checks from that historical run:

- then-current processes were `Ragnarok` and `TheIsland`, both with `-ActiveEvent=Summer`;
- then-current process env had the observer and diagnostic env above on both instances;
- `Obelisk.log` on both instances contains `PlayerPrincipalLifecycleObserver enabled` and
  `PlayerPrincipalLifecycleDiagnostic candidate-only logging enabled`;
- GameDig returned `status=ok`, expected maps, and `players=0/70` on both query ports at
  `2026-06-04T01:57Z`.

Superseding passive monitor PID `2221667` writes
`/tmp/obelisk-passive-player-monitor-20260604.log` every 10s with `--no-details` and
`--linger-after-detect 900` on `arkserver2:TheIsland`. Leave it running while offline
development continues. If players appear, copy/analyze logs before changing markers or
restarting. Candidate
diagnostic lines are non-evidence and cannot clear `approved_runtime_evidence_missing`;
they only identify which lifecycle candidates fire under organic player join/leave
activity.

## 2026-06-04 TheIsland Candidate Capture

While the active diagnostic window was left running, `arkserver2` / `TheIsland` logged
organic lifecycle candidates:

- `04:20:36` local: `ShooterGameMode.CheckJoinInProgress` (`fname_index=1845`),
  `ShooterGameMode.HandleNewPlayer` (`2170`, `accepted_lifecycle_target=true`), and
  `GameMode.K2_PostLogin` (`4943`).
- `04:21:12` local: `CheckJoinInProgress` and `HandleNewPlayer` again.

Copied capture directory:
`/tmp/obelisk-player-principal-live-capture-20260604T0220Z/`.

Copied file hashes:

- `arkserver2-Obelisk.log`:
  `68aac785f35e9c189e9d01f53a8f1c4e3fb846372be22b5eb3bbc74afd3ca34a`
- `arkserver-Obelisk.log`:
  `b3b7a601bd3bcadbe6b303feec7fa6a9ccd9557f7441a87f24c5839b1a3d479f`
- `passive-player-monitor.log`:
  `0056f7e4d276584817a9c313fa35bcf6403205409e33da2765acc9ac2ef73c01`

`python3 scripts/analyze_runtime_observer_log.py` on the copied TheIsland log still
reports `accepted_count=0` and blockers `runtime_observer_evidence_only` plus
`no_accepted_or_rejected_observer_lines`. This proves the hook sees the accepted
`HandleNewPlayer` FName during organic join activity, but the current reflected/copy path
does not emit a normal `PlayerPrincipalLifecycleObserver event` line.

Follow-up implemented and deployed once: `ProcessEventHook.cpp` logs safe reflection/copy
rejection reasons under the existing
`PlayerPrincipalLifecycleDiagnostic candidate ... evidence_claim=none` prefix. The new
diagnostic line keeps `params_logged=false` and `identity_logged=false`; it is still
non-evidence and only helps identify why a `HandleNewPlayer` invocation did not become
`session_start`/`session_start_rejected`.

After deploying the rejection logger, TheIsland immediately logged:

```text
PlayerPrincipalLifecycleDiagnostic candidate sequence=1 target=ShooterGameMode.HandleNewPlayer fname_index=2170 post_original=true accepted_lifecycle_target=true reflection_status=rejected read_status=implausible reason=lifecycle_property_FName_mismatch params_logged=false identity_logged=false evidence_claim=none.
```

Interpretation: the hook sees the accepted `HandleNewPlayer` target, but the runtime
property shape does not match the static planning snapshot. A follow-up fix changed
`PlayerPrincipalLifecycleReflection` to match lifecycle properties by FName while still
validating each expected offset, size, flags, class, bool metadata, and copied bool range.
A reordered property-chain unit test was added, but after that build was deployed
TheIsland still logged the same generic `lifecycle_property_FName_mismatch` at local
`04:50:47`.

The next deployed diagnostic expands the mismatch reason with observed property FName
indices. It was installed to `/servidor/ark/obelisk` and both approved instances were
restarted at local `04:54`/`04:55`. Post-deploy state:

- `arkserver2` / `TheIsland` PID `1777299`;
- `arkserver` / `Ragnarok` PID `1779863`;
- both processes have `-ActiveEvent=Summer`;
- both process envs have the lifecycle observer and diagnostic candidates enabled with
  log limit `10`, dispatch limit `0`, and plugins disabled;
- both map `/servidor/ark/obelisk/lib/libobelisk.so` without a deleted mapping;
- monitor PID `1408991` was active for that historical window and is now superseded.

The route is still blocked at `approved_runtime_evidence_missing` until the next organic
join/leave produces normal `PlayerPrincipalLifecycleObserver event` lines accepted by the
evidence checkers. If it still rejects, the next diagnostic line should include the
observed property FName-index list needed for the next offline fix.

## 2026-06-04 05:12 TheIsland Negative Snapshot

`arkserver2` / `TheIsland` was refreshed again in observer-debug at local `05:12` as the
then-current live observation target:

- PID `1877917`;
- `-ActiveEvent=Summer`;
- ProcessEvent hook installed at `0x1d34e20`;
- plugins disabled;
- observer gate logged at local `05:13:17`;
- lifecycle log limit `10`, dispatch limit `0`, and candidate-only diagnostics enabled.

After the user reported a new player, the copied snapshot
`/tmp/obelisk-player-principal-live-capture-20260604T0317Z/` was analyzed with
`scripts/analyze_runtime_observer_log.py`. Result:

```text
accepted_count=0
rejected_count=0
no PlayerPrincipalLifecycleObserver event lines
```

This is another negative observation, not approved runtime-principal lifecycle evidence.
The runtime remains observational only and does not support a public SDK/runtime readiness
claim. The reported join produced no accepted/rejected/candidate outcome lines in the
copied window, and TheIsland query still reported `players=0/70`.

Follow-up monitor hardening was applied after this snapshot: the passive monitor now
surfaces metadata-only `PlayerPrincipalLifecycleDiagnostic candidate` lines and supports
`--no-details` so long waits do not spawn LinuxGSM helper processes for stopped instances.
The then-active passive monitor was PID `2221667`, command
`scripts/monitor_ark_player_presence_passive.sh --interval 10 --linger-after-detect 900
--no-details arkserver2:TheIsland`, writing
`/tmp/obelisk-passive-player-monitor-20260604.log`. Do not restart while waiting.
`arkserver` / `Ragnarok` is stopped after external backup state and must not be restarted
unless explicitly approved.

That six-agent analyzer/monitor round integration: this negative analyzer result and
the `--no-details` passive monitor state were the runtime facts for that historical window. They do
not clear `approved_runtime_evidence_missing` or authorize another restart. The analyzer
now preserves strict non-evidence diagnostic-candidate aggregates from copied logs: the
`0220Z` copied TheIsland log reports 5 candidates
(`CheckJoinInProgress` 2, `HandleNewPlayer` 2, `K2_PostLogin` 1), and the `0245Z` copied
TheIsland log reports 3 candidates including one
`lifecycle_property_FName_mismatch` rejection with `read_status=implausible`. Both remain
`accepted_count=0`, `rejected_count=0`, `readiness_gate=none`.

## 2026-06-04 Local Metadata-Only FName Mismatch Diagnostics Patch

A newer local runtime patch extends `ue/PlayerPrincipalLifecycleReflection.cpp` and
`tests/core/PlayerPrincipalLifecycleReflectionTests.cpp` so
`lifecycle_property_FName_mismatch` carries bounded observed property-chain metadata:
`expected_name_index`, `observed_count`; per-property `prop_N_name_index`,
`prop_N_number`, `prop_N_offset`, `prop_N_size`, `prop_N_element_size`,
`prop_N_array_dim`, `prop_N_flags`, `prop_N_class_name_index`, and
`prop_N_class_number`; plus `prop_N_bool_field_size`, `prop_N_bool_byte_offset`,
`prop_N_bool_byte_mask`, and `prop_N_bool_field_mask` for bool properties. It deliberately
excludes `class_object`, params, identity, pointers, and hex. Analyzer tests were also
extended to accept the richer safe diagnostic reason tokens.

These reasons still flow through `PlayerPrincipalLifecycleDiagnostic candidate` lines with
`params_logged=false`, `identity_logged=false`, and `evidence_claim=none`, so they are
diagnostic-only and cannot satisfy approved runtime-principal lifecycle evidence.

Follow-up after a user-reported new TheIsland player at local `05:45`-`05:47`: a one-shot
passive query reported `players=0/70`, and a live-path opt-in analyzer read of
`/servidor/ark/obelisk/logs/arkserver2/Obelisk.log` still had `accepted_count=0`,
`rejected_count=0`, `diagnostic_candidate_count=0`, `readiness_gate=none`, hook active,
plugins disabled, and scanner disabled. The log mtime remained local `05:13:17`; no new
diagnostic or lifecycle evidence was produced by the currently deployed older runtime.
The passive monitor was then replaced with PID `2132502` using `--linger-after-detect
900`, so the next detected player keeps the read-only log/query window open for 15
minutes without LinuxGSM `details`, marker edits, starts, stops, or restarts.

Safety correction: the local reflection patch now rejects reordered `HandleNewPlayer`
property chains again. A short-lived search-by-FName matcher was rejected because lifecycle
evidence must preserve exact `Children` chain position; the safe diagnostic path reports
the observed `prop_N_*` chain on rejection instead of accepting reordered shapes.
Analyzer correction: diagnostic reason safety now normalizes `_ . : -` separators before
forbidden-fragment matching, so identity-like variants such as `steam_id`, `player_id`,
`unique_net_id`, `resource_handle`, `tribe_id`, and `ip_address` are rejected as malformed
diagnostics rather than counted as safe candidate reasons. A later local hardening also
rejects `class_object`/`pointer`/`params` diagnostic reason fragments and redacts unsafe
lower-level lifecycle reasons to `lifecycle_reflection_rejected`. It is local-only until a
separate approved deploy/restart window.

Follow-up after a second user-reported TheIsland join at local `06:12`: the direct
read-only query again reported `players=0/70`, `Obelisk.log` mtime remained local
`05:13:17`, and live-path opt-in analysis still reported `accepted_count=0`,
`rejected_count=0`, `diagnostic_candidate_count=0`, `readiness_gate=none`. The 60s
two-target monitor was replaced with the 10s TheIsland-only passive monitor PID `2221667`
to reduce the chance of missing very short joins without restarting ARK.

Lead-reported validation passed: `ctest PlayerPrincipalLifecycleReflectionTests`,
`python3 -m unittest scripts.test_analyze_runtime_observer_log`, targeted CMake build for
`player_principal_lifecycle_reflection_tests`,
`process_event_player_principal_lifecycle_observer_tests`, and `obelisk`, plus touched-file
`git diff --check`.

No server deploy, marker change, or restart was performed for this local patch. Active
posture remains passive wait on `arkserver2` / `TheIsland`, copied-log analysis before any
marker/server change, and no restart of stopped `arkserver` / `Ragnarok` without explicit
approval.

## 2026-06-04 Latest User-Reported Join Recheck

At local `06:42`, after another user-reported TheIsland join, read-only checks still found
`arkserver2` running TheIsland with PID `1877917` and passive monitor PID `2221667`. A
one-shot GameDig query returned `players=0/70`, and `/tmp/obelisk-passive-player-monitor-20260604.log`
had no `players=1+` sample for the reported interval. The live Obelisk log stayed at
mtime local `05:13:17` and size `1478`; analyzer output remained
`accepted_count=0`, `rejected_count=0`, `diagnostic_candidate_count=0`, and
`readiness_gate=none`.

This is another negative runtime observation, not accepted lifecycle evidence. It should
not clear `approved_runtime_evidence_missing`, trigger SDK readiness, or justify chained
restarts while the passive monitor is still running.

In parallel, the lead collected/closed all six delegated agents. Integrated local checker
work in this round:

- bound route reports now expose top-level route aliases so the current blocker is visible
  as `current_route_blocker=approved_runtime_evidence_missing`;
- scoped SDK release-statement scope validation detects embedded surface outcome rows;
- public identity contract gap reporting keeps the contract gate inactive until approved
  runtime evidence exists and lists unresolved decision keys;
- `inventory-custom-filter-array-boundary` is a candidate-only, non-P0, non-promoting
  side-lane checker for the committed `InventoryCustomFilter` array metadata snapshot.

Validation passed locally: route-bound 19 OK, public-contract gap report 40 OK, inventory
side-lane 5 OK, focused SDK release-statement tests 3 OK, and `py_compile` for touched
Python checkers. No server operation, marker/env change, deployment, restart, GitHub,
Discord, tag, release, or publication was performed.

## 2026-06-04 Local CheckJoinInProgress Diagnostic-Only Patch

At local `06:59`-`07:00`, after another user report that a player entered TheIsland,
read-only checks still showed:

```text
arkserver2 query: players=0/70
Obelisk.log mtime: 2026-06-04 05:13:17.449112210 +0200
accepted_count=0
rejected_count=0
diagnostic_candidate_count=0
readiness_gate=none
```

The passive monitor remained PID `2221667` with 10s interval, `--no-details`, and 900s
post-detect linger. No marker/env change, deployment, restart, LinuxGSM monitor/details,
Discord, GitHub, tag, release, or publication occurred.

In parallel, a local-only runtime patch added an exact-shape diagnostic recognizer for
`ShooterGameMode.CheckJoinInProgress` (`fname_index=1845`). The recognizer validates the
reflected function shape, copies only canonical bools from `bIsFromLogin` and
`ReturnValue`, redacts the `NewPlayer` object field, keeps
`accepted_lifecycle_target=false`, `params_logged=false`, `identity_logged=false`, and
`evidence_claim=none`, and never emits `PlayerPrincipalLifecycleObserver event` or
dispatches callbacks. This is designed to make the next approved runtime window more
informative without promoting diagnostic candidates into lifecycle evidence.

Validation passed:

```text
cmake --build build --target player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests obelisk -j2
ctest --test-dir build -R 'PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_analyze_runtime_observer_log
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_monitor_ark_player_presence_passive
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_operational_doc_guardrails scripts.test_research_doc_guardrails
git diff --check
```

The full `scripts.test_check_public_sdk_v1_completion` module remained too slow for a
300s sub-agent cap; focused SDK completion alias tests passed, and the complete SDK route
still reports SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`, and
`approved_runtime_evidence_missing`.

## 2026-06-04 K2_PostLogin Metadata-Only Diagnostic Follow-Up

After a later user-reported TheIsland join, read-only checks at local `07:16` found the
same active TheIsland server PID `1877917` and passive monitor PID `2221667`, but still no
query/log proof of a player: GameDig reported `players=0/70`, the passive monitor had no
`players=1+` or `player_presence_*` samples, and both live Obelisk logs stayed unchanged
after the observer gate lines. Direct analyzer output remained `accepted_count=0`,
`rejected_count=0`, `diagnostic_candidate_count=0`, and `readiness_gate=none`. This is a
negative observation, not approved runtime evidence.

A local-only runtime/test patch now recognizes exact-shape `GameMode.K2_PostLogin`
(`fname_index=4943`) as diagnostic-only metadata:

- outer object: `GameMode` name index `9731`, object index `405`;
- function flags: `0x0c020800`;
- params: `NumParms=1`, `ParmsSize=8`, `ReturnValueOffset=0xffff`;
- field: one redacted `NewPlayer:ObjectProperty` at offset `0`, size `8`;
- log contract: `accepted_lifecycle_target=false`, `diagnostic_shape=K2_PostLogin`,
  `params_logged=false`, `identity_logged=false`, and `evidence_claim=none`.

Unlike `CheckJoinInProgress`, K2 copies no bool values. The observer rejects it as an
accepted lifecycle observation, accepts it only through
`TryBuildCopiedLifecycleDiagnosticObservation`, and rejects it when building a public
`PlayerPrincipalEventView`. The analyzer counts valid K2 lines only as
`diagnostic_candidate_count`; the approved-evidence checker rejects diagnostic-only K2
logs and allows K2 lines beside already-valid real lifecycle evidence without changing
`observed_runtime_cases`.

The SDK completion checker gained a test-only subprocess cache controlled by
`OBELISK_PUBLIC_SDK_V1_COMPLETION_SUBPROCESS_CACHE_DIR`, keyed by argv, `OBELISK_*` env,
Python version, and file-argument hashes. This does not change release semantics:
uncached and cached runs preserve route `approved_runtime_evidence_missing`, SDK `0/12`,
P0 `0/4`, and `stable_claim_allowed=false`.

Additional validation passed:

```text
cmake --build build --target player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests obelisk -j2
ctest --test-dir build -R 'PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_analyze_runtime_observer_log
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_monitor_ark_player_presence_passive scripts.test_build_v1_scoped_release_statement
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate_bound_identity_sources scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_inventory_custom_filter_array_boundary
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion
git diff --check -- hooks/ProcessEventHook.cpp hooks/ProcessEventPlayerPrincipalLifecycleObserver.cpp ue/PlayerPrincipalLifecycleReflection.cpp ue/PlayerPrincipalLifecycleReflection.h tests/core/PlayerPrincipalLifecycleReflectionTests.cpp tests/core/ProcessEventPlayerPrincipalLifecycleObserverTests.cpp scripts/analyze_runtime_observer_log.py scripts/test_analyze_runtime_observer_log.py scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py scripts/test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py
```

The full SDK completion module passed 253 tests in this round. The scoped release
statement check still reports `status=blocked`, `current_route_blocker=approved_runtime_evidence_missing`,
`stable_claim_allowed=false`, and `scoped_release_statement.ready=true`; it does not unlock
public SDK readiness.

No server deploy, marker/env change, restart, LinuxGSM monitor/details, GitHub, Discord,
tag, release, or publication occurred for this follow-up. All delegated agents from the
round were closed.

## 2026-06-04 Ragnarok Re-Enabled Passive Two-Map Window

After the operator asked why Ragnarok was off and explicitly directed that both
`Ragnarok` and `TheIsland` remain up for passive player-evidence collection, `arkserver`
was checked and restarted into the same bounded observer-debug posture as `arkserver2`.

Read-only preflight facts:

- `arkserver.cfg` still points to `Ragnarok`, query port `27015`, RCON `27020`, and
  `-ActiveEvent=Summer`.
- `arkserver2.cfg` points to `TheIsland`, query port `27016`, RCON `27021`, and
  `-ActiveEvent=Summer`.
- both instance marker directories contained only the expected lifecycle observer window
  files: `enable-process-event-hook`, `disable-plugins`, `allow-observer-debug-window`,
  `allow-experimental-observers`, and `enable-player-principal-lifecycle-observer`.

Two plain start attempts failed before ARK wrote console output. The root cause was the
observer marker/profile mismatch: with experimental observer markers present, a normal
stable wrapper launch refuses to start unless `OBELISK_WRAPPER_PROFILE=observer-debug`
and the required player-principal lifecycle SHA/log-limit/dispatch env are inherited by
the tmux process. Because the wrapper exits before LinuxGSM attaches `pipe-pane`, the
console can remain empty. LinuxGSM's fail message displayed TheIsland because the shared
`GameUserSettings.ini` still supplies that `SessionName`; the real launch command must be
verified from `pgrep -af ShooterGameServer`.

Successful restart used:

```text
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1
```

It did not enable plugins, scanner, ptrace, native exec, global/filtered callbacks,
ProcessEvent blocking, or payload/identity logging.

Post-start facts at local `07:39`:

- `arkserver` / `Ragnarok` PID `2603032`, query `27015`, `players=0/70`, runtime loaded
  by LD_PRELOAD, ProcessEvent hook `0x1d34e20`, plugins disabled, scanner disabled,
  observer gate local `07:38:12`.
- `arkserver2` / `TheIsland` PID `1877917`, query `27016`, `players=0/70`, same
  observer-debug lifecycle posture.
- persistent passive monitor is tmux session `obelisk_passive_monitor` on socket
  `obelisk-passive-monitor`, appending
  `/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log` with:

```text
scripts/monitor_ark_player_presence_passive.sh --interval 10 --linger-after-detect 900 --no-details arkserver:Ragnarok arkserver2:TheIsland
```

The monitor reported both maps queryable and both logs showing only observer/diagnostic
gate lines. There are still no `PlayerPrincipalLifecycleObserver event` lines for
`session_start`, `session_start_rejected`, or `session_end`, so the route remains blocked
at `approved_runtime_evidence_missing`.

## 2026-06-04 Lead Integration After Passive Two-Map Restore

All six previously open delegated agents were closed after their final reports were
collected. Local checker/runtime-test integration for this round includes:

- scoped release-statement output now rejects protected live-server paths and symlinked
  protected outputs;
- SDK completion JSON exposes a backward-compatible top-level `summary` with
  `sdk_completion`, `p0_completion`, and `non_claim` while preserving blocked semantics;
- approved runtime principal lifecycle evidence tests reject diagnostic-only
  `CheckJoinInProgress` and `K2_PostLogin` material even when wrapped beside valid
  lifecycle observations;
- bound route checks ensure top-level route aliases cannot drift past
  `identity_public_contract_gate_missing` after accepted runtime evidence;
- C++ lifecycle observer tests reject diagnostic-only copied bool payloads when building
  public `PlayerPrincipalEventView`.

Validation passed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_v1_scoped_release_statement scripts.test_check_public_sdk_v1_completion scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate_bound_identity_sources scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_inventory_custom_filter_array_boundary scripts.test_analyze_runtime_observer_log scripts.test_monitor_ark_player_presence_passive
cmake --build build --target obelisk player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests -j2
ctest --test-dir build -R 'PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_operational_doc_guardrails scripts.test_research_doc_guardrails
git diff --check
```

The first Python command ran 350 tests and the second ran 109 tests. Direct SDK summary
still reports:

```text
status=blocked
current_route_blocker=approved_runtime_evidence_missing
stable_claim_allowed=false
sdk_progress=0/12
p0_progress=0/4
sdk_ready=false
sdk_claim_ready=false
```

## 2026-06-04 Passive Snapshot and Monitor Hardening

After the operator reported concern that `Ragnarok` appeared off, the lead rechecked the
actual process table instead of relying on PATH-local `arkmanager`. Both servers were
running and were left untouched:

- `arkserver` / `Ragnarok`: PID `2603032`, started local `07:37:30`, query `27015`,
  `-ActiveEvent=Summer`.
- `arkserver2` / `TheIsland`: PID `1877917`, started local `05:12:35`, query `27016`,
  `-ActiveEvent=Summer`.

The full passive monitor log and both live Obelisk logs were searched for `players=1+`,
`PlayerPrincipalLifecycleObserver event`, `session_start`, `session_start_rejected`, and
`session_end`. No matching player-positive or accepted lifecycle evidence lines were
present in the available logs.

Offline snapshot helper added:

```text
scripts/capture_player_principal_passive_snapshot.py
```

The helper copies current logs only to a non-protected output directory and analyzes the
copied files. It does not start, stop, restart, call LinuxGSM `monitor`, edit markers, or
claim runtime/public SDK readiness. Its live snapshot was written outside the server tree:

```text
/tmp/obelisk-player-principal-passive-snapshot-20260604T055410Z/manifest.json
```

Snapshot result:

- `all_logs_copied=true`
- `ready=false`
- `approved_runtime_evidence=false`
- `arkserver` / `Ragnarok`: accepted `0`, rejected `0`, diagnostic candidates `0`
- `arkserver2` / `TheIsland`: accepted `0`, rejected `0`, diagnostic candidates `0`

The passive monitor script was hardened and then refreshed in tmux without restarting
either ARK server. New monitor facts at local `07:55`:

- tmux socket/session: `obelisk-passive-monitor` / `obelisk_passive_monitor`
- monitor PID: `2695206`
- same command: `--interval 10 --linger-after-detect 900 --no-details
  arkserver:Ragnarok arkserver2:TheIsland`
- log: `/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log`
- new per-instance lines report `observer_tail status=matched` for both instances.

Follow-up at local `08:03`: the tmux monitor was refreshed again without restarting ARK
to enable the new opt-in one-shot snapshot trigger:

```text
--snapshot-output-root /tmp/obelisk-passive-evidence-snapshots
--snapshot-monitor-log /tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log
```

The monitor only calls `scripts/capture_player_principal_passive_snapshot.py` after
`players=1+` is detected. Until that happens, no new snapshot directory is created. The
captured manifest remains `ready=false` and `approved_runtime_evidence=false`; accepted
runtime evidence still requires real copied `PlayerPrincipalLifecycleObserver event` lines
accepted by the evidence checkers.

Integrated validations:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_capture_player_principal_passive_snapshot
bash -n scripts/monitor_ark_player_presence_passive.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_monitor_ark_player_presence_passive
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_normalized_summary_completion_sections_remain_non_claim_when_route_blocked scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_scoped_release_statement_builder_generates_non_claim_blocker_outcomes
python3 scripts/test_operational_doc_guardrails.py
bash scripts/test_linuxgsm_wrapper_markers.sh
```

Result: this is a better passive-evidence capture posture, not approved runtime evidence.
The route remains `approved_runtime_evidence_missing`; SDK remains `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`.

## 2026-06-04 08:05 Lead Integration Round

All six previously open delegated agents were closed. Integrated changes from this round:

- passive monitor can now run an opt-in one-shot copied-log snapshot after first
  `players=1+`, writing only under `/tmp/obelisk-passive-evidence-snapshots`;
- scoped release-statement builder emits structured JSON rows for the seven post-v1 or
  excluded blocker outcomes, with `stable_claim_allowed=false` and
  `complete_sdk_claim_allowed=false`;
- approved runtime-principal lifecycle evidence checker rejects passive snapshot manifests,
  passive monitor logs, passive monitor tail text, and observer gate-only logs as named
  blockers;
- C++ lifecycle observer tests cover observer-gate-only dispatch mismatch: no reservation,
  no accepted lifecycle observation, and no public `PlayerPrincipalEventView`;
- SDK normalized summary exposes `route_gate_blocked` and keeps P0 blocked under route
  blockers even if accounting is inconsistent;
- research/handoff guardrails pin two-map passive wait, no chained restarts, passive
  snapshot non-evidence, closed agents, and the active SDK blocker.

Verification with a generated temporary statement:

```text
/tmp/obelisk-scoped-release-statement-20260604T060532Z.md
```

`scripts/check_public_sdk_v1_completion.py --release-statement <tmp> --validate-release-statement-scope --json`
reported `missing_statement_blocker=False` and `scoped_ready=True`, while still reporting
`status=blocked`, `current_route_blocker=approved_runtime_evidence_missing`,
`stable_claim_allowed=False`, SDK `0/12`, and P0 `0/4`.

This is not approved runtime evidence. The monitor snapshot output remains
`ready=false` and `approved_runtime_evidence=false` until real copied
`PlayerPrincipalLifecycleObserver event` lines are accepted by the evidence checkers.

## 2026-06-04 08:20 Ragnarok Status Recheck

After the operator reported that Ragnarok appeared off, the lead rechecked actual process,
query, tmux, and socket state instead of restarting or trusting a stale external status.

- `arkserver` / `Ragnarok`: `ShooterGameServer` PID `2603032`, started local `07:37:30`,
  game/query ports `7777`/`27015`, query `status=ok`, `players=0/70`,
  `-ActiveEvent=Summer`.
- `arkserver2` / `TheIsland`: `ShooterGameServer` PID `1877917`, started local
  `05:12:35`, game/query ports `7780`/`27016`, query `status=ok`, `players=0/70`,
  `-ActiveEvent=Summer`.
- passive monitor still attached as tmux socket/session
  `obelisk-passive-monitor` / `obelisk_passive_monitor`, with script PID `2724253`;
  latest ticks show both maps queryable and only the observer-enabled plus
  candidate-only diagnostic header lines.

No server start, stop, restart, marker edit, scanner/native-exec/ptrace/gcore, Discord,
GitHub, tag, release, or SDK claim action was performed for this recheck. The correct
posture remains keeping both servers up and letting the passive monitor capture a copied
snapshot only after `players=1+`; accepted runtime evidence still requires real
`PlayerPrincipalLifecycleObserver event` lines accepted by the evidence checkers.

## 2026-06-04 08:34 Supervised Offline Hardening Round

All six delegated agents were collected and closed. No server start, stop, restart,
marker/env change, scanner/native-exec/ptrace/gcore, Discord, GitHub, tag, release, or SDK
claim action was performed in this round.

Live/passive read-only status:

- `arkserver` / `Ragnarok`: PID `2603032`, query `27015`, direct GameDig `players=0/70`.
- `arkserver2` / `TheIsland`: PID `1877917`, query `27016`, direct GameDig `players=0/70`.
- passive monitor tmux/script PIDs remain `2724252` / `2724253`, newest audited tick
  `2026-06-04T06:27:35Z`.
- since the `08:20` handoff there were no `players=1+`, no
  `passive_snapshot_captured`, and no accepted `PlayerPrincipalLifecycleObserver event`,
  `session_start`, `session_start_rejected`, or `session_end` lines.

Integrated offline changes:

- `scripts/check_public_sdk_v1_completion.py` now preserves
  `approved_runtime_evidence_missing` in `remaining_route_blockers` when a helper reports
  the current blocker but an empty blocker list.
- `scripts/test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
  rejects snapshot-on-detect copied logs named like `arkserver-Ragnarok-Obelisk.log` as
  approved bundles even if they contain valid-looking lifecycle lines; approved evidence
  still requires the live-validation sibling-set path.
- `scripts/test_check_player_identity_public_contract_readiness.py` pins the state where
  all current contract-review inputs are present: the report is
  `contract_review_input_only`, while `abi.public_pod_contract`, `lifecycle.owner_cleanup`,
  and downstream separation remain promotion blockers.
- `tests/core/PluginManagerTests.cpp` extends the copied `DestroyUserData` retry
  regression so owner-token registration is rejected while retained/unloading for
  ProcessEvent, gameplay policy, chat, and timers.
- `scripts/compare_reflection_snapshots.py`,
  `scripts/test_compare_reflection_snapshots.py`, and
  `docs/research/player-identity-planning-sources/players-lifecycle-anchor-candidates-all-six-planning-gap.json`
  record the all-six lifecycle candidate comparison gap as durable planning-only material.
  Current durable source-bound lifecycle anchor evidence remains limited to
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`.

Validation observed by the lead:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_compare_reflection_snapshots
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest <focused SDK route-blocker/scoped statement tests>
cmake --build build --target plugin_manager_tests -j2
ctest --test-dir build -R '^PluginManagerTests$' --output-on-failure
python3 -m json.tool docs/research/player-identity-planning-sources/players-lifecycle-anchor-candidates-all-six-planning-gap.json
git diff --check
```

Results: approved-evidence 98 OK, compare snapshots 105 OK, docs guardrails 66 OK,
public-contract readiness/gap 99 OK, focused SDK tests 5 OK, PluginManager CTest passed,
JSON parsed, and `git diff --check` passed. The scoped SDK statement check still reports
`status=blocked`, `current_route_blocker=approved_runtime_evidence_missing`,
`remaining_route_blockers=[approved_runtime_evidence_missing]`, `scoped_ready=true`, SDK
`0/12`, P0 `0/4`, and `stable_claim_allowed=false`. The default SDK check exits blocked
with the same route blocker and statement blocker still present.

This round improves false-positive resistance and offline planning. It is not approved
runtime evidence and does not promote player identity, public ABI, public SDK readiness,
runtime readiness, release readiness, or v1 completion.

## 2026-06-04 08:56 Supervised Offline SDK Hardening Round

All six spawned agents were closed before handoff update. No server operation, marker/env
change, restart, `/servidor/ark` write, scanner/native-exec/ptrace/gcore/Frida/rr,
Discord, GitHub, tag, push, or SDK readiness claim occurred.

Live/passive posture:

- `arkserver` / `Ragnarok`: PID `2603032`, query `27015`, latest passive query
  `players=0/70`.
- `arkserver2` / `TheIsland`: PID `1877917`, query `27016`, latest passive query
  `players=0/70`.
- passive monitor remains `obelisk-passive-monitor` / `obelisk_passive_monitor` with
  `--interval 10`, `--linger-after-detect 900`, `--no-details`,
  `--snapshot-output-root /tmp/obelisk-passive-evidence-snapshots`, and both
  `arkserver:Ragnarok` plus `arkserver2:TheIsland`.
- no `players=1+`, `passive_snapshot_captured`, `PlayerPrincipalLifecycleObserver event`,
  `session_start`, `session_start_rejected`, or `session_end` lines were found.

Integrated offline changes:

- `scripts/build_player_identity_planning_source_manifests.py` validates the optional
  all-six planning-gap artifact during `--verify-existing-dir`. The artifact is accepted
  only as `planning_only`; promotional drift, accepted second-source/runtime evidence, or
  missing `approved_runtime_evidence_missing` blockers fail verification. Current checked
  artifact SHA256:
  `50d353a0c8b05d07ec639a50b97bc28f0c323aa1b11857cb0d1a91c99cefd235`.
- `scripts/check_player_identity_public_contract_readiness.py` and
  `scripts/check_player_identity_public_contract_gap_report.py` reject `public_api_*`,
  `api_readiness`, public API symbol-list, and public-API prose aliases from approved
  runtime, planning, helper, or source artifacts.
- `scripts/check_public_sdk_v1_completion.py` rejects passive snapshots, passive
  observations, scoped non-complete release statements, and contract-review-only artifacts
  or ready scopes as promotion evidence. It also has an optional test-only helper
  subprocess cache controlled by `OBELISK_PUBLIC_SDK_V1_COMPLETION_SUBPROCESS_CACHE_DIR`;
  default behavior is unchanged when the env var is unset.
- `scripts/check_player_identity_owner_token_sdk_consumer_contract.py` rejects owner-token
  registration-handle lifetime overclaims such as handles surviving server restarts,
  reloads, plugin unload, or `dlclose`.
- `scripts/test_agent_handoff_guardrails.py` and
  `scripts/test_research_doc_guardrails.py` pin the passive wait/no chained restart rule,
  real copied lifecycle event requirements, and SDK non-claim posture.

Validation observed by the lead:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_planning_source_manifests scripts.test_check_player_identity_owner_token_sdk_consumer_contract scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_player_identity_owner_token_sdk_consumer_contract
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion
cmake --build build --target plugin_manager_tests -j2
ctest --test-dir build -R '^PluginManagerTests$' --output-on-failure
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_player_identity_planning_source_manifests.py --verify-existing-dir docs/research/player-identity-planning-sources --json
env -u OBELISK_PUBLIC_SDK_V1_COMPLETION_SUBPROCESS_CACHE_DIR PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json
git diff --check
```

Results: planning-source/owner-token/docs guardrails 89 OK, public contract/gap plus
owner-token 106 OK, SDK completion 257 OK, PluginManager CTest passed, planning-source
verify accepted the optional all-six artifact as planning-only, and `git diff --check`
passed. The default SDK checker still exits blocked by design with
`current_route_blocker=approved_runtime_evidence_missing`,
`remaining_route_blockers=[approved_runtime_evidence_missing]`, SDK `0/12`, P0 `0/4`,
and `stable_claim_allowed=false`.

This round is guardrail/accounting hardening only. It does not promote player identity,
public player identity API, public ABI, runtime readiness, public SDK readiness, release
readiness, or v1 completion.

## 2026-06-04 09:16 Ragnarok Passive Player Diagnostic Snapshot

After the operator reported Ragnarok looked off, direct read-only checks showed it was
still running and queryable. No server start, stop, restart, marker/env change,
scanner/native-exec/ptrace/gcore/Frida/rr, LinuxGSM monitor/details fallback, Discord,
GitHub, tag, push, or SDK readiness claim occurred.

Live status:

- `arkserver` / `Ragnarok`: `ShooterGameServer` PID `2603032`, started local `07:37:30`,
  `-ActiveEvent=Summer`, UDP `7777`/`7778`, query `27015`, RCON `27020`,
  `/servidor/ark/obelisk/lib/libobelisk.so` mapped with no deleted libobelisk mapping.
- `arkserver2` / `TheIsland`: `ShooterGameServer` PID `1877917`, started local
  `05:12:35`, `-ActiveEvent=Summer`, UDP `7780`/`7781`, query `27016`, RCON `27021`,
  `/servidor/ark/obelisk/lib/libobelisk.so` mapped with no deleted libobelisk mapping.
- passive monitor `obelisk-passive-monitor` / `obelisk_passive_monitor` is active with
  script PID `2724253`.

The passive monitor detected a real player on `arkserver` / `Ragnarok` and captured:

```text
/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260604T070443Z-arkserver-2724253/
```

Snapshot manifest facts:

- `schema=obelisk.player-principal-passive-snapshot.v1`
- `captured_at_utc=2026-06-04T07:04:43Z`
- `all_logs_copied=true`
- `ready=false`
- `approved_runtime_evidence=false`
- `readiness_gate=none`
- copied Ragnarok log SHA256
  `887071a26a83014585459aa21249f7d0c8ff57247bca2fedec4773d5b6d370b4`
- copied TheIsland log SHA256
  `ab200169c046e073e6f53b05106d5d60f862fd52140877139c43f76213ec85a6`
- copied passive monitor log SHA256
  `ff8031228a724156bc8e32ece6c45240a57920b91c98b1cee1fb7e5e1d9b7b1d`

Analyzer result for Ragnarok:

- `accepted_count=0`
- `rejected_count=0`
- `diagnostic_candidate_count=4`
- targets: `ShooterGameMode.CheckJoinInProgress:1`,
  `ShooterGameMode.HandleNewPlayer:2`, `GameMode.K2_PostLogin:1`
- `diagnostic_candidate_read_status_counts={"implausible": 1}`
- rejection reason:
  `lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724`
- runtime posture still shows LD_PRELOAD loaded, ProcessEvent hook installed, scanner
  disabled, and plugins disabled.

Analyzer result for TheIsland in the same snapshot has `accepted_count=0`,
`rejected_count=0`, and `diagnostic_candidate_count=0`.

Interpretation: passive waiting successfully captured organic Ragnarok runtime signal.
The hook sees `HandleNewPlayer`, but the current reflection/copy path rejects the live
parameter chain as implausible because the expected first lifecycle property FName index
`28411` did not match the observed chain `28418,21314,22968,28516,17724`. This is useful
debug evidence, but it is not approved runtime lifecycle evidence and does not clear
`approved_runtime_evidence_missing`. Accepted evidence still requires real copied
`PlayerPrincipalLifecycleObserver event` lines for `session_start`,
`session_start_rejected`, and `session_end` plus status-proof fields inside the approved
sibling-set bundle.

Historical next step at that time was to keep both servers up in passive wait and work
offline on the `HandleNewPlayer` live-layout mismatch. For current offline scopes, do not
reuse that line as live authorization. Do not promote a search-by-FName matcher or relax
positional safety based on this snapshot alone; resolve the observed indices with static
fixtures or a second-source-safe explanation first, then request an exact scoped deploy or
restart only after the offline patch is ready.

## 2026-06-04 09:23 Property FName Drift Fix, Not Deployed

Read-only live audit after the Ragnarok player left showed both approved passive wait
servers still running:

- `arkserver` / `Ragnarok`: PID `2603032`, query `27015`, `0/70` players.
- `arkserver2` / `TheIsland`: PID `1877917`, query `27016`, `0/70` players.
- passive monitor `obelisk-passive-monitor` / `obelisk_passive_monitor`, script PID
  `2724253`, still active.

The current Ragnarok log added an `OnLogout` diagnostic at local `09:22:19`:

```text
PlayerPrincipalLifecycleDiagnostic ... target=ShooterGameMode.OnLogout ... reflection_status=rejected read_status=implausible reason=lifecycle_property_FName_mismatch_expected_28543_observed_28550 ...
```

There are still no accepted `PlayerPrincipalLifecycleObserver event`, `session_start`,
`session_start_rejected`, or `session_end` lines.

Offline FName root validation used the existing vanilla-gdb core under
`/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/`
and root slot `0x5956f30`. It resolved the expected `HandleNewPlayer` property indices as
the static fixture expects:

- `28411 -> NewPlayer`
- `21307 -> PlayerData`
- `22961 -> PlayerCharacter`
- `28509 -> bIsFromLogin`
- `17716 -> ReturnValue`

The observed Ragnarok indices resolve to unrelated names in that offline core:

- `28418 -> PlayerStarts`
- `21314 -> PreviousLatitudeNumber`
- `22968 -> OutTagIds`
- `28516 -> RadiusAroundEachIndivitualFoliageToCheck`
- `17724 -> ExplorerNoteIndex`

This supports a narrow interpretation: property `FName` comparison indices can drift
between the static/offline cores and a live loaded map/mod/event state, while the function
target, outer, flags, `NumParms`, `ParmsSize`, `ReturnValueOffset`, and positional
property shape remain the stronger gate.

Local code now implements a strict fallback in
`ue/PlayerPrincipalLifecycleReflection.*`: property `FName` drift is accepted only after
the exact function/outer/shape gate passes, including positional property class, offset,
size, element size, array dim, property flags, and bool metadata. Reordered property
chains and wrong-shape chains still reject. `LifecycleInvocation` records
`PropertyNameIndicesMatched=false` plus bounded `PropertyFNameDrifts`; the `ReadResult`
OK reason carries a safe `lifecycle_property_FName_drift...` token for diagnostics.

Guardrail work in the same round keeps the current passive material non-promotional:

- `scripts/analyze_runtime_observer_log.py` summarizes compact and rich
  `lifecycle_property_FName_mismatch` diagnostic chains without increasing accepted or
  rejected observer event counts.
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
  rejects player-presence plus diagnostic-only copied logs.
- `scripts/check_public_sdk_v1_completion.py` rejects passive/window/request/preflight/
  operator/live-sidecar artifacts and diagnostic mismatch summaries as approved runtime
  evidence.
- `scripts/compare_reflection_snapshots.py --observed-fname-chain` produced planning-only
  artifact
  `docs/research/player-identity-planning-sources/players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json`.

No server operation, restart, marker/env change, deploy, scanner/native-exec/ptrace/gcore,
Frida/rr, Discord, GitHub, tag, push, or SDK readiness claim occurred. The fallback is not
active on `arkserver` or `arkserver2` until a future exact scoped deploy/restart is
approved. Accepted evidence still requires copied `PlayerPrincipalLifecycleObserver
event` lines for `session_start`, `session_start_rejected`, and `session_end` plus
status-proof fields inside the approved sibling-set bundle.

## 2026-06-04 09:54 Passive Wait Verification

Read-only live verification after the operator asked why Ragnarok was off found that
Ragnarok was not off:

- `arkserver` / `Ragnarok`: `ShooterGameServer` PID `2603032`, `-ActiveEvent=Summer`,
  observer-debug posture OK, query `27015` OK, `0/70`.
- `arkserver2` / `TheIsland`: `ShooterGameServer` PID `1877917`, `-ActiveEvent=Summer`,
  observer-debug posture OK, query `27016` OK, `0/70`.
- Both processes have `LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so`,
  plugins disabled, lifecycle observer enabled, log limit `10`, dispatch limit `0`, and
  diagnostic candidates enabled.

The previous passive monitor had completed its linger, so the lead restarted only the
read-only passive monitor, not either ARK server. Current monitor state:

- tmux server/session: `obelisk-passive-monitor` / `obelisk_passive_monitor`
- script PID: `3198398`
- log: `/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log`
- snapshot root: `/tmp/obelisk-passive-evidence-snapshots`
- targets: `arkserver:Ragnarok`, `arkserver2:TheIsland`
- interval: `10s`
- post-detect linger: `900s`
- mode: `--no-details`

The monitor tail at `2026-06-04T07:53:53Z` showed both maps query OK and `0/70`. The
latest useful copied snapshot is still
`/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260604T070443Z-arkserver-2724253/`;
it remains `ready=false` and `approved_runtime_evidence=false`. Direct route gate remains
valid/planning-only at `approved_runtime_evidence_missing`, while the full SDK checker
exits blocked with `complete_sdk_ready=false`, `complete_sdk_progress_ratio=0/12`, and
`stable_claim_allowed=false`.

All active sub-agents from this latest round were closed. No server restart, marker/env
change, deploy, scanner/native-exec/ptrace/gcore, Frida/rr, Discord, GitHub, tag, push, or
SDK readiness claim occurred during this verification.

## 2026-06-04 10:32 Delegated Round and New Passive Snapshot

A supervised six-agent round completed, all six spawned agents were closed, and no active
sub-agent was left open. The round kept server operations read-only and advanced offline
guardrails:

- lifecycle reflection now bounds lifecycle diagnostic reasons and tests property-FName
  drift acceptance only after exact positional shape validation;
- approved-evidence tests reject observer-gate plus `player_presence_detected` plus FName
  diagnostics when no real lifecycle observer events exist;
- `compare_reflection_snapshots.py --observed-fname-chain` reports observed chains as
  `planning_only`, `not_second_source`, `readiness_effect=none`, with runtime/public SDK
  readiness false, and records the `OnLogout` `28543 -> 28550` mismatch;
- route/SDK scanners ignore schema/argv metadata while still rejecting true positive
  public/runtime/readiness claims;
- permissions/admin remains query-only planning and requires a reviewed
  `obelisk.player_identity.v1` promotion certificate before any downstream accounting;
- `InventoryCustomFilter` fixture guidance now states it is planning-only, candidate-only
  ArrayProperty metadata, not Inventory SDK or release-readiness scope.

During the round, the passive monitor detected another organic Ragnarok player; after the
player left, a read-only manual passive snapshot copied the current logs to:

```text
/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T083246Z-arkserver+arkserver2-3168261/
```

Snapshot manifest facts:

- `captured_at_utc=2026-06-04T08:32:46Z`
- `ready=false`
- `approved_runtime_evidence=false`
- `all_logs_copied=true`
- Ragnarok copied log SHA256
  `5ffadc29e1f2f80205d55a6c889d6e8901e584b417841a6c19296e3233ff6fc4`
- TheIsland copied log SHA256
  `ab200169c046e073e6f53b05106d5d60f862fd52140877139c43f76213ec85a6`
- passive monitor copied log SHA256
  `a591ce170d1e6274e64c69518fa8eb68258ae553ccba3600bfb2870aed93679b`

Analyzer result for Ragnarok:

- `accepted_count=0`
- `rejected_count=0`
- `diagnostic_candidate_count=11`
- diagnostic targets: `ShooterGameMode.HandleNewPlayer:4`,
  `ShooterGameMode.OnLogout:4`, `GameMode.K2_PostLogin:2`,
  `ShooterGameMode.CheckJoinInProgress:1`
- mismatch counts:
  `lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724:2`
  and `lifecycle_property_FName_mismatch_expected_28543_observed_28550:2`

Analyzer result for TheIsland:

- `accepted_count=0`
- `rejected_count=0`
- `diagnostic_candidate_count=0`

The approved-evidence checker rejects the snapshot manifest directly:
`approved_runtime_evidence_present=false`, `runtime_evidence_ready=false`, blockers
include `schema_mismatch` and `passive_snapshot_manifest_is_not_approved_runtime_evidence`.
Direct route remains `valid=true`, `accepted_for_planning=true`, `planning_only=true`,
`current_route_blocker=approved_runtime_evidence_missing`. Full SDK checker remains
blocked with `complete_sdk_ready=false`, `complete_sdk_progress_ratio=0/12`,
`stable_claim_allowed=false`.

No server restart, marker/env change, deploy, scanner/native-exec/ptrace/gcore, Frida/rr,
Discord, GitHub, tag, push, or SDK readiness claim occurred. The snapshot is useful
diagnostic material only; it does not promote player identity/principal,
permissions/admin, command response, commands/replies, runtime readiness, public SDK
readiness, or complete/stable v1 SDK status.

## 2026-06-04 11:32 Live/Passive State

Ragnarok was verified not off: `arkserver` / `Ragnarok` PID `2603032` and `arkserver2` /
`TheIsland` PID `1877917` both pass observer-debug posture with `-ActiveEvent=Summer`,
plugins disabled, lifecycle observer enabled, log limit `10`, dispatch limit `0`, and
GameDig query OK `0/70`. The previous passive monitor PID `3198398` completed its
linger; the active read-only passive monitor is
`obelisk-passive-monitor` / `obelisk_passive_monitor` with script PID `3261082`, polling
both `arkserver:Ragnarok` and `arkserver2:TheIsland` with `--no-details`,
`--linger-after-detect 900`, `--snapshot-output-root /tmp/obelisk-passive-evidence-snapshots`,
and `--snapshot-monitor-log /tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log`.

Latest passive snapshot:

```text
/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json
```

Snapshot manifest facts:

- `captured_at_utc=2026-06-04T08:51:19Z`
- `ready=false`
- `approved_runtime_evidence=false`

Analyzer result for Ragnarok:

- `accepted_count=0`
- `rejected_count=0`
- `diagnostic_candidate_count=17`
- target counts: `HandleNewPlayer=7`, `OnLogout=5`, `CheckJoinInProgress=2`,
  `K2_PostLogin=3`
- mismatch counts: `HandleNewPlayer=4`, `OnLogout=3`
- `HandleNewPlayer` mismatch detail: expected `28411`, observed
  `28418,21314,22968,28516,17724`
- `OnLogout` mismatch detail: expected `28543`, observed `28550`

Analyzer result for TheIsland:

- `accepted_count=0`
- `rejected_count=0`
- `diagnostic_candidate_count=0`

The passive snapshot remains `passive_snapshot_non_evidence`; the approved-evidence
checker rejects it. This passive snapshot is diagnostic-only, not approved runtime
evidence, and cannot clear
`approved_runtime_evidence_missing`. Route/SDK remain blocked at
`approved_runtime_evidence_missing`; SDK remains `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`.

The planning-source artifact
`docs/research/player-identity-planning-sources/players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json`
records these latest counts as `planning_only`, `not_second_source`, and
`readiness_effect=none`. The next offline evidence step is to compare or regenerate exact
sanitized lifecycle snapshots from a distinct non-protected offline artifact and explain
the property FName drift without relaxing positional property-chain validation.

## 2026-06-04 Worker 6 Offline FName-Drift Guardrail

The observed Ragnarok property FName chains remain diagnostic-only even if a copied chain
later matches committed fixture indices. `compare_reflection_snapshots.py
--observed-fname-chain` now emits explicit machine-readable blockers:
`layout_evidence_status=not_layout_evidence`,
`can_be_used_as_second_source_layout_evidence=false`,
`can_be_used_as_candidate_snapshot_root=false`, and
`second_source_status=not_applicable`. The matching planning-source JSON carries the same
contract.

Next exact offline evidence needed before any deploy request: a distinct sanitized
`obelisk.ufunction-chain.snapshot.v1` lifecycle snapshot root for
`ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`, generated from a
non-protected offline artifact with complete artifact identity
(`ark_binary_sha256`, `artifact_kind=offline_core`, `artifact_sha256`, `capture_id`, and
`evidence_pack_id`). The comparison must prove semantic property shape only: target
outer/name/class, `NumParms`, `ParmsSize`, `ReturnValueOffset`, property order/classes,
offsets, sizes, flags, bool metadata, and candidate-uobject membership. Do not use copied
runtime FName-chain lines, passive snapshot manifests, direct or symlink-resolved live
server paths, broad FName/GObjects scans, or unapproved `ReflectionScanner` output.

Suggested offline comparison once that sanitized root exists:

```bash
python3 scripts/compare_reflection_snapshots.py --base-root tests/fixtures/ufunction_snapshots --candidate-root <distinct-sanitized-lifecycle-root> --target ShooterGameMode.HandleNewPlayer --target ShooterGameMode.OnLogout --readiness-report --json
```

## 2026-06-04 11:07 Integration Result

All six delegated agents from the 11:07 integration round were closed. Local code now has
a regression proving diagnostic candidate budget exhaustion cannot starve accepted
lifecycle observation budget, and passive tooling reports `diagnostic_log_budget_reached`
and `diagnostic_only_non_evidence` while keeping `approved_runtime_evidence=false`.
Route/SDK and public-contract checkers now scan nested approved-runtime and contract
inputs for hidden public/runtime readiness claims. This improves fail-closed visibility
only; it does not deploy code, restart servers, clear `approved_runtime_evidence_missing`,
or change SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`.

## 2026-06-04 11:30 Six-Agent Integration

All six agents from the current round were closed before lead integration completed. The
round integrated only offline/local hardening:

- scoped release-statement validation now uses
  `docs/SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md` by default for
  `--validate-release-statement-scope`, while the full SDK gate still does not
  auto-discover it or count it toward completion;
- local lifecycle observer regressions model the observed Ragnarok `HandleNewPlayer` and
  `OnLogout` property FName drift and keep diagnostic-only targets non-events;
- passive monitor/snapshot tooling records monitor/session metadata and summarizes nested
  diagnostic max sequence/log-budget pressure while keeping passive snapshots non-evidence;
- public identity contract checks reject copied-log source-kind aliases that are not
  `runtime-observer-log`;
- inventory custom-filter array-boundary side-lane checks record reflected `TArray` shell
  boundaries, forged payload-boundary rejection, artifact identity, and non-counting
  side-lane accounting.

No live-server write, marker/env mutation, start/stop/restart, LinuxGSM `monitor`,
runtime capture, Discord/GitHub publication, SDK readiness wording, or v1 completion claim
occurred. Route/SDK remain blocked at `approved_runtime_evidence_missing`, SDK `0/12`, P0
`0/4`, and `stable_claim_allowed=false`.

## 2026-06-04 11:50 Six-Agent Integration

All six agents from the current round were closed before lead integration completed. The
round integrated only offline/local hardening:

- request/preflight tooling now records exact `current_turn_approval_scope` requirements
  and `deployment_intent=lifecycle_anchor_drift_fix_deploy_request_only`;
- approved-evidence checks reject copied logs contaminated with passive monitor metadata
  such as `tick utc=`, `query instance=`, `observer_tail`, or passive snapshot lines, even
  if lifecycle event-looking lines are present;
- wrapper/posture guardrails reject stale observer env/markers, missing or unsupported
  lifecycle binary SHA, wrong lifecycle log limit, and wrong dispatch limit;
- route tests prove accepted approved runtime evidence can advance only to
  `identity_public_contract_gate_missing`, with permissions/admin, command response,
  commands/replies, public SDK, runtime readiness, ABI/header, accounting, and v1
  completion still false;
- public identity ABI preflight rejects hidden readiness aliases for headers,
  capabilities, callbacks, lookup, and `ResourceHandle`;
- observed FName-chain artifacts remain `not_layout_evidence`, `not_second_source`, and
  invalid as candidate snapshot roots.

No live-server write, marker/env mutation, start/stop/restart, LinuxGSM `monitor`,
runtime capture, Discord/GitHub publication, SDK readiness wording, or v1 completion claim
occurred. Route/SDK remain blocked at `approved_runtime_evidence_missing`, SDK `0/12`, P0
`0/4`, and `stable_claim_allowed=false`.

## 2026-06-04 12:25 Passive-Wait Guardrail Checkpoint

All six agents from the prior round were closed before lead integration; no new sub-agent
work is opened by this note. Historical routing at this checkpoint was a passive wait on
both `arkserver` / `Ragnarok` and `arkserver2` / `TheIsland`; current active routing is
now `arkserver` / `Ragnarok` plus `arkserver3` / `Genesis2:27017`, with `arkserver2` /
`TheIsland` off. This checkpoint does not authorize new marker/env changes, deploys,
server starts, stops, restarts, runtime capture, LinuxGSM `monitor`, or chained restarts
while waiting for organic player activity.
Any future active server operation must get a fresh current-turn approval that names the
exact instance or instances, marker/env gates, process-control window, evidence paths,
rollback/posture expectation, privacy bounds, and no-public-readiness/no-publication
boundaries. Passive wait docs, monitor output, passive snapshots, and diagnostic summaries
cannot be reused as that approval.

Latest passive-wait guardrail from that historical window: keep only the then-active two-server pair up, never keep three
ARK servers running, and passive monitor handling must remain `process_control=none`.
Monitor ticks, copied passive snapshots,
`--latest` summaries, `--latest-diff` output, FName-drift diffs, and diagnostic lines are
diagnostic-only; they are not runtime evidence and must not trigger chained restarts or
server-side changes while waiting.

Durable statement for future agents: the `2026-06-04T11:30:21Z` TheIsland passive
detection at
`/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260604T113021Z-arkserver2-3261082`
is useful diagnostic material only, not accepted evidence; it is missing
`session_start`, `session_start_rejected`, and `session_end`, the remaining diagnostic
mismatch is `lifecycle_property_FName_mismatch`, and that historical TheIsland passive
route is no longer active routing. `arkserver2` / `TheIsland` was later recorded as off while
`arkserver` / `Ragnarok` and `arkserver3` / `Genesis2:27017` were the then-active passive pair.

Active diagnostic material is non-evidence unless a copied approved sibling-set bundle is
accepted by the evidence checkers. Passive monitor output, passive snapshot manifests,
`PlayerPrincipalLifecycleDiagnostic` lines, player-presence lines, FName-drift metadata,
and `passive_activity_triage` remain `ready=false`, `approved_runtime_evidence=false`,
and `passive_snapshot_non_evidence`; do not promote them into SDK, runtime, public ABI, or
route readiness. The `passive_activity_triage` label is classification only; non-claim
wording must not describe it as public/runtime readiness or imply that runtime evidence is
accepted.

Historical passive state to preserve:

- passive monitor script PID `3261082`, log
  `/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log`, snapshot root
  `/tmp/obelisk-passive-evidence-snapshots`;
- latest passive snapshot path
  `/tmp/obelisk-passive-evidence-snapshots/passive-detect-20260604T113021Z-arkserver2-3261082`
  from organic `arkserver2` / `TheIsland` player presence at
  `2026-06-04T11:30:21Z`, with `ready=false`, `approved_runtime_evidence=false`, and
  `passive_snapshot_non_evidence`;
- the latest passive snapshot is missing `session_start`, `session_start_rejected`, and
  `session_end`, so it is useful diagnostic material only and not accepted evidence;
- TheIsland's remaining diagnostic mismatch is `lifecycle_property_FName_mismatch`;
- the older Ragnarok passive snapshots remain historical diagnostic material only and do
  not change the current wait-only posture.

Accepted runtime evidence still requires the copied approved sibling-set bundle with real
`PlayerPrincipalLifecycleObserver event` lines for `session_start`,
`session_start_rejected`, and `session_end` plus status-proof fields. Until that bundle is
accepted by the approved evidence checkers, the route remains
`approved_runtime_evidence_missing`; SDK remains `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`.

## 2026-06-04 14:22 Lead Round And Manual Passive Snapshot

All six spawned agents from the 14:22 lead round were closed explicitly before handoff.
The round integrated only offline/local hardening: SDK completion now rejects
accepted-runtime precondition aliases and package-shape references as non-promotional,
approved-evidence checks reject passive monitor metadata such as `passive_monitor_session`
and `query_warning`, passive capture/summarization forces nested readiness and approval
fields to non-evidence, lifecycle reflection accepts only exact-shape FName drift for
`HandleNewPlayer`/`OnLogout`, TimerManager cleanup guardrails were tightened, and release
readiness now has a regression proving the scoped non-complete statement cannot pass the
complete SDK gate.

Manual passive snapshot:
`/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T121016Z-arkserver+arkserver2-lead/manifest.json`.
It was captured at `2026-06-04T12:10:19Z`, copied both logs, and is
`ready=false`, `approved_runtime_evidence=false`, and `passive_snapshot_non_evidence`.
It contains `diagnostic_candidates=26` and still lacks `session_start`,
`session_start_rejected`, and `session_end`. The approved-evidence checker rejects it as
`passive_snapshot_manifest_is_not_approved_runtime_evidence`.

Final read-only live recheck for this round: `arkserver` / `Ragnarok` remains up,
queryable `0/70`; `arkserver2` / `TheIsland` remains up, queryable `1/70`; both keep
`-ActiveEvent=Summer`; passive monitor PID `3261082` remains active with
`process_control=none`. No deploy, restart, marker/env change, runtime capture, scanner,
native exec, ptrace/gcore, GitHub, Discord, publication, or SDK readiness claim occurred.

## 2026-06-04 14:38 Lead Round And Ragnarok Recheck

All six spawned agents from this round were closed explicitly. The round integrated
offline/local hardening only: SDK completion now exposes a machine-readable
`fastest_next_sdk_unblock` object for `obelisk.player_identity.v1`; the lifecycle observer
has exact-shape `HandleNewPlayer`/`OnLogout` FName-drift tests; request/preflight checks
bind planned Obelisk build identity; player identity readiness/gap reports expose the
post-evidence blocker `identity_public_contract_gate_missing`; permissions/admin, command
response, and commands/replies remain locked behind identity/permissions; and the
command-principal bridge checker accepts next-blocker non-claim wording while still
rejecting real public/runtime claims.

The operator asked why Ragnarok was off. Read-only live recheck showed it was not off:
`arkserver` / `Ragnarok` PID `2603032`, query OK `0/70`, `-ActiveEvent=Summer`.
`arkserver2` / `TheIsland` also remained up: PID `1877917`, query OK `1/70`,
`-ActiveEvent=Summer`. Passive monitor PID `3261082` remains active with
`process_control=none`, `--no-details`, and 900s linger against both maps. No server
restart, deploy, marker/env change, runtime capture, LinuxGSM monitor/details, GitHub,
Discord, publication, or SDK readiness claim occurred.

Validation after integration: command-principal bridge tests pass (20 OK), bridge checker
exits `0` with `valid=true`, command-permission route gate exits `0` with `valid=true` and
no blockers, and the full SDK completion checker exits blocked as expected with
`current_route_blocker=approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`. Current live logs still contain diagnostic candidate lines
with `evidence_claim=none`, not accepted `PlayerPrincipalLifecycleObserver event` triplets.

## 2026-06-04 14:51 Supervised Offline Hardening Round

All six spawned agents from this round were closed explicitly. The integrated work stayed
offline/local and hardened the fastest route without changing live servers: approved
runtime evidence now requires the complete lifecycle event triplet plus post-correlation
status proof and stale
manifest/copied-log SHA failures stay closed; route-bound identity sources reject
`routeAcceptedAs*` public/runtime/P0 aliases while keeping planning-only route acceptance
non-counting; identity ABI/owner-token consumer checks reject public identity, lookup,
owner-token identity, runtime principal, and SDK-completion aliases; stable wrapper/posture
tests reject player-principal observer env/marker leakage; passive monitor metadata
explicitly reports `process_control=none`, `approved_runtime_evidence=false`, and
`ready=false`; inventory side-lanes reject public Inventory SDK, item mutation, return
override, identity/lookup, and complete-SDK contribution claims; and completion/scoped
statement rows report zero claim contribution.

Validation after integration: approved-evidence/window-manifest tests passed (192 OK);
identity ABI/consumer/route-bound tests passed (54 OK); inventory/docs guardrail tests
passed (110 OK); live-ops offline checks passed; completion focused tests passed (12 OK);
route gate exits `0` with `valid=true`; full SDK completion exits blocked as expected with
`current_route_blocker=approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`; global `git diff --check` passed.

Read-only live recheck: `arkserver` / `Ragnarok` PID `2603032`, query OK `0/70`,
`-ActiveEvent=Summer`; `arkserver2` / `TheIsland` PID `1877917`, query OK `1/70`,
`-ActiveEvent=Summer`; passive monitor PID `3261082` remains active with
`process_control=none`, `--no-details`, and 900s linger. A newer Ragnarok `14:45:19`
`OnLogout` diagnostic line remains `evidence_claim=none` and does not satisfy approved
runtime evidence. No server restart, deploy, marker/env change, runtime capture, LinuxGSM
monitor/details, GitHub, Discord, publication, or SDK readiness claim occurred.

## 2026-06-04 Historical TheIsland Observer Candidate (Old Format)

Historical copied run directory:

```text
/servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle/
```

The first generated request pack used a 10-minute window. The operator had asked to
lengthen player wait windows to about 15 minutes, and the copied clean log contained
events through local `19:25:05` (`17:25:05Z`) while preflight-pre was checked at
`2026-06-04T17:13:15Z`. The request/window tooling was therefore updated from a
600-second maximum approved window to 900 seconds, and the offline request sidecars were
corrected to this exact 15-minute window:

```text
approved_window_start_utc=2026-06-04T17:13:15Z
approved_window_end_utc=2026-06-04T17:28:15Z
operator approval recorded at=2026-06-04T17:12:54Z
```

The corrected request pack passes post-window replay:

```text
scripts/check_player_principal_lifecycle_window_request.py --json --post-window-replay ...
ready=true
post_window_replay=true
post_window_replay_expiry_tolerated=true
blockers=[]
```

The copied log is a real copy of the clean TheIsland observer log, not a filtered or
truncated log:

```text
Obelisk.log sha256=d90afcc464381b743b7b88b625b5200de49cb7f68a56c29d0b808de0a63e4168
window-request.json sha256=253e6876065bb9b06984b64b6719a9a46aba560ccd5da051c0ae21b32c33f0c9
operator-approval-receipt.json sha256=a6c038c86b4bf0d46c19762aedc8daea05f7f0883be2a49097e3cb719974a946
preflight-pre.json sha256=62e3bfca9d2c0940d5c3a8e622aa3559db08350912b34329d99019d7382889e2
```

Historical pre-correlation copied-log analysis passed quality checks, but this old-format
role-triplet output is no longer sufficient without status-proof fields:

```text
python3 scripts/analyze_runtime_observer_log.py --fail-on-quality-blockers \
  /servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle/Obelisk.log

accepted_count=7
diagnostic_candidate_count=0
accepted_lifecycle_event_roles=session_start,session_start_rejected,session_end
complete_lifecycle_event_triplet_candidate_present=true
quality_blockers=[]
```

The runtime log shows `PlayerPrincipalLifecycleObserver enabled` with `limit=10`,
`dispatch_limit=0`, `delivery_claim=none`, and `principal_claim=none`. It then records
legacy analyzer-accepted observer lines for `session_start`, `session_start_rejected`, and
`session_end` without logging player identifiers or principal generations. A current
accepted bundle must also carry the required `apply_status`/`correlation_status` values.

Historical blocker at capture time: the approved bundle could not be completed because
rollback/post-preflight was pending while a player was connected to TheIsland. That is no
longer active server routing: `arkserver2` / `TheIsland` was later recorded as off, and the then-active
pair was `arkserver` / `Ragnarok` plus `arkserver3` / `Genesis2`. Preserve the copied
TheIsland log and sibling files as historical candidate material, but do not restart
TheIsland or run it as a third ARK server while the active pair is up.

Two read-only delegated agents from this live round were explicitly closed. One validated
the bundle/checker sidecar requirements and timestamp pitfalls; the other identified the
fastest post-evidence SDK slice: a copied POD player-principal lifecycle callback surface
with opaque process-local handle/generation, owner-token register/unregister, and no
lookup, permissions/admin, commands, persistence, mutation, or return override. That ABI
slice remains blocked until the approved runtime bundle and public header gate allow it.

## 2026-06-04 Genesis2 Historical Routing Correction

Two prior Genesis2 audit agents were closed before this durable update. Then-observed
live state for routing:

- `arkserver` / `Ragnarok`: running PID `1848240`;
- `arkserver3` / `Genesis2`: running PID `1989133`;
- `arkserver2` / `TheIsland`: off.

Never keep three ARK servers running. The then-current passive monitor was read-only for
`arkserver:Ragnarok` and `arkserver3:Genesis2:27017`, writing:

```text
/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log
```

Genesis2 local and public query now work. A read-only GameDig check after the operator
opened ports returned map `Gen2`, `queryPort=27017`, `connect=79.116.87.223:7783`,
`numplayers=0`, `maxplayers=70`, and ping about `13ms`. This resolves the earlier
non-SDK live-ops reachability blocker.

This correction supersedes active TheIsland passive-wait routing only. It does not erase
the historical TheIsland clean observer evidence or older passive snapshots, and it does
not convert them into approved evidence. The route remains
`approved_runtime_evidence_missing`; SDK remains `0/12`, P0 `0/4`, and
`stable_claim_allowed=false`.

## Durable Guardrail

No current-turn exact live-op or Discord scope exists in this offline memory slice.
Historical TheIsland, Ragnarok, and Genesis2 material is timestamped context only and
does not authorize live server work, public SDK readiness, stable v1 wording, Plugin Hub
publication, or approved in-game evidence.

Current-head offline fixes, continuous-development cadence, closed sub-agent or
all-six-agents-closed notes, six-agent closure notes, package-shape/install success,
package installs,
exact-version `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`
package-shape checks, `source_overclaim_total_flag_count=0`, passing local tests, local
validation results, the latest validation pass, `.codex` cleanup, scoped release
statements, request/preflight artifacts, closure requests, evidence-closure reports,
public reachability, passive monitor ticks, passive monitor output, organic player
presence, passive triplets, status reports, diagnostic candidate lines,
`fastest_next_sdk_unblock` objects, generated repo temp dirs, passive snapshots, Mission
copied-bool fixture-boundary reports, internal Mission copied-bool
summaries, Inventory copied-signal stability reports, Transfer `bAccept` readiness
reports, Transfer ScriptStruct readiness, Buff fixture manifest/source binding, Dino
scalar readiness, route post-evidence P0 lock simulation, and
Mission/Transfer/Dino/Tribe umbrella accounting are review/planning artifacts only. These
side-lane artifacts are candidate-only/non-authorizing and cannot be read as SDK
completion, runtime readiness, live ops approval, P0 progress, approved runtime evidence,
approved in-game evidence, public SDK readiness, stable readiness, SDK/P0/runtime
progress, or public/stable progress. They do not authorize live ops, server/log reads,
deploy/restart/marker/env changes, server-operation approval, approved runtime evidence,
runtime readiness, public SDK readiness, or complete SDK progress.

Approved evidence intake, approved manifests, copied evidence bundles, route reports, and
status reports are consume-only and non-authorizing. A checker-accepted approved runtime
bundle may answer only the `approved_runtime_evidence_missing` blocker; it does not
authorize server operations, future evidence windows, SDK/P0 progress, public header,
API, ABI work, runtime readiness, public SDK readiness, publication, or complete/stable SDK
claims. Words such as approved, accepted, ready, or complete must stay scoped to evidence
intake and cannot be reused as public-readiness or SDK-progress language.

Player notice artifacts have the same non-authorizing boundary. The
`player_notice_action` result, notice dry-run output, rendered notice text, and
sent-notice attestation prove only that the current-turn approved communication step was
prepared or sent. They are not accepted runtime evidence, live-ops approval, SDK progress,
P0 progress, public readiness, public SDK readiness, runtime readiness, publication, or
public-ready status, and they cannot replace the checker-accepted copied lifecycle
evidence bundle.

Do not store Discord webhook URLs, webhook tokens, secret environment assignments, or raw
secret-bearing dry-run output in Git, research docs, receipts, or sidecars. Preserve only
the non-secret notice path/channel label, dry-run status, send action, send timestamp,
reviewer/operator scope, and non-secret command metadata.

Mission copied-bool fixture-boundary checks, policy-slice reports, attestations, and
internal observer reports are offline evidence-only and planning-only. They do not grant a
public Mission SDK, runtime readiness, v1 completion, transfer authority,
reward/mutation authority, server authorization, operator approval, or live-observation
approval.

Sub-agent closure, repeated local hardening rounds, install/package shape success,
exact-version `COMPONENTS SDK` package-shape validation, zero
`source_overclaim_total_flag_count`, the latest validation pass, `.codex` cleanup, and
local validation results are process/accounting hygiene only; they do not move SDK, P0,
or v1 counters and cannot substitute for accepted runtime evidence or current-turn
operator approval.
Generated repo temp dirs from SDK consumer or promotion test runs, including
`tests/core/PlayerIdentityPromotion*` and `tests/sdk_consumer/player_identity_promotion*`,
are cleanup/test artifacts only; they are not handoff evidence, runtime evidence, SDK
progress, public readiness, or runtime readiness.

Rejected shortcut: a prior active passive-wait or two-server routing posture is not
standing authorization in later supervised offline rounds. Public reachability, active
monitor paths, passive triplets, historical copied sidecars, and status-helper
`current_turn_scope_required=true` fields must not be used to read live logs, inspect
servers, touch `/servidor/ark`, or claim runtime/public SDK readiness.

Only a fresh current-turn operator approval for the exact active operation can authorize a
deploy or runtime window. Only accepted copied `PlayerPrincipalLifecycleObserver event`
lines for `session_start`, `session_start_rejected`, and `session_end` with required
`apply_status`/`correlation_status` values in the approved sibling-set bundle can clear
`approved_runtime_evidence_missing`. Until then,
`complete_sdk_ready=false`, `complete_sdk_progress_ratio=0/12`, and
`stable_claim_allowed=false`.

Compaction invariant for future agents: no complete approved in-game evidence exists yet;
beta testers Discord notices and `player_notice_action` attestations are communication
artifacts, not evidence; passive diagnostics are diagnostic-only/non-evidence; no standby
sub-agent remains from these rounds; and this note grants no current-turn server
authorization.

For scoped player-backed evidence windows, the beta testers Discord notice is an
executable required action, not a passive note. If the current-turn approval names the
beta testers Discord path or any other player notice path, the approved dry-run-checked
notice must be sent before marker/env activation, restart, runtime capture, or passive
player-backed waiting begins. A window whose notice path is only documented, drafted,
included in request/receipt text, or documented but not sent is incomplete; request the
missing notice/send scope instead of silently waiting for players, and treat any resulting
intake or bundle as non-authorizing and non-evidence.
If a `player_notice_action` value appears in a request, receipt, report, or status output,
it is an execution/attestation field only; it is not runtime evidence, live-ops approval,
SDK progress, public readiness, or public SDK readiness.

## 2026-06-04 20:30 Second Supervised Integration

All six agents from the second supervised round were collected and explicitly closed; no
sub-agent remains open. The round stayed offline/read-only for servers.

Integrated facts:

- Genesis2 public reachability is now confirmed after the operator opened ports: public
  GameDig query to `79.116.87.223:27017` returns map `Gen2`,
  `connect=79.116.87.223:7783`, `queryPort=27017`, and `0/70` players.
- The then-active passive pair was `arkserver` / `Ragnarok` plus `arkserver3` /
  `Genesis2`; `arkserver2` / `TheIsland` was off and three ARK servers must not be
  kept running.
- `/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log` contains Genesis2
  passive observer events for `session_start` and `session_start_rejected` at local
  `20:14`, but no Genesis2 `session_end` yet. These passive lines are non-evidence.
- `scripts/prepare_player_principal_lifecycle_evidence_closure_request.py --format json`
  against the historical TheIsland candidate reports the exact missing artifacts:
  `window-manifest.env`, `preflight-post.json`, and
  `approved-bundle/approved-runtime-principal-lifecycle-evidence.json`. The report keeps
  `workspace_writes_authorized=false`, `server_operations_authorized=false`, and all
  public/runtime/SDK readiness fields false.
- The player-principal header gate proposal now freezes ordered proposal-only public
  constants for event kinds, scope flags, state flags, invalidation reasons, and contract
  flags. `include/obelisk/ObeliskApi.h` still has no player-principal symbols.
- Runtime ABI audit says the next implementation slice after approved evidence is an
  internal process-local principal registry with opaque handle/generation, linked
  invalidation semantics, real event sequence, and server-process epoch before any public
  callback ABI. Current observer material deliberately redacts UE object fields and cannot
  safely expose identity.
- Explicit `--release-statement docs/SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md`
  satisfies all 7 scoped non-complete release-statement outcomes, but contributes `0`
  progress and leaves SDK `0/12`, P0 `0/4`, route
  `approved_runtime_evidence_missing`, and `stable_claim_allowed=false`.

Validation:

```text
python3 -m unittest -q scripts.test_prepare_player_principal_lifecycle_evidence_closure_request scripts.test_check_player_identity_public_header_gate scripts.test_check_player_identity_public_contract_decision_record scripts.test_check_player_identity_public_contract_readiness
# Ran 106 tests OK

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_explicit_durable_scoped_statement_satisfies_bookkeeping_without_progress scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_validate_release_statement_scope_uses_durable_default_without_completion_progress scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_plain_gate_does_not_auto_discover_durable_scoped_statement
# Ran 3 tests OK
```

The full `scripts.test_check_public_sdk_v1_completion` unittest module was attempted but
the aggregate process stalled without output after more than a minute and was killed; the
targeted release-statement tests and checker CLI were run instead. No deploy, restart,
marker/env change, `/servidor/ark` write, Discord/GitHub publication, public SDK readiness
claim, or v1 completion claim occurred.

## 2026-06-04 20:45 Third Supervised Integration

All six agents from the third supervised round were collected and explicitly closed; no
sub-agent remains open. Server work stayed read-only.

Integrated facts:

- `core/PlayerPrincipalRegistry.h` and `.cpp` now provide an internal process-local
  opaque principal token primitive with nonzero handle/generation, invalidation reason
  flags, stale-generation rejection, no live handle reuse, and overflow fail-closed
  behavior. This is not public ABI and is not wired to `ProcessEvent` yet.
- Read-only integration audit places the future observer hook point after successful
  lifecycle observation construction in `ProcessEventHook.cpp`, before log/future dispatch.
  `session_start_rejected` must remain no-op; `session_end` can only link if a future
  registry keeps a private start anchor and resolves `OnLogout.Exiting` internally.
- Passive snapshot summarization now emits
  `player_principal_triplet_candidates_by_target`, including `roles_seen`,
  `missing_roles`, `complete_triplet_candidate`, and `last_event_times`, while forcing
  `approved_runtime_evidence=false`, `ready=false`, and `route_ready=false`.
- The closure helper can emit safe Markdown request output outside `/servidor/ark`; its
  commands are marked `NOT EXECUTED` and it still grants no server/workspace/readiness
  authorization.
- `fastest_next_sdk_unblock.actionable_paths` named two non-authorizing paths:
  historical TheIsland candidate sidecar closure, and then-active Genesis2 passive wait for
  missing roles. `scripts/report_obelisk_sdk_status.py` summarizes these gate results
  without changing readiness.
- Read-only pulse after a 180-second wait showed two ARK processes only, public GameDig
  OK for Ragnarok and Genesis2, `0/70` players on both, Genesis2 still missing
  `session_end`, and swap effectively exhausted.

Validation:

```text
python3 -m unittest -q scripts.test_report_obelisk_sdk_status scripts.test_prepare_player_principal_lifecycle_evidence_closure_request scripts.test_summarize_player_principal_passive_snapshots scripts.test_capture_player_principal_passive_snapshot
# Ran 46 tests OK

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_lists_non_authorizing_runtime_paths scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_human_output_names_actionable_v1_blocker_details scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_is_prioritization_only_with_p0_zero_of_four
# Ran 3 tests OK

cmake --build build --target player_principal_registry_tests -j$(nproc)
ctest --test-dir build --output-on-failure -R '^PlayerPrincipalRegistryTests$'
# passed

cmake --build build --target obelisk -j$(nproc)
# passed
```

Final checker summaries remained blocked as intended:

```text
check_public_sdk_v1_completion.py --json --release-statement docs/SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md
# status=blocked route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false action_paths=2 release_missing=0

report_obelisk_sdk_status.py --evidence-dir /servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle --json
# route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false closure=non_ready_missing_required_artifacts action_paths=2
```

No deploy, restart, marker/env change, `/servidor/ark` write, Discord/GitHub publication,
public SDK readiness claim, or v1 completion claim occurred.

## 2026-06-04 21:00 Fourth Supervised Integration

All six agents from the next supervised round were collected and explicitly closed. Server
work remained read-only/passive.

Integrated facts:

- `core/PlayerPrincipalRegistry.cpp` and `core/PlayerPrincipalEventDispatcher.cpp` no
  longer enable test hooks from `!obelisk_EXPORTS`; CMake now grants the hook macros only
  to the relevant test targets. `nm -C build/libobelisk.so` showed no exported
  `Set*ForTesting` symbols for those classes.
- `hooks/ProcessEventPlayerPrincipalLifecycleApplicator.*` is an internal, no-throw
  lifecycle-to-registry bridge. It accepts only copied lifecycle observations that
  `TryBuildPlayerPrincipalEventView` validates, allocates a process-local principal for
  accepted `session_start`, keeps `session_start_rejected` no-op, and keeps
  `session_end` fail-closed unless a private correlated principal token is supplied. This
  is not hook-wired, not public ABI, and not runtime evidence.
- The ABI audit kept the public player-principal plan append-only after
  `OBELISK_API_CAPABILITY_TIMERS` / `UnregisterTimerWithOwnerToken`, but no public symbols
  were added. Proposed header gate `ready=true` remains proposal-review-only; promotion,
  runtime, public SDK, permissions, commands, lookup, persistence, mutation, return
  override, and ResourceHandle remain false/forbidden.
- `scripts/report_obelisk_sdk_status.py` now preserves full `fastest_next_sdk_unblock`
  action paths, `sdk_counts`, `p0_counts`, public-header readiness, and explicit
  fail-closed authorization flags.
- `scripts/prepare_player_principal_lifecycle_evidence_closure_request.py` now classifies
  historical TheIsland sidecar-closure vs active Genesis2 incomplete-triplet cases,
  detects missing lifecycle roles, records target query port, and emits `NOT EXECUTED`
  closure commands without authorizing `/servidor/ark` writes or server operations.
- Read-only live pulse at local `20:56` saw exactly two ARK servers:
  `arkserver`/Ragnarok and `arkserver3`/Genesis2. Public query was OK for both and both
  had `0/70` players. Genesis2 still lacked `session_end`; Ragnarok had a complete
  passive triplet, still non-evidence. Swap remained nearly exhausted.

Validation:

```text
python3 -m unittest -q scripts.test_report_obelisk_sdk_status scripts.test_prepare_player_principal_lifecycle_evidence_closure_request scripts.test_check_player_identity_public_header_gate scripts.test_player_identity_public_contract_decisions scripts.test_check_player_identity_public_contract_decision_record scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails
# Ran 130 tests OK

ctest --test-dir build --output-on-failure -R 'PlayerPrincipalLifecycleApplicatorTests|PlayerPrincipalRegistryTests|PlayerPrincipalEventDispatcherTests|ProcessEventPlayerPrincipalLifecycleObserverTests'
# 4/4 tests passed

cmake --build build --target obelisk -j$(nproc)
# passed

python3 scripts/report_obelisk_sdk_status.py --evidence-dir /servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle --json
# status=blocked route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false action_paths=2
```

No deploy, restart, marker/env change, `/servidor/ark` write, Discord/GitHub publication,
public SDK readiness claim, or v1 completion claim occurred.

## 2026-06-04 21:15 Fifth Supervised Integration

All six agents from the latest supervised round were collected and explicitly closed.
Server work remained read-only/passive.

Integrated facts:

- `hooks/ProcessEventHook.cpp` now wires
  `ProcessEventPlayerPrincipalLifecycleApplicator::ApplyLifecycleObservationToRegistry`
  into the post-original player-principal lifecycle observer path after a copied
  lifecycle observation is built and before logging-budget returns. This keeps internal
  process-local registry state from depending on `gate.LogLimit`.
- `IsPlayerPrincipalLifecycleObserverActive()` now follows the observer gate instead of
  observation-budget counters, so `nameIndex` routing stays active while the approved
  observer gate is enabled. No public ABI or plugin-facing callback was added.
- The hook does not log registry handles, generations, live counts, UE pointers, raw
  params, or identity fields. Existing observer logs keep `principal_id_logged=false`,
  `principal_generation_logged=false`, and `delivery_claim=none`.
- `session_start` observations can allocate process-local internal principal tokens.
  `session_start_rejected` remains no-op. `session_end` remains fail-closed as
  `SessionEndUnresolvedNoop` until a private correlated principal token exists; no
  "last principal" or global heuristic is used.
- `scripts/test_player_principal_runtime_guardrails.py` now requires explicit test-hook
  macros for player-principal internals, requires hook-side applicator use before the log
  gate, and rejects reintroducing logging-budget dependence in
  `IsPlayerPrincipalLifecycleObserverActive()`.
- `scripts/check_public_sdk_v1_completion.py` now exposes
  `active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle` as a third
  non-authorizing action path with target `arkserver`/`Ragnarok`, zero claim contribution,
  `counts_as_approved_runtime_evidence=false`, and `passive_snapshot_evidence_allowed=false`.
- `scripts/report_obelisk_sdk_status.py` human output lists action paths with target,
  missing roles, evidence status, authorization, and false authorization flags.
- Read-only live pulse at local `21:09` saw exactly two ARK servers:
  `arkserver`/Ragnarok and `arkserver3`/Genesis2. Local and public GameDig were OK for
  both, both showed `0/70` players, and TheIsland was off. Ragnarok still had a complete
  passive triplet, non-evidence; Genesis2 still lacked `session_end`. Swap remained nearly
  exhausted.

Validation:

```text
python3 -m unittest -q scripts.test_check_public_sdk_v1_completion scripts.test_report_obelisk_sdk_status scripts.test_player_principal_runtime_guardrails
# Ran 289 tests OK

python3 -m unittest -q scripts.test_player_principal_runtime_guardrails scripts.test_report_obelisk_sdk_status scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_ragnarok_passive_triplet_path_is_non_evidence_without_progress scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_lists_non_authorizing_runtime_paths scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_is_prioritization_only_with_p0_zero_of_four scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_human_output_names_actionable_v1_blocker_details
# Ran 12 tests OK

ctest --test-dir build --output-on-failure -R 'PlayerPrincipalLifecycleApplicatorTests|PlayerPrincipalRegistryTests|PlayerPrincipalEventDispatcherTests|ProcessEventPlayerPrincipalLifecycleObserverTests'
# 4/4 tests passed

cmake --build build --target obelisk -j$(nproc)
# passed

python3 scripts/report_obelisk_sdk_status.py --evidence-dir /servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle --json
# status=blocked route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false action_paths=3
```

No deploy, restart, marker/env change, `/servidor/ark` write, RCON, Discord/GitHub
publication, public SDK readiness claim, or v1 completion claim occurred.

## 2026-06-04 21:25 Sixth Supervised Integration

All six agents from the latest supervised round were collected and explicitly closed.
Server work remained read-only/passive.

Integrated facts:

- `ProcessEventHook.cpp` now maintains a player-principal lifecycle runtime-event counter
  separate from `s_PlayerPrincipalLifecycleObservations`. This counter is process-local,
  monotonic until wrap, and is not bounded by `gate.LogLimit`.
- The hook now creates a nonzero process-local `ServerProcessEpoch` from steady-clock
  ticks mixed with PID. The value is restart-local and not identity, persistence,
  ordering across processes, or approved evidence.
- `ProcessEventPlayerPrincipalLifecycleApplicator` accepts an optional
  `ProcessLocalEventContext` containing `EventSequence` and `ServerProcessEpoch`. It
  copies those values into the validated internal `PlayerPrincipalEventView` and mirrors
  them in `ApplyResult` for tests. Existing callers without context still receive zero
  context, preserving default behavior.
- The hook passes `ProcessLocalEventContext` to `ApplyLifecycleObservationToRegistry`
  only after `TryBuildCopiedLifecycleObservationAfterOriginal` succeeds. Unsupported or
  malformed observations do not retain supplied context in applicator tests.
- The lifecycle observer log's `sequence={}` now uses the runtime-event sequence instead
  of the log-budget observation number. `observationNumber` still gates whether the log is
  emitted; it no longer defines runtime ordering for accepted copied observations.
- Guardrails now reject using the logging counter or `gate.LogLimit` as the lifecycle
  runtime event sequence, keep player-principal test hooks behind explicit macros, and
  reject public `ObeliskPlayerPrincipal*` hook-path tokens.
- `check_player_identity_public_header_gate.py` now keeps public promotion/readiness
  blocked unless the contract-decision source preserves nonzero `event_sequence` and
  `server_process_epoch` semantics. Default proposal review still passes as proposal-only
  with public header/API/ABI/SDK false.
- Status reporting now classifies three non-authorizing paths distinctly:
  historical TheIsland sidecar closure, active Genesis2 missing `session_end`, and active
  Ragnarok role-complete passive triplet requiring an approved bundle.
- Read-only live pulse at local `21:21` saw exactly two ARK servers:
  `arkserver`/Ragnarok and `arkserver3`/Genesis2. Local and public GameDig were OK for
  both, both showed `0/70`, TheIsland was off, Ragnarok's triplet remained passive
  non-evidence, Genesis2 still lacked `session_end`, and swap remained nearly exhausted.

Validation:

```text
python3 -m unittest -q scripts.test_player_principal_runtime_guardrails scripts.test_report_obelisk_sdk_status scripts.test_check_player_identity_public_header_gate
# Ran 32 tests OK

python3 scripts/check_player_identity_public_header_gate.py --json
# ready=true promotion_ready=false public_header_allowed=false public_abi_ready=false public_sdk_ready=false

python3 scripts/check_player_identity_public_header_gate.py --json --promote
# fails closed with promotion_event_sequence_nonzero_contract_missing and promotion_server_process_epoch_nonzero_contract_missing

cmake --build build --target player_principal_lifecycle_applicator_tests player_principal_event_dispatcher_tests process_event_player_principal_lifecycle_observer_tests player_principal_registry_tests -j$(nproc)
# passed

ctest --test-dir build --output-on-failure -R 'PlayerPrincipalLifecycleApplicatorTests|PlayerPrincipalRegistryTests|PlayerPrincipalEventDispatcherTests|ProcessEventPlayerPrincipalLifecycleObserverTests'
# 4/4 tests passed

cmake --build build --target obelisk -j$(nproc)
# passed

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_ragnarok_passive_triplet_path_is_non_evidence_without_progress scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_lists_non_authorizing_runtime_paths scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_fastest_next_sdk_unblock_is_prioritization_only_with_p0_zero_of_four scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_human_output_names_actionable_v1_blocker_details
# Ran 4 tests OK

python3 scripts/report_obelisk_sdk_status.py --evidence-dir /servidor/ark/workspace-offline/live-validation-logs/20260604T171315Z-player-principal-lifecycle --json
# status=blocked route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false action_paths=3
```

No deploy, restart, marker/env change, `/servidor/ark` write, RCON, Discord/GitHub
publication, public SDK readiness claim, or v1 completion claim occurred.

## 2026-06-04 21:40 Seventh Supervised Integration

All six delegated agents from this round were collected and explicitly closed. Delegated
scopes covered contract review, runtime guardrails, dispatcher audit, status reporting,
read-only live pulse, and applicator/registry edge-case tests.

Integrated facts:

- `docs/player_identity_public_contract_decisions.json` now preserves explicit promotion
  semantics that `event_sequence` and `server_process_epoch` are nonzero for every
  delivered player-principal event and that value `0` is invalid for public-header
  promotion.
- `check_player_identity_public_header_gate.py` now machine-checks both the nonzero text
  and the zero-invalid promotion text. In `--promote`, the repo proposal now fails only
  with `promote_blocked_until_runtime_bundle_and_header_promotion`; it no longer fails
  because those sequence/epoch semantics are absent.
- `PlayerPrincipalEventDispatcher` rejects copied events whose `EventSequence` or
  `ServerProcessEpoch` is zero before dispatching callbacks. This is still internal-only
  and does not add public `ObeliskPlayerPrincipal*` ABI symbols, public registration
  wrappers, lookup, permissions, commands, runtime readiness, or SDK readiness.
- `ProcessEventHook` now calls
  `DispatchLifecycleApplyResultToInternalSubscribers` immediately after
  `ApplyLifecycleObservationToRegistry` and before the logging-budget return. The helper
  dispatches only safe validated statuses with nonzero sequence/epoch:
  `SessionStartCreated`, `SessionStartRejectedNoop`, and correlated
  `SessionEndInvalidated`. It rejects unresolved, duplicate, stale, unsupported,
  allocation-failed, registry-failed, malformed, and zero-context cases.
- Runtime guardrails now cover the hook-side `ProcessLocalEventContext` creation point,
  dedicated runtime sequence counter, nonzero process-local epoch source, context passed
  into `ApplyLifecycleObservationToRegistry`, dispatch bridge ordering before log budget,
  applicator context copy before registry actions, and no public player-principal tokens
  in the internal hook path.
- Applicator/registry tests now cover correlated, duplicate, and stale logout context
  preservation plus unsupported/malformed observations with zero context staying
  fail-closed.
- `report_obelisk_sdk_status.py` now exposes
  `next_required_artifact=approved_runtime_principal_lifecycle_evidence_bundle`,
  `current_turn_scope_required=true`, and false authorization flags for live ops,
  runtime capture, live-log reads, server operations, and workspace writes. Ragnarok
  complete passive triplets and historical TheIsland closure remain explicit
  non-evidence/non-authorizing paths.
- Read-only live pulse at local `21:31` found exactly two ARK servers: Ragnarok
  `arkserver` PID `1848240` and Genesis2 `arkserver3` PID `1989133`. Local/public GameDig
  were OK with both at `0/70`; TheIsland remained off; the two-server cap was preserved.

Validation:

```text
cmake --build build --target obelisk player_principal_lifecycle_applicator_tests player_principal_event_dispatcher_tests process_event_player_principal_lifecycle_observer_tests player_principal_registry_tests -j$(nproc)
# passed; known external fmt/spdlog warnings only

ctest --test-dir build --output-on-failure -R 'PlayerPrincipalLifecycleApplicatorTests|PlayerPrincipalRegistryTests|PlayerPrincipalEventDispatcherTests|ProcessEventPlayerPrincipalLifecycleObserverTests'
# 4/4 tests passed

python3 -m unittest -q scripts.test_player_principal_runtime_guardrails scripts.test_report_obelisk_sdk_status scripts.test_check_player_identity_public_header_gate
# Ran 39 tests OK

python3 -m unittest -q scripts.test_plugin_manager_guardrails scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails
# Ran 98 tests OK

python3 scripts/check_player_identity_public_header_gate.py --promote --json
# fails closed only with promote_blocked_until_runtime_bundle_and_header_promotion

python3 scripts/report_obelisk_sdk_status.py --json
# status=blocked route=approved_runtime_evidence_missing sdk=0/12 p0=0/4 stable=false

git diff --check -- .
# passed
```

Next safe implementation step: private logout correlation. Keep `session_end` unresolved
without a private correlated principal; do not fake correlation with last-principal
heuristics. Public ABI/header/plugin registration remains blocked until approved runtime
evidence, contract review, owner cleanup, ABI layout, SDK consumer, and downstream P0
gates are satisfied.

No deploy, restart, marker/env change, `/servidor/ark` write, RCON, Discord/GitHub
publication, public SDK readiness claim, or v1 completion claim occurred.

## 2026-06-04 22:20 Private Correlation Offline Integration

Integrated an internal-only process-local correlation path for player-principal lifecycle
events. Reflection now assigns an Obelisk-owned `ProcessLocalSubjectToken` from redacted
object parameters while leaving `Range.Data` null and `ExposesRange=false`; copied
observations preserve that token only for `NewPlayer` and `Exiting`, not for unused
`PlayerData` or `PlayerCharacter` redactions.

`ProcessEventPlayerPrincipalLifecycleCorrelation.*` binds a subject token only after an
accepted `SessionStartCreated`, resolves `OnLogout.Exiting` to the matching
`PlayerPrincipalToken`, clears after session end, and supersedes an old live principal if
the same process-local subject appears in a new accepted start. It is not ABI-public and
does not expose lookup, identity values, UE pointers, raw params, FName/GObjects indices,
or public registration callbacks.

The hook now resolves `logoutCorrelationPrincipal` before
`ApplyLifecycleObservationToRegistry`, binds accepted starts after apply, clears session
ends after apply, and still dispatches internal events only after safe apply results with
nonzero sequence/epoch. Runtime guardrails explicitly reject fake/latest/previous/cached
principal-token correlation and require non-null hook correlation to flow through an
explicit private logout/session_end helper path.

Validation:

```text
cmake --build build --target obelisk player_principal_lifecycle_applicator_tests process_event_player_principal_lifecycle_observer_tests -j$(nproc)
# passed

ctest --test-dir build -R 'PlayerPrincipal(LifecycleApplicator|Registry)Tests|ProcessEventPlayerPrincipalLifecycleObserverTests|PlayerPrincipalEventDispatcherTests' --output-on-failure
# 4/4 tests passed

python3 -m unittest -q scripts.test_player_principal_runtime_guardrails scripts.test_report_obelisk_sdk_status scripts.test_check_player_identity_public_header_gate scripts.test_player_identity_public_contract_decisions scripts.test_check_player_identity_public_contract_readiness
# Ran 130 tests OK

python3 -m unittest -q scripts.test_plugin_manager_guardrails scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_public_sdk_guardrails
# Ran 296 tests OK

python3 scripts/report_obelisk_sdk_status.py --json
# status=blocked route=approved_runtime_evidence_missing private_correlation=implemented/offline-pending-runtime-evidence ready=false public_sdk_ready=false runtime_ready=false stable=false

python3 scripts/check_player_identity_public_header_gate.py --promote
# fails closed with promote_blocked_until_runtime_bundle_and_header_promotion

git diff --check -- .
# passed
```

No deploy, restart, marker/env change, `/servidor/ark` write, live-log read, RCON,
Discord/GitHub publication, public SDK readiness claim, runtime readiness claim, or v1
completion claim occurred. The next blocker remains approved copied runtime principal
lifecycle evidence.

## 2026-06-04 Post-Compaction Correlation Evidence Hardening

The post-correlation runtime-evidence path now has a machine-checkable proof field instead
of relying on `principal_action` alone. `ProcessEventHook` emits only safe status tokens:
`apply_status=<closed vocabulary>` and `correlation_status=<closed vocabulary>`. The
approved analyzer/checker accepts `session_end` only when the copied logout event has
`apply_status=session_end_invalidated` and `correlation_status=matched`; unresolved,
missing, stale, duplicate, unsupported, registry-failure, or old-format logout lines stay
non-evidence. Starts must show `session_start_created` with `not_applicable` correlation,
and rejected starts must show `session_start_rejected_noop` with `not_applicable`
correlation.

Additional internal hardening from this round:

- zero private `NewPlayer` subject tokens fail closed before principal allocation;
- stale/duplicate logout cleanup erases a subject-token binding only when the mapped
  handle/generation still matches the apply result, so it cannot erase a newer principal;
- reflection subject-token state and correlation state use process-lifetime storage;
- status reporting normalizes ambiguous nested `ready` fields to false and preserves
  source values under scoped names.

Validation:

```text
python3 -m unittest -q scripts.test_analyze_runtime_observer_log scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
# Ran 161 tests OK

python3 -m unittest -q scripts.test_player_principal_runtime_guardrails scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest scripts.test_monitor_ark_player_presence_passive scripts.test_capture_player_principal_passive_snapshot scripts.test_summarize_player_principal_passive_snapshots scripts.test_prepare_player_principal_lifecycle_evidence_closure_request scripts.test_report_obelisk_sdk_status
# Ran 171 tests OK

cmake --build build --target obelisk player_principal_lifecycle_applicator_tests process_event_player_principal_lifecycle_observer_tests -j$(nproc)
# passed; known external fmt/spdlog warnings only

ctest --test-dir build -R 'PlayerPrincipal(LifecycleApplicator|Registry)Tests|ProcessEventPlayerPrincipalLifecycleObserverTests|PlayerPrincipalEventDispatcherTests' --output-on-failure
# 4/4 tests passed

python3 -m unittest -q scripts.test_public_sdk_guardrails scripts.test_plugin_manager_guardrails scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_check_player_identity_public_header_gate scripts.test_player_identity_public_contract_decisions scripts.test_check_player_identity_public_contract_decision_record scripts.test_check_player_identity_public_contract_readiness
# Ran 416 tests OK

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; public_sdk_ready=false; runtime_ready=false

git diff --check -- .
# passed
```

`scripts.test_check_public_sdk_v1_completion` was isolated after the broader guardrail
tandem ran too long and was stopped for abnormal duration without failure output. Treat it
as pending validation, not as passed. No server control, marker/env change,
`/servidor/ark` write, live-log read, RCON, Discord/GitHub publication, public SDK
readiness claim, runtime readiness claim, or v1 completion claim occurred.

## 2026-06-04 Offline SDK Gate False-Positive Closure

Subsequent supervised offline work closed several release-accounting false positives
without live-server access or public SDK promotion:

- `plugin_manager_tests` now compiles `core/ItemReturnEventDispatcher.cpp` through CMake
  instead of including the implementation directly from the test translation unit.
- command/chat response public-readiness now enforces exact P0 dependency ordering,
  requires all P0 surfaces in both `v1_required_dependency_chain` and
  `v1_sdk_completion_blockers`, and rejects treating
  `obelisk.command_chat_response_path.v1` as promoted evidence.
- runtime principal lifecycle bundle preflight now requires copied-log/window-manifest
  path and SHA binding before `copied_log_and_window_manifest_ready` can be true.
- permissions/admin public-readiness now requires a repo-relative, non-symlinked,
  hash-bound, P0-chain-ordered `obelisk.player_identity.v1` promotion certificate with
  explicit copied-principal semantic proof fields. Passive, diagnostic, review-only,
  stale, symlinked, or hash-unbound artifacts remain non-counting.

Validation for the current head after this closure:

```text
python3 -m unittest -q scripts.test_check_command_chat_response_public_readiness scripts.test_check_commands_replies_public_readiness
# Ran 101 tests OK

python3 -m unittest -q scripts.test_check_player_identity_public_header_gate scripts.test_check_player_identity_public_contract_decision_record scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence
# Ran 223 tests OK

python3 -m unittest -q scripts.test_check_permissions_admin_public_readiness scripts.test_permissions_admin_public_contract_decisions
# Ran 87 tests OK

cmake --build build --target plugin_manager_tests -j$(nproc)
ctest --test-dir build -R '^PluginManagerTests$' --output-on-failure
# passed

python3 -m unittest -q scripts.test_plugin_manager_guardrails scripts.test_player_principal_runtime_guardrails scripts.test_report_obelisk_sdk_status
# Ran 69 tests OK

python3 scripts/check_command_permission_route_gate.py --json
# valid=true planning_only=true route_blocked=true current_route_blocker=approved_runtime_evidence_missing

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; SDK 0/12; P0 0/4; stable_claim_allowed=false

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion
# Ran 282 tests OK in 240.143s
```

This supersedes the pending completion-suite note above for the current head only. The
route still requires approved copied runtime principal lifecycle evidence before public
identity, permissions/admin, command response, or commands/replies can move.

## 2026-06-04 Late Offline SDK/Runtime Guardrail Round

The late offline round closed additional false-positive and runtime cleanup risks without
server access. All active/known delegated agents were closed; one compacted prior worker
id was not present in the active agent runtime. No live server, `/servidor/ark`, marker/env,
RCON, Discord, GitHub, tag, publication, deploy, restart, runtime capture, or readiness
claim occurred.

Accepted deltas:

- owner-token SDK consumer contract now requires copied principal handle/generation/scope
  fields and rejects passive/diagnostic/runtime-bundle-only readiness aliases.
- public SDK completion/status tooling normalizes active route blockers to SDK `0/12` and
  P0 `0/4`, and rejects package-shape or planning-route aliases as promotion evidence.
- command route/bridge checks reject downstream unlock/accounting aliases such as command
  response, replies, runtime delivery, and completion-credit fields.
- inventory custom-filter array boundary checks reject symlinked/protected snapshot and
  public-header paths while remaining candidate-only/non-P0.
- handoff/doc guardrails preserve the rule that passive observations and planning
  artifacts are non-authorizing and non-evidence.
- `PlayerPrincipalEventDispatcher` deferred `DestroyUserData` failures now stay visible
  to owner cleanup even if deferred failure storage fails. Deferred failure slots are
  reserved before callback registry mutation, and a bounded fallback record preserves retry
  state under the test-injected storage failure path. The test hook is internal-only under
  `OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS` and does not add public ABI.

Validation for this head:

```text
python3 -m unittest -q scripts.test_check_command_permission_route_gate scripts.test_check_command_principal_authz_response_bridge scripts.test_check_command_permission_route_gate_bound_identity_sources
# Ran 114 tests OK

python3 -m unittest -q scripts.test_check_player_identity_owner_token_sdk_consumer_contract scripts.test_report_obelisk_sdk_status
# Ran 26 tests OK

python3 -m unittest -q scripts.test_check_inventory_custom_filter_array_boundary
# Ran 15 tests OK

python3 scripts/check_inventory_custom_filter_array_boundary.py --json
# ready=true; candidate_only=true; no public SDK/runtime/v1 completion flags

python3 -m unittest -q scripts.test_agent_handoff_guardrails scripts.test_operational_doc_guardrails scripts.test_research_doc_guardrails
# Ran 72 tests OK

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion
# Ran 282 tests OK in 241.541s

cmake --build build --target player_principal_event_dispatcher_tests
ctest --test-dir build -R PlayerPrincipalEventDispatcherTests --output-on-failure
./build/player_principal_event_dispatcher_tests
python3 scripts/test_player_principal_runtime_guardrails.py
# all passed; compile emitted existing fmt/spdlog warnings

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; SDK 0/12; P0 0/4; stable_claim_allowed=false

git diff --check -- .
# OK
```

The accepted runtime cleanup hardening does not change route accounting. The next required
artifact remains an approved copied runtime principal lifecycle evidence bundle.

## 2026-06-05 Offline SDK/Runtime Guardrail Round

The next supervised offline round closed all six delegated agents and kept the same safety
boundary: no live server control, live-log read, `/servidor/ark` read/write, marker/env
change, RCON, Discord, GitHub, tag, deploy, runtime capture, or readiness claim.

Accepted deltas:

- public identity contract and gap-report checkers reject additional readiness aliases for
  lookup, permissions/admin, command response/replies, runtime work authorization,
  `counts_toward_*`, production SDK, and stable SDK claims.
- public SDK completion/status tooling rejects secondary report, route gate, package-shape,
  installed-header, scoped release-statement, passive/diagnostic, and helper-artifact
  false promotions.
- inventory copied-signal stability checks reject symlinked or protected decisions/header
  paths before reading them, while preserving candidate-only/non-completion status.
- `StructureEventDispatcher` now mirrors the copied-event cleanup hardening: deferred
  `DestroyUserData` failures remain visible to owner cleanup even if deferred-failure
  storage fails, and retry state is retained outside the dispatchable callback set.
- the closure-request helper emits explicit false authorization/readiness/accounting flags
  and NOT EXECUTED commands, and a smoke run against `/tmp/obelisk-closure-smoke.jwJUBE`
  returned non-ready as expected without granting runtime or server authority.
- live-ops skill and handoff/research wording now distinguish historical approvals and
  then-active passive waits from current-turn authorization.

Validation for this head:

```text
python3 -m unittest -q scripts.test_check_inventory_item_copied_signals_stability scripts.test_check_player_principal_lifecycle_planning_blocker_smoke scripts.test_prepare_player_principal_lifecycle_evidence_closure_request scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails scripts.test_plugin_manager_guardrails
# Ran 168 tests OK

python3 -m unittest -q scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_public_sdk_v1_completion scripts.test_report_obelisk_sdk_status
# Ran 422 tests OK in 282.090s

cmake --build build --target structure_event_dispatcher_tests plugin_manager_tests
ctest --test-dir build -R '^(StructureEventDispatcherTests|PluginManagerTests)$' --output-on-failure
# passed, with existing fmt/spdlog compile warnings

python3 scripts/check_inventory_item_copied_signals_stability.py --json
# ready=true; public_sdk_ready=false; v1_completion_ready=false

python3 scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json
# ready=true; approved_runtime_evidence=false; runtime_capture_authorized=false

python3 scripts/check_command_permission_route_gate.py --json
# valid=true; planning_only=true; route_blocked=true; current_route_blocker=approved_runtime_evidence_missing

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; SDK 0/12; P0 0/4; stable_claim_allowed=false

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion
# Ran 288 tests OK in 253.233s

python3 scripts/check_public_sdk_v1_completion.py --json
# exited 1 as expected; stable_claim_allowed=false; SDK 0/12; P0 0/4; current_route_blocker=approved_runtime_evidence_missing
```

This round improves false-positive resistance and copied-event cleanup safety only. It
does not satisfy approved runtime evidence, public identity, permissions/admin, command
response, commands/replies, runtime readiness, public SDK readiness, or stable SDK status.

## 2026-06-05 Mission/Transfer Side-Lane Hardening

The follow-up supervised offline round closed all six delegated agents and kept the same
safety boundary: no live server control, live-log read, `/servidor/ark` read/write,
marker/env change, RCON, Discord, GitHub, tag, deploy, runtime capture, or readiness
claim.

Accepted deltas:

- `check_mission_copied_bool_readiness.py --fixture-boundary-only` now validates the
  repo-local Mission copied-bool fixture boundary without inspecting protected roots or
  manifests, without artifact consume/promote gates, without a repo frontier, and without
  attestation. It reports fixture-boundary acceptance only while all public SDK, runtime,
  promotion, and v1 completion flags stay false.
- public SDK completion rejects Mission copied-bool policy slices, fixture-boundary
  reports, readiness-only reports, scoped/internal Mission markers, and leaf-scoped
  fixture-boundary artifacts as promotion evidence.
- `check_transfer_baccept_readiness.py` now reads manifests through no-symlink
  regular-file handling, rejects symlink swaps and protected paths before read, and emits
  explicit false public/runtime/v1 readiness aliases.
- `MissionCopiedBoolEventDispatcher` now retains deferred `DestroyUserData` cleanup
  failures outside the dispatchable callback set, including the injected storage-failure
  path, so owner cleanup can retry instead of losing plugin-owned failure state.
- release-scope/build guardrails keep Mission copied-bool dispatcher/test/benchmark
  surfaces out of public SDK, runtime install, and plugin-facing target wiring.
- research and handoff wording preserve that Mission copied-bool fixture-boundary reports
  and internal summaries are offline evidence/planning material only.

Validation for this head:

```text
python3 -m unittest -q scripts.test_check_mission_copied_bool_readiness scripts.test_check_transfer_baccept_readiness scripts.test_research_doc_guardrails scripts.test_plugin_manager_guardrails
# Ran 119 tests OK

python3 -m unittest -q scripts.test_release_scope_guardrails.ReleaseScopeGuardrailTests.test_mission_copied_bool_dispatcher_remains_test_only_if_added scripts.test_release_scope_guardrails.ReleaseScopeGuardrailTests.test_mission_copied_bool_observer_stays_internal_and_non_authoritative scripts.test_release_scope_guardrails.ReleaseScopeGuardrailTests.test_mission_copied_bool_tail_contract_stays_documented_and_candidate_only
# Ran 3 tests OK

cmake --build build --target mission_copied_bool_event_dispatcher_tests mission_copied_bool_event_dispatcher_benchmark
ctest --test-dir build -R '^MissionCopiedBoolEventDispatcherTests$' --output-on-failure
build/mission_copied_bool_event_dispatcher_benchmark | python3 scripts/check_mission_copied_bool_dispatcher_benchmark.py -
# passed, with existing fmt/spdlog compile warnings

python3 scripts/check_mission_copied_bool_readiness.py --fixture-boundary-only --json
# fixture_boundary_ready=true; public_sdk_ready=false; runtime_ready=false; v1_completion=false

python3 scripts/check_transfer_baccept_readiness.py --skip-artifact-gates --json
# candidate_ready; public/runtime/v1 readiness flags false

python3 scripts/check_command_permission_route_gate.py --json
# valid=true; planning_only=true; route_blocked=true; current_route_blocker=approved_runtime_evidence_missing

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; SDK 0/12; P0 0/4; stable_claim_allowed=false
```

This round improves internal side-lane safety and false-positive resistance only. It does
not satisfy approved runtime evidence, public identity, permissions/admin, command
response, commands/replies, Transfer runtime authority, Mission public SDK, runtime
readiness, public SDK readiness, or stable SDK status.

Inventory copied-signal stability, Mission copied-bool fixture-boundary, Transfer
`bAccept`, and Mission/Transfer/Dino/Tribe umbrella accounting remain
candidate-only/non-authorizing side-lane accounting. They cannot count as SDK completion,
runtime readiness, live ops approval, P0 progress, approved runtime evidence, public SDK
readiness, or v1 completion.

## 2026-06-05 Side-Lane Accounting and Route-Lock Round

The next supervised offline round closed all six delegated agents and preserved the same
safety boundary: no live server control, live-log read, `/servidor/ark` read/write,
marker/env change, RCON, Discord, GitHub, tag, deploy, runtime capture, or readiness
claim.

Accepted deltas:

- Inventory copied-signal stability now emits an explicit non-counting latch:
  `candidate_only=true`, `counts_toward_complete_sdk_claim=false`,
  `counts_toward_p0_dependency_chain_claim=false`, both progress contributions `0`, and
  public/runtime/v1/stable flags false.
- Mission/Transfer/Dino/Tribe umbrella accounting now consumes the focused Mission
  copied-bool and Transfer `bAccept` readiness reports, mirrors blocker parity, and keeps
  both leaves candidate-only with false complete-SDK/P0 accounting aliases.
- Public SDK completion rejects Inventory copied-signal and Mission/Transfer umbrella
  side-lane reports that try to set positive completion-accounting aliases.
- `PlayerPrincipalEventDispatcher` gained a granular unregister regression for deferred
  `DestroyUserData` failure propagation and retry retention.
- `check_command_permission_route_gate.py` now reports a `post_evidence_p0_lock_simulation`
  showing that accepted runtime evidence can move only to `identity_public_contract_gate_missing`
  and cannot unlock permissions/admin, command response, commands/replies, P0 progress, or
  complete-SDK progress.
- Tribe scalar-boundary readiness now requires `ShooterPlayerController.ServerRequestTribeLog`
  as a zero-param control instead of treating it as optional.
- Research guardrails now explicitly keep Inventory copied-signal stability, Mission
  fixture-boundary, Transfer `bAccept`, and umbrella accounting candidate-only and
  non-authorizing.

Validation for this head:

```text
python3 -m unittest -q scripts.test_check_command_permission_route_gate scripts.test_check_inventory_item_copied_signals_stability scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting scripts.test_check_tribe_scalar_boundary_readiness scripts.test_research_doc_guardrails scripts.test_agent_handoff_guardrails
# Ran 211 tests OK in 48.783s

python3 -m unittest -q scripts.test_check_public_sdk_v1_completion
# Ran 288 tests OK in 348.402s

python3 scripts/check_public_sdk_v1_completion.py --json
# exited 1 as expected; stable_claim_allowed=false; SDK 0/12; P0 0/4; current_route_blocker=approved_runtime_evidence_missing

python3 -m unittest -q scripts.test_check_command_permission_route_gate
# Ran 61 tests OK

cmake --build build --target player_principal_event_dispatcher_tests -- -j2
ctest --test-dir build -R '^PlayerPrincipalEventDispatcherTests$' --output-on-failure
./build/player_principal_event_dispatcher_tests
# passed

python3 scripts/check_tribe_scalar_boundary_readiness.py --json
python3 scripts/check_inventory_item_copied_signals_stability.py --json
python3 scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json
# all ready/candidate-only; all public/runtime/v1 completion flags false

python3 scripts/report_obelisk_sdk_status.py
# status=blocked; current_route_blocker=approved_runtime_evidence_missing; SDK 0/12; P0 0/4; stable_claim_allowed=false

git diff --check -- .
# OK
```

This round improves non-counting accounting, route-lock simulation, and internal fixture
boundary safety only. It does not satisfy approved runtime evidence, public identity,
permissions/admin, command response, commands/replies, public Tribe/Inventory/Mission/
Transfer SDKs, runtime readiness, public SDK readiness, or stable SDK status.

## 2026-06-05 Transfer/Buff/Dino Side-Lane Guardrail Round

The latest supervised offline round closed all six delegated workers and left no standby
agent open. No live server, live log, `/servidor/ark`, marker/env, RCON, Discord, GitHub,
tag, deploy, restart, runtime capture, or readiness claim was touched.

Integrated changes:

- `check_transfer_scriptstruct_readiness.py` wraps the redacted ScriptStruct signature
  builder for `transfer-scriptstruct`, requires `ARKTributeDino` and
  `ArkTributePlayerData`, records the three bool-tail fields, keeps every payload field
  redacted, and explicitly excludes `ItemNetInfo`.
- `check_buff_status_readiness.py` binds both `buff-compact-intake` and
  `buff-breadth-intake` to manifest-listed `sdk_buffs` fixtures, rejects missing or
  duplicate manifest entries, misplaced snapshots, symlinked paths, public/runtime/v1
  overclaims, and keeps all Buff public module/SDK/P0 aliases false or zero.
- `check_dino_scalar_readiness.py` now rejects external-report public/runtime/v1/P0
  overclaims and emits false/zero SDK/P0 accounting aliases.
- `check_public_sdk_v1_completion.py` rejects Transfer ScriptStruct, Buff status, Tribe
  scalar-boundary, and route post-evidence P0 lock simulation reports as completion
  evidence, including true/nonzero progress aliases.
- `report_obelisk_sdk_status.py` surfaces `post_evidence_p0_lock_simulation` as
  simulation-only: accepted runtime evidence can only move toward identity public contract
  review and does not unlock P0 progress, runtime readiness, public SDK readiness, live
  ops, runtime capture, or workspace writes.
- Copied-dispatcher guardrails now require every owner-cleanup dispatcher family to be
  wired into `PluginManager::UnregisterPluginCallbacks` or explicitly internal/test-only.

Validation for this head:

```text
python3 -m unittest scripts.test_check_transfer_scriptstruct_readiness scripts.test_check_buff_status_readiness scripts.test_check_dino_scalar_readiness scripts.test_report_obelisk_sdk_status scripts.test_plugin_manager_guardrails scripts.test_release_scope_guardrails scripts.test_research_doc_guardrails
# Ran 193 tests OK

python3 -m unittest scripts.test_check_public_sdk_v1_completion
# Ran 290 tests OK in 352.936s

python3 scripts/check_public_sdk_v1_completion.py --json
# exited 1 as expected; stable_claim_allowed=false; SDK 0/12; P0 0/4; current_route_blocker=approved_runtime_evidence_missing

python3 scripts/check_command_permission_route_gate.py --json
# valid=true; planning_only=true; current_route_blocker=approved_runtime_evidence_missing; post-evidence simulation counts false

python3 scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json
python3 scripts/check_transfer_scriptstruct_readiness.py --json
python3 scripts/check_buff_status_readiness.py --json
python3 scripts/check_dino_scalar_readiness.py --json
# all candidate-only/non-counting; public/runtime/v1/P0 flags false or zero
```

This is internal safety and accounting hardening only. The Transfer ScriptStruct, Buff
manifest/source binding, Dino scalar, and accounting-integration results are
candidate-only/non-authorizing and do not authorize live ops, server/log reads, or any
SDK/P0/runtime/public/stable progress. They do not satisfy approved runtime principal
lifecycle evidence, public player identity, permissions/admin, command response,
commands/replies, Transfer/Buff/Dino SDK readiness, runtime readiness, public SDK
readiness, P0 progress, or stable SDK status.

## 2026-06-06 InventoryCustomFilter Extra-Param Guard

While no users were online for runtime lifecycle evidence, the fastest offline side-lane
was hardened without touching servers. `check_inventory_custom_filter_array_boundary.py`
now treats any reflected property beyond the two expected `InventoryCustomFilter`
`ArrayProperty` shells as `unexpected_extra_param_payload`, so a forged third parameter
cannot hide behind the boundary-only fixture.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_custom_filter_array_boundary.py --json`
  passed with `ready=true`, `candidate_only=true`, two array boundaries, and all
  public/runtime/v1 readiness flags false.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_inventory_custom_filter_array_boundary`
  passed `27 OK`.
- Related inventory suite
  `python3 -m unittest scripts.test_check_inventory_item_copied_signals_stability
  scripts.test_check_inventory_action_redacted_observer_gate
  scripts.test_check_inventory_custom_filter_array_boundary` passed `90 OK`.

This remains fixture-only, candidate-only, and non-completion. It does not provide
runtime evidence, second-source evidence, copied array payload ownership, identity,
lookup, `ResourceHandle`, mutation, return override, Inventory/Items SDK readiness, P0
progress, or v1 completion.

## 2026-06-06 Side-Lane Shortcut Alias Hardening

During the later no-user offline round, the Transfer, Mission, Buff, Dino, and umbrella
Mission/Transfer/Dino/Tribe accounting checkers were hardened against another shortcut
class:

- readiness/promotion aliases using `allowed`, `unblocked`, or `unlocked`;
- numeric `credit`/`credits` aliases under SDK, runtime, v1, P0, public, complete, or
  stable claim contexts;
- Dino textual overclaims, while preserving explicit negative/exclusion containers.

Validation:

- `python3 -m py_compile` for the touched side-lane checker/test modules: passed.
- `python3 -m unittest scripts.test_check_transfer_scriptstruct_readiness
  scripts.test_check_mission_copied_bool_readiness scripts.test_check_buff_status_readiness
  scripts.test_check_dino_scalar_readiness
  scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting`: `123 OK`.
- The later integrated focal Python suite passed `515 OK`.

These aliases are rejected as guardrail hardening only. They do not add raw payload
decoding, runtime validation, public SDK, SDK v1, mutation, return override, identity,
lookup, `ResourceHandle`, or any P0/complete-SDK progress.

## Required Evidence Siblings

For any future current-turn approved evidence window, the copied evidence bundle must preserve this exact sibling set under
`/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`:

- `window-request.json`
- `observer-window.env`
- `operator-approval-request.md`
- completed `operator-approval-receipt.json`
- `preflight-pre.json`
- `preflight-post.json`
- `window-manifest.env`
- copied `Obelisk.log`

The generated receipt template is not evidence. The completed receipt must bind the
request pack for the current run.

When the current-turn approval includes the beta testers Discord path or another player
notice path, the copied intake must also preserve a sent-notice attestation in the run
sidecars or completed receipt: approved notice path, dry-run result, send action, send
timestamp, and reviewer/operator scope. The eight files above remain mandatory; the notice
attestation is additional for player-noticed windows. A notice path recorded only as
documented, drafted, or documented but not sent blocks approved evidence intake.
The sent-notice attestation must be secret-free metadata only: no Discord webhook URLs,
webhook tokens, secret environment assignment, or raw secret-bearing dry-run output. Keep
only the non-secret notice path/channel label, dry-run result/status, send action,
send timestamp, reviewer/operator scope, and non-secret command metadata. The dry-run
result, send action, and `player_notice_action` value are communication proof only, not
runtime evidence, live-ops approval, SDK progress, public readiness, public SDK readiness,
runtime readiness, publication, or complete/stable SDK status.

## Non-Claims

This fast path is intended to clear the runtime evidence blocker only. It does not promote
player identity/principal, permissions/admin, command response, commands/replies,
ResourceHandle, lookup, mutation, return override, runtime readiness, public SDK
readiness, or complete/stable v1 SDK status.
