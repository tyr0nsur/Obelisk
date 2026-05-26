# Obelisk Research Notes

This directory stores reproducible investigation notes for Obelisk runtime, UE4 reflection,
ARK server operations, and plugin experiments.

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
