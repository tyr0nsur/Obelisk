# Compact Context Snapshot

Updated: 2026-05-28

Use this file when conversation context is compacted or an agent needs to resume Obelisk
work from repository state instead of chat history.

## Active Operating Objective

- The persistent leader objective is tracked in the goal tool. Do not copy the full goal
  text into default sub-agent prompts.
- When delegating work, pass only the scoped objective, ownership, relevant skills, safety
  baseline, and expected deliverable for that agent's task.
- Safety remains first: no server restarts, `/servidor/ark` changes, marker edits,
  ReflectionScanner, ptrace/gcore, broad `ProcessEvent` tracing, or runtime observations
  without explicit operator approval for that run.
- Discord updates are reserved for major Obelisk milestones relevant to future
  mod/plugin creators; do not post routine development, validation, fixture, or research
  checkpoint updates.

## Current Repo State

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Current known good baseline: latest pushed and validated `main` after the 2026-05-27
  priority round. Check `git log --oneline -5` for the exact head if resuming after a
  compaction.
- Current development version line: `0.1.0-dev`. This is a coordination label, not a
  release tag. See `docs/VERSIONING.md`.
- Local ignored artifacts normally present: `build/`, `Obelisk.log`
- Do not commit built `.so` files, logs, server config, core dumps, or state markers.
- Server config restore notes: `docs/SERVER_RESTORE.md`
- Latest config backup symlink: `/home/flowcommunity-ark/backups/ark-config-latest`

## Production Server State

- ARK root: `/servidor/ark`
- Central Obelisk root: `/servidor/ark/obelisk`
- Gameplay config backup was created at
  `/home/flowcommunity-ark/backups/ark-config-20260527-015805`.
- Ragnarok stable live posture and current Obelisk development/test target:
  - `/servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook`
  - `/servidor/ark/obelisk/state/instances/arkserver/disable-plugins`
- Current operator direction as of 2026-05-28:
  - RAM is tight;
  - keep `arkserver2` / TheIsland stopped unless the operator explicitly reopens it;
  - use `arkserver` / Ragnarok as the Obelisk development/test harness;
  - risky probes on `arkserver` still need explicit approval for the exact run window and
    rollback plan.
- Operational correction on 2026-05-28: `arkserver2` stop was requested and confirmed
  already stopped; `arkserver` was restarted after removing
  `/servidor/ark/obelisk/state/instances/arkserver/enable-chat-reflection`. Current
  Ragnarok PID after restart: `1820244`. Read-only posture passes with
  `scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map
  Ragnarok --instance arkserver`.
- Exception already completed with explicit operator approval: `AllowCaveBuildingPvP=True`
  was applied to Ragnarok `GameUserSettings.ini` on 2026-05-27, `arkserver` was restarted,
  and a later read-only-agent protocol violation refreshed backup
  `/home/flowcommunity-ark/backups/ark-config-20260527-190558` as `ark-config-latest`.
- Do not restart servers, edit marker files, change `/servidor/ark`, or activate
  ReflectionScanner unless it is part of the current approved `arkserver` test window.
- Structure reflection is marker-gated in code and wrapper:
  `/servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection`.
  Env-only structure reflection activation is rejected; budget defaults to `0`.
- Stable posture rejects structure reflection env, and supervisor snapshots include
  `structure-reflection.txt`. Structure budget is reserved only after an exact structure
  FName filter passes.
- Inventory reflection now has an internal hook-side observer and test target. It remains
  disabled by default, marker/env/SHA/budget gated, metadata-only, and not a public SDK
  event.
- Runtime observer marker checks are centralized in `runtime/RuntimeMarkers.*`; unsafe
  path components, directory markers, symlink markers, and symlink instance directories are
  rejected before observers can enable.
- Second-source reversing gates are centralized in
  `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`. Current
  `FName`/`GObjects`/`UObject`/`UFunction` evidence remains candidate-only until a second
  isolated core or independent static path satisfies the matrix.
- `ue/BuffReflection.*` adds the next broad gameplay API building block: an offline
  internal `sdk.buffs` recognizer around exact compact `PrimalBuff` fixtures. Keep runtime
  hooks, callbacks, return overrides, raw object/class exposure, and gameplay mutation
  blocked.
