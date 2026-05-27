# Obelisk Research Notes

This directory stores reproducible investigation notes for Obelisk runtime, UE4 reflection,
ARK server operations, and plugin experiments.

Notes written before `OBELISK_INSTANCE_ID` may mention obsolete map-based marker files and
root-level map logs. New research should record the LinuxGSM instance id, map, ARK binary
hash, and runtime flags.

## Index

| Note | Topic | Result |
| --- | --- | --- |
| [2026-05-27-runtime-and-chat-baseline.md](2026-05-27-runtime-and-chat-baseline.md) | Runtime and chat baseline | Documents the live-safe Ragnarok posture and chat discovery risk. |
| [2026-05-27-reflection-chat-metadata-audit.md](2026-05-27-reflection-chat-metadata-audit.md) | Reflection/chat metadata audit | Adds shared UE probe layouts and keeps object/UFunction tail logging gated. |
| [2026-05-27-reflection-scanner-candidate-validation.md](2026-05-27-reflection-scanner-candidate-validation.md) | ReflectionScanner candidate validation | Documents bounded UObject candidate scoring for isolated scanner captures. |
| [2026-05-27-fname-indirect-table-probe.md](2026-05-27-fname-indirect-table-probe.md) | FName indirect table probe | Adds bounded scanner-only GNames/FName indirect-array candidate logging. |
| [2026-05-27-reflectionscanner-isolated-capture-runbook.md](2026-05-27-reflectionscanner-isolated-capture-runbook.md) | ReflectionScanner isolated capture runbook | Documents flags, expected logs, GNames acceptance criteria, and rollback for the next isolated capture. |
| [2026-05-27-reflectionscanner-isolated-instance-audit.md](2026-05-27-reflectionscanner-isolated-instance-audit.md) | ReflectionScanner isolated instance audit | Records read-only evidence that no confirmed isolated/debug ARK instance currently exists. |
| [2026-05-27-isolated-debug-instance-plan.md](2026-05-27-isolated-debug-instance-plan.md) | Isolated debug instance plan | Plans a new LGSM debug instance with isolated ports, saves, cluster posture, Obelisk env, rollback, and permission checklist. |
| [2026-05-27-arkserver2-debug-pivot.md](2026-05-27-arkserver2-debug-pivot.md) | arkserver2 debug pivot | Records the operational pivot: protect Ragnarok performance testing and use TheIsland for Obelisk debug/development windows. |
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
| [2026-05-27-general-ufunction-inventory.md](2026-05-27-general-ufunction-inventory.md) | General UFunction inventory | Adds a broad offline UFunction inventory so future roadmap work can target players, dinos, items, and commands beyond chat. |
| [2026-05-27-runtime-chat-reflection-plan.md](2026-05-27-runtime-chat-reflection-plan.md) | Runtime chat reflection plan | Defines the safe internal path from reflected chat evidence to a gated `ProcessEvent` filter. |
| [2026-05-27-chat-reflection-no-hit-audit.md](2026-05-27-chat-reflection-no-hit-audit.md) | Chat reflection no-hit audit | Historical read-only snapshot that found stable hook/gate posture but no recognized chat hits in the reviewed window; later runtime-hit evidence supersedes its next step. |
| [2026-05-27-server-send-chat-runtime-hit.md](2026-05-27-server-send-chat-runtime-hit.md) | ServerSendChatMessage runtime hit | Records accepted runtime `ServerSendChatMessage` observations with `send_mode=0` and keeps SDK dispatch blocked until copied text ownership is designed. |
| [2026-05-27-sdk-chat-event-ownership-plan.md](2026-05-27-sdk-chat-event-ownership-plan.md) | SDK chat event ownership plan | Defines ownership, ABI, callback cleanup, and validation gates required before a public `OnChatMessage` API. |
| [2026-05-27-chat-sdk-abi-preflight.md](2026-05-27-chat-sdk-abi-preflight.md) | Chat SDK ABI preflight | Defines the test-first ABI and dispatcher gates for future `OnChatMessage` without changing the public header yet. |
| [2026-05-27-theisland-chat-reflection-ab-runbook.md](2026-05-27-theisland-chat-reflection-ab-runbook.md) | TheIsland chat reflection A/B runbook | Defines the approved-window flow for reflection off, metadata-only on, text logging on, and rollback without touching Ragnarok. |
| [2026-05-27-isolated-second-core-runbook.md](2026-05-27-isolated-second-core-runbook.md) | Isolated second core runbook | Defines the approved-window flow for a second isolated core capture, preferring `arkserver-obelisk-debug` and keeping Ragnarok untouched. |
| [2026-05-27-quiet-posture-readonly-audit.md](2026-05-27-quiet-posture-readonly-audit.md) | Quiet posture read-only audit | Confirms the stricter production/performance guard detects chat reflection active on Ragnarok and that TheIsland is not currently running. |
| [2026-05-27-ragnarok-readonly-posture-snapshot.md](2026-05-27-ragnarok-readonly-posture-snapshot.md) | Ragnarok read-only posture snapshot | Records a supervisor snapshot showing stable posture with chat reflection still active, requiring a future maintenance window for quiet posture. |
| [2026-05-27-shootergamemode-chat-candidates.md](2026-05-27-shootergamemode-chat-candidates.md) | ShooterGameMode chat candidates | Validates `SendServerChatMessage` and `OnServerChatMessage__DelegateSignature` as exact metadata-only fallback recognizers from offline core evidence. |
| [2026-05-27-isreadable-dev-null-hotpath.md](2026-05-27-isreadable-dev-null-hotpath.md) | `Memory::IsReadable` hot-path audit | Rejects `write(/dev/null)` as a Linux readability probe and recommends cached maps checks plus direct UE-owned hot-path reads. |
| [2026-05-27-fstring-layout.md](2026-05-27-fstring-layout.md) | FString layout candidate | Promotes UTF-32LE `FString` as the internal decoder candidate for reflected `StrProperty` chat params. |
| [2026-05-27-chat-reflection-stack-cycle-guard.md](2026-05-27-chat-reflection-stack-cycle-guard.md) | Chat reflection stack cycle guard | Removes one matched-path allocation by replacing temporary property-cycle vector storage with a fixed stack guard. |
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
