# Obelisk Research Notes

This directory stores reproducible investigation notes for Obelisk runtime, UE4 reflection,
ARK server operations, and plugin experiments.

Routing authority: `docs/agent-handoff/CURRENT.md` is the source of truth for active
agent routing, current next steps, and any lead-approved priority changes. This README is
a research index and evidence map only; it must not be used to override CURRENT.md,
authorize release/publication work, or recenter the active route on an older module lane.

Notes written before `OBELISK_INSTANCE_ID` may mention obsolete map-based marker files and
root-level map logs. New research should record the LinuxGSM instance id, map, ARK binary
hash, and runtime flags.

Historical module-specific notes, especially early chat reflection notes, remain indexed as
evidence trails. Treat them as examples of the common reflection and promotion-gate ladder,
not as the current product center. For contributor-facing release scope, use
`docs/STATUS.md` and `docs/RELEASE.md` plus the RC evidence path below; broad UE4
reflection, FName/GObjects expansion, and new module surface discovery are post-RC unless a
new binary hash or contradictory evidence changes the current research priority.

## Start Here

Use these notes as the current curated evidence path for the complete-SDK route and the
historical core-first RC baseline. This README is a
navigation aid, not an exhaustive inventory of every evidence note; unlisted notes may
still preserve durable evidence and should not be deleted only because they are absent
from this index.

Published RC baseline evidence lane (historical release evidence, not current routing;
current published tag: `v0.1.0-rc.2`; use the release evidence notes for ref details):

- [2026-05-28-reversing-objective-map.md](2026-05-28-reversing-objective-map.md)
- [2026-05-28-second-source-reversing-gap-matrix.md](2026-05-28-second-source-reversing-gap-matrix.md)
- [2026-05-28-second-source-core-intake-runbook.md](2026-05-28-second-source-core-intake-runbook.md)
- [2026-05-29-minimal-second-source-readiness.md](2026-05-29-minimal-second-source-readiness.md)
- [2026-05-29-public-gameplay-event-readiness-audit.md](2026-05-29-public-gameplay-event-readiness-audit.md)
- [2026-05-29-chat-message-second-source-readiness.md](2026-05-29-chat-message-second-source-readiness.md)
- [2026-05-30-rc-second-source-release-gate-check.md](2026-05-30-rc-second-source-release-gate-check.md)
- [2026-05-30-head-rc-second-source-refresh-gap.md](2026-05-30-head-rc-second-source-refresh-gap.md)

Current reflection evidence lane:

| Area | Current status | Primary notes |
| --- | --- | --- |
| FName | Binary-scoped clues accepted for current artifacts; broad table scans should reuse the reviewed root slot unless a new binary/hash contradicts it. | [2026-05-28-second-source-reversing-gap-matrix.md](2026-05-28-second-source-reversing-gap-matrix.md), [2026-05-31-fname-gobjects-offline-route.md](2026-05-31-fname-gobjects-offline-route.md) |
| GObjects | Strong internal/offline `GUObjectArray` candidate for enumeration and fixture generation; no public/runtime identity or lookup contract. For the ResourceHandle lane and the next UFunction snapshot route, reuse the canonical no-scan inputs instead of rerunning broad GObjects/core discovery on the current binary hash. | [2026-05-29-gobjects-cross-manifest-comparison.md](2026-05-29-gobjects-cross-manifest-comparison.md), [2026-05-30-gobjects-strict-consume-recapture-needed.md](2026-05-30-gobjects-strict-consume-recapture-needed.md), [2026-05-30-post-rc-offline-resourcehandle-priority.md](2026-05-30-post-rc-offline-resourcehandle-priority.md), [2026-05-31-fname-gobjects-offline-route.md](2026-05-31-fname-gobjects-offline-route.md) |
| UObject | Object fields and flags remain evidence for candidate classification; public lifecycle/validity semantics are not proven. | [2026-05-29-uobject-flags-validity-blocker.md](2026-05-29-uobject-flags-validity-blocker.md) |
| UFunction layout | Accepted only per named target set after fixture and second-source comparison; RC target sets cover the current public copied surfaces. | [2026-05-30-rc-ufunction-layout-evidence-audit.md](2026-05-30-rc-ufunction-layout-evidence-audit.md) |
| ResourceHandle | Post-RC/internal and blocked until lifecycle, runtime rejection samples, runtime serial semantics, lookup privacy, and public contract gates are proven; do not answer this blocker with more broad FName/GObjects/core/serial scans on the current binary hash. Historical serial/fullscan notes are audit evidence only; the current next blocker is approved-runtime negative samples plus serial reuse/wraparound semantics under the live-ops brief. | [2026-05-30-post-rc-offline-resourcehandle-priority.md](2026-05-30-post-rc-offline-resourcehandle-priority.md) |
| Artifact identity | Strict consume gates require complete top-level `artifact_identity` for current static-global and UObject flag-policy evidence. Normalized artifact packs additionally require `artifact-pack.manifest.json` plus matching relative `SHA256SUMS`; use the pack manifest through `--manifest`, keep normalizer stdout summaries outside the pack, and do not treat pack integrity as per-report identity or promotion evidence. The target-set catalog report from `scripts/compare_reflection_snapshots.py --list-target-sets --json` now carries `target_set_revision_schema`, `target_set_revision_source`, `target_set_revision_target_schema_filter=all`, and `target_set_revision_source_sha256` so research memory can detect stale target-set catalog reuse before treating a derived artifact as current. | [2026-05-30-artifact-identity-hardening.md](2026-05-30-artifact-identity-hardening.md) |

Historical recovery reference:

- [2026-05-29-rc-checkpoint-slicing-plan.md](2026-05-29-rc-checkpoint-slicing-plan.md)

## Tool Availability Guardrail

Research notes may record that optional static tools such as `radare2`, `rizin`, or
Ghidra headless are installed for a specific investigation, but contributor workflows and
tests must not require those tools just to validate documentation or offline artifact
hygiene. A note that uses one of them should capture `command -v`, version output when
available, exact command lines, input/output artifact hashes, and the protected-path
check result.

Optional analyzer output remains offline static evidence only. Keep projects and output
files in `/tmp`, `<offline-artifact-root>`, or another documented non-protected artifact
root; do not cite direct or symlink-resolved protected live-server paths.
If an optional tool is absent, record the absence and continue with baseline
`readelf`/`objdump` or existing provenance-gated artifacts instead of weakening tests.
If an optional tool is present, use it for bounded known-root/window confirmation; do not
use availability alone to rerun broad scans where the current evidence lane already says
to reuse canonical no-scan inputs.

Current post-RC research evidence lane (side-lane inventory for research reuse; follow
`docs/agent-handoff/CURRENT.md` for the active assignment):

