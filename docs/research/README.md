# Obelisk Research Notes

This directory stores reproducible investigation notes for Obelisk runtime, UE4 reflection,
ARK server operations, and plugin experiments.

Notes written before `OBELISK_INSTANCE_ID` may mention obsolete map-based marker files and
root-level map logs. New research should record the LinuxGSM instance id, map, ARK binary
hash, and runtime flags.

Historical module-specific notes, especially early chat reflection notes, remain indexed as
evidence trails. Treat them as examples of the common reflection and promotion-gate ladder,
not as the current product center. For contributor-facing release scope, use
`docs/STATUS.md` and `docs/RELEASE.md` plus the RC evidence path below; broad UE4
reflection, FName/GObjects expansion, and new module surface discovery are post-RC unless a
new binary hash or contradictory evidence changes the active routing.

## Start Here

Use these notes as the current curated core-first path for new work. This README is a
navigation aid, not an exhaustive inventory of every evidence note; unlisted notes may
still preserve durable evidence and should not be deleted only because they are absent
from this index.

Published RC baseline evidence lane (current published tag: `v0.1.0-rc.2` at `1a7cd98`):

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
| FName | Binary-scoped clues accepted for current artifacts; broad table scans should reuse the reviewed root slot unless a new binary/hash contradicts it. | [2026-05-28-second-source-reversing-gap-matrix.md](2026-05-28-second-source-reversing-gap-matrix.md) |
| GObjects | Strong internal/offline `GUObjectArray` candidate for enumeration and fixture generation; current strict consume evidence needs durable recapture before reuse; no public/runtime identity or lookup contract. | [2026-05-29-gobjects-cross-manifest-comparison.md](2026-05-29-gobjects-cross-manifest-comparison.md), [2026-05-30-gobjects-strict-consume-recapture-needed.md](2026-05-30-gobjects-strict-consume-recapture-needed.md) |
| UObject | Object fields and flags remain evidence for candidate classification; public lifecycle/validity semantics are not proven. | [2026-05-29-uobject-flags-validity-blocker.md](2026-05-29-uobject-flags-validity-blocker.md) |
| UFunction layout | Accepted only per named target set after fixture and second-source comparison; RC target sets cover the current public copied surfaces. | [2026-05-30-rc-ufunction-layout-evidence-audit.md](2026-05-30-rc-ufunction-layout-evidence-audit.md) |
| ResourceHandle | Post-RC/internal and blocked until lifecycle, validity, reuse, lookup privacy, and fail-closed semantics are proven. | [2026-05-30-post-rc-offline-resourcehandle-priority.md](2026-05-30-post-rc-offline-resourcehandle-priority.md) |
| Artifact identity | Strict consume gates require complete top-level `artifact_identity` for current static-global and UObject flag-policy evidence. | [2026-05-30-artifact-identity-hardening.md](2026-05-30-artifact-identity-hardening.md) |

Historical recovery reference:

- [2026-05-29-rc-checkpoint-slicing-plan.md](2026-05-29-rc-checkpoint-slicing-plan.md)

Current post-RC research lane:

