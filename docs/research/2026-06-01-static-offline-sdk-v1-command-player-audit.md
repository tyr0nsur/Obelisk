# Static Offline SDK v1 Command/Player Audit

Date: 2026-06-01

## Scope

This note audits whether already-existing offline artifacts can support an additional
useful SDK v1 report for command response or player identity. It is read-only evidence
triage plus this documentation note. No servers, live logs, runtime probes, new dumps,
Git, Discord, ArkApi/AseApi source, protected dump paths, or `/servidor/ark` writes were
used.

## Result

The existing offline artifacts support one useful additional report class: a
cross-route blocker/status report that ties player principal, permissions/admin, command
response path, and commands/replies together without promoting any SDK surface.

They do not support a new public SDK, runtime readiness, command reply, send-chat,
player identity, permission, lookup, mutation, return override, `ResourceHandle`, raw UE
pointer, raw `FString`, FName/GObjects, or cross-instance identity claim.

## Evidence

Reviewed command/chat response root:

```text
/servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601/
```

Relevant files:

```text
manifest.json
command-chat-response-route-planning-readiness.json
base-snapshots/ShooterPlayerController.ClientChatMessage.snapshot.json
base-snapshots/ShooterPlayerController.ClientServerChatDirectMessage.snapshot.json
base-snapshots/ShooterPlayerController.ClientServerChatMessage.snapshot.json
vanilla-gdb-snapshots/ShooterPlayerController.ClientChatMessage.snapshot.json
vanilla-gdb-snapshots/ShooterPlayerController.ClientServerChatDirectMessage.snapshot.json
vanilla-gdb-snapshots/ShooterPlayerController.ClientServerChatMessage.snapshot.json
```

The manifest is
`obelisk.command-chat-response-route-planning-distinct-second-source.v1`, status
`candidate-only`, target set `command-chat-response-route-planning`. It records distinct
base/candidate core identities:

- base core artifact SHA256:
  `62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78`;
- candidate core artifact SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`.

The readiness report is `obelisk.reflection-snapshot-readiness.v1` with
`targets=3`, `second_source_accepted=3`, `second_source_inconclusive=0`,
`second_source_rejected=0`, `planning_layout_gate.ready=true`,
`ready_scope=planning_only`, `promotion_ready=false`, `public_sdk_ready=false`, and
`runtime_ready=false`.

Reviewed player identity/principal policy root:

```text
/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/
```

Relevant files:

```text
players-identity-lifecycle-anchor-candidates.json
players-identity-principal-invalidation-policy.json
```

The lifecycle anchor checker accepts `ShooterGameMode.HandleNewPlayer` as the candidate
start target and `ShooterGameMode.OnLogout` as the candidate end target. The principal
policy checker accepts the consume-only policy shape and keeps `promotion_ready=false`,
`public_sdk_ready=false`, and `runtime_ready=false`.

The combined player-identity readiness checker reports 12/12 fixture coverage, accepted
reflection inventory, accepted second-source layout, accepted lifecycle anchors and
principal policy, then exits blocked on `approved_runtime_evidence_missing`. That is the
correct current blocker.

## Repro Commands

```bash
find /servidor/ark/workspace-offline -maxdepth 4 -type f \
  \( -iname '*identity*' -o -iname '*player*' -o -iname '*principal*' \
     -o -iname '*command*' -o -iname '*response*' -o -iname '*routing*' \) \
  -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601 \
  --manifest /servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601/manifest.json \
  --mode consume --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_chat_response_public_readiness.py --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_commands_replies_public_readiness.py --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z \
  --manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-lifecycle-anchor-candidates.json \
  --mode consume --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z \
  --manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-principal-invalidation-policy.json \
  --mode consume --json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_lifecycle_anchor_candidates.py \
  --json /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-lifecycle-anchor-candidates.json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_principal_invalidation_policy.py \
  --json /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-principal-invalidation-policy.json

PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_identity_first_evidence_readiness.py \
  --artifact-root /servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z \
  --candidate-root /servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots \
  --lifecycle-anchor-candidates-manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-lifecycle-anchor-candidates.json \
  --principal-invalidation-policy-manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-principal-invalidation-policy.json \
  --json
```

Expected last-command status is blocked/non-zero because
`approved_runtime_evidence_missing` remains the primary blocker.

## Limits

- Static and offline evidence is sufficient for planning/status only.
- Command response still depends on promoted player principal and permissions/admin
  before any copied response contract can be considered.
- Commands/replies remain post-v1/planning-only in the current checks.
- Player identity still needs approved copied runtime principal lifecycle evidence before
  public ABI review.
- No direct live log, protected dump, server marker, wrapper, runtime process, or new
  dump was read or modified.
- `/servidor/ark/workspace-offline` was read as an approved offline artifact root only;
  no files were written there.

## Paths Touched

Read:

```text
agent-skills/obelisk-static-binary-analysis/SKILL.md
agent-skills/obelisk-ue4-reversing/SKILL.md
agent-skills/obelisk-tooling-discipline/SKILL.md
docs/agent-handoff/CURRENT.md
docs/research/2026-05-31-command-chat-response-static-orientation.md
docs/research/2026-05-31-command-chat-response-thunk-orientation.md
docs/research/2026-05-31-commands-principal-routing-contract.md
docs/research/2026-06-01-player-principal-policy-route.md
docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md
docs/research/2026-06-01-player-principal-runtime-observer-brief.md
docs/research/2026-06-01-player-principal-runtime-window-brief-template.md
docs/research/2026-06-01-sdk-offline-evidence-routing-audit.md
scripts/check_command_chat_response_public_readiness.py
scripts/check_commands_replies_public_readiness.py
scripts/check_player_identity_first_evidence_readiness.py
scripts/check_player_identity_lifecycle_anchor_candidates.py
scripts/check_player_identity_principal_invalidation_policy.py
scripts/validate_offline_artifact_gate.py
/servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601/
/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/
/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z/
/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots/
```

Written:

```text
docs/research/2026-06-01-static-offline-sdk-v1-command-player-audit.md
```