- [2026-05-30-v1-core-capability-map.md](2026-05-30-v1-core-capability-map.md)
- [2026-06-02-copied-event-destroy-userdata-retry-stability.md](2026-06-02-copied-event-destroy-userdata-retry-stability.md)
- [2026-05-30-aseapi-reference-scan.md](2026-05-30-aseapi-reference-scan.md)
- [2026-05-30-nextgenplugins-reference-inventory.md](2026-05-30-nextgenplugins-reference-inventory.md)
- [2026-05-31-plugin-hub-experimental-chat-audit-template.md](2026-05-31-plugin-hub-experimental-chat-audit-template.md)
- [2026-05-30-chat-command-helper-roadmap.md](2026-05-30-chat-command-helper-roadmap.md)
- [2026-05-31-chat-command-readiness.md](2026-05-31-chat-command-readiness.md)
- [2026-05-31-commands-principal-routing-contract.md](2026-05-31-commands-principal-routing-contract.md)
- [2026-05-31-command-chat-response-thunk-orientation.md](2026-05-31-command-chat-response-thunk-orientation.md) (candidate-only static thunk orientation)
- [2026-05-31-radare2-lifecycle-smoke.md](2026-05-31-radare2-lifecycle-smoke.md) (candidate-only lifecycle window smoke)
- [2026-05-31-permissions-admin-minimum-post-identity.md](2026-05-31-permissions-admin-minimum-post-identity.md)
- [2026-05-31-operator-ingress-storage-blocker-brief.md](2026-05-31-operator-ingress-storage-blocker-brief.md)
- [2026-05-30-chat-audit-plugin-plan.md](2026-05-30-chat-audit-plugin-plan.md)
- [2026-05-29-module-surface-roadmap.md](2026-05-29-module-surface-roadmap.md)
- [2026-05-31-v02-module-priority.md](2026-05-31-v02-module-priority.md)
- [2026-05-31-v1-sdk-round-identity-static-demand-audit.md](2026-05-31-v1-sdk-round-identity-static-demand-audit.md)
- [2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md](2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md)
- [2026-06-01-aseapi-name-demand-map.md](2026-06-01-aseapi-name-demand-map.md)
- [2026-06-01-mission-transfer-dino-tribe-v1-split.md](2026-06-01-mission-transfer-dino-tribe-v1-split.md) - decomposes the umbrella Mission/Transfer/Dino/Tribe/Buff demand lane into candidate-only leaf accounting; Buff/status now has fixture-only readiness but no public/runtime/ABI/ResourceHandle/v1 claim.
- [2026-05-31-aggregate-census-product-priority.md](2026-05-31-aggregate-census-product-priority.md)
- [2026-05-29-next-targetset-discovery.md](2026-05-29-next-targetset-discovery.md)
- [2026-05-31-batch-snapshot-planner-design.md](2026-05-31-batch-snapshot-planner-design.md)
- [2026-05-29-mission-reflection-internal-readiness.md](2026-05-29-mission-reflection-internal-readiness.md)
- [2026-05-30-mission-copied-bool-observer-plan.md](2026-05-30-mission-copied-bool-observer-plan.md)
- [2026-05-29-item-compact-second-source-readiness.md](2026-05-29-item-compact-second-source-readiness.md)
- [2026-05-29-item-return-only-policy-bridge-plan.md](2026-05-29-item-return-only-policy-bridge-plan.md) (historical bridge plan; current item-return routing lives in the 2026-05-30 slice)
- [2026-05-30-item-return-only-policy-slice.md](2026-05-30-item-return-only-policy-slice.md)
- [2026-05-29-inventory-action-redacted-signature-readiness.md](2026-05-29-inventory-action-redacted-signature-readiness.md)
- [2026-05-29-transfer-second-source-readiness.md](2026-05-29-transfer-second-source-readiness.md)
- [2026-05-30-transfer-scriptstruct-booltail-refresh.md](2026-05-30-transfer-scriptstruct-booltail-refresh.md)
- [2026-05-29-transfer-copied-scalar-feasibility.md](2026-05-29-transfer-copied-scalar-feasibility.md)
- [2026-06-03-tribe-scalar-boundary-design.md](2026-06-03-tribe-scalar-boundary-design.md) (candidate-only internal Tribe scalar/control boundary; no public Tribe SDK, identity, permission enforcement ABI, runtime observer, mutation, return override, or v1 completion)
- [2026-06-04-arkserver2-runtime-sdk-fast-path.md](2026-06-04-arkserver2-runtime-sdk-fast-path.md) (historical `arkserver2` / `TheIsland` debug-target approval superseded by Ragnarok+Genesis2 passive-route facts; non-authorizing research chronology only; not public SDK readiness)
- [2026-05-30-redacted-scriptstruct-signatures.md](2026-05-30-redacted-scriptstruct-signatures.md)
- [2026-05-30-structure-return-only-policy-slice.md](2026-05-30-structure-return-only-policy-slice.md)
- [2026-05-30-structure-nonpin-copied-scalar-policy-slice.md](2026-05-30-structure-nonpin-copied-scalar-policy-slice.md)
- [2026-05-31-structure-aggregate-census-v0.md](2026-05-31-structure-aggregate-census-v0.md)
- [2026-05-30-structure-build-policy-triage.md](2026-05-30-structure-build-policy-triage.md)
- [2026-05-30-player-identity-lifecycle-plan.md](2026-05-30-player-identity-lifecycle-plan.md)
- [2026-05-31-player-identity-first-evidence.md](2026-05-31-player-identity-first-evidence.md)
- [2026-05-31-player-identity-targetset-gap.md](2026-05-31-player-identity-targetset-gap.md)
- [2026-05-31-player-identity-privacy-invalidation-contract.md](2026-05-31-player-identity-privacy-invalidation-contract.md)
- [2026-05-31-planning-layout-intake-contract.md](2026-05-31-planning-layout-intake-contract.md)
- [2026-05-31-player-identity-offline-pack-preflight.md](2026-05-31-player-identity-offline-pack-preflight.md)
- [2026-05-31-player-identity-static-admin-thunks.md](2026-05-31-player-identity-static-admin-thunks.md)
- [2026-05-31-player-identity-static-target-orientation.md](2026-05-31-player-identity-static-target-orientation.md)
- [2026-05-31-player-identity-static-target-orientation.json](2026-05-31-player-identity-static-target-orientation.json)
- [2026-06-01-player-principal-offline-to-runtime-plan.md](2026-06-01-player-principal-offline-to-runtime-plan.md)
- [2026-06-01-player-principal-runtime-capture-plan.md](2026-06-01-player-principal-runtime-capture-plan.md)
- [2026-06-01-player-identity-runtime-capture-readiness-checklist.md](2026-06-01-player-identity-runtime-capture-readiness-checklist.md)
- [2026-06-04-lifecycle-anchor-fname-drift-delta.md](2026-06-04-lifecycle-anchor-fname-drift-delta.md) - records lead5 passive lifecycle FName drift as diagnostic-only non-evidence (`accepted=0`, `diagnostics=36`, `rejected=0`, `process_control=none`) and preserves the no-restart posture while players are connected.
- [2026-06-06-player-principal-lifecycle-evidence-feasibility.md](2026-06-06-player-principal-lifecycle-evidence-feasibility.md) - concise player-principal lifecycle anchor digest and Worker 6 offline route audit: `HandleNewPlayer(1,1)` start, exact `CheckJoinInProgress(1,0)` rejected start, `OnLogout` end, superseded/non-evidence `HandleNewPlayer` rejected tuples, `K2_PostLogin` rejection, all-six planning gap, passive/diagnostic non-evidence boundary, and the blocked-route conclusion that exact `CheckJoinInProgress(1,0)` remains the fastest valid route while broad diagnostics/map changes/offline layout discovery are not primary next actions.
- [2026-06-07-checkjoin-runtime-evidence-gap.md](2026-06-07-checkjoin-runtime-evidence-gap.md) - narrow audit, post-patch runtime plan, and 2026-06-08 offline/static tooling checkpoints for the current `CheckJoinInProgress` gap: strict selector/status/runner/copy/runtime-window tooling now prepares analyzer -> triplet selector -> preflight -> checker evidence flow, Discord bot tester workflow metadata is non-evidence, the three triplet source registrations cluster at registrar `0x1ccc140` with `CheckJoinInProgress` byte-checked as rejected-start orientation only, and `approved_runtime_evidence_missing` remains active until an accepted copied `CheckJoinInProgress(1,0)` bundle passes the checker chain.
- [2026-06-08-player-principal-post-apply-evidence-log-budget.md](2026-06-08-player-principal-post-apply-evidence-log-budget.md) - runtime/SDK integration checkpoint: approved player-principal lifecycle evidence logging now reserves per-role budget only after safe apply/correlation status, so an unmatched canonical `OnLogout` cannot consume the single `session_end` approved-evidence slot before the matched logout; the same checkpoint hardened downstream promotion-certificate surface hashes, identity certificate hash policy, and permissions/command response public-header alias scans while keeping SDK `0/12`, P0 `0/4`, and source overclaims `0`.
- [2026-06-08-sdk-runtime-bridge-activation-abi-certificate-hardening.md](2026-06-08-sdk-runtime-bridge-activation-abi-certificate-hardening.md) - supervised SDK checkpoint after resume: passive runtime monitor stayed on TheIsland/Ragnarok with only partial non-evidence and no restarts, bot-first beta bridge/window activation tooling was hardened around active-notice reuse and stale-window rejection, public ABI/consumer guards kept raw ProcessEvent and `CallProcessEvent` out of public examples, P0 promotion certificates gained stricter hash-bound upstream chain checks, all agents were closed, and route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-focused-runtime-correlation-p0-guardrails-1500.md](2026-06-08-sdk-focused-runtime-correlation-p0-guardrails-1500.md) - focused SDK checkpoint: passive monitor state remains non-evidence, approved-evidence checker rejects stray beta notice sidecars, C++ lifecycle apply/correlation proof is stricter, installed C ABI consumers clear copied API state on invalid context, structure side-lanes and P0 promotion builders reject stale/shortcut artifacts, five agents were integrated, one identity-public-contract agent was shut down without integration, no live mutation/restart/RCON/Discord/release operation occurred, and strict status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-runtime-beta-bridge-correlation-side-lane-1524.md](2026-06-08-sdk-runtime-beta-bridge-correlation-side-lane-1524.md) - SDK checkpoint: Discord beta bridge dependency installed in ignored local venv, active beta notice PATCHed through dry-run receipt and bot run started for 2h, passive monitor stayed open with no players, C++ matched-logout proof, completion installed-consumer non-promotion, commands/replies package-shape upstream rejection, and Dino package/support/plugin labels were hardened; two agents were shut down without integration, no ARK restart/RCON/marker/env/release operation occurred, and strict status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-focused-offline-runtime-evidence-hardening-1602.md](2026-06-08-sdk-focused-offline-runtime-evidence-hardening-1602.md) - SDK-focused checkpoint: standing-authority beta notices, Discord beta bridge embeds/buttons, multi-surface beta capture source metadata, runtime evidence bundle sidecar rejection, identity public-contract template currentness, active/passive monitor non-progress accounting, and lifecycle dispatcher/applicator validation were integrated or verified; all six agents closed, no live/server/Discord/release operation occurred, strict status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`, and full completion remains blocked by an external structure-build-policy alias if required.
- [2026-06-08-sdk-structure-beta-runtime-p0-hardening-1629.md](2026-06-08-sdk-structure-beta-runtime-p0-hardening-1629.md) - SDK hardening checkpoint: structure build-policy offline intake now accepts the current build-policy lane with `blockers=[]` while staying non-counting, standing-authority beta notice send scope is restored for guarded bot sends without SDK/evidence claims, stale active notices reject overclaim aliases, runtime evidence copy/status metadata and P0 promotion-certificate bindings are stricter, all six agents closed, no live/server/Discord/release operation occurred, and strict status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-sdk-runtime-evidence-identity-abi-bridge-accounting-1737.md](2026-06-08-sdk-runtime-evidence-identity-abi-bridge-accounting-1737.md) - SDK acceleration checkpoint: runtime evidence sidecars are copied-log path/SHA bound, player identity public-contract source hashes are stricter, C ABI/package consumers reject raw ProcessEvent/CallProcessEvent readiness aliases, lifecycle apply stamps bind exact copied observations, beta bridge button interactions are local/ephemeral/non-evidence, one duplicate Discord bridge process was closed leaving one persistent bridge, all six agents closed, no ARK restart/RCON/marker/env/release operation occurred, completion `431 OK`, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-sdk-p0-runtime-evidence-closure-hardening-1850.md](2026-06-08-sdk-p0-runtime-evidence-closure-hardening-1850.md) - SDK checkpoint: runtime evidence closure commands, static exact-triplet orientation, beta bot channel gating, permissions/admin, command/chat response, commands/replies, and public completion accounting were integrated; the lead fixed path-summary metadata propagation so the Ragnarok passive complete triplet is explicitly historical diagnostic non-evidence; all six agents closed, final completion/status/release suite `431 OK`, no ARK restart/RCON/Discord send/marker/env/release operation occurred, and route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-theisland-player-principal-window-171142.md](2026-06-08-theisland-player-principal-window-171142.md) - standing-authorized TheIsland runtime window `20260608T171142Z`: bot beta notice PATCHed in the bidirectional channel, installed wrapper refreshed, preflight passed, `SaveWorld` succeeded, only `arkserver2` restarted, fresh observer enabled inside the window, bounded passive monitor started, all six agents closed, the non-evidence beta notice sidecar was moved to the report dir so the exact evidence sibling-set stays clean, and strict SDK status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4` until the copied sibling-set bundle checker accepts `session_start`, exact `CheckJoinInProgress(1,0)`, and matched `session_end`.
- [2026-06-08-sdk-offline-terminal-gate-runtime-watch-1932.md](2026-06-08-sdk-offline-terminal-gate-runtime-watch-1932.md) - offline SDK P0 terminal-gate checkpoint while TheIsland monitor waits: all four new agents closed, three shut down without integration, commands/replies terminal certificate hardening accepted after lead rerun, route-gate accepted, compact SDK status unchanged at `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-sdk-offline-single-player-pack-abi-watch-1952.md](2026-06-08-sdk-offline-single-player-pack-abi-watch-1952.md) - offline SDK checkpoint while TheIsland monitor waits: single-player full-sequence multi-surface worksheet added and checker-bound as candidate-only/non-evidence, package-shape ABI/example guardrails lead-validated, Singer's read-only reversing audit recorded the `CheckJoinInProgress` observer-only rejected-start split, all six agents closed, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-sdk-offline-lifecycle-target-split-parallel-lanes-2007.md](2026-06-08-sdk-offline-lifecycle-target-split-parallel-lanes-2007.md) - offline SDK checkpoint while TheIsland monitor waits: lifecycle static report now splits anchor-binding versus triplet-source target sets, dependent planning manifests were regenerated and verified, lifecycle next-action planner/runner exposes blocked parallel offline lanes for active/expired windows, CheckJoin drift parity gained fail-closed diagnostics, all six agents closed, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- [2026-06-08-sdk-scoped-8of8-mission-helper-stabilization-2121.md](2026-06-08-sdk-scoped-8of8-mission-helper-stabilization-2121.md) - SDK scoped-release/accounting checkpoint: active scoped release statement/status/tests now use `8/8` bookkeeping-only rows, mission/transfer/dino/tribe/buff helper selects the canonical mission umbrella row before scanning claims, current manifest route is `manifest_umbrella_excluded` while candidate-only tests use explicit fixtures, all audit agents closed, no live/server/Discord/release operation occurred, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-parallel-lanes-p0-guardrails-2144.md](2026-06-08-sdk-offline-parallel-lanes-p0-guardrails-2144.md) - offline SDK checkpoint: runner-blocked parallel lanes, identity post-runtime checklist policy, generated bundle-report overclaim rejection, terminal certificate non-counting guards, package-shape raw-PE/CallProcessEvent guardrails, all-six planning-gap meaning fields, and scoped `8/8` fixture semantics were integrated; no live/server/Discord/release operation occurred, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-post-identity-chain-runner-hardening-2212.md](2026-06-08-sdk-offline-post-identity-chain-runner-hardening-2212.md) - offline SDK checkpoint: four-lane runner drift detection, identity public-contract non-promotion guards, runtime evidence/observer adjacent-schema rejection, static exact-triplet orientation guards, permissions/admin and command-route shortcut rejection, ResourceHandle public-contract alias rejection, and reviewed identity decision-record source-hash rebinding; all six agents closed, no live/server/Discord/release operation occurred, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-runtime-p0-alias-hardening-2245.md](2026-06-08-sdk-offline-runtime-p0-alias-hardening-2245.md) - offline SDK checkpoint: runtime evidence sidecar alias rejection, generated bundle diagnostic-sidecar false-positive fix, stale live-context marking, post-runtime identity bridge constraints, and P0 alias hardening across permissions/admin, command route/replies, ResourceHandle, offline artifact gate, and status accounting; all six agents closed, no live/server/Discord/release operation occurred, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-one-server-runtime-p0-guardrails-2355.md](2026-06-08-sdk-one-server-runtime-p0-guardrails-2355.md) - SDK/live-ops checkpoint: TheIsland `arkserver2` was stopped after local query showed `0/70`, leaving Ragnarok `arkserver` as the only ARK server process; six agents closed after ABI/example, side-lane, item/transfer, dispatcher cleanup, artifact-gate, and status/release guardrails; checker `202 OK`, bundle builder `127 OK`, completion `350 OK`, `git diff --check` clean, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-09-sdk-offline-runtime-command-beta-hardening.md](2026-06-09-sdk-offline-runtime-command-beta-hardening.md) - SDK checkpoint after compaction: all remaining standby agents closed, only Ragnarok observed running, no live/server/RCON/Discord/release operation occurred, permissions/admin `217 OK`, commands/replies `423 OK`, beta bridge pack `137 OK`, dispatcher CTest `4/4`, artifact gate `495 OK`, route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-09-sdk-offline-abi-static-runtime-chain-hardening.md](2026-06-09-sdk-offline-abi-static-runtime-chain-hardening.md) - SDK checkpoint: runtime evidence closure, identity public-contract binding, permissions/admin and command chain promotion certificates, ABI/package examples, dispatcher cleanup retry, offline artifact gates, release-scope docs, and post-RC mission/transfer runtime-target exclusion were integrated; release scope `62 OK`, CTest `4/4`, runtime evidence `457 OK`, permissions/commands `633 OK`, status remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-fast-path-post-identity-chain-hardening-1343.md](2026-06-08-sdk-offline-fast-path-post-identity-chain-hardening-1343.md) - offline SDK checkpoint: runtime evidence status now exposes a non-authorizing fast-path view for first blocker/first helper, identity header/contract, permissions/admin, command response, commands/replies, and public SDK consumer/C ABI boundaries were hardened, five agents were integrated, Zeta was closed without integration, no live/Discord/server/release operation occurred, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-public-boundary-runtime-contract-hardening-1310.md](2026-06-08-sdk-offline-public-boundary-runtime-contract-hardening-1310.md) - offline SDK hardening checkpoint: public/debug raw ProcessEvent leakage was removed from generic SDK consumers, approved runtime evidence bundle and public contract/header/completion/command gates were hardened against shortcut aliases, the identity decision-record checker `TypeError` was fixed, all six agents were closed, no live/Discord/server/release operation occurred, and the route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-p0-chain-beta-pack-hardening-1133.md](2026-06-08-sdk-offline-p0-chain-beta-pack-hardening-1133.md) - offline SDK/P0 checkpoint: identity decision-record validity is split from accepted runtime binding, permissions/admin requires current hash-bound identity plus own fail-closed contracts, command/chat response and commands/replies reject stale/shortcut certificate aliases, status start/end inputs cannot advance the route, and the multi-surface beta pack no-flood metadata validates as candidate-only; Nash/Volta were shut down without integration and all remaining agents were closed, no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-final-gate-discord-summary.md](2026-06-08-sdk-offline-final-gate-discord-summary.md) - offline SDK acceleration checkpoint: commands/replies final-gate promotion-certificate builder, commands/replies public-header token hardening, package-shape/example README non-claim guardrails, local Discord beta event summaries, and completion-checker source/report alias hardening; all six agents closed, no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, and source overclaims `0`.
- [2026-06-08-sdk-offline-gate-hardening-round.md](2026-06-08-sdk-offline-gate-hardening-round.md) - offline SDK integration checkpoint: multi-surface beta capture worksheet, bot-first editable beta notice/button guardrails, commands/replies final-gate status, gapped lifecycle sequence coverage, planning-manifest provenance-only demotion, and runtime applicator exact-token evidence-budget validation; all six agents closed, no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, and source overclaims `0`.
- [2026-06-08-sdk-offline-hardening-round-0919.md](2026-06-08-sdk-offline-hardening-round-0919.md) - offline SDK hardening checkpoint: public-contract readiness now requires a bound reviewed decision record after runtime evidence, decision-record/bridge strict-checker replay rejects stale evidence, duplicate start/end ready-log copies are blocked, synthetic lifecycle vocabulary now mirrors `CheckJoinInProgress(1,0)`, public completion requires terminal commands/replies certificate and canonical certificate bindings, and Discord beta summary is local-only; no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-hardening-round-1004.md](2026-06-08-sdk-offline-hardening-round-1004.md) - offline SDK hardening checkpoint: deterministic candidate-only multi-surface beta pack manifests, one-message/no-flood beta bridge controls, full-chain commands/replies certificate builder, public completion terminal-certificate/binding hardening, status final-gate inline certificate demotion, and duplicate start/end selector demotion to diagnostic-only selection; all six agents closed, no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-runtime-observer-hardening-1026.md](2026-06-08-sdk-offline-runtime-observer-hardening-1026.md) - offline SDK/runtime hardening checkpoint: `HandleNewPlayer(1,0)` no longer builds copied lifecycle evidence, diagnostic-only copies use a non-event role, runtime-window/closure/status helpers keep diagnostic/passive material non-evidence, and public docs preserve the non-claim boundary; all six agents closed, no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-08-sdk-offline-reflection-applicator-hardening-1044.md](2026-06-08-sdk-offline-reflection-applicator-hardening-1044.md) - offline SDK/runtime hardening checkpoint: exact `CheckJoinInProgress(1,0)` reflection now proves a no-drift state, mixed Ragnarok/TheIsland drift chains are rejected, applicator dispatch/log gates require apply-validation provenance plus exact function/outer indices, static/runtime approved-evidence checkers keep diagnostic/FName drift material zero-credit, and the bot-first beta bridge stays dry-run/single-message/no-claim; all six agents closed, no live/Discord/server/release operation, route still `approved_runtime_evidence_missing`.
- [2026-06-08-sdk-offline-start-end-noncompletion-hardening-1113.md](2026-06-08-sdk-offline-start-end-noncompletion-hardening-1113.md) - offline SDK/runtime hardening checkpoint: C++ observer/applicator regressions prove start+matched-end remains incomplete without exact `CheckJoinInProgress(1,0)` rejected-start, start/end/status checkers keep partial/beta/window/copied-log material non-evidence until the exact sibling-set bundle is checker-accepted, and identity promotion/post-runtime bridge artifacts require same-runtime-evidence hash binding; no live/Discord/server/release operation, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- [2026-06-07-theisland-player-principal-window-125115.md](2026-06-07-theisland-player-principal-window-125115.md) - lead-owned TheIsland runtime window `20260607T125115Z`: accepted fresh-window `HandleNewPlayer(1,1)` `session_start` and matched `OnLogout` `session_end`, but post-window copy dry-run stayed blocked with `ready_to_copy=false` because exact `CheckJoinInProgress(1,0)` `session_start_rejected` was missing; no log was copied, bundled, promoted, or counted as SDK/P0 progress.
- [2026-06-07-player-principal-long-passive-window-workflow.md](2026-06-07-player-principal-long-passive-window-workflow.md) - records the current long passive-window workflow clarification: standing authority is not evidence/readiness, exact copied lifecycle triplet evidence is still required, the `20260607T132020Z` TheIsland window produced start/end only and stayed blocked missing `session_start_rejected`, broad windows should remain open while players may enter, tooling now targets 15-minute to 2-hour windows, connected-player sessions should not be cut merely to broaden observer coverage, live Ragnarok `28416`/`28548` and `28419/21315/22969/28517...` FName drift remains diagnostic non-evidence, safe truncated mismatch summaries are analyzer-only, and bundle/checker closure suites should run serially.
- [2026-06-07-discord-beta-bridge-ops-plan.md](2026-06-07-discord-beta-bridge-ops-plan.md) - offline plan and scaffold checkpoint for a two-way beta tester Discord bridge: the existing webhook helper remains outbound-only, interactive tester coordination should use a least-privilege bot with slash commands/buttons and redacted local JSONL events, token values are never recorded or repeated, live run preflight requires a rotated-token UTC attestation plus `discord.py`, event writes fail closed on raw fields/secret-shaped strings/authorization-progress-evidence aliases, and all bridge events remain communication metadata only, not runtime evidence, live-op authority, SDK/P0 progress, public readiness, or stable readiness.
- [2026-06-02-sdk-complete-priority-map.md](2026-06-02-sdk-complete-priority-map.md) - accumulated complete-SDK blocker ledger; read with its current route boundary, where old `lifecycle_anchor_first_evidence_provenance_unbound` validation lines are historical only and the active default blocker is `approved_runtime_evidence_missing`.
- [2026-06-03-p0-runtime-evidence-gate-snapshot.md](2026-06-03-p0-runtime-evidence-gate-snapshot.md) - current P0 gate snapshot after same-day SDK guardrail/non-claim rounds; route remains `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, and `stable_claim_allowed=false`.
- [2026-06-04-sdk-route-claim-hardening.md](2026-06-04-sdk-route-claim-hardening.md) - six-agent offline hardening checkpoint for request approval aliases, identity public-contract overclaims, bound-route text claims, SDK release-statement accounting, Buff/status umbrella accounting, and Logger path aliases; route remains `approved_runtime_evidence_missing`.
- [2026-06-01-player-identity-private-candidate-contract.json](2026-06-01-player-identity-private-candidate-contract.json) - candidate-only private planning artifact for copied opaque principal shape; no public header, capability bit, callback ABI, lookup, permissions/admin, commands/replies, storage, mutation, return override, runtime readiness, public SDK readiness, or v1 claim.
- [player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json](player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json) - candidate-only public ABI preflight routing artifact for `obelisk.player_identity.v1`; verifies accepted review inputs while keeping public header symbols, capability bits, callback ABI, promotion, SDK readiness, runtime readiness, and v1 completion false.
- [2026-06-01-static-offline-sdk-v1-command-player-audit.md](2026-06-01-static-offline-sdk-v1-command-player-audit.md)
- [2026-05-31-native-ufunction-registration-static-discovery-plan.md](2026-05-31-native-ufunction-registration-static-discovery-plan.md)
- [2026-05-31-arktribute-playerdata-identity-boundary.md](2026-05-31-arktribute-playerdata-identity-boundary.md)
- [2026-05-28-fname-index-manifest-plan.md](2026-05-28-fname-index-manifest-plan.md)
- [2026-05-31-fname-gobjects-offline-route.md](2026-05-31-fname-gobjects-offline-route.md)
- [2026-05-29-ghidra-fuobjectarray-field-window-probe.md](2026-05-29-ghidra-fuobjectarray-field-window-probe.md)
- [2026-05-30-gobjects-strict-consume-recapture-needed.md](2026-05-30-gobjects-strict-consume-recapture-needed.md)
- [2026-05-29-resource-handle-revalidation-evaluator.md](2026-05-29-resource-handle-revalidation-evaluator.md)
- [2026-05-29-resource-handle-nonzero-revalidation.md](2026-05-29-resource-handle-nonzero-revalidation.md)
- [2026-05-29-uobject-flags-fullscan.md](2026-05-29-uobject-flags-fullscan.md)
- [2026-05-29-weak-helper-flag-polarity.md](2026-05-29-weak-helper-flag-polarity.md)
- [2026-05-29-offline-evidence-canonicality.md](2026-05-29-offline-evidence-canonicality.md)
- [2026-05-29-resource-identity-feasibility.md](2026-05-29-resource-identity-feasibility.md)
- [2026-05-29-uobject-flags-validity-blocker.md](2026-05-29-uobject-flags-validity-blocker.md)
- [2026-05-29-fuobjectitem-serial-lifetime-audit.md](2026-05-29-fuobjectitem-serial-lifetime-audit.md)
- [2026-05-29-resource-handle-flag-policy-candidate.md](2026-05-29-resource-handle-flag-policy-candidate.md)
- [2026-05-30-post-rc-offline-resourcehandle-priority.md](2026-05-30-post-rc-offline-resourcehandle-priority.md)
- [2026-05-30-artifact-identity-hardening.md](2026-05-30-artifact-identity-hardening.md)
- [2026-05-30-static-build-policy-tooling.md](2026-05-30-static-build-policy-tooling.md)
- [2026-05-29-reflection-inventory-pack-smoke.md](2026-05-29-reflection-inventory-pack-smoke.md)