- `sdk.transfers` ScriptStruct snapshots preserve target/property object and FName
  identity fields, while `regenerate_scriptstruct_snapshots.py --check-layout` remains a
  semantic/layout-only gate for second-source portability.
- `scripts/compare_reflection_snapshots.py --target Outer.Name` supports focused
  second-source checks for one UFunction or ScriptStruct without preparing a separate
  fixture root. Use `--list-target-sets` to print named intakes such as
  `minimal-second-source-intake` and `transfer-scriptstruct`.
- Second-source comparison now requires sanitized artifact identity in both roots:
  `artifact_kind`, `artifact_sha256`, `capture_id`, and `evidence_pack_id`. Missing or
  matching identity is `inconclusive`, so self-comparison cannot pass as independent
  evidence. Readiness JSON includes per-target details for evidence packs.
- UFunction and ScriptStruct regenerators accept the artifact identity flags above; the
  committed primary fixtures carry the primary core artifact SHA without storing core
  paths.
- CI and release validation now run reflection snapshot comparison and ScriptStruct
  fixture tests. README/STATUS present module-first observers and snapshot tooling instead
  of a chat-centered roadmap. Mixed-schema target-filter behavior is covered by tests.
- Public ProcessEvent callback lifecycle now includes owner-token handle registration:
  plugins can register with handle-returning owner-token functions and explicitly
  unregister through `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)`.
  Handles are process-local and must not be stored in shared cluster config or reused
  across ARK instances.
- Reflection/reversing/type-reconstruction skills now use the shared module promotion
  ladder and require explicit debug-window approval before marker edits, restarts,
  scanners, ptrace/gcore, or broad tracing. Public SDK guardrails now block premature
  gameplay module APIs, not only chat.
- Operational docs/skills outside `docs/research/` are guarded by
  `scripts/test_operational_doc_guardrails.py`, which blocks active marker/restart
  command examples from returning to install, supervision, or skill docs.
- `scripts/test_public_sdk_guardrails.py` is the canonical module-first public SDK
  guardrail; `test_public_sdk_chat_guardrails.py` remains a legacy wrapper.
- Commit `cd57189`:
  - supervisor default was aligned to `arkserver-obelisk-debug`;
  - CI/release/README were updated to run `scripts/test_obelisk_supervisor_snapshot.sh`;
  - `PluginManager::LoadPlugins` was hardened so already-loaded `plugin_id` values are
    skipped on repeated load attempts and duplicate handles are closed without duplicating
    callbacks.
- Current agent audit backlog:
  - runtime/API: owner-token callback handles, active-detour hook removal, owned
    debug-control shutdown, and `CallProcessEvent` pre-callback double-execution guard are
    implemented;
  - cluster/plugin config: shared config default creation is now safe for concurrent
    multi-instance startup; mutable shared plugin state still requires plugin-level
    locking/atomic-write design;
  - reflection/offline: second-source evidence is the bottleneck, and safe work should
    keep improving deterministic readiness/comparison tooling without touching live
    servers.
- Commit `6b9fe8a` documents `CallProcessEvent` reentrancy in the SDK
  header and plugin docs without changing ABI layout: pre-callbacks that call it must
  return `false` to avoid double execution; later runtime hardening added a guard that
  skips automatic original execution and warns if a pre-callback calls it and returns
  `true`.
- Commit `5cf3de7` adds internal `EventManager` registration IDs and
  `UnregisterCallback(id)` tests. Public `ObeliskApi` callback registration remains
  unchanged for ABI v1.
- Commit `f5d1b0e` tracks active ProcessEvent detour/trampoline frames and avoids
  unmapping the trampoline during hook removal until frames drain; on timeout it warns and
  intentionally leaves the trampoline mapped to avoid use-after-free.
- Commit `8519b2b` owns the debug-control thread and joins it before logger shutdown
  instead of detaching it.
- Commit `2095b1a` aligns ProcessEvent callback dispatch with chat dispatcher
  self-unregister behavior by using a recursive dispatch mutex and testing a callback that
  unregisters its own registration during dispatch. Public ABI remains unchanged.
