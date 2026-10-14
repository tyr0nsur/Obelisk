# Lifecycle Anchor FName Drift Delta

Date: 2026-06-04

Scope: audit of existing repo evidence for `ShooterGameMode.HandleNewPlayer` and
`ShooterGameMode.OnLogout`, plus passive diagnostic mismatch facts copied to `/tmp`.
No ptrace/gcore, Frida/rr, scanner/native-exec, raw payload logging, GitHub/Discord
action, commit, tag, or push was performed. The latest update includes a minimal live
Ragnarok launch-config fix and passive copied-log snapshot; raw live logs are not copied
into Git.

## Current Audit Conclusion

Current local C++/test state contains a bounded acceptance design: property FName index
drift is accepted only for `ShooterGameMode.HandleNewPlayer` and
`ShooterGameMode.OnLogout` after exact function/outer/class, function shape, positional
property shape, property class, flags, offsets, sizes, array dims, bool metadata, and
redaction/copy-scope checks. Diagnostic-only lifecycle-adjacent targets still reject
property FName drift. Focused Python guardrail tests and the two lifecycle C++ tests pass
locally.

2026-06-07 source-bound planning audit result: the manifest verifier now checks the
FName-mismatch planning artifact against the committed sanitized snapshots for
`HandleNewPlayer` and `OnLogout`, including base fixture path/SHA, property order, and
fixture expected property FName indices. The newer redacted-monitor values
`HandleNewPlayer=28422,21318,22972,28520,17727` and `OnLogout=28554` remain passive
diagnostic context by themselves, but the distinct non-protected lifecycle snapshot root
below supplies the semantic source-bound shape needed for a narrow recognizer update.
They are still not an accepted copied observer event, not runtime evidence, and cannot
clear readiness by themselves.

That implementation/test coverage plus the follow-up offline snapshot-root check is now
enough to treat the property-FName-drift acceptance as a planning/layout candidate. A
distinct non-protected root was recovered under
`/home/flowcommunity-ark/obelisk-artifacts/lifecycle-snapshot-root-check-20260604T1531Z/candidate-root/`
with exactly `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`; the
comparator accepted it with `offline_requirement.satisfied=true`, `status=accepted`,
`comparison_counts accepted=2 rejected=0 inconclusive=0`, and no extra or missing
targets. That result source-binds the semantic lifecycle property shape only; it does
not source-bind the later `28422` / `28554` passive FName deltas themselves, update
fixture expectations, or turn copied diagnostic indices into second-source layout
evidence. This still does not clear approved runtime evidence, runtime readiness, public
SDK readiness, release readiness, or v1 completion.

Latest live-safe integration result: the current local patch recognizes the observed
Ragnarok `HandleNewPlayer` chains `28417,21313,22967,28515,17723` and
`28422,21318,22972,28520,17727`, plus `OnLogout=28554`, only as explicit recognizer
drift-chain alternatives after exact shape checks. `GameMode.K2_PostLogin=28422` remains
reject-only diagnostic context. This is local recognizer coverage, not an accepted copied
observer event, not approved runtime evidence, and not installed on the live server.

Read-only drift-audit delta: no mixed old/new bypass was found in the current
implementation. The fail-closed boundary still depends on complete approved-chain
revalidation after restart, not on accepting partially shifted property FName chains.

## Sources Audited

- `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/manifest.json`
  - Latest passive snapshot reviewed for this note; schema
    `obelisk.player-principal-passive-snapshot.v1`, captured
    `2026-06-04T15:04:23Z`.
  - Copied monitor log:
    `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/passive-monitor.log`
    (`sha256=a6e5a279141d44bbb959b4aafd1cc8918af902489ef65401eda05082f1e22fa0`).
  - Copied Obelisk logs:
    `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/arkserver-Ragnarok-Obelisk.log`
    (`sha256=ac06a1a99791edf039fedfbc6833932fae24a8cb1d67d13b1de043206cf918fe`;
    source path `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`) and
    `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/arkserver2-TheIsland-Obelisk.log`
    (`sha256=df01bebc821d00b2cdaeebd817e8f22c362590b0ad0b15c2dd49d9a5d8ec5391`;
    source path `/servidor/ark/obelisk/logs/arkserver2/Obelisk.log`).