Keep this lane broad enough to preserve the full modding surface: players, tribes, dinos,
items, structures, permissions, commands, admin, transfers, missions, timers, storage,
economy, homes, teleport, safe zones, and mobility.
Focused evidence lanes such as copied chat, `ResourceHandle` blocker work, and
`APrimalStructure.IsAllowedToBuild` triage are inputs to that broader map, not a narrowed
v1 product center or SDK promise.

Read the current v1 route through three gates:

- Routing snapshot: the table below is a research index for next work, not live agent
  routing, release authorization, or a public compatibility roadmap. Current task routing
  belongs outside this research index.
- Evidence gate: accepted target-set, consume-gate, or layout evidence can justify
  fixture/internal work only for the named slice. It does not promote adjacent identity,
  lookup, mutation, return override, runtime observer, or SDK surfaces.
- SDK boundary: public v1 APIs stay copied, redacted, C/POD, owner-token scoped, and
  capability-discovered. ArkApi/AseApi material remains a names/demand reference only,
  not an architecture, ergonomics, behavior, or implementation reference.
  ArkServerApi/AseApi/NextGenPlugins material is never authority for porting targets,
  API ergonomics, wrapper semantics, command parser behavior, timer behavior, return
  semantics, return override semantics, support-tier classification, offsets, layouts,
  ABI, schemas, constants, or source code.