- Commit `228ef7e` snapshots the ProcessEvent original
  trampoline under a hook-state mutex, starts the active-frame guard before public
  `CallOriginalProcessEvent` observes hook state, and makes hook removal mark `removing`
  under the same mutex before restoring bytes or unmapping the trampoline.
- Commit `0994d3f` makes global ProcessEvent callbacks runtime
  default-deny. `RegisterPreProcessEvent` and `RegisterPostProcessEvent` no-op with a
  warning unless `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1` and the per-instance
  marker `allow-global-process-event-callbacks` are both active. Filtered callbacks remain
  available by default and ABI v1 layout is unchanged.
- Global ProcessEvent callback gating uses the existing `OBELISK_ROOT` marker root, and
  stable posture checks reject `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS`.
- Commit `4e4f5cf` adds
  `scripts/compare_reflection_snapshots.py --readiness-report`. Use it to summarize
  comparable snapshot coverage and second-source status by schema/module. Current fixtures
  are layout-comparable: UFunction `35/35`, ScriptStruct `2/2`; both still need a real
  second sanitized snapshot root with independent artifact identity before promotion.
- Minimal second-source intake should run before expanding more gameplay surfaces:
  `PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory`,
  `PrimalStructure.AllowStructureAccess`, and `PrimalStructure.IsAllowedToDemolish`.
  Current readiness is `4/4` comparable and blocked only by missing second-source root.
- Latest restart audit:
  `docs/research/2026-05-27-ops-restart-audit-instance-id.md`
  - live `ObeliskRun.sh` exports `OBELISK_INSTANCE_ID=arkserver`
  - active process maps only central `libobelisk.so` and `libsubhook.so`
  - no active `ChatPlugin`, `ObeliskPlugins`, or deleted Obelisk mappings remain

## What Is Stable Enough

- LD_PRELOAD runtime bootstrap.
- Central install layout under `/servidor/ark/obelisk`.
- `OBELISK_INSTANCE_ID` separates logs and preferred state markers per LinuxGSM instance.
- Absolute x64 ProcessEvent hook with executable range and known prologue validation.
- ProcessEvent direct-offset fallback is removed from active runtime code; a unique
  signature match is required.
- C ABI plugin loading.
- Strict plugin metadata/config ABI:
  - plugins must export `ObeliskPlugin_GetInfo`
  - runtime creates/validates `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`
  - runtime skips `ObeliskPlugin_Init` when common config has `enabled=false` or the
    current `OBELISK_INSTANCE_ID` is not in `instance_allowlist`
  - duplicate `plugin_id` values are rejected during one load pass
  - `ObeliskPlugin_Init` receives `ObeliskPluginInitContext`
- Stable install only deploys runtime libraries; plugins are activated by placing `.so`
  files directly in `/servidor/ark/obelisk/plugins/`.
- Plugin-owned callback cleanup on init failure and unload.
- Optional plugin export: `extern "C" void ObeliskPlugin_Shutdown()`.
- `plugins/oBaseEvents` builds as the first official plugin example.
- Public docs present Obelisk as a Linux modding runtime/API/SDK. ARK/LinuxGSM are
  debug harness/adapters, not the project center.
- Top-level README has been refreshed for the SDK/runtime direction, current stability
  boundaries, install layout, plugin ABI, and roadmap.
- CTest is enabled. `PluginConfigTests` is the first offline C++ test suite and
  validates runtime-owned plugin config defaults and rejection paths.
- SDK/API baseline:
  - canonical public header is `include/obelisk/ObeliskApi.h`
  - `api/ObeliskApi.h` is a transition wrapper
  - `obelisk_sdk` is the CMake interface target
  - `AbiLayoutTests` locks ABI v1 layout on Linux x86_64
  - `AbiLayoutTests` currently fail if public chat capability is added before intentional
    ABI promotion
  - `tests/sdk_consumer` builds and loads a minimal external plugin against the public SDK
    through CTest
- `EventManagerTests` cover global/filtered pre callbacks, blocking behavior, post
  callbacks, owner cleanup, and null callback handling.
- Installed SDK layout validation exists through `scripts/test_install_obelisk_layout.sh`
  and is run by CI. The layout test now validates installed-header consumption, plugin
  placement, config dir/path, and instance id passed to a consumer plugin.