- `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T153516Z-arkserver-ragnarok-postrestart-drift/manifest.json`
  - Copied Ragnarok-only passive snapshot captured at `2026-06-04T15:35:21Z`.
  - It is non-evidence: `ready=false`, `approved_runtime_evidence=false`, `accepted=0`,
    `diagnostic_candidates=9`, `rejected=0`, `players=1/70`, and
    `process_control=none`.
  - The copied `arkserver` log SHA256 is
    `4dff952ed41740ced8d2f1d3fdddefbaacee49880977719ece78a190ff58db73`.
- `docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json`
  - SHA256: `03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4`
- `docs/research/player-identity-planning-sources/players-identity-lifecycle-anchor-candidates.json`
- `docs/research/player-identity-planning-sources/players-lifecycle-anchor-candidates-all-six-planning-gap.json`
- `docs/research/player-identity-planning-sources/players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json`
- `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/players_lifecycle/*.snapshot.json`
- `docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md`
- `docs/agent-handoff/CURRENT.md` read-only, for latest routing facts only.

Commands used for this audit:

```bash
sha256sum docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json
jq '{artifact_identity, accepted_targets, blockers, non_claims}' docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json
jq '{artifact_identity, lifecycle_acceptance, candidate_anchors, promotion_gate}' docs/research/player-identity-planning-sources/players-identity-lifecycle-anchor-candidates.json
jq '{runtime_observation_summary, fixture_expected_name_indices, observed_name_indices, related_observed_fname_mismatches, next_offline_artifact_requirement}' docs/research/player-identity-planning-sources/players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json
jq '{captured_at_utc, schema, source_kind, ready, readiness_gate, ready_scope, evidence_classification, approved_evidence_claim, approved_runtime_evidence, target_count, all_logs_copied, diagnostics: {candidate_count: .diagnostics.candidate_count, classification: .diagnostics.classification, rejected_drift_count: .diagnostics.rejected_drift_count, rejected_targets: .diagnostics.rejected_drift_targets, accepted_triplets: .diagnostics.observer_event_triage.accepted_observer_event_triplet_candidate_count, missing_roles: .diagnostics.observer_event_triage.missing_observer_event_triplet_roles}, monitor_log: {copied_path: .monitor_log.copied_path, copied_sha256: .monitor_log.copied_sha256, copied_size: .monitor_log.copied_size, line_count: .monitor_log.metadata.line_count}, targets: [.targets[] | {target_key, instance, map, query_port, source_path, copied_path, copied_sha256, copied_size, counts, diagnostic_only_non_evidence, evidence_classification, approved_evidence_claim, approved_runtime_evidence, readiness_gate, ready, latest: .diagnostics.latest_observer_line, query: {players: .query_state.players, players_current: .query_state.players_current, players_max: .query_state.players_max, process_control: .query_state.process_control, reported_process_control: .query_state.reported_process_control, presence_detected: .query_state.presence_detected, last_query_utc: .query_state.last_query_utc, last_presence_detected_utc: .query_state.last_presence_detected_utc}, module: {accepted_count: .analyzer.summary.modules.player_principal_lifecycle.accepted_count, diagnostic_candidate_count: .analyzer.summary.modules.player_principal_lifecycle.diagnostic_candidate_count, rejected_count: .analyzer.summary.modules.player_principal_lifecycle.rejected_count, target_counts: .analyzer.summary.modules.player_principal_lifecycle.diagnostic_candidate_target_counts, mismatches: .analyzer.summary.modules.player_principal_lifecycle.diagnostic_candidate_lifecycle_property_fname_mismatches, missing_roles: .analyzer.summary.modules.player_principal_lifecycle.missing_lifecycle_event_roles, non_evidence_reasons: .analyzer.summary.modules.player_principal_lifecycle.non_evidence_reasons}}]}' /tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/manifest.json
python3 scripts/compare_reflection_snapshots.py --list-target-sets --json
python3 scripts/compare_reflection_snapshots.py --list-target-guidance --target-set players-lifecycle-anchor-candidates --json
python3 scripts/compare_reflection_snapshots.py --base-root tests/fixtures/ufunction_snapshots --observed-fname-chain 28418,21314,22968,28516,17724 --observed-fname-chain-occurrences 4 --target-set players-lifecycle-anchor-candidates --json
python3 scripts/compare_reflection_snapshots.py --base-root tests/fixtures/ufunction_snapshots --observed-fname-chain 28550 --observed-fname-target ShooterGameMode.OnLogout --observed-fname-chain-occurrences 3 --target-set players-lifecycle-anchor-candidates --json
find . -path './.git' -prune -o -path './build*' -prune -o -name 'ShooterGameMode.HandleNewPlayer.snapshot.json' -print | sort
find . -path './.git' -prune -o -path './build*' -prune -o -name 'ShooterGameMode.OnLogout.snapshot.json' -print | sort
python3 -m unittest scripts.test_compare_reflection_snapshots scripts.test_summarize_player_principal_passive_snapshots
cmake --build build --target player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests
ctest --test-dir build -R 'PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests' --output-on-failure
python3 scripts/capture_player_principal_passive_snapshot.py --allow-server-path --log-root /servidor/ark/obelisk/logs --monitor-log /tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log --output-dir /tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T153516Z-arkserver-ragnarok-postrestart-drift --target arkserver:Ragnarok:27015
python3 scripts/analyze_runtime_observer_log.py --allow-server-path /servidor/ark/obelisk/logs/arkserver/Obelisk.log
sha256sum /servidor/ark/obelisk/lib/libobelisk.so build/libobelisk.so
```