Historical notes and fixture paths may use labels such as `sdk_buffs`, `sdk_dinos`,
`sdk.tribes`, or `sdk.transfers`. In this research tree those labels are snapshot or
target-set namespaces only. They are not public SDK module names, ABI commitments,
runtime hooks, callback families, or permission to expose UE object identity.
Likewise, `promotion_gate.ready=true`, `accepted targets`, and `candidate` in
module-specific notes mean offline evidence readiness for the named layout or artifact
gate only. They do not make the named UE functions callable or usable plugin functions,
and they do not authorize public SDK surfaces, runtime observers, hooks, mutation, return
overrides, lookup, identity, or raw UE pointer access.
The named `planning-layout-intake` contract is even narrower: it is planning-only and
consume-only for closed layout target sets, currently oriented around player identity
planning. It is not a promotion gate and must keep `promotion_ready=false`,
`public_sdk_ready=false`, `runtime_ready=false`, and `release_readiness=false`.

For the current inventory/mission route, the offline hardening target is boundary
preservation. Inventory may use only the already promoted copied/redacted
`GameplayPolicyEvent` lane or candidate/internal-only planning notes. Mission remains
internal/test-only copied-bool planning. Neither lane is a public Inventory SDK, public
Mission SDK, new capability family, identity/lookup contract, mutation path, return
override, or server-observation approval.

Side-lane accounting guardrail: Inventory copied-signal stability, Mission copied-bool
fixture-boundary, Transfer `bAccept`, Transfer ScriptStruct readiness, Buff fixture
manifest/source binding, Dino scalar readiness, route post-evidence P0 lock simulation, and
Mission/Transfer/Dino/Tribe umbrella accounting remain candidate-only/non-authorizing.
The 2026-06-05 offline artifact/side-lane audit only tightened explicit
`offline_only`, `not_artifact_gate`, and internal-planning markers on these local reports.
They cannot be read as SDK completion, runtime readiness, live ops approval, P0 progress,
approved runtime evidence, public SDK readiness, stable readiness, SDK/P0/runtime
progress, public/stable progress, or v1 completion, and they do not authorize live ops or
server/log reads.
Artifact gates must also reject positive `*_readiness_satisfied` aliases on side-lane or
planning reports, including stale `second_source_readiness_satisfied=true` fields; those
fields are not promotion/public SDK evidence.
Mission/Transfer/Dino/Tribe/Buff umbrella leaf accounting must carry explicit false
SDK/P0/runtime/v1 readiness flags plus zero complete-SDK, P0 dependency-chain, and v1
completion progress counters even when the focused checker is accepted for internal
planning. Tribe scalar and Buff/status leaf summaries are no exception.

Current-turn exact scope is required for live server/log reads, marker/env changes,
Discord sends, and runtime capture unless both `docs/agent-handoff/CURRENT.md` and
`docs/agent-handoff/COMPACT_CONTEXT.md` record an active standing launch authority for
the same named ObeliskSDK debug/evidence operation and safety limits. That standing
authority survives compaction until revoked, but it is authorization only: passive
observations, beta tester notices, request packs, receipts, research notes, copied-log
analysis, Historical TheIsland/Ragnarok/Genesis2 material, public reachability,
install/package success, support-tier labels, validation passes, agent-closure notes,
`.codex` cleanup, and package-shape markers remain timestamped context or diagnostics
only. They do not count as runtime evidence, approved in-game evidence, SDK/P0 progress,
public SDK readiness, publication, stable claims, stable v1 wording, or Plugin Hub
publication.

Player-backed evidence-window notice is executable, not passive. If current-turn approval
names the beta testers Discord path or another player notice path, the approved
dry-run-checked notice must be sent before activation, restart, runtime capture, or
passive player-backed waiting begins. Request packs, receipts, and research notes that
only document a notice path, leave it drafted, or leave it documented but not sent are not
enough for the window or its evidence intake.

Notice artifacts are also secret-free and non-authorizing. `player_notice_action`, notice
dry-run output, rendered notice text, and sent-notice attestation prove only communication
execution. They are not runtime evidence, live-ops approval, SDK/P0 progress, public
readiness, public SDK readiness, runtime readiness, publication, or complete/stable SDK
status. Do not put Discord webhook URLs, webhook tokens, secret environment assignments,
or secret-bearing dry-run output into research docs, receipts, sidecars, or Git; keep only
non-secret notice path/channel, dry-run status, send action, send timestamp, and
reviewer/operator scope.
Notice actions have the same boundary: they are not evidence-window approval, runtime
evidence, public readiness, or SDK progress.

Approved evidence intake and copied bundles are consume-only and non-authorizing. Even a
checker-accepted approved runtime bundle can answer only the current
`approved_runtime_evidence_missing` blocker; it cannot claim SDK/P0 progress, public SDK
readiness, runtime readiness, public/stable progress, live-ops approval, publication, or
complete/stable SDK status.

Request packs, package-shape/install success, exact-version
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
package installs, support-tier labels, prior approvals, historical live approvals/map
names, historical approvals/map names, passing local tests, local validation results,
the latest validation pass, six-agent closure notes, `.codex` cleanup, scoped release
statements, release-readiness passes, copied evidence bundle shape,
closure requests, evidence-closure reports, Discord notice drafts, CMake/header checks,
public reachability, passive observation, passive monitor output, passive monitors,
passive summaries, passive snapshots, passive triplets, diagnostic candidate lines,
diagnostic logs, status reports, status-helper route reports, `progress_normalization_trace`,
source_overclaim diagnostics, and `source_overclaim_total_flag_count=0` are accounting or
diagnostic artifacts only. They do not move SDK, P0, or v1 counters and cannot be reused
as complete SDK readiness, current-turn live-op scope, runtime evidence, SDK evidence,
approved in-game evidence, public SDK readiness, runtime readiness, live-op authorization,
Discord authorization, publication authority, Plugin Hub readiness, live-ops approval,
package-shape/public package readiness, stable claims, stable SDK claims, or a stable SDK claim. The current
passive-route facts remain non-evidence too: the Ragnarok role-complete passive triplet
is diagnostic-only/passive and is not the accepted copied approved sibling-set bundle,
while Genesis2 still lacks `session_end`. The research-index default remains SDK `0/12`, P0
`0/4`, `stable_claim_allowed=false`, and `approved_runtime_evidence_missing` until the
executable completion gate and approved runtime evidence checkers say otherwise.

Compaction invariant for future agents: no complete approved in-game evidence exists yet;
beta notice artifacts and `player_notice_action` attestations are communication artifacts,
not evidence; passive diagnostics are diagnostic-only/non-evidence; no standby sub-agent
remains from the recorded supervised rounds; closed-agent accounting and `.codex` cleanup
are process hygiene only; and these research notes grant no current-turn server
authorization, including live reads of server state or logs, marker/env changes, Discord
sends, or runtime capture.