- [2026-05-30-v1-core-capability-map.md](2026-05-30-v1-core-capability-map.md)
- [2026-05-30-aseapi-reference-scan.md](2026-05-30-aseapi-reference-scan.md)
- [2026-05-30-nextgenplugins-reference-inventory.md](2026-05-30-nextgenplugins-reference-inventory.md)
- [2026-05-30-chat-command-helper-roadmap.md](2026-05-30-chat-command-helper-roadmap.md)
- [2026-05-30-chat-audit-plugin-plan.md](2026-05-30-chat-audit-plugin-plan.md)
- [2026-05-29-module-surface-roadmap.md](2026-05-29-module-surface-roadmap.md)
- [2026-05-29-next-targetset-discovery.md](2026-05-29-next-targetset-discovery.md)
- [2026-05-29-mission-reflection-internal-readiness.md](2026-05-29-mission-reflection-internal-readiness.md)
- [2026-05-30-mission-copied-bool-observer-plan.md](2026-05-30-mission-copied-bool-observer-plan.md)
- [2026-05-29-item-compact-second-source-readiness.md](2026-05-29-item-compact-second-source-readiness.md)
- [2026-05-29-item-return-only-policy-bridge-plan.md](2026-05-29-item-return-only-policy-bridge-plan.md)
- [2026-05-30-item-return-only-policy-slice.md](2026-05-30-item-return-only-policy-slice.md)
- [2026-05-29-inventory-action-redacted-signature-readiness.md](2026-05-29-inventory-action-redacted-signature-readiness.md)
- [2026-05-29-transfer-second-source-readiness.md](2026-05-29-transfer-second-source-readiness.md)
- [2026-05-30-transfer-scriptstruct-booltail-refresh.md](2026-05-30-transfer-scriptstruct-booltail-refresh.md)
- [2026-05-29-transfer-copied-scalar-feasibility.md](2026-05-29-transfer-copied-scalar-feasibility.md)
- [2026-05-30-redacted-scriptstruct-signatures.md](2026-05-30-redacted-scriptstruct-signatures.md)
- [2026-05-30-structure-return-only-policy-slice.md](2026-05-30-structure-return-only-policy-slice.md)
- [2026-05-30-structure-nonpin-copied-scalar-policy-slice.md](2026-05-30-structure-nonpin-copied-scalar-policy-slice.md)
- [2026-05-28-fname-index-manifest-plan.md](2026-05-28-fname-index-manifest-plan.md)
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
- [2026-05-29-reflection-inventory-pack-smoke.md](2026-05-29-reflection-inventory-pack-smoke.md)

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
| [2026-05-27-ops-restart-audit-instance-id.md](2026-05-27-ops-restart-audit-instance-id.md) | Ops restart audit after instance id | Records the read-only `/servidor/ark` audit, deleted library mappings, wrapper gap, restart plan, and verification commands. |
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
| [2026-05-30-aseapi-reference-scan.md](2026-05-30-aseapi-reference-scan.md) | AseApi reference scan | Allows ArkServerApi/AseApi as a names/behavior dictionary while banning copied offsets, vtables, MSVC ABI, Windows libs, direct UE pointer APIs, and direct memory access patterns. |
| [2026-05-30-chat-command-helper-roadmap.md](2026-05-30-chat-command-helper-roadmap.md) | Chat command helper roadmap | Defines a plugin-local, non-ABI helper pattern over `ChatMessageEvent` with `principal=unknown`, global config-only enablement, and no player permissions or chat response path. |
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
| [2026-05-27-server-send-chat-runtime-hit.md](2026-05-27-server-send-chat-runtime-hit.md) | Historical module runtime hit | Records accepted runtime observations and keeps SDK dispatch blocked until copied-data ownership is designed. |
| [2026-05-28-passive-chat-reflection-live-observation.md](2026-05-28-passive-chat-reflection-live-observation.md) | Passive module live observation | Records an operator-supplied Ragnarok log excerpt as passive runtime observer evidence, not SDK readiness. |
| [2026-05-28-second-source-core-intake-runbook.md](2026-05-28-second-source-core-intake-runbook.md) | Second-source core intake runbook | Defines the shortest offline evidence-pack and UFunction comparison path for an approved independent core artifact. |
| [2026-05-28-fname-index-manifest-plan.md](2026-05-28-fname-index-manifest-plan.md) | FName index manifest plan | Defines a binary-scoped manifest/resolver path so raw `FName` indices remain evidence-backed and fail closed by ARK binary hash. |
| [2026-05-29-module-surface-roadmap.md](2026-05-29-module-surface-roadmap.md) | Module surface roadmap | Ranks current module surfaces and keeps accepted compact target sets separate from public SDK promotion. |
| [2026-05-29-next-targetset-discovery.md](2026-05-29-next-targetset-discovery.md) | Next target-set discovery | Records accepted second-source layout evidence for mission and tribe compact target sets and ranks mission as the cleaner next module candidate. |
| [2026-05-29-mission-reflection-internal-readiness.md](2026-05-29-mission-reflection-internal-readiness.md) | Mission reflection internal readiness | Reviews the expanded `MissionReflectionTests` coverage and limits mission readiness to an internal recognizer/copy-readiness pack without public SDK, hook, dispatcher, identity, mutation, or return override promotion. |
| [2026-05-30-mission-copied-bool-observer-plan.md](2026-05-30-mission-copied-bool-observer-plan.md) | Mission copied-bool observer plan | Freezes the docs-only internal observer model for exactly four Mission functions, five copied bool fields, six redacted object/container fields, log grammar, gates, rollback, and non-goals without runtime or public SDK promotion. |
| [2026-05-29-reflection-inventory-pack-smoke.md](2026-05-29-reflection-inventory-pack-smoke.md) | Reflection inventory pack smoke | Validates the redacted candidate-only inventory pack builder on offline core evidence, with FName root ready and 8/8 requested target-set functions present. |
| [2026-05-29-gobjects-cross-manifest-comparison.md](2026-05-29-gobjects-cross-manifest-comparison.md) | GObjects cross-manifest comparison | Compares existing gobjects-sampling manifests across two copied cores, reinforcing `0x595b7e0` for internal offline work while keeping public GObjects, ResourceHandle, identity, lookup, mutation, and return override blocked. |
| [2026-05-29-ghidra-fuobjectarray-field-window-probe.md](2026-05-29-ghidra-fuobjectarray-field-window-probe.md) | Bounded Ghidra/r2 FUObjectArray probe | Records redacted internal evidence that the static GObjects candidate and serial accessors share one coherent field-window hypothesis for the current ARK binary hash. |
| [2026-05-29-resource-handle-nonzero-revalidation.md](2026-05-29-resource-handle-nonzero-revalidation.md) | ResourceHandle nonzero serial revalidation | Records `32/32` accepted offline samples with `32` nonzero serial candidates and proven GObjects field coherence, while keeping public ResourceHandle blocked on `uobject_flags_validity_semantics_unproven`. |
| [2026-05-29-uobject-flags-fullscan.md](2026-05-29-uobject-flags-fullscan.md) | UObject flags fullscan | Records full copied-core scans with thousands of nonzero serial candidates, zero `InternalIndex` mismatches, and no `0x100`/`0x4000` mask-positive samples, refining the ResourceHandle blocker. |
| [2026-05-29-weak-helper-flag-polarity.md](2026-05-29-weak-helper-flag-polarity.md) | Weak helper flag polarity | Refines `UObject+0x8` validity semantics from bounded static helper/caller evidence while keeping public ResourceHandle blocked. |
| [2026-05-29-resource-handle-flag-policy-candidate.md](2026-05-29-resource-handle-flag-policy-candidate.md) | ResourceHandle flag-policy candidate | Consolidates weak-helper caller-mode and nonzero readiness JSON into a short matrix: FName/GObjects/serial are not the main blocker; flag and lifecycle semantics keep post-callback handles blocked. |
| [2026-05-29-offline-evidence-canonicality.md](2026-05-29-offline-evidence-canonicality.md) | Offline evidence canonicality | Marks stale ResourceHandle evaluator output, dry-run plans, and duplicate GObjects reports so future rounds do not use them as independent promotion evidence. |
| [2026-05-29-dispatcher-hook-safety-hardening.md](2026-05-29-dispatcher-hook-safety-hardening.md) | Dispatcher hook safety hardening | Records Chat/Structure/Inventory dispatcher fail-closed behavior and reentrant unregister cleanup rules for hook-called dispatchers. |
| [2026-05-29-buff-compact-second-source-result.md](2026-05-29-buff-compact-second-source-result.md) | Buff compact second-source result | Records accepted second-source layout evidence for the three-target buff compact intake without promoting a public Buff SDK. |
| [2026-05-29-dino-compact-second-source-readiness.md](2026-05-29-dino-compact-second-source-readiness.md) | Dino compact second-source readiness | Records accepted second-source layout evidence for passenger/carry dino targets without promoting public Dino callbacks or identity. |
| [2026-05-29-item-compact-second-source-readiness.md](2026-05-29-item-compact-second-source-readiness.md) | Item compact second-source readiness | Records accepted strict second-source layout evidence for four compact `PrimalItem` targets without promoting public Items/Inventory SDKs, identity, mutation, return override, or ResourceHandle. |
| [2026-05-29-item-return-only-policy-bridge-plan.md](2026-05-29-item-return-only-policy-bridge-plan.md) | Item return-only bridge plan | Defines the safe post-RC internal path for item return-only observations without public Items SDK, dispatcher weakening, identity, mutation, return override, or ResourceHandle claims. |
| [2026-05-30-item-return-only-policy-slice.md](2026-05-30-item-return-only-policy-slice.md) | Item return-only policy slice | Adds an evidence-only report for exactly three copied `PrimalItem` return bools while excluding CraftBlueprint, non-return bools, object refs, mutation, return override, and public SDK claims. |
| [2026-05-29-inventory-action-redacted-signature-readiness.md](2026-05-29-inventory-action-redacted-signature-readiness.md) | Inventory action redacted signature readiness | Records candidate-only redacted signatures, accepted second-source layout evidence, and the next strict target-set consume-gate artifact flow for controller-side inventory use actions without promoting public Inventory/Items SDKs, `ItemNetID`, identity, mutation, return override, or ResourceHandle. |
| [2026-05-29-transfer-second-source-readiness.md](2026-05-29-transfer-second-source-readiness.md) | Transfer second-source readiness | Records accepted layout-only second-source evidence for seven transfer UFunctions and two transfer ScriptStructs, plus consume-mode redacted signatures, without promoting public Transfer SDKs, payload decoding, identity, mutation, return override, runtime hooks, or ResourceHandle. |
| [2026-05-30-transfer-scriptstruct-booltail-refresh.md](2026-05-30-transfer-scriptstruct-booltail-refresh.md) | Transfer ScriptStruct bool-tail refresh | Regenerates current `transfer-scriptstruct` second-source snapshots with bool-tail metadata preserved and accepts 2/2 targets as layout-only evidence. |
| [2026-05-29-transfer-copied-scalar-feasibility.md](2026-05-29-transfer-copied-scalar-feasibility.md) | Transfer copied-scalar feasibility | Ranks post-RC transfer copied-scalar candidates, with `ServerTransferredPlayerConfirmationResult.bAccept` as the only clean first internal candidate and no RC/public Transfer SDK claim. |
| [2026-05-30-redacted-scriptstruct-signatures.md](2026-05-30-redacted-scriptstruct-signatures.md) | Redacted ScriptStruct signatures | Adds candidate-only redacted ScriptStruct signature summaries from sanitized snapshots without replacing second-source readiness, payload decoding, runtime promotion, or SDK gates. |
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
