# Radare2 Static Orientation Wrapper

Date: 2026-05-31T00:00:00Z

`scripts/capture_radare2_static_orientation_windows.py` captures bounded radare2
disassembly windows for reviewed player identity, admin, and chat-response UFunction
candidate addresses against an offline `ShooterGameServer` binary.

This wrapper is candidate-only orientation tooling. Its manifest is not artifact-gate
evidence, is not accepted promotion evidence, and must not be consumed in promote mode.

## Default Scope

- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Expected SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Address convention: non-PIE ELF VMA for the reviewed ARK Linux binary.
- Default output root:
  `/tmp/obelisk-radare2-static-orientation`
- Target groups:
  `player-identity`, `admin`, and `chat-response`.

## Repro Command

```bash
python3 scripts/capture_radare2_static_orientation_windows.py \
  --output-root /tmp/obelisk-radare2-static-orientation \
  --run-id <safe-run-id> \
  --json
```

The wrapper rejects protected live-server input paths and rejects any output root under
`/servidor/ark`, including `/servidor/ark/workspace-offline`, because these captures are
scratch orientation outputs and should stay under `/tmp` or another explicit
non-protected root.

Each run writes:

- `manifest.json` with binary SHA256, expected SHA256, radare2 path/version probe,
  Obelisk commit, exact argv for every window, non-claims, blockers, and artifact-gate
  false fields.
- `windows/*.r2.txt` with one bounded `pd` window per candidate registration/thunk/FName
  init address.

## Verification Run

On 2026-05-31, a real offline smoke run used `/usr/bin/radare2` 5.5.0 and wrote:

```text
/tmp/obelisk-radare2-static-orientation/codex-verification-20260531/manifest.json
```

The run reported:

- `status`: `candidate_only_orientation_captured`
- `binary_sha256`: `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- `blockers`: `[]`
- `artifact_gate.registered`: `false`
- `promotion_ready`, `public_sdk_ready`, `runtime_ready`: `false`

No live server paths, restarts, markers, runtime probes, ptrace, core inspection, Discord,
or Git operations were used.

## Promotion Limitations

These radare2 windows are navigation context only. They do not prove `UFunction` object
identity, FName indices, property chains, parameter offsets, player principal mapping,
permissions, commands, chat replies, lifecycle semantics, public SDK readiness, runtime
readiness, object lookup, `ResourceHandle`, mutation, or return override.

Promotion still requires the relevant non-protected complete core evidence pack, reviewed
reflection inventory or focal snapshots, second-source layout evidence, privacy and
invalidation policy where applicable, and separately approved runtime validation if that
lane is ever resumed.