## Facts

The durable static report hash matches the accepted planning anchor hash exactly. It is
bound to ARK binary SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
source artifact id `artifact_sha256:62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`,
`capture_id:base-identity-core`, and
`evidence_pack_id:player-identity-base-core-evidence-pack`.

Accepted offline planning anchors remain exactly:

- `ShooterGameMode.HandleNewPlayer`: `static_accepted` session-start layout candidate,
  `fname_index=2170`, `NumParms=5`, `ParmsSize=26`, `ReturnValueOffset=0x19`, property
  order `NewPlayer`, `PlayerData`, `PlayerCharacter`, `bIsFromLogin`, `ReturnValue`.
- `ShooterGameMode.OnLogout`: `static_accepted` session-end layout candidate,
  `fname_index=2384`, `NumParms=1`, `ParmsSize=8`, `ReturnValueOffset=0xffff`, property
  order `Exiting`.

The three HandleNewPlayer object fields and the OnLogout `Exiting` object field remain
recognition/redaction-only. Only `bIsFromLogin` and `ReturnValue` are copied
non-identity scalar candidates, and only inside the private lifecycle evidence route. None
of this promotes public identity, lookup, `ResourceHandle`, mutation, return override,
runtime readiness, public SDK readiness, or v1 completion.

The committed all-six `players-lifecycle-anchor-candidates` fixture set contains
`GameMode.K2_PostLogin`, `ShooterGameMode.CheckJoinInProgress`,
`ShooterGameMode.HandleNewPlayer`, `ShooterGameMode.OnLogout`,
`ShooterGameMode.OnPostLogin__DelegateSignature`, and
`ShooterGameMode.OnStartNewPlayer__DelegateSignature`. The all-six planning-gap artifact
keeps the durable accepted anchor binding limited to `HandleNewPlayer` and `OnLogout`.
The other four targets are guidance/candidate-only and are not lifecycle anchors.

The latest machine-readable mismatch artifact records copied passive diagnostic analysis
for the `2026-06-04T08:51:19Z` Ragnarok/TheIsland snapshot as `planning_only`,
`not_second_source`, `layout_evidence_status=not_layout_evidence`, and
`readiness_effect=none`. It records `accepted_count=0`, `rejected_count=0`, Ragnarok
`diagnostic_candidate_count=17`, and TheIsland `diagnostic_candidate_count=0`.