- `PluginManagerTests` cover plugin lifecycle and rejection paths with a fake loader:
  valid load/unload, missing entry points, invalid metadata, init failure, callback cleanup,
  shutdown, disabled/default config skip, instance allowlist skip, duplicate `plugin_id`,
  and close behavior.
- `PluginManager::UnloadAll()` unloads plugins in reverse load order and has a multi-plugin
  order test.
- The SDK now installs a CMake package export:
  `lib/cmake/Obelisk/ObeliskTargets.cmake`, `ObeliskConfig.cmake`, and
  `ObeliskConfigVersion.cmake`.
- Installed SDK layout validation consumes the installed package with
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED)` and `Obelisk::obelisk_sdk`, and
  rejects installed CMake package files that leak local source or build paths.
- Runtime install uses the CMake `Runtime` component for `libobelisk.so`, which preserves
  the intended installed `RUNPATH=$ORIGIN` and avoids build-tree dependency path leaks.
- Versioning policy is documented in `docs/VERSIONING.md`: no stable `0.1.0` tag yet;
  use `0.1.0-alpha.N` only for intentional contributor previews and `0.1.0-rc.N` only
  after scope freeze.

## What Is Experimental Or Blocked

- Legacy chat/monitor prototype source has been removed from the release tree.
- ReflectionScanner is experimental and must stay disabled on live servers.
- `arkserver` / Ragnarok is the current debug/development harness because the operator made
  it available and RAM is constrained. Keep `arkserver2` / TheIsland stopped unless the
  operator explicitly reopens it. High-risk scanners/native exec/ptrace still require an
  approved `arkserver` window and rollback plan.
- General-purpose SDK reflection is not solved yet. However, the current ARK binary has
  binary-hash-scoped evidence for FName, `GUObjectArray`, chat `UFunction` property chains,
  bounded param ranges, and an internal UTF-32 `FString` decoder candidate.
- Analyzer-level GNames table triage is available in
  `scripts/analyze_reflectionscanner_capture.py` and documented in
  `docs/research/2026-05-27-reflectionscanner-gname-table-triage.md`. A
  `research-candidate` label is evidence for follow-up only, not an accepted offset.
- Analyzer JSON now includes an `evidence_pack` block when run with copied logs. Use
  `--binary` to record the offline ShooterGameServer SHA256 and `--objdump-xrefs` to attach
  static xref evidence. Workflow:
  `docs/research/2026-05-27-gname-evidence-pack-workflow.md`.
- `scripts/build_reflection_evidence_pack.py` wraps that manual flow into a reproducible
  offline pack: copied logs, SHA256/file/readelf/objdump artifacts, analyzer JSON, and a
  manifest. It refuses to write artifacts under `/servidor/ark`.
- Analyzer static xref entries now include access classification (`load`, `store`,
  `address`, `call`, `jump`, or `other`) and evidence-pack access counts.
- ReflectionScanner can probe explicit static FName root slots supplied through
  `OBELISK_REFLECTION_STATIC_FNAME_ROOTS` at startup and through a one-minute delayed
  retry. Analyzer strict mode accepts a static-root research candidate only with exact
  `None`/`ClientMessage`/`ServerChat`, `header_index_ok=3/3`, plausible counts, and no
  reject markers; see
  `docs/research/2026-05-27-static-fname-root-probe.md`.
- ReflectionScanner can also sample observed `UObject.NamePrivate.ComparisonIndex` values
  against env-supplied static FName roots with
  `OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1`. Analyzer JSON records
  `static_fname_root_samples` and sample counts by status/reason/target; `--strict` does
  not pass from samples alone. See
  `docs/research/2026-05-27-static-fname-root-sampling.md`.
- First sampling capture produced 44 samples and all rejected with
  `implausible_num_elements`; this means the sampler currently rejects too early on
  counters that are known to be zero for the candidate table. Next runtime change should
  relax only the sampler path to read bounded entries while still logging counters.
- Authorized `arkserver` core dump evidence changed the FName status. With
  `OBELISK_DEBUG_ALLOW_PTRACE=1`, `gcore` captured PID `2902200` to
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z`. The server was then restored
  to stable posture. The core confirms static FName slot `0x5956f30 -> 0x2ae5c660`,
  `num_elements=0x4516e`, `num_chunks=0x12`, `0 -> None`,
  `4884 -> ClientMessage`, and `9619 -> ServerChat`; see
  `docs/research/2026-05-27-arkserver-core-fname-evidence.md`.