Current v1 research indexing keeps the full modding surface visible, but the active order
is SDK-complete first: player identity/principal evidence, permissions/admin query-only
groundwork, then command response, then commands/replies. Plugin Hub notes are archived boundaries, not
active priority before SDK completion. `GameplayPolicyEvent` backing evidence and mission
copied-bool internal planning remain side lanes only.
Next v1 research round: keep the complete-SDK blocker route first, not hub foundation
first.
Use [2026-05-31-v02-module-priority.md](2026-05-31-v02-module-priority.md) for the
selected Mission copied-bool internal lane,
[2026-05-31-player-identity-first-evidence.md](2026-05-31-player-identity-first-evidence.md)
and
[2026-05-31-player-identity-targetset-gap.md](2026-05-31-player-identity-targetset-gap.md)
and
[2026-05-31-player-identity-privacy-invalidation-contract.md](2026-05-31-player-identity-privacy-invalidation-contract.md)
for the still-blocked identity lane, and
[2026-05-31-batch-snapshot-planner-design.md](2026-05-31-batch-snapshot-planner-design.md)
for pre-target-set focal snapshot planning. Do not repeat broad discovery on the current
binary, do not promote new SDK modules, and do not recenter the roadmap on chat.

`GameplayPolicyEvent` backing currently means exactly three copied-data lanes:
`structure-observer-intake`, `minimal-second-source-intake`, and
`item-return-only-policy-slice`. Preserve the boundary as copied `field_mask`,
`bool_values`, and `int32_values` only. Do not widen this phrase into public Inventory
SDK, Items SDK, `StructureEvents`, build-policy API, identity/lookup, `ResourceHandle`,
mutation, return override, runtime observation, or raw UE parameter access.

Plugin Hub contributor intake uses the same three buckets as the public matrix, but it is
parked until SDK completion. Its archived buckets remain: future release-supported seed
after SDK completion for lifecycle/config/logging, descriptor/catalog, timer, packaging;
experimental pattern only for passive copied chat or copied policy examples; blocked
backlog for commands, identity, persistence, operator ingress, mutation, enforcement,
`ResourceHandle`, raw UE access, or cross-instance state. ArkApi/AseApi/NextGenPlugins
demand can keep a blocked idea visible, but it cannot change the support tier without a
named promotion gate.

Current v1 research lane snapshot from the current notes:

| Lane | Current state | Use next |
| --- | --- | --- |
| Complete-SDK route: identity/principal -> permissions/admin -> command response -> commands/replies | Fact: current blocker chain requires player identity before permissions, command response, and commands/replies. | Keep active rounds on SDK blockers; Plugin Hub work stays parked. |
| Passive copied chat notification/parsing | Fact: minimal copied `ChatMessageEvent` exists; plugin-local parsing is only an experimental copied-pattern lane. | Treat chat as one small copied notification lane, not the v1 module center. Keep sender identity, permissions, replies/send-chat, moderation, and command SDK blocked until copied identity and authority are promoted. |
| Inventory lane | Fact: current inventory evidence is promoted publicly only through copied/redacted `GameplayPolicyEvent` fields; copied-signal stability remains side-lane accounting, not SDK/P0 progress. | Preserve copied scalar observation and fixture gates without publishing a public Inventory SDK, item identity, lookup, mutation, return override, or `ResourceHandle`. |
| Structures lane | Fact: structure access/demolish/variant/activation/PIN/seat policy slices back current copied gameplay policy. Build placement remains second-wave. | Keep structure target sets layout-only unless a strict readiness note promotes a named copied surface; do not publish StructureEvents, build-policy SDKs, return override, identity, lookup, or raw params. |
| Items lane | Fact: item return-only evidence supports three copied `GameplayPolicyEvent` kinds; item detail remains internal/evidence-only. | Preserve item return-only evidence without publishing Items SDKs, Inventory SDKs, item identity, mutation, return override, or `ResourceHandle`. |
| Players identity lifecycle | Candidate-only high-value blocker for future commands, permissions, economy, and moderation. The admin-surface fixture gap is closed: the lane has a non-protected complete `obelisk.core-dump-evidence-pack.v1`, an accepted `obelisk.reflection-inventory-pack.v1`, 12/12 `players-identity-lifecycle-intake` coverage, committed `ShooterPlayerController.ServerListPlayers`/`ShooterPlayerController.ServerKickPlayer` fixtures as admin targets, not lifecycle anchors, and source-bound repo-local lifecycle/principal consume manifests for `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`. Current rejected-start routing accepts only exact copied `ShooterGameMode.CheckJoinInProgress(1,0)`; historical `HandleNewPlayer` rejected tuples are superseded non-evidence. The default aggregate route now consumes those source-aligned manifests and blocks at `approved_runtime_evidence_missing`; with accepted approved runtime evidence, the route may advance only to locked planning blocker `identity_public_contract_gate_missing`. | Do not rerun broad FName/GObjects/core discovery, admin snapshots, second-source layout, or lifecycle layout routes. The Worker 6 offline audit keeps exact `CheckJoinInProgress(1,0)` as the fastest valid blocked route; extra broad diagnostics, map/tester changes, and offline layout discovery are not primary next actions from offline evidence alone. Next useful step is approved copied runtime principal lifecycle evidence under a current-turn operator-approved live-ops window; request packs and replay checks remain offline guardrails, not runtime approval. Post-window consumption requires `--post-window-replay`, completed digest-bound `operator-approval-receipt.json`, stable-only final posture, and sidecars beside copied live-validation evidence. Keep any future principal opaque, generation-checked, process-local by default, and invalidated fail-closed. |
| Mission lane | Fact: accepted compact layout evidence and copied-bool test planning make it the selected post-RC internal/test-only module planning thread; fixture-boundary reports are candidate-only/non-authorizing. The mission/transfer/dino/tribe/buff helper now selects the canonical mission umbrella release-statement row, so mention/comment rows, unrelated surface rows, and negated readiness context do not create false release-statement blockers. | Use as internal/test-only copied-bool hardening; no runtime hooks, public Mission SDK, object/array/player identity, mutation, return override, SDK completion, runtime readiness, live ops approval, or P0 progress. |
| Transfer lane | Fact: UFunction and ScriptStruct layouts have exact layout-only evidence, and `ServerTransferredPlayerConfirmationResult.bAccept` now has a CTest-only hook-side helper. Payloads remain sensitive, and `bAccept` accounting is candidate-only/non-authorizing. | Keep transfer as offline/internal and absent from runtime/public/ops surfaces until copied payload ownership, privacy/redaction, lifecycle, second-source/static evidence, ABI tests, installed SDK consumer coverage, and approved runtime validation all pass. |
| Buff lane | Fact: compact and breadth target sets provide internal layout evidence for bool/class/zero-param shapes. | Treat as copied-payload/redaction design only; no public Buff SDK, runtime hooks, class/object exposure, mutation, return override, or gameplay semantics. |
| Dino lane | Fact: passenger/carry compact target sets have accepted layout evidence; Mission/Transfer/Dino/Tribe umbrella accounting remains candidate-only/non-authorizing. | Use only for later recognizer design until identity, lifetime, privacy/redaction, resource-handle, mutation, return-override, and callback gates are resolved; no SDK completion, runtime readiness, live ops approval, or P0 progress. |
| Tribe lane | Fact: permission, membership, log-control, online-list, and mission-tag shapes are useful but identity-sensitive; Mission/Transfer/Dino/Tribe umbrella accounting remains candidate-only/non-authorizing. | Keep as internal/layout planning until player/tribe identity, arrays/strings, privacy, and permission policy are promoted; no SDK completion, runtime readiness, live ops approval, or P0 progress. |
| Admin/permissions lane | Fact: admin, permissions, RCON, economy, storage, and operator surfaces are demand signals or documentation-only. | Keep `permissions/admin` blocked until identity is promoted; the minimum later shape is query-only, owner-scoped, capability-gated, process-local, and fail-closed. Require explicit abuse controls, permission model, lifecycle/ownership policy, ABI tests, and operator approval before any runtime or public SDK proposal. |

Historical reusable evidence:

- [2026-05-27-general-ufunction-inventory.md](2026-05-27-general-ufunction-inventory.md)
- [2026-05-27-sdk-module-taxonomy.md](2026-05-27-sdk-module-taxonomy.md)

Use older module-specific notes only when they provide reusable evidence for this path or
when a task explicitly targets that module.

## Index