The latest passive snapshot reviewed here is lead5 at
`/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/manifest.json`.
It is still non-evidence: `ready=false`, `readiness_gate=none`,
`ready_scope=passive_snapshot_only`,
`evidence_classification=passive_snapshot_non_evidence`,
`approved_evidence_claim=none`, `approved_runtime_evidence=false`, and
`all_logs_copied=true`. Aggregate observer triage reports
`accepted_observer_event_triplet_candidate_count=0`, `candidate_count=36`,
`rejected_drift_count=0`, and the target module counters sum to `accepted=0`,
`diagnostics=36`, `rejected=0`. The accepted lifecycle roles remain missing:
`session_start`, `session_start_rejected`, and `session_end`.

Lead5 target status:

- `arkserver:Ragnarok:27015`: copied log
  `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/arkserver-Ragnarok-Obelisk.log`,
  query state `players=2/70`, `presence_detected=true`,
  `process_control=none`, `reported_process_control=none`,
  latest diagnostic line `14:45:19` / line `35`; module counters
  `accepted_count=0`, `diagnostic_candidate_count=20`, `rejected_count=0`.
- `arkserver2:TheIsland:27016`: copied log
  `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/arkserver2-TheIsland-Obelisk.log`,
  query state `players=0/70`, `presence_detected=false`,
  `process_control=none`, `reported_process_control=none`,
  latest diagnostic line `15:27:30` / line `31`; module counters
  `accepted_count=0`, `diagnostic_candidate_count=16`, `rejected_count=0`.

Because `arkserver` / `Ragnarok` had connected players in the latest reviewed snapshot,
and because passive wait approval is wait-only, future agents must not restart either ARK
instance to chase these lines. Passive snapshot paths, monitor ticks, copied diagnostic
logs, and summarized FName mismatches do not authorize process control, marker/env
changes, deployment, runtime capture, publication, or SDK readiness claims.

The exact recorded drift shapes are stable across the reviewed passive material:

- `HandleNewPlayer`: expected property FName indices
  `28411,21307,22961,28509,17716`; observed
  `28418,21314,22968,28516,17724`; deltas `7,7,7,7,8`. Lead5 records this as
  `lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724`
  with six Ragnarok and four TheIsland diagnostic occurrences.
- `OnLogout`: expected `28543`; observed `28550`; delta `7`.
  Lead5 records this as
  `lifecycle_property_FName_mismatch_expected_28543_observed_28550` with four Ragnarok
  and two TheIsland diagnostic occurrences.

Later repo summaries preserve the same non-evidence conclusion: a `2026-06-04T12:10:19Z`
passive snapshot has `ready=false`, `approved_runtime_evidence=false`, and
`diagnostic_candidates=26`; a newer Ragnarok `14:45:19` `OnLogout` diagnostic line still
has `evidence_claim=none`. No recorded passive snapshot contains the accepted
`PlayerPrincipalLifecycleObserver event` triplet for `session_start`,
`session_start_rejected`, and `session_end`.

The 2026-06-07 repo-only audit did not find checked-in source data for the later
`28422` / `28554` observations. Those values are carried in
`players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json` as
`latest_unbound_passive_diagnostic_context`, with `approved_runtime_evidence=false`,
`can_update_fixture_expectations=false`, and
`counts_as_second_source_layout_evidence=false`. Future source-bound updates still need a
distinct sanitized lifecycle snapshot root or an approved copied observer-event bundle.

After a later Ragnarok restart fix at local `17:24`-`17:35`, the live installed runtime
logged a new `HandleNewPlayer` mismatch chain:

- expected first property index: `28411`;
- observed complete chain: `28417,21313,22967,28515,17723`;
- count in copied/analyzed log: `3`;
- associated passive query: `arkserver:Ragnarok:27015`, `players=1/70`;
- evidence status: diagnostic-only, `evidence_claim=none`, not approved runtime evidence.

