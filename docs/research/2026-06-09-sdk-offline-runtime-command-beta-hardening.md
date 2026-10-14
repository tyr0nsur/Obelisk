# 2026-06-09 SDK Offline Runtime, Command, And Beta Hardening

## Objective

Integrate the delegated SDK hardening round after compaction, close standby agents, and
validate the fastest offline path toward the complete ObeliskSDK without promoting runtime
readiness.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Local time: 2026-06-09 00:37 CEST
- Live posture checked read-only with `pgrep -af 'ShooterGameServer|arkserver'`.
- ARK processes observed: only Ragnarok `arkserver` / `ShooterGameServer` running with
  `-ActiveEvent=Summer`; TheIsland and Genesis2 were not running.
- Live operations: none. No RCON, Discord send, server restart, marker/env write, GitHub,
  commit, tag, or release operation occurred.

## Integrated Work

- Player principal runtime status/report gates reject snake/camel/dashed shortcut aliases
  for approved runtime/public/progress claims.
- Permissions/admin promotion gates reject bare readiness, runtime, support-tier,
  package-shape, beta, Discord, passive-snapshot, scoped-statement, Plugin Hub, and P0
  aliases unless exact upstream identity evidence and hash-bound promotion certificates
  exist.
- Command chat response and commands/replies gates reject nested route/runtime
  authorization aliases and stale/inline upstream certificate substitutions.
- Copied-event dispatchers preserve fallback-aware deferred `DestroyUserData` cleanup
  failure records so plugin-owned cleanup remains visible to `PluginManager` retry paths.
- Offline artifact gates require exact lifecycle target-set policy and reject duplicate
  source IDs, duplicate snapshot hashes, non-exact target names, and provenance shortcuts.
- Discord beta bridge and multi-surface beta capture tooling now model one updated
  embed/buttons operational message; all beta interaction metadata remains
  non-evidence, non-progress, non-readiness, and non-authorizing.
- Public SDK completion labels now mark the Genesis2 passive action path as historical
  diagnostic context, not current runtime posture or live capture evidence.

## Validation

- Player principal runtime evidence/report: `53 OK`.
- Static/offline artifact gate group: `495 OK`; py_compile passed for changed artifact
  scripts.
- Dispatcher/PluginManager group: CMake build passed; CTest `4/4` passed; guardrail
  script `58 OK`.
- Permissions/admin group: `217 OK` after rerunning serially; earlier concurrent fixture
  failures were repo-local tempdir races, not accepted as functional evidence.
- Command response/replies group: `423 OK`.
- Discord beta bridge/multi-surface capture group: py_compile passed; `137 OK`.
- Public SDK completion focal tests: `350 OK` before final handoff update.
- Status guardrails already observed: route remains `approved_runtime_evidence_missing`,
  SDK `0/12`, P0 `0/4`, source overclaims `0`.

## Result

Confirmed. This round closes more offline SDK gates and fixes several shortcut/alias
paths, but it does not change the public readiness state. Complete SDK remains blocked on
the checker-accepted copied runtime principal lifecycle evidence bundle containing
`session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
`session_start_rejected`, and matched `session_end`.

## Risks And Next Steps

- Keep B-style repo-local tempdir suites serial; do not run them concurrently with other
  tests that create fixture roots under `tests/core` or `tests/sdk_consumer`.
- Continue offline hardening while runtime evidence is absent.
- When runtime evidence is needed, use the standing-authorized beta/RCON workflow and keep
  one or two ARK servers running, never three.