- Runtime scanner retest with corrected clues was still inconclusive through the old 60s
  retry window: the slot pointed to `0x30752660`, but counters and clue reads stayed zero.
  Static-root delayed retry has been extended to 10 minutes; see
  `docs/research/2026-05-27-static-root-runtime-retry-capture.md`.
- Runtime debug control now exists behind `OBELISK_ENABLE_DEBUG_CONTROL=1` and the
  `enable-debug-control` marker. It runs bounded probes after the server is alive and is
  forbidden by stable posture. First live post-start probe of `0x5956f30` rejected with
  `table=0x13733660` / `implausible_num_elements`; waiting longer in bootstrap is rejected
  as a strategy. See `docs/research/2026-05-27-runtime-debug-control.md`.
- Core evidence promotes `0x595b7e0` to `GUObjectArray research-candidate` for the current
  ARK binary hash. `0x595b7f0` points to chunks, count-like field at `0x595b804` is
  `1243796`, first object item resolves to `/Script/CoreUObject`, and its class resolves
  to `Package` through the confirmed FName table. See
  `docs/research/2026-05-27-core-gobjects-candidate.md`.
- `scripts/build_core_dump_evidence_pack.py` writes `gobjects-static-xrefs.json` for
  `--gobjects-candidate`, covering root, chunks, count, and serial fields. Offline
  validation for `0x595b7e0` found 3 root, 8016 chunks, 5870 count, and 2 serial xrefs.
  New packs record the Obelisk commit in `manifest.json`.
- Static context anchors for `0x595b7e0`: `0x79ce22` is lookup/bootstrap cache,
  `0x7a27a7` is init/destructor registration, `0x81f118` is startup reset, and
  `0x81f206` is startup helper. Labels are anchors only, not accepted function names; see
  `docs/research/2026-05-27-gobjects-static-anchor-classification.md`.
- `gobjects-static-xrefs.json` groups objdump xrefs by function anchor, but broad
  nearest-symbol groups can be contaminated. The `0x12d1400` group is not accepted as one
  decompiler target.
- Offline core UObject enumeration now works through `scripts/enumerate_core_uobjects.py`
  and has found real gameplay `Function` objects in `GObjects`; see
  `docs/research/2026-05-27-core-uobject-enumeration.md`.
- Do not restart `GObjects` discovery from broad candidate search. Current priority is a
  second static path for `0x595b7e0`: classify `0x12d1400`, `0x79ce22`, `0x7a27a7`,
  `0x81f118`, and `0x81f206`, then strengthen class/outer back-reference validation.
- No second isolated core is currently available; read-only dump inventory only found the
  existing Ragnarok-derived core and derivative packs. Current core/runtime captures should
  use the operator-approved `arkserver` window only after explicit approval for that run.
  Keep `arkserver2` stopped for RAM.
- Offline `UFunction` and `ScriptStruct` property-chain inspection now works through
  `scripts/inspect_core_ufunctions.py`. Treat module-specific offsets as candidate-only
  fixture evidence until second-source comparison and SDK ownership gates pass.
- `scripts/inspect_core_ufunctions.py` now validates target/class/outer/property objects
  with direct `GObjects[InternalIndex]` back-references; see
  `docs/research/2026-05-27-ufunction-membership-backrefs.md`.
- `scripts/inspect_core_ufunctions.py` supports offline `--name-contains` and
  `--outer-contains` filters for Function/Struct discovery from core dumps. Use broad
  substring searches only for discovery; runtime filters should stay exact
  FName+outer+ParmsSize+property-chain matches.
- `scripts/inspect_core_ufunctions.py` reports bounded enum candidates for `ByteProperty`
  through the observed `+0x70` enum pointer.
- historical module evidence: chat produced useful patterns for exact UFunction/outer/
  `ParmsSize`/property-chain recognition, bounded FString decoding, marker/env/SHA gates,
  dispatcher ownership, ABI guardrails, and benchmark gates. Keep details in
  `docs/research/2026-05-27-*chat*.md`, `docs/research/2026-05-27-fstring-layout.md`,
  and `docs/research/2026-05-27-sdk-chat-event-ownership-plan.md`.