| Note | Topic | Result |
| --- | --- | --- |
| [2026-05-27-runtime-and-chat-baseline.md](2026-05-27-runtime-and-chat-baseline.md) | Historical runtime/module baseline | Documents the live-safe Ragnarok posture and early module discovery risk. |
| [2026-05-27-reflection-chat-metadata-audit.md](2026-05-27-reflection-chat-metadata-audit.md) | Historical reflection metadata audit | Adds shared UE probe layouts and keeps object/UFunction tail logging gated. |
| [2026-05-27-reflection-scanner-candidate-validation.md](2026-05-27-reflection-scanner-candidate-validation.md) | ReflectionScanner candidate validation | Documents bounded UObject candidate scoring for isolated scanner captures. |
| [2026-05-27-fname-indirect-table-probe.md](2026-05-27-fname-indirect-table-probe.md) | FName indirect table probe | Adds bounded scanner-only GNames/FName indirect-array candidate logging. |
| [2026-05-27-reflectionscanner-isolated-capture-runbook.md](2026-05-27-reflectionscanner-isolated-capture-runbook.md) | ReflectionScanner isolated capture runbook | Documents flags, expected logs, GNames acceptance criteria, and rollback for the next isolated capture. |
| [2026-05-27-reflectionscanner-isolated-instance-audit.md](2026-05-27-reflectionscanner-isolated-instance-audit.md) | ReflectionScanner isolated instance audit | Records read-only evidence that no confirmed isolated/debug ARK instance currently exists. |
| [2026-05-27-isolated-debug-instance-plan.md](2026-05-27-isolated-debug-instance-plan.md) | Isolated debug instance plan | Plans a new LGSM debug instance with isolated ports, saves, cluster posture, Obelisk env, rollback, and permission checklist. |
| [2026-05-27-arkserver2-debug-pivot.md](2026-05-27-arkserver2-debug-pivot.md) | arkserver2 debug pivot | Historical/superseded: current direction uses `arkserver2` only for explicit approved scoped tests and shuts it down afterward. |
| [2026-05-27-ops-restart-audit-instance-id.md](2026-05-27-ops-restart-audit-instance-id.md) | Ops restart audit after instance id | Records the read-only protected live-server audit, deleted library mappings, wrapper gap, restart plan, and verification commands. |
| [2026-05-27-reflectionscanner-analyzer-review.md](2026-05-27-reflectionscanner-analyzer-review.md) | ReflectionScanner analyzer review | Reviews false-positive and missed-candidate risks in the FName probe/analyzer path. |
| [2026-05-27-fname-reject-evidence-logging.md](2026-05-27-fname-reject-evidence-logging.md) | FName reject evidence logging | Adds opt-in rejection reasons and analyzer evidence-pack counts for failed FName probes. |
| [2026-05-27-live-fname-reject-capture.md](2026-05-27-live-fname-reject-capture.md) | Live development FName reject capture | Records one controlled Ragnarok capture: 22 UObject leads, 22 FName rejects, no GNames candidate. |
| [2026-05-27-runtime-debug-control.md](2026-05-27-runtime-debug-control.md) | Runtime debug control | Adds a marker-file debug path for post-start static FName root probes, avoiding blind bootstrap waits. |
| [2026-05-27-core-gobjects-next-development.md](2026-05-27-core-gobjects-next-development.md) | Core-based GObjects next development | Documents the offline core workflow for FName-root-backed GObjects triage and pointer-value scans. |
| [2026-05-27-core-gobjects-candidate.md](2026-05-27-core-gobjects-candidate.md) | Core GUObjectArray candidate | Promotes `0x595b7e0` to a binary-hash-specific `GUObjectArray research-candidate` from core evidence. |
| [2026-05-27-gobjects-static-anchor-classification.md](2026-05-27-gobjects-static-anchor-classification.md) | GObjects static anchor classification | Classifies concrete `0x595b7e0` static contexts and rejects broad objdump function-group volume as a standalone decompiler target. |
| [2026-05-27-core-uobject-enumeration.md](2026-05-27-core-uobject-enumeration.md) | Core UObject enumeration | Adds offline UObject enumeration from core evidence and identifies real chat-related `UFunction` objects. |
| [2026-05-27-core-ufunction-property-chain.md](2026-05-27-core-ufunction-property-chain.md) | Core UFunction property chain | Reconstructs chat `UFunction` property chains and parameter offsets from offline core evidence. |
| [2026-05-27-ufunction-membership-backrefs.md](2026-05-27-ufunction-membership-backrefs.md) | UFunction membership back-references | Strengthens offline target/class/outer/property validation with direct `GObjects[InternalIndex]` back-reference checks. |
| [2026-05-27-general-ufunction-inventory.md](2026-05-27-general-ufunction-inventory.md) | General UFunction inventory | Adds a broad offline UFunction inventory so future roadmap work can target players, dinos, items, and commands across the full modding surface. |
| [2026-05-27-shooterplayercontroller-function-inventory.md](2026-05-27-shooterplayercontroller-function-inventory.md) | ShooterPlayerController function inventory | Focuses the general inventory on player/controller capabilities: inventory, dinos, structures, tribe, transfer, notifications, and admin surfaces. |
| [2026-05-27-primalitem-function-inventory.md](2026-05-27-primalitem-function-inventory.md) | PrimalItem function inventory | Focuses the general inventory on item use, equip, crafting, repair, durability, remote inventory, and item NetExec candidates. |
| [2026-05-27-inventory-controller-snapshot-fixtures.md](2026-05-27-inventory-controller-snapshot-fixtures.md) | Inventory controller snapshot fixtures | Adds real-core snapshots for compact item gates and controller inventory-use requests. |
| [2026-05-27-primalbuff-snapshot-fixtures.md](2026-05-27-primalbuff-snapshot-fixtures.md) | PrimalBuff snapshot fixtures | Adds a focused buffs inventory and minimal real-core snapshots for bool-return and zero-param buff functions. |
| [2026-05-27-rejected-snapshot-discovery.md](2026-05-27-rejected-snapshot-discovery.md) | Rejected snapshot discovery | Records exact deferred targets that remained valid metadata chains, so no fake rejected real-core fixture was added. |
| [2026-05-27-module-readiness-matrix.md](2026-05-27-module-readiness-matrix.md) | Module readiness matrix | Summarizes manifest-backed module readiness and next gates without promoting public SDK status. |
| [2026-05-28-reversing-objective-map.md](2026-05-28-reversing-objective-map.md) | Reversing objective map | Defines the broad ARK/UE4 research objective and keeps module work aligned to a general Linux modding core. |
| [2026-05-28-second-source-reversing-gap-matrix.md](2026-05-28-second-source-reversing-gap-matrix.md) | Second-source reversing gap matrix | Defines the evidence gaps and target-set promotion gates for FName/GObjects/UObject/UFunction reflection evidence. |
| [2026-05-29-minimal-second-source-readiness.md](2026-05-29-minimal-second-source-readiness.md) | Minimal second-source readiness | Records accepted direct-root second-source layout evidence and the current validator refresh for two inventory and two structure UFunction targets, without promoting GObjects, identity, mutation, return override, or public SDK surfaces. |
| [2026-05-29-public-gameplay-event-readiness-audit.md](2026-05-29-public-gameplay-event-readiness-audit.md) | Public gameplay event readiness audit | Promotes `GameplayPolicyEvent` as copied/redacted POD backed by accepted target-set evidence, while keeping public Inventory/Structure SDKs, identity, mutation, and return override blocked. |
| [2026-05-29-chat-message-second-source-readiness.md](2026-05-29-chat-message-second-source-readiness.md) | Chat message second-source readiness | Records accepted layout evidence plus copied plugin-facing delivery validation for all four known chat send modes, while keeping identity, commands, mutation, and UE internals blocked. |
| [2026-05-30-v1-core-capability-map.md](2026-05-30-v1-core-capability-map.md) | v1 core capability map | Defines the post-RC route toward a general Linux ARK modding core and separates v1 infrastructure from later ArkApi-style module/plugin work. |
| [2026-05-30-aseapi-reference-scan.md](2026-05-30-aseapi-reference-scan.md) | AseApi reference scan | Allows ArkServerApi/AseApi as names/demand evidence only while banning copied architecture, ergonomics, behavior, offsets, vtables, MSVC ABI, Windows libs, direct UE pointer APIs, and direct memory access patterns. |
| [2026-05-30-nextgenplugins-reference-inventory.md](2026-05-30-nextgenplugins-reference-inventory.md) | NextGenPlugins reference inventory | Records the local ArkApi plugin-source clone as a future Plugin Hub demand signal only, not as runtime evidence or portable implementation source. |
| [2026-06-01-aseapi-name-demand-map.md](2026-06-01-aseapi-name-demand-map.md) | AseApi/NextGen name demand map | Maps high-demand dictionary-only plugin capability families to candidate Obelisk surfaces and likely UE4 names without promoting SDK, runtime, mutation, or Plugin Hub work. |
| [2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md](2026-06-01-v1-sdk-demand-chain-from-aseapi-nextgen.md) | v1 SDK demand chain from AseApi/NextGen | Condenses dictionary-only demand into blocker ordering without promoting compatibility, public SDK completion, runtime observers, command replies, storage, mutation, or porting work. |
| [2026-06-01-mission-transfer-dino-tribe-v1-split.md](2026-06-01-mission-transfer-dino-tribe-v1-split.md) | Mission/Transfer/Dino/Tribe/Buff split | Splits the umbrella side-lane into candidate-only leaf accounting; Buff/status readiness is fixture-only and still does not promote public SDK, runtime, ABI, identity, mutation, return override, ResourceHandle, or v1 completion. |
| [2026-05-30-post-rc-targetset-priorities.md](2026-05-30-post-rc-targetset-priorities.md) | Post-RC target-set priorities | Ranks Mission, Dino, Buff, Structure build-policy, Tribe, and Transfer follow-up work for offline/internal research without promoting new SDK surfaces. |
| [2026-05-30-chat-command-helper-roadmap.md](2026-05-30-chat-command-helper-roadmap.md) | Chat command helper roadmap | Defines a plugin-local, non-ABI helper pattern over `ChatMessageEvent` with `principal=unknown`, global config-only enablement, and no player permissions or chat response path. |
| [2026-05-31-chat-command-readiness.md](2026-05-31-chat-command-readiness.md) | Chat command readiness audit | Confirms copied chat is enough for repo-local plugin command parsing tests only, with docs/tests as the next hardening step and no public command SDK, identity, replies, moderation, mutation, or live-test approval. |
| [2026-05-31-command-chat-response-thunk-orientation.md](2026-05-31-command-chat-response-thunk-orientation.md) | Command/chat response thunk orientation | Preserves candidate-only static thunk orientation without promoting replies, send-chat, command routing, identity, permissions, runtime readiness, or public SDK status. |
| [2026-05-29-filtered-process-event-debug-gate-hardening.md](2026-05-29-filtered-process-event-debug-gate-hardening.md) | Filtered ProcessEvent debug gate hardening | Records why raw filtered `ProcessEvent` callbacks moved behind an explicit debug gate so copied events remain the RC plugin path. |
| [2026-05-29-rc-checkpoint-slicing-plan.md](2026-05-29-rc-checkpoint-slicing-plan.md) | RC checkpoint slicing | Splits the broad dirty worktree into reviewable local checkpoints and keeps the first RC limited to core API, lifecycle, release gates, and redacted evidence. |
| [2026-05-29-buff-after-compact-next-step.md](2026-05-29-buff-after-compact-next-step.md) | Buff after compact next step | Recommends no buff runtime hooks after accepted compact layout evidence; limits useful follow-up to docs or offline target-set expansion. |
| [2026-05-27-primaldinocharacter-function-inventory.md](2026-05-27-primaldinocharacter-function-inventory.md) | PrimalDinoCharacter function inventory | Focuses the general inventory on dino passenger, carry, attack, flight, tame-status, and blueprint hook candidates. |
| [2026-05-27-dino-second-wave-fixtures.md](2026-05-27-dino-second-wave-fixtures.md) | Dino second-wave fixtures | Adds fixture-backed coverage and real-core snapshots for dino passenger and carry surfaces. |
| [2026-05-27-primalstructure-function-inventory.md](2026-05-27-primalstructure-function-inventory.md) | PrimalStructure function inventory | Focuses the general inventory on structure access, snapping, pickup, demolish, variants, containers, seating, and elevator controls. |
| [2026-05-27-structure-access-policy-fixtures.md](2026-05-27-structure-access-policy-fixtures.md) | Structure access policy fixtures | Adds fixture-backed coverage for compact structure access, demolish, pincode, variant, and seating policy chains. |
| [2026-05-27-real-core-ufunction-snapshot-fixtures.md](2026-05-27-real-core-ufunction-snapshot-fixtures.md) | Real core UFunction snapshot fixtures | Adds sanitized real-core snapshot fixtures for compact structure and mission property chains. |
| [2026-05-27-missiontype-function-inventory.md](2026-05-27-missiontype-function-inventory.md) | MissionType function inventory | Focuses the general inventory on mission player membership, leave/add hooks, state, leaderboard, spawn, and deferred string/array-heavy candidates. |
| [2026-05-27-tribe-control-observation-fixture.md](2026-05-27-tribe-control-observation-fixture.md) | Tribe control observation fixture | Adds a zero-param gameplay control fixture and real-core snapshot for `ServerRequestTribeLog`. |
| [2026-05-27-ufunction-snapshot-manifest-regeneration.md](2026-05-27-ufunction-snapshot-manifest-regeneration.md) | UFunction snapshot manifest regeneration | Adds manifest-driven regeneration and drift checks for real-core UFunction snapshot fixtures. |
| [2026-05-27-sdk-module-taxonomy.md](2026-05-27-sdk-module-taxonomy.md) | SDK module taxonomy | Defines candidate-only module areas, readiness levels, promotion gates, and first fixture targets across the full modding surface. |
| [2026-05-27-runtime-chat-reflection-plan.md](2026-05-27-runtime-chat-reflection-plan.md) | Historical module reflection plan | Defines a safe internal path from reflected module evidence to a gated `ProcessEvent` filter. |
| [2026-05-27-chat-reflection-no-hit-audit.md](2026-05-27-chat-reflection-no-hit-audit.md) | Historical module no-hit audit | Historical read-only snapshot that found stable hook/gate posture but no recognized module hits in the reviewed window; later runtime-hit evidence supersedes its next step. |
| [2026-05-27-server-send-chat-runtime-hit.md](2026-05-27-server-send-chat-runtime-hit.md) | Historical module runtime hit | Records historical accepted chat-observer runtime observations; not current approved runtime evidence, and SDK dispatch stays blocked until copied-data ownership is designed. |
| [2026-05-28-passive-chat-reflection-live-observation.md](2026-05-28-passive-chat-reflection-live-observation.md) | Passive module live observation | Records an operator-supplied Ragnarok log excerpt as passive runtime observer evidence, not SDK readiness. |
| [2026-05-28-second-source-core-intake-runbook.md](2026-05-28-second-source-core-intake-runbook.md) | Second-source core intake runbook | Defines the shortest offline evidence-pack and UFunction comparison path for an approved independent core artifact. |
| [2026-05-28-fname-index-manifest-plan.md](2026-05-28-fname-index-manifest-plan.md) | FName index manifest plan | Defines a binary-scoped manifest/resolver path so raw `FName` indices remain evidence-backed and fail closed by ARK binary hash. |
| [2026-05-29-module-surface-roadmap.md](2026-05-29-module-surface-roadmap.md) | Module surface roadmap | Ranks current module surfaces and keeps accepted compact target sets separate from public SDK promotion. |
| [2026-05-31-v02-module-priority.md](2026-05-31-v02-module-priority.md) | v0.2 module priority | Selects Mission copied-bool as the next internal module lane after copied chat/policy while keeping public Mission SDK, runtime observers, identity, lookup, mutation, and return override blocked. |
| [2026-05-31-batch-snapshot-planner-design.md](2026-05-31-batch-snapshot-planner-design.md) | Batch/focal snapshot planner design | Defines the safe pre-target-set planner path for exact candidate-only UFunction snapshots from reviewed inventory packs, without command execution or SDK promotion. |
| [2026-05-29-next-targetset-discovery.md](2026-05-29-next-targetset-discovery.md) | Next target-set discovery | Records accepted second-source layout evidence for mission and tribe compact target sets and ranks mission as the cleaner next module candidate. |
| [2026-05-29-mission-reflection-internal-readiness.md](2026-05-29-mission-reflection-internal-readiness.md) | Mission reflection internal readiness | Reviews the expanded `MissionReflectionTests` coverage and limits mission readiness to an internal recognizer/copy-readiness pack without public SDK, hook, dispatcher, identity, mutation, or return override promotion. |
| [2026-05-30-mission-copied-bool-observer-plan.md](2026-05-30-mission-copied-bool-observer-plan.md) | Mission copied-bool observer plan | Freezes the docs-only internal observer model for exactly four Mission functions, five copied bool fields, six redacted object/container fields, log grammar, gates, rollback, and non-goals without runtime or public SDK promotion. |
| [2026-05-29-reflection-inventory-pack-smoke.md](2026-05-29-reflection-inventory-pack-smoke.md) | Reflection inventory pack smoke | Validates the redacted candidate-only inventory pack builder on offline core evidence, with FName root ready and 8/8 requested target-set functions present. |
| [2026-05-31-fname-gobjects-offline-route.md](2026-05-31-fname-gobjects-offline-route.md) | FName/GObjects offline route | Records the no-repeat route for the current binary: reuse the reviewed FName root and GObjects candidate, then advance through closed target-set snapshots, second-source comparison, and redacted signatures. |
| [2026-05-29-gobjects-cross-manifest-comparison.md](2026-05-29-gobjects-cross-manifest-comparison.md) | GObjects cross-manifest comparison | Compares existing gobjects-sampling manifests across two copied cores, reinforcing `0x595b7e0` for internal offline work while keeping public GObjects, ResourceHandle, identity, lookup, mutation, and return override blocked. |
| [2026-05-29-ghidra-fuobjectarray-field-window-probe.md](2026-05-29-ghidra-fuobjectarray-field-window-probe.md) | Bounded Ghidra/r2 FUObjectArray probe | Records redacted internal evidence that the static GObjects candidate and serial accessors share one coherent field-window hypothesis for the current ARK binary hash. |
| [2026-05-29-resource-handle-nonzero-revalidation.md](2026-05-29-resource-handle-nonzero-revalidation.md) | ResourceHandle nonzero serial revalidation | Records `32/32` accepted offline samples with `32` nonzero serial candidates and proven GObjects field coherence, while keeping public ResourceHandle blocked on `uobject_flags_validity_semantics_unproven`. |
| [2026-05-30-post-rc-offline-resourcehandle-priority.md](2026-05-30-post-rc-offline-resourcehandle-priority.md) | Post-RC ResourceHandle priority | Records the current fail-closed ResourceHandle lane, including identity-complete evaluator input with 44/44 accepted samples while keeping public ResourceHandle, GObjects, lookup, mutation, and post-callback handles blocked. |
| [2026-05-30-static-build-policy-tooling.md](2026-05-30-static-build-policy-tooling.md) | Static build-policy tooling audit | Confirms offline `radare2`, Ghidra headless, and non-protected artifact availability for future `IsAllowedToBuild` triage without promoting any build-policy candidate. |
| [2026-05-31-structure-build-policy-focal-snapshot-planner.md](2026-05-31-structure-build-policy-focal-snapshot-planner.md) | Structure build-policy focal snapshot planner | Adds a candidate-only `--plan-target` path from complete evidence-pack manifests or explicit direct-core identity to exact `IsAllowedToBuild` snapshot commands, while keeping target sets, SDKs, runtime hooks, mutation, and return override blocked. |
| [2026-05-29-uobject-flags-fullscan.md](2026-05-29-uobject-flags-fullscan.md) | UObject flags fullscan | Historical no-repeat evidence: copied-core volume found thousands of nonzero serial candidates and no `0x100`/`0x4000` mask-positive samples, so the current blocker is semantic runtime evidence rather than another broad scan. |
| [2026-05-29-weak-helper-flag-polarity.md](2026-05-29-weak-helper-flag-polarity.md) | Weak helper flag polarity | Refines `UObject+0x8` validity semantics from bounded static helper/caller evidence while keeping public ResourceHandle blocked. |
| [2026-05-29-resource-handle-flag-policy-candidate.md](2026-05-29-resource-handle-flag-policy-candidate.md) | ResourceHandle flag-policy candidate | Consolidates weak-helper caller-mode and nonzero readiness JSON into a short matrix: FName/GObjects/serial are not the main blocker; flag and lifecycle semantics keep post-callback handles blocked. |
| [2026-05-29-offline-evidence-canonicality.md](2026-05-29-offline-evidence-canonicality.md) | Offline evidence canonicality | Marks stale ResourceHandle evaluator output, dry-run plans, and duplicate GObjects reports so future rounds do not use them as independent promotion evidence. |
| [2026-05-29-dispatcher-hook-safety-hardening.md](2026-05-29-dispatcher-hook-safety-hardening.md) | Dispatcher hook safety hardening | Records Chat/Structure/Inventory dispatcher fail-closed behavior and reentrant unregister cleanup rules for hook-called dispatchers. |
| [2026-05-29-buff-compact-second-source-result.md](2026-05-29-buff-compact-second-source-result.md) | Buff compact second-source result | Records accepted second-source layout evidence for the three-target buff compact intake without promoting a public Buff SDK. |
| [2026-05-29-dino-compact-second-source-readiness.md](2026-05-29-dino-compact-second-source-readiness.md) | Dino compact second-source readiness | Records accepted second-source layout evidence for passenger/carry dino targets without promoting public Dino callbacks or identity. |
| [2026-05-31-dino-scalar-policy-planning.md](2026-05-31-dino-scalar-policy-planning.md) | Dino scalar policy planning | Defines the next internal copied-scalar planning lane for passenger/carry Dino targets while blocking public Dino SDK, identity, mutation, return override, and runtime observation. |
| [2026-05-29-item-compact-second-source-readiness.md](2026-05-29-item-compact-second-source-readiness.md) | Item compact second-source readiness | Records accepted strict second-source layout evidence for four compact `PrimalItem` targets without promoting public Items/Inventory SDKs, identity, mutation, return override, or ResourceHandle. |
| [2026-05-29-item-return-only-policy-bridge-plan.md](2026-05-29-item-return-only-policy-bridge-plan.md) | Item return-only bridge plan | Historical bridge plan superseded by the 2026-05-30 item-return slice for current routing; preserves the original safe-path rationale without public Items SDK, identity, mutation, return override, or ResourceHandle claims. |
| [2026-05-30-item-return-only-policy-slice.md](2026-05-30-item-return-only-policy-slice.md) | Item return-only policy slice | Adds an evidence-only report for exactly three copied `PrimalItem` return bools while excluding CraftBlueprint, non-return bools, object refs, mutation, return override, and public SDK claims. |
| [2026-05-29-inventory-action-redacted-signature-readiness.md](2026-05-29-inventory-action-redacted-signature-readiness.md) | Inventory action redacted signature readiness | Records candidate-only redacted signatures, accepted second-source layout evidence, and the next strict target-set consume-gate artifact flow for controller-side inventory use actions without promoting public Inventory/Items SDKs, `ItemNetID`, identity, mutation, return override, or ResourceHandle. |
| [2026-05-29-transfer-second-source-readiness.md](2026-05-29-transfer-second-source-readiness.md) | Transfer second-source readiness | Records accepted layout-only second-source evidence for seven transfer UFunctions and two transfer ScriptStructs, plus consume-mode redacted signatures, without promoting public Transfer SDKs, payload decoding, identity, mutation, return override, runtime hooks, or ResourceHandle. |
| [2026-05-30-transfer-scriptstruct-booltail-refresh.md](2026-05-30-transfer-scriptstruct-booltail-refresh.md) | Transfer ScriptStruct bool-tail refresh | Regenerates current `transfer-scriptstruct` second-source snapshots with bool-tail metadata preserved and accepts 2/2 targets as layout-only evidence. |
| [2026-05-29-transfer-copied-scalar-feasibility.md](2026-05-29-transfer-copied-scalar-feasibility.md) | Transfer copied-scalar feasibility | Records the CTest-only `ServerTransferredPlayerConfirmationResult.bAccept` hook-side helper boundary while keeping it out of runtime/public/ops surfaces and making no RC/public Transfer SDK claim. |
| [2026-05-30-redacted-scriptstruct-signatures.md](2026-05-30-redacted-scriptstruct-signatures.md) | Redacted ScriptStruct signatures | Adds candidate-only redacted ScriptStruct signature summaries from sanitized snapshots without replacing second-source readiness, payload decoding, runtime promotion, or SDK gates. |
| [2026-05-30-structure-build-policy-triage.md](2026-05-30-structure-build-policy-triage.md) | Structure build-policy triage | Records `APrimalStructure.IsAllowedToBuild` as a high-demand NextGenPlugins dictionary signal, but keeps it second-wave until sanitized snapshots, second-source evidence, redaction policy, and mutation/return-override blockers are resolved. |
| [2026-05-30-player-identity-lifecycle-plan.md](2026-05-30-player-identity-lifecycle-plan.md) | Player identity lifecycle plan | Defines the first docs-only `players_identity_lifecycle` target set from existing target names, with copied/redacted fields only and no ResourceHandle, lookup, SDK, runtime, mutation, or return override. |
| [2026-05-31-player-identity-first-evidence.md](2026-05-31-player-identity-first-evidence.md) | Player identity first evidence | Defines the smallest candidate-only identity evidence package needed before public permissions, commands, or economy SDK design can start. |
| [2026-05-31-player-identity-targetset-gap.md](2026-05-31-player-identity-targetset-gap.md) | Player identity target-set gap | Historical gap note: the missing `ServerListPlayers`/`ServerKickPlayer` snapshot gap is now closed; lifecycle/runtime evidence remains the active blocker. |
| [2026-05-31-player-identity-privacy-invalidation-contract.md](2026-05-31-player-identity-privacy-invalidation-contract.md) | Player identity privacy invalidation contract | Defines the candidate-only future principal contract: opaque copied principal plus generation, lifecycle invalidation, process-local multi-instance limits, and explicit non-claims for SDK/runtime/lookup. |
| [2026-05-31-planning-layout-intake-contract.md](2026-05-31-planning-layout-intake-contract.md) | Planning layout intake contract | Defines `planning-layout-intake` as a planning-only, consume-only layout contract for player identity target sets, with no promotion, SDK, runtime, or release-readiness claim. |
| [2026-05-31-player-identity-static-admin-thunks.md](2026-05-31-player-identity-static-admin-thunks.md) | Player identity static admin thunks | Preserves lightweight static clues for `ServerListPlayers` and `ServerKickPlayer` native thunks while keeping them orientation-only and not a substitute for core/reflection inventory evidence. |
| [2026-06-01-player-principal-offline-to-runtime-plan.md](2026-06-01-player-principal-offline-to-runtime-plan.md) | Player principal offline-to-runtime plan | Records the golden path from reviewed `0x5956f30`/`0x595b7e0` offline evidence through focal `HandleNewPlayer`/`OnLogout` snapshots to the next private runtime consume-only observer evidence, without public SDK or live-run approval. |
| [2026-06-01-player-principal-runtime-capture-plan.md](2026-06-01-player-principal-runtime-capture-plan.md) | Player principal runtime capture plan | Documents the approval-required consume-only runtime capture window for `PlayerPrincipalLifecycleObserver`, including prerequisites, markers/env, copied-log evidence, manifest/checker flow, rollback, user no-go conditions, and remaining gaps. |
| [2026-06-01-player-identity-lifecycle-route-audit.md](2026-06-01-player-identity-lifecycle-route-audit.md) | Player identity lifecycle route audit | Condenses the accepted `HandleNewPlayer`/`OnLogout` route, checker chain, and exact `approved_runtime_evidence_missing` blocker while rejecting broad FName/GObjects scans, ResourceHandle promotion, public lookup, SDK, mutation, and return override claims. |
| [2026-06-04-lifecycle-anchor-fname-drift-delta.md](2026-06-04-lifecycle-anchor-fname-drift-delta.md) | Lifecycle anchor FName drift delta | Records lead5 passive snapshot paths, copied log hashes, `HandleNewPlayer`/`OnLogout` FName drift, non-evidence status, rejected claims, no-restart live posture, and next offline verification questions. |
| [2026-06-06-player-principal-lifecycle-evidence-feasibility.md](2026-06-06-player-principal-lifecycle-evidence-feasibility.md) | Player principal lifecycle evidence feasibility | Start with its operational digest and Worker 6 offline route audit: accepted `HandleNewPlayer(1,1)` start, exact `CheckJoinInProgress(1,0)` rejected start, `OnLogout` end, superseded/non-evidence `HandleNewPlayer` rejected tuples, rejected `K2_PostLogin` drift, all-six planning gap, passive/diagnostic non-evidence boundary, and the conclusion that exact `CheckJoinInProgress(1,0)` remains the fastest valid blocked route. The historical updates remain context only and do not authorize runtime, SDK, publication, or Plugin Hub work. |
| [2026-06-07-checkjoin-runtime-evidence-gap.md](2026-06-07-checkjoin-runtime-evidence-gap.md) | CheckJoinInProgress runtime evidence gap | Documents the post-patch accepted-event gap, runtime plan, and 2026-06-08 offline/static tooling checkpoints: strict selector/status/runner/copy/runtime-window tooling prepares the copied triplet evidence flow, Discord bot tester workflow metadata remains non-evidence, the three triplet source registrations cluster at registrar `0x1ccc140` with `CheckJoinInProgress` byte-checked as rejected-start orientation only, and `approved_runtime_evidence_missing` remains active until an accepted copied `CheckJoinInProgress(1,0)` bundle passes the checker chain. |
| [2026-06-07-player-principal-long-passive-window-workflow.md](2026-06-07-player-principal-long-passive-window-workflow.md) | Player principal long passive window workflow | Records that standing authority is not evidence/readiness, accepted lifecycle evidence still requires the exact copied `HandleNewPlayer(1,1)`, `CheckJoinInProgress(1,0)`, and matched `OnLogout` triplet, the `20260607T132020Z` and `20260607T134929Z` TheIsland windows remained non-evidence, broad windows should stay open while players may enter, connected-player sessions should not be cut merely to broaden observer coverage, live Ragnarok `28416`/`28548` and `28419/21315/22969/28517...` FName drift remains diagnostic non-evidence unless the exact copied triplet passes the approved checker chain, and bundle/checker closure suites should run serially. |
| [2026-06-01-static-offline-sdk-v1-command-player-audit.md](2026-06-01-static-offline-sdk-v1-command-player-audit.md) | Static offline SDK v1 command/player audit | Confirms existing offline artifacts support only a blocker/status report across player principal, permissions/admin, command response, and commands/replies; no public SDK, runtime, reply, lookup, mutation, or return-override claim is promoted. |
| [2026-05-31-radare2-static-orientation-wrapper.md](2026-05-31-radare2-static-orientation-wrapper.md) | Radare2 static orientation wrapper | Documents the `/tmp`-rooted candidate-only radare2 window capture wrapper for player identity, admin, and chat-response UFunction addresses, with SHA/tool provenance and no artifact-gate or promotion claim. |
| [2026-05-31-permissions-admin-minimum-post-identity.md](2026-05-31-permissions-admin-minimum-post-identity.md) | Permissions/admin minimum post-identity | Defines the smallest safe post-identity permission/admin design as query-only, owner-scoped, capability-gated, process-local, and fail-closed while keeping public permissions, admin actions, commands, replies, storage, and operator ingress blocked. |
| [2026-05-31-offline-artifact-curation.md](2026-05-31-offline-artifact-curation.md) | Historical offline artifact curation | Historical/superseded for player identity: later source-bound planning manifests close the old offline fixture gaps; current identity blocker is `approved_runtime_evidence_missing`. |
| [2026-05-31-offline-artifact-inventory-audit.md](2026-05-31-offline-artifact-inventory-audit.md) | Historical offline artifact inventory audit | Historical/superseded for player identity; use the route audit and committed planning manifests for current identity routing, while command/chat response orientation remains non-promoting. |
| [2026-05-27-sdk-chat-event-ownership-plan.md](2026-05-27-sdk-chat-event-ownership-plan.md) | Historical SDK event ownership plan | Defines ownership, ABI, callback cleanup, and validation gates required before a public module callback API. |
| [2026-05-27-chat-sdk-abi-preflight.md](2026-05-27-chat-sdk-abi-preflight.md) | Historical SDK ABI preflight | Defines test-first ABI and dispatcher gates for a future module callback without changing the public header yet. |
| [2026-05-27-theisland-chat-reflection-ab-runbook.md](2026-05-27-theisland-chat-reflection-ab-runbook.md) | TheIsland historical module A/B runbook | Historical/superseded; do not execute without explicit approval to start `arkserver2`, test, and shut it down afterward. |
| [2026-05-27-isolated-second-core-runbook.md](2026-05-27-isolated-second-core-runbook.md) | Isolated second core runbook | Defines the approved-window flow for a second isolated core capture, preferring `arkserver-obelisk-debug` and keeping Ragnarok untouched. |
| [2026-05-27-quiet-posture-readonly-audit.md](2026-05-27-quiet-posture-readonly-audit.md) | Quiet posture read-only audit | Confirms the stricter production/performance guard detects chat reflection active on Ragnarok and that TheIsland is not currently running. |
| [2026-05-27-ragnarok-readonly-posture-snapshot.md](2026-05-27-ragnarok-readonly-posture-snapshot.md) | Ragnarok read-only posture snapshot | Historical/superseded; records a legacy posture snapshot while chat reflection was still active. Current `--expect-stable` fails that state. |
| [2026-05-27-shootergamemode-chat-candidates.md](2026-05-27-shootergamemode-chat-candidates.md) | Historical ShooterGameMode candidates | Validates exact metadata-only fallback recognizers from offline core evidence. |
| [2026-05-27-isreadable-dev-null-hotpath.md](2026-05-27-isreadable-dev-null-hotpath.md) | `Memory::IsReadable` hot-path audit | Rejects `write(/dev/null)` as a Linux readability probe and recommends cached maps checks plus direct UE-owned hot-path reads. |
| [2026-05-27-fstring-layout.md](2026-05-27-fstring-layout.md) | FString layout candidate | Promotes UTF-32LE `FString` as the internal decoder candidate for reflected `StrProperty` params. |
| [2026-05-27-chat-reflection-stack-cycle-guard.md](2026-05-27-chat-reflection-stack-cycle-guard.md) | Historical reflection stack cycle guard | Removes one matched-path allocation by replacing temporary property-cycle vector storage with a fixed stack guard. |
| [2026-05-27-plugin-callback-ownership-hardening.md](2026-05-27-plugin-callback-ownership-hardening.md) | Plugin callback ownership | Documents callback owner-token cleanup on init failure and unload. |
| [2026-05-27-plugin-shutdown-lifecycle.md](2026-05-27-plugin-shutdown-lifecycle.md) | Plugin shutdown lifecycle | Documents optional `ObeliskPlugin_Shutdown()` resolution and unload ordering. |
| [2026-05-27-processevent-target-validation.md](2026-05-27-processevent-target-validation.md) | ProcessEvent target validation | Historical note for range/prologue validation; active runtime now rejects direct-offset fallback. |
| [2026-05-27-subhook-reproducibility.md](2026-05-27-subhook-reproducibility.md) | FetchContent reproducibility | Documents local FetchContent commit pins and the remaining mirror/vendor risk. |

Use one file per investigation:

```text
YYYY-MM-DD-short-topic.md
```

Each note should capture:

- Objective
- Environment: ARK binary path, SHA256, instance id, map, Obelisk commit, plugins state
- Hypothesis
- Evidence: relevant log snippets, addresses, signatures, command summaries
- Result: confirmed, rejected, or inconclusive
- Risks
- Next steps

Keep raw logs out of Git. Summarize the important lines and reference the local log path when
needed.