The installed live runtime remains SHA256
`97a50aedcd8ca183cb2dce8be5bcb2dbe64cfb106c0e98c2eb98dac9598981b8`. The locally rebuilt
runtime SHA256 is `5625327fb28d4ea57aefa102a5edf06c238b83eda25ead5eea3885d45191207c`
and contains the new approved-chain logic, but deployment is deferred while Ragnarok has
a player connected. A copied passive snapshot at
`/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T154738Z-arkserver-ragnarok-continuation/manifest.json`
was captured at `2026-06-04T15:47:43Z`; it still reports Ragnarok `players=1/70`,
`accepted=0`, `diagnostic_candidates=9`, and missing lifecycle roles `session_start`,
`session_start_rejected`, and `session_end`.

Current local offline guardrails accept property FName drift only for the two accepted
anchor functions and only after exact function/outer/positional shape validation:
function name, function class, outer, function flags, `NumParms`, `ParmsSize`,
`ReturnValueOffset`, property count, property order by position, property class, offset,
size, element size, array dim, property flags, and bool metadata. Reordered fields,
duplicate observed names, wrong FName number, wrong offsets/classes/flags/bool metadata,
and drift on diagnostic-only targets still reject and clear copied output.

Follow-up audit result: the focused Python guardrail suite
`scripts.test_compare_reflection_snapshots` plus
`scripts.test_summarize_player_principal_passive_snapshots` passed `143` tests, and CTest
passed `PlayerPrincipalLifecycleReflectionTests` and
`ProcessEventPlayerPrincipalLifecycleObserverTests`. These results prove the local
guardrail behavior, not the missing distinct offline evidence root.

## Hypotheses

The observed Ragnarok property FName indices may reflect map/mod/event/runtime name-table
drift relative to the offline core used for committed fixtures. Existing offline core name
resolution does not prove that hypothesis: the observed indices resolve to unrelated names
in the audited offline core, so the diagnostic chain is not semantic layout evidence.

The safer working hypothesis is that exact positional property shape is the evidence to
reconcile next, while raw observed FName-chain equality is too brittle to use alone. A
search-by-FName matcher alone remains rejected.

## Diagnostic-Only Material

These remain non-evidence and must not be used as second-source layout, runtime evidence,
public SDK readiness, or deploy justification:

- passive snapshot manifests and passive monitor output;
- `PlayerPrincipalLifecycleDiagnostic` lines, including `evidence_claim=none` lines;
- copied runtime observed FName chains;
- lead5 copied logs and monitor transcript under
  `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T150405Z-arkserver+arkserver2-lead5/`;
- the `players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json` artifact;
- all-six scratch/triage comparison history and the four non-anchor lifecycle-adjacent
  targets;
- any broad FName/GObjects scan or unapproved ReflectionScanner output.

## Snapshot Format Audit

Existing committed lifecycle snapshots use one sanitized
`obelisk.ufunction-chain.snapshot.v1` payload per `*.snapshot.json` file under:

```text
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/players_lifecycle/
```

The two accepted anchor files are:

- `ShooterGameMode.HandleNewPlayer.snapshot.json`
- `ShooterGameMode.OnLogout.snapshot.json`

The minimal candidate root that can answer
`distinct_lifecycle_snapshot_root_check_required` must contain exactly those two targets,
with the same root shape:

```text
<distinct-sanitized-lifecycle-root>/<ark-sha12>/players_lifecycle/ShooterGameMode.HandleNewPlayer.snapshot.json
<distinct-sanitized-lifecycle-root>/<ark-sha12>/players_lifecycle/ShooterGameMode.OnLogout.snapshot.json
```

Required snapshot fields observed in the existing format:

- top-level `schema=obelisk.ufunction-chain.snapshot.v1`;
- exactly one `targets[]` entry per file;
- `evidence.ark_binary_sha256`, `evidence.artifact_kind=offline_core`,
  `evidence.artifact_sha256`, `evidence.capture_id`, and
  `evidence.evidence_pack_id`;
