# Obelisk Research Notes

This directory stores reproducible investigation notes for Obelisk runtime, UE4 reflection,
ARK server operations, and plugin experiments.

## Index

| Note | Topic | Result |
| --- | --- | --- |
| [2026-05-27-runtime-and-chat-baseline.md](2026-05-27-runtime-and-chat-baseline.md) | Runtime and chat baseline | Documents the live-safe Ragnarok posture and chat discovery risk. |
| [2026-05-27-reflection-chat-metadata-audit.md](2026-05-27-reflection-chat-metadata-audit.md) | Reflection/chat metadata audit | Adds shared UE probe layouts and keeps object/UFunction tail logging gated. |
| [2026-05-27-reflection-scanner-candidate-validation.md](2026-05-27-reflection-scanner-candidate-validation.md) | ReflectionScanner candidate validation | Documents bounded UObject candidate scoring for isolated scanner captures. |
| [2026-05-27-fname-indirect-table-probe.md](2026-05-27-fname-indirect-table-probe.md) | FName indirect table probe | Adds bounded scanner-only GNames/FName indirect-array candidate logging. |
| [2026-05-27-reflectionscanner-isolated-capture-runbook.md](2026-05-27-reflectionscanner-isolated-capture-runbook.md) | ReflectionScanner isolated capture runbook | Documents flags, expected logs, GNames acceptance criteria, and rollback for the next isolated capture. |
| [2026-05-27-plugin-callback-ownership-hardening.md](2026-05-27-plugin-callback-ownership-hardening.md) | Plugin callback ownership | Documents callback owner-token cleanup on init failure and unload. |
| [2026-05-27-processevent-target-validation.md](2026-05-27-processevent-target-validation.md) | ProcessEvent target validation | Documents range/prologue validation before hook installation or direct-offset fallback. |
| [2026-05-27-subhook-reproducibility.md](2026-05-27-subhook-reproducibility.md) | Subhook reproducibility | Documents the local FetchContent commit pin and remaining mirror/vendor risk. |

Use one file per investigation:

```text
YYYY-MM-DD-short-topic.md
```

Each note should capture:

- Objective
- Environment: ARK binary path, SHA256, map/server, Obelisk commit, plugins state
- Hypothesis
- Evidence: relevant log snippets, addresses, signatures, command summaries
- Result: confirmed, rejected, or inconclusive
- Risks
- Next steps

Keep raw logs out of Git. Summarize the important lines and reference the local log path when
needed.
