# 2026-06-08 SDK Runtime Beta Bridge, Correlation, And Side-Lane Guardrails

## Summary

Checkpoint at 2026-06-08 15:24 CEST. The strict SDK route remains unchanged:

- `route=approved_runtime_evidence_missing`
- `next=approved_runtime_principal_lifecycle_evidence_bundle`
- `after_runtime_evidence=identity_public_contract_gate_missing`
- SDK `0/12`
- P0 `0/4`
- runtime/public/stable false
- source overclaims `0`

This round kept the passive runtime window open, restored the Discord beta bridge runtime
dependency in a local venv, updated the single active beta notice, and integrated four
offline SDK guardrails. No ARK server restart, RCON command, marker/env change, server
deployment, GitHub action, release tag, or publication action occurred.

## Runtime/Beta Operations

- Passive ARK monitor still active:
  `/tmp/obelisk_passive_player_monitor_20260608T124647Z-player-principal-lifecycle.log`
  with parent PID `2164532` and script PID `2164533`.
- Latest checked monitor ticks showed TheIsland/Ragnarok `players=0/70`; only stale
  partial non-evidence lifecycle material is present: exact `CheckJoinInProgress(1,0)`
  `session_start_rejected` plus unresolved `session_end`.
- Installed `discord.py 2.7.1` into ignored local venv
  `local/discord-bot-venv` after system pip rejected global install under PEP 668.
- Discord beta notice was dry-run reviewed and then sent as a `PATCH` to the existing
  active message `1513299287927296171` in channel `1513238083741683934`.
- The update used the single-message/no-flood path; repeated `@everyone` was suppressed
  on PATCH. The resulting notice remains communication metadata only.
- Discord beta bridge bot is running for a 2-hour timeout:
  `/tmp/obelisk_discord_beta_bridge_20260608T1308Z.log`, parent PID `2218766`, child PID
  `2218767`. It connected to the Discord Gateway and records only redacted metadata
  events.
- Latest local beta event summary stayed at `active_tester_alias_count=0` and
  `invalid_event_count=0`.

## Integrated Agent Work

- Agent C / C++ lifecycle internals completed and was closed. Integrated
  `MatchedLogoutCorrelation` proof into `ApplyResult`, validation stamps, dispatch, and
  approved-loggability so `SessionEndInvalidated` requires fresh matched logout
  correlation proof.
- Agent D / downstream P0 chain completed and was closed. Added a commands/replies
  regression proving a hash-bound upstream command-response certificate with a
  `package_shape_artifact.status=ready` payload blocks and does not write a certificate.
- Agent E / package/completion completed and was closed. Public SDK completion now
  rejects `tests/sdk_installed_consumer/*` as standalone SDK-consumer promotion evidence
  and removes `installed_sdk_consumer_tests` as a standalone promotion machine key.
- Agent F / side lanes completed and was closed. Dino scalar readiness now treats
  positive `package_shape`, `support_tier`, and `plugin_hub` labels/statuses as
  overclaims.

Agents A and B were shut down without final reports and without lead integration:

- Agent A owned identity public-contract/post-runtime bridge files.
- Agent B owned approved runtime lifecycle evidence checker/bundle files.

Any changes in those ownership scopes remain pending review and must not be treated as
integrated by this checkpoint.

## Validation

Lead-run validation:

- `python3 -m unittest scripts.test_check_dino_scalar_readiness scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting`: 75 OK
- lifecycle CTest regex for registry/event-dispatcher/reflection/applicator/observer: 5/5 passed
- focused public completion installed-consumer regression: 1 OK
- focused commands/replies package-shape upstream regression: 1 OK
- `python3 scripts/report_obelisk_sdk_status.py --compact`: unchanged blocked route, SDK `0/12`, P0 `0/4`, source overclaims `0`
- `git diff --check` over integrated files passed
- Discord beta bridge config valid under `local/discord-bot-venv`, notice sent by guarded dry-run receipt, and local event summary remained metadata-only.

Agent-reported validation:

- C++ lifecycle build plus 5 focused CTest entries passed.
- Downstream P0 chain suite: 412 OK.
- Public completion/package-shape focused build and CTest checks passed.
- Dino side-lane and mission/transfer/dino/tribe accounting tests passed.

## Remaining Risk

The main route is still missing the live accepted runtime bundle. The current passive
window has not observed players or a complete accepted lifecycle triplet. Identity
public-contract and runtime-evidence checker/bundle scopes have pending unintegrated
changes from shut-down agents and need a clean audit before being promoted.
