# 2026-06-08 SDK Runtime Bridge, Activation, ABI, And Certificate Hardening

## Scope

Lead-owned ObeliskSDK checkpoint after a compaction/resume. The priority stayed on the
complete SDK route, not server stability or publication. Standing launch authorization was
used only for passive process/log/query observation and a guarded beta notice path. No ARK
server restart, marker/env change, RCON broadcast, GitHub operation, tag, release, Plugin
Hub action, or public/stable SDK claim occurred in this checkpoint.

Strict accounting remained unchanged:

- route: `approved_runtime_evidence_missing`
- next: `approved_runtime_principal_lifecycle_evidence_bundle`
- after-runtime blocker: `identity_public_contract_gate_missing`
- SDK: `0/12`
- P0: `0/4`
- runtime/public/stable readiness: false
- source overclaims: `0`

## Live Runtime Posture

Process observation at 2026-06-08 14:25 CEST showed exactly two ARK servers:

- `arkserver2` / TheIsland, query `27016`, RCON `27021`, `ActiveEvent=Summer`
- `arkserver` / Ragnarok, query `27015`, RCON `27020`, `ActiveEvent=Summer`

No Genesis2 server was running. A passive monitor was left running as intended:

```text
PID 2072410 timeout 7200 scripts/monitor_ark_player_presence_passive.sh --interval 60 --linger-after-detect 600 --snapshot-output-root /tmp/obelisk-passive-evidence-snapshots/20260608T115401Z-player-principal-lifecycle --snapshot-monitor-log /tmp/obelisk_passive_player_monitor_20260608T115401Z-player-principal-lifecycle.log arkserver2:TheIsland arkserver:Ragnarok
PID 2072411 bash scripts/monitor_ark_player_presence_passive.sh --interval 60 --linger-after-detect 600 --snapshot-output-root /tmp/obelisk-passive-evidence-snapshots/20260608T115401Z-player-principal-lifecycle --snapshot-monitor-log /tmp/obelisk_passive_player_monitor_20260608T115401Z-player-principal-lifecycle.log arkserver2:TheIsland arkserver:Ragnarok
```

The tail at 2026-06-08 12:24 UTC still showed `players=0/70` on both maps. The latest
observer material remained partial non-evidence:

- TheIsland: `session_start_rejected` plus unresolved `session_end`, no accepted
  `session_start`
- Ragnarok: `session_start_rejected` plus unresolved `session_end`, no accepted
  `session_start`

Both were classified as `passive_tail_non_evidence` /
`partial_accepted_observer_event_triplet_candidate_non_evidence`.

## Discord Beta Bridge And Window Tooling

The direct bot helper had previously PATCHed the active beta notice in channel
`1513238083741683934`, message `1513299287927296171`; it did not use the deprecated
webhook path. The official wrapper later refused a confirmed send because the original
window start was already in the past (`approved_window_start_not_in_future`). That remains
the correct fail-closed behavior: an active notice state is communication state only, not
activation preconditions, runtime evidence, SDK progress, or permission to reuse a stale
window.

Changes integrated in this checkpoint:

- `scripts/discord_beta_bridge.py` now normalizes legacy metadata-only event rows that
  predate newer false flags and refreshes `active-notice.json` when PATCHing an existing
  message.
- `scripts/prepare_player_principal_lifecycle_beta_notice.py` preserves confirmed-send
  dry-run receipt binding, reports stale-window/active-notice decisions, imports `os` for
  the active-notice env path, and keeps stale windows blocked before invoking the helper.
- `scripts/check_discord_beta_bridge_plan.py` records the active notice reuse policy:
  reuse is communication-state-only, existing messages are PATCHed, new messages are POSTed
  only when state is missing, and active notice state never satisfies activation or
  readiness.
- `scripts/check_player_principal_lifecycle_activation_preconditions.py` and
  `scripts/prepare_player_principal_lifecycle_runtime_window_execution.py` separate
  attempted activation checks from accepted checked preconditions. Direct bot stdout and
  active-notice state are explicitly rejected as activation inputs.

Local bridge summary after the fix reported `invalid_event_count=0`, `valid_event_count=3`,
`discord_events_are_evidence=false`, and all SDK/P0/runtime/readiness/publication flags
false.

## Runtime Evidence And ABI Boundary

Runtime player-principal lifecycle logging was kept strict:

- `CheckJoinInProgress(1,0)` plus `OnLogout` without prior accepted `HandleNewPlayer(1,1)`
  stays non-evidence.
- A canonical `OnLogout` alone cannot consume the approved `session_end` budget unless the
  applicator result is approved-loggable with matched logout correlation.
- Direct/patched Discord beta notices, passive monitor ticks, copied-log presence, status
  reports, active notice state, route samples, and partial observer lines remain
  non-evidence.

