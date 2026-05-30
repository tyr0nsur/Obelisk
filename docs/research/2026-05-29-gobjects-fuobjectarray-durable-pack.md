# GObjects FUObjectArray Durable Pack

## Objective

Move the current `GObjects` / `FUObjectArray` evidence out of `/tmp` into a durable,
offline-only evidence pack. This is internal research evidence for the current ARK binary
hash only; it does not promote public object identity, resource handles, mutation, return
overrides, or a runtime-stable `GUObjectArray` API.

Historical caveat: this pre-`cbf00bd` / `2a178ee` static-global pack is
pre-strict-identity evidence. Regenerate it with current producers before using it in
strict artifact-identity gates.

## Pack

```text
/servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z
```

Contents:

```text
field-window/fuobjectarray-field-window.redacted.json
static-global/manifest.json
static-global/static-global-xrefs.json
static-global/ShooterGameServer.objdump
static-global/ShooterGameServer.objdump.provenance.json
static-global/ShooterGameServer.readelf-programs.txt
static-global/ShooterGameServer.readelf-programs.txt.provenance.json
static-global/ShooterGameServer.readelf-sections.txt
static-global/ShooterGameServer.readelf-sections.txt.provenance.json
core-reconciliation/gobjects-reconciliation.json
```

The static artifacts were regenerated directly from the offline binary, so the consumable
manifest paths stay outside `/tmp` and outside protected live-server roots. No server was
attached, restarted, probed, or otherwise touched.

## Commands

```bash
mkdir -p \
  /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/field-window \
  /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/core-reconciliation

python3 scripts/convert_fuobjectarray_field_window_probe.py \
  --ghidra-stdout /tmp/obelisk-guobjectarray-field-window-ghidra-20260529/raw/ghidra-headless.stdout \
  --r2-windows /tmp/obelisk-guobjectarray-field-window-ghidra-20260529/raw/r2-target-windows.txt \
  --binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --candidate-address 0x595b7e0 \
  --tool-version ghidra=12.1 \
  --tool-version radare2=5.5.0 \
  --output /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/field-window/fuobjectarray-field-window.redacted.json

python3 scripts/build_static_global_promotion_evidence.py \
  --binary /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  --candidate gobjects=0x595b7e0 \
  --candidate-kind gobjects=gobjects \
  --fuobjectarray-field-window-evidence /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/field-window/fuobjectarray-field-window.redacted.json \
  --output-dir /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/static-global

python3 scripts/reconcile_gobjects_samples.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --gobjects-candidate 0x595b7e0 \
  --fname-root-slot 0x5956f30 \
  --sample-index package=0 \
  --sample-index object_class=1 \
  --sample-index primal_dino_character=225 \
  --sample-index shooter_cheat_manager=400 \
  --sample-index package_class=516 \
  --sample-index class_class=517 \
  --sample-index function_class=518 \
  --sample-index server_chat=25447 \
  --sample-index dino_add_passenger=19479 \
  --sample-index dino_allow_carry_character=19489 \
  --output /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/core-reconciliation/gobjects-reconciliation.json
```

## Result

Static pack summary:

```text
schema=obelisk.static-global-promotion-evidence.v1
binary.sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
candidate=gobjects address=0x595b7e0
candidate.static_contract.satisfied=true
candidate.static_contract.blockers=[]
promotion_gate.ready=false
promotion_gate.blockers=[static_only_evidence]
static artifact provenance verified=true for objdump/readelf artifacts
```

Core reconciliation summary:

```text
schema=obelisk.gobjects-sample-reconciliation.v1
sample_count=10
accepted_count=10
rejected_count=0
membership_pass_count=10
promotion_status=internal-only-single-artifact
```

## Accept Criteria

- All generated pack artifacts live under
  `/servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z`.
- The static manifest has no `/tmp` paths and no `/servidor/ark` paths outside
  `/servidor/ark/workspace-offline`.
- `static-global/manifest.json` records verified provenance for `objdump`,
  `readelf -l -W`, and `readelf -S -W`.
- The `gobjects` candidate has `static_contract.satisfied=true` after consuming the
  redacted FUObjectArray field-window evidence.
- The top-level static `promotion_gate.ready` remains `false` with
  `static_only_evidence`.
- The reconciliation report accepts the requested samples and keeps
  `promotion_status=internal-only-single-artifact`.

## Reject Criteria

- Any consumable manifest path points to `/tmp` or to a protected live-server root outside
  `/servidor/ark/workspace-offline`.
- Any copied or generated static artifact lacks verified provenance or has a mismatched
  binary/artifact SHA256.
- `promotion_gate.ready=true`, or the pack is cited as promoting public `GObjects`,
  `ResourceHandle`, object identity, lifetime, mutation, return overrides, or ABI changes.
- Any requested `GObjects` sample fails `InternalIndex` round-trip, target/class/outer
  membership, or bounds checks.
- Any validation requires ptrace, `gcore`, `ReflectionScanner`, marker changes, restarts,
  or live-server paths.

## Validation

```bash
rg --pcre2 -n "/tmp|/servidor/ark/(?!workspace-offline)" \
  /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/static-global/manifest.json \
  /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/field-window/fuobjectarray-field-window.redacted.json \
  /servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z/core-reconciliation/gobjects-reconciliation.json

python3 scripts/test_convert_fuobjectarray_field_window_probe.py
python3 scripts/test_reconcile_gobjects_samples.py
python3 scripts/test_build_static_global_promotion_evidence.py
```

Results:

```text
path scan: no matches
test_convert_fuobjectarray_field_window_probe.py: Ran 3 tests, OK
test_reconcile_gobjects_samples.py: Ran 8 tests, OK
test_build_static_global_promotion_evidence.py: Ran 42 tests, OK
```