- fact: chat remains internal/experimental only. The public SDK exposes no chat
  structs/capabilities/functions, runtime dispatch is blocked, and tests guard accidental
  promotion. Treat chat as one module proving promotion gates, not the active project
  center.
- Core-pack tooling now supports direct FName entry reads and bounded
  `--gobjects-candidate` previews for the next `GUObjectArray` investigation.
- Read-only overnight snapshots are documented in `docs/SUPERVISION.md` and implemented by
  `scripts/obelisk_supervisor_snapshot.sh`. They write to
  `/servidor/ark/obelisk/dumps/supervisor/`, fail closed on unstable posture, and must not
  restart, install, edit markers, attach debuggers, enable scanners, commit, or push.
- UE4 type reconstruction planning is captured in
  `docs/research/2026-05-27-ue4-type-reconstruction-roadmap.md`; keep the milestone
  order as `FName`, `GObjects`, `UFunction`, then bounded params.
- Current local Ragnarok logs do not contain a usable ReflectionScanner capture. The
  current GNames evidence audit is inconclusive because scanner logs only show
  `ReflectionScanner disabled`; see
  `docs/research/2026-05-27-current-gname-evidence-pack-audit.md`.
- `scripts/check_obelisk_server_posture.sh --expect-stable` is the required read-only
  guardrail after server debug work. It checks expected env, requires central
  `${OBELISK_ROOT}/lib/libobelisk.so` in `LD_PRELOAD` and maps, rejects deleted Obelisk
  mappings, and has offline procfs fixture coverage in
  `scripts/test_check_obelisk_server_posture.sh`.
- Add `--forbid-chat-reflection` to the posture check when validating
  production/performance or quiet-baseline posture. It rejects
  `OBELISK_ENABLE_CHAT_REFLECTION`, the chat SHA/log-limit env, and
  `OBELISK_CHAT_REFLECTION_LOG_TEXT`.
- Read-only quiet-posture audit at commit `5da65d6` found Ragnarok PID `3940524` still
  has `OBELISK_ENABLE_CHAT_REFLECTION=1`, so it fails the stricter
  production/performance guard. TheIsland was not running. Do not auto-fix this without an
  operator-approved restart window; see
  `docs/research/2026-05-27-quiet-posture-readonly-audit.md`.
- `scripts/obelisk_supervisor_snapshot.sh` writes `quiet-posture.txt` and
  `quiet_posture_status` so debug-stable snapshots do not hide active chat reflection from
  production/performance review.
- `Memory::IsReadable` was changed away from `write(/dev/null)` after local evidence showed
  that probe reports invalid and `PROT_NONE` mappings as readable. The replacement uses
  cached readable ranges from `/proc/self/maps` and has `MemoryTests`. Commit `257f432` is
  included in the deployed runtime; keep future scanner reads metadata-bounded and
  benchmark ProcessEvent overhead separately.
- A later controlled Ragnarok development capture on commit `8cb3bbe` produced 22
  UObject/UFunction leads and 22 FName reject rows, with zero positive FName probes.
  Rejection reasons were `implausible_num_elements` and `implausible_num_chunks`, so the
  chat UObject globals should not be promoted directly into GNames roots; see
  `docs/research/2026-05-27-live-fname-reject-capture.md`.
- A static-root probe for slot `0x5956f30` was added and retried for 60s. The slot becomes
  non-null (`table=0x41f8d660`) and has `header_index_ok=3/3`, but rejects with
  `num_elements=0`, `num_chunks=0`, and shifted names (`9619 -> ServerChat`,
  `9622 -> SetActiveMissionDebugFlags`). Do not accept it as GNames yet; next FName work
  should sample/validate using observed `UObject.NamePrivate` indices.
- A controlled Ragnarok development capture on commit `5754fca` tested
  `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`; the startup static-root probe rejected
  it with `table=0x0` / `unreadable_table_header`. The server was restarted afterward
  without scanner/static-root env. Treat this as inconclusive until a delayed retry or
  stronger static evidence; see
  `docs/research/2026-05-27-static-fname-root-live-capture.md`.

## Current Research Direction