Public ABI/SDK boundary hardening in this checkpoint kept debug escape hatches out of
public consumers:

- `include/obelisk/ObeliskApi.h` documents append-only `struct_size` gated ABI fields,
  owner-token scope, no identity/lookup/ResourceHandle semantics in copied seeds, and raw
  ProcessEvent default-deny behavior.
- `tests/sdk_consumer/AbiLayoutGuard.c` proves public consumers read appended fields only
  after `struct_size` covers them and no longer initializes `.CallProcessEvent`, so public
  guardrails keep that escape hatch out of examples/SDK consumers.
- ABI layout tests and SDK consumer guards keep raw ProcessEvent usage default-deny and
  non-counting.

## P0 Certificate Chain

The post-runtime P0 chain was hardened without changing progress:

- Player identity, permissions/admin, command/chat-response, and commands/replies
  promotion certificate builders now replay strict preflight/checkers and require current
  hash-bound upstream artifacts.
- `commands_replies` now rejects a command-response certificate that is not bound to the
  current identity and permissions certificates; status reports, beta notices, public
  header readiness, builder reports, and inline certificate-shaped payloads remain
  shortcuts and fail closed.
- `scripts/report_obelisk_sdk_status.py` rejects bot notice aliases such as
  `confirmed_send` and `send_performed` as progress/readiness inputs.

The identity public-contract gate was audited by a worker and had no safe patch applied;
its current tests already cover stale binding, generated/template shortcuts, and
pre-evidence non-progress behavior.

## Delegation Closure

All agents from this round were closed:

- Alpha/Kierkegaard: identity public contract gate audit, no file changes, 330 tests OK.
- Hubble: commands/replies upstream certificate cross-binding hardening, 117 tests OK
  after serial rerun.
- Lorentz: Discord beta bridge/window diagnostics; lead fixed the missing import and
  validated 76 tests OK.
- Carver: SDK status bot-notice alias guardrail; focused status tests OK.
- Earlier same-checkpoint workers for beta activation, ABI boundary, runtime status,
  promotion certificates, and applicator behavior were also closed before this handoff.

No standby sub-agent remains.

## Validation

Passed after integration:

- `PYTHONPATH=scripts python3 -m unittest scripts.test_prepare_player_principal_lifecycle_runtime_window_execution scripts.test_check_player_principal_lifecycle_activation_preconditions` - 92 tests
- `python3 -m unittest scripts.test_prepare_player_principal_lifecycle_beta_notice` - 32 tests
- `python3 -m unittest scripts.test_discord_beta_bridge` - 32 tests
- `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_prepare_player_principal_lifecycle_beta_notice scripts.test_check_discord_beta_bridge_plan` - 76 tests
- `python3 -m unittest scripts.test_check_commands_replies_public_readiness scripts.test_build_commands_replies_promotion_certificate` - 117 tests
- `python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_player_identity_public_contract_decision_record scripts.test_build_player_identity_public_contract_decision_record scripts.test_check_player_identity_public_header_gate` - 330 tests
- `python3 -m unittest scripts.test_public_sdk_guardrails` - 209 tests
- `cmake --build build --target player_principal_lifecycle_applicator_tests -j2 && ctest --test-dir build -R '^(PlayerPrincipalLifecycleApplicatorTests|AbiLayoutTests|CAbiLayoutTests|SdkConsumerAbiLayoutGuard|SdkConsumerFixtureCAbiPlugin)$' --output-on-failure` - 5 CTest tests
- `cmake --build build --target sdk_consumer_abi_layout_guard -j2 && ctest --test-dir build -R '^SdkConsumerAbiLayoutGuard$' --output-on-failure` - 1 CTest test
- `python3 -m py_compile` for touched bridge/status/certificate scripts
- `local/discord-beta-venv/bin/python scripts/discord_beta_bridge.py --summarize-events --recent-limit 8 --json`
- `python3 scripts/report_obelisk_sdk_status.py --compact`
- `git diff --check`

The combined global suite
`python3 -m unittest scripts.test_report_obelisk_sdk_status scripts.test_check_public_sdk_v1_completion scripts.test_build_v1_scoped_release_statement scripts.test_public_sdk_guardrails`
ran 635 tests but failed once before the `AbiLayoutGuard.c` `.CallProcessEvent` removal.
After that fix, the exact failing guardrail and the full public SDK guardrail suite passed.

## Result

The SDK is better prepared for the next valid player-backed evidence window, but the
route is still blocked until a checker-accepted copied approved runtime principal
lifecycle evidence bundle contains the exact triplet:

1. `session_start`
2. exact `ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`
3. matched `session_end`

After that bundle is accepted, the next blocker remains
`identity_public_contract_gate_missing`.
