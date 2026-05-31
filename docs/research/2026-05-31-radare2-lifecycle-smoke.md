# Radare2 Lifecycle Orientation Smoke

Date: 2026-05-31

## Scope

This records one offline smoke of the candidate-only radare2 lifecycle window capture.
It is reviewer navigation only and is not artifact-gate, runtime, promotion, public SDK,
identity, permissions, command, lookup, mutation, or return-override evidence.

## Input

- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Expected SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Output root: `/tmp`

## Command

```bash
python3 scripts/capture_radare2_static_orientation_windows.py \
  --output-root /tmp \
  --run-id lifecycle-smoke-20260531T000000Z \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --target-group lifecycle \
  --timeout-sec 120 \
  --json \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
```

## Result

- Exit code: `0`
- Manifest: `/tmp/lifecycle-smoke-20260531T000000Z/manifest.json`
- Captured windows: 6
- Targets: `ShooterGameMode.HandleNewPlayer`, `ShooterGameMode.OnLogout`

The manifest remains `obelisk.radare2-static-orientation-windows.v1` with
`candidate_evidence_status=candidate_only_orientation`, `promotion_ready=false`,
`public_sdk_ready=false`, `runtime_ready=false`, and
`artifact_gate.may_gate_artifacts=false`.

## Non-Claims

This smoke does not prove lifecycle semantics, UFunction identity, object lookup,
ResourceHandle safety, mutation, return override, player identity, permissions,
commands/replies, or SDK readiness. It does not replace the required non-protected core
evidence pack, reflection inventory pack, focal snapshots, second-source evidence, or an
approved runtime validation window.