Next technical milestone is `FName -> string` resolution:

1. Run `ReflectionScanner` only on a confirmed isolated/debug instance.
2. Use `docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md`.
3. Add `OBELISK_REFLECTION_LOG_FNAME_REJECTS=1` during isolated captures when we need
   diagnostic reasons for rejected FName candidates.
4. For the current static candidate, add
   `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30` only on an isolated/debug capture.
   To test observed object name indices instead of fixed clues, also add
   `OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1`.
5. Analyze copied logs with:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/isolated/Obelisk.log
objdump -d /path/to/ShooterGameServer > /tmp/ShooterGameServer.objdump
python3 scripts/analyze_reflectionscanner_capture.py \
  --json \
  --binary /path/to/ShooterGameServer \
  --objdump-xrefs /tmp/ShooterGameServer.objdump \
  /path/to/isolated/Obelisk.log
```

6. Treat indirect-table `GNames` only as a research candidate when `matched_clues=3/3` repeats for the
   same table pointer through distinct `source_global` values or distinct targets, and
   there are no reject markers.
7. Treat static-root `GNames` only as a research candidate when exact clue matches and
   `header_index_ok=3/3` appear with plausible counts and no reject markers. Static-root
   samples are supporting evidence only until promoted by a later gate.
8. Before committing offsets, require a second isolated capture or static xref validation.
   Static xrefs are supporting evidence only; inspect whether they are real load/store paths
   before designing runtime name-resolution code.

## Hard Rules

- Never enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` plus the
  `enable-native-exec-probes` instance marker on live servers.
- Never enable raw chat discovery on live Ragnarok as a normal test.
- Run Obelisk debug or reversing experiments on `arkserver` only within the current
  approved scope; keep `arkserver2` stopped while RAM is constrained.
- Do not reintroduce legacy map markers or binary-local `ObeliskPlugins` fallback.
- Do not treat observed FName indices such as `9619` or `9622` as stable API contracts.
- Do not promote plugins with HTTP, threads, or file readers until they implement and
  validate `ObeliskPlugin_Shutdown()`.
- Global ProcessEvent callbacks are debug-only unless documented and measured.

## Key Files To Read First

- `docs/agent-handoff/CURRENT.md`
- `docs/STATUS.md`
- `docs/PLUGIN_ARCHITECTURE.md`
- `docs/research/README.md`
- `agent-skills/obelisk-agent-handoff/SKILL.md`
- `agent-skills/obelisk-continuous-learning/SKILL.md`
- subsystem-specific skill under `agent-skills/`
- For reversing/static work also read:
  `agent-skills/obelisk-static-binary-analysis/SKILL.md`,
  `agent-skills/obelisk-ue4-type-reconstruction/SKILL.md`, and
  `agent-skills/obelisk-tooling-discipline/SKILL.md`.

## Next Good Rounds

- Ops: use `arkserver` / Ragnarok as the current development/test harness, keep
  `arkserver2` stopped for RAM, and keep scanner/native-exec/ptrace behind run-window
  approval.
- Reflection core: strengthen `RuntimeReflection`, snapshot fixtures, comparators,
  sanitizer tests, and evidence packs before adding public SDK module surfaces.
- Module breadth: use focused snapshot comparison for inventory, structures, buffs, dinos,
  tribes, missions, transfers, and admin candidates. Keep recognizers candidate-only until
  second-source evidence and ABI/lifetime policy are satisfied.
- Runtime safety: keep ProcessEvent observers gated by binary hash, markers, budgets, and
  explicit approval for the current `arkserver` window.
- SDK/API: promote public module APIs only after copied-data ownership, callback cleanup,
  installed SDK consumer coverage, and ABI layout tests are in place.
- Historical chat work remains internal and blocked from public SDK promotion; do not let
  it dominate new rounds unless the operator explicitly asks for that module.
- Evidence: after any isolated scanner capture, run
  `scripts/build_reflection_evidence_pack.py` against copied logs and the matching binary
  before promoting candidates.
- Build/QA: keep package/export validation tied to concrete external plugin consumption
  gaps.
- Core runtime: extend PluginManager coverage only if a new lifecycle risk is identified;
  the main missing test surface has moved from basic lifecycle to packaging/export.