- `evidence.source=offline_core`, `evidence.status=candidate-only`, and
  `evidence.generated_by=scripts/inspect_core_ufunctions.py --snapshot-json`;
- target `status=candidate`, empty target reject reasons, and target/class/outer
  membership all `candidate-uobject`;
- property-chain `status=candidate`, empty reject reasons, exact observed/expected
  property count, and per-property membership/class/outer status all
  `candidate-uobject`;
- for bool properties, copied `bool_property_semantics`, `bool_field_size`,
  `bool_byte_offset`, `native_bool`, `byte_mask`, and `field_mask`.

The lifecycle root check is intentionally semantic-layout only. It must ignore unstable
FName/object identity indices while comparing target outer/name/class, `NumParms`,
`ParmsSize`, `ReturnValueOffset`, property order, property classes, offsets, element
sizes, array dims, property flags, and bool metadata.

Follow-up verification recovered a distinct sanitized
`obelisk.ufunction-chain.snapshot.v1` lifecycle snapshot root for exactly
`ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` from a non-protected
offline artifact:

```text
/home/flowcommunity-ark/obelisk-artifacts/lifecycle-snapshot-root-check-20260604T1531Z/candidate-root/
```

It carries complete artifact identity for the candidate root and is deliberately outside
the committed fixture root, so it does not create duplicate target keys under
`tests/fixtures/ufunction_snapshots/`.

## Offline Requirement Status

The comparison must prove semantic layout only: target outer/name/class, `NumParms`,
`ParmsSize`, `ReturnValueOffset`, property order, property classes, offsets, element
sizes, array dims, flags, bool metadata, and candidate-uobject membership for target,
class, outer, and properties. It must not require strict FName/object identity index
equality, and it must not consume copied runtime diagnostic lines as the candidate root.

Verified offline command:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /home/flowcommunity-ark/obelisk-artifacts/lifecycle-snapshot-root-check-20260604T1531Z/candidate-root \
  --lifecycle-snapshot-root-check \
  --json
```

Observed result:

```text
offline_requirement.satisfied=true
offline_requirement.status=accepted
comparison_counts accepted=2 rejected=0 inconclusive=0
exact_required_targets=true
approved_runtime_evidence=false
promotion_ready=false
runtime_ready=false
```

This accepted root answers only the distinct sanitized lifecycle-root requirement for
semantic property shape. It is not a checker-accepted copied runtime bundle and does not
bind the redacted passive `28422` / `28554` observations as exact FName-index evidence;
the observed-chain comparator still classifies those deltas as diagnostic-only,
`second_source_layout_evidence=false`, and `can_be_used_as_candidate_snapshot_root=false`.

Remaining offline/research questions:

- Are the observed passive FName deltas explained by a shifted runtime name table, a
  map/mod/runtime injection, or by reading the wrong lifecycle candidate; what offline
  evidence can distinguish those causes without live probing?
- Can the lifecycle comparator report the exact semantic-layout fields that match while
  keeping copied passive FName chains classified as diagnostic-only?
- Do any of the four guidance-only lifecycle-adjacent targets share enough shape to cause
  false acceptance if only FName-chain drift is used; if so, which fail-closed predicate
  rejects them?
- Add reflection-scanner and lifecycle-observer tests that mutate or force post-restart
  FName drift so stale anchors fail closed and must revalidate before copied lifecycle
  output can be accepted.

Even a clean result is planning-layout evidence only. Runtime evidence remains blocked
until a separately approved runtime window produces the accepted copied lifecycle event
triplet and the approved evidence checkers accept the sibling-set bundle.

## Risks

- The worktree is already dirty; some local guardrails referenced above are uncommitted
  implementation/test state, not deployed runtime evidence.
- The accepted static report and the distinct lifecycle snapshot root anchor planning
  layout only.
- The diagnostic mismatches prove that the current passive observations are not accepted
  evidence. They do not prove the root cause of the drift.
