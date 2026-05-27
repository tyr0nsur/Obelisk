# Compact Context Snapshot

Updated: 2026-05-27

Use this file when conversation context is compacted or an agent needs to resume Obelisk
work from repository state instead of chat history.

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
- Ragnarok stable live posture:
  - `/servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook`
  - `/servidor/ark/obelisk/state/instances/arkserver/disable-plugins`
- Current development posture uses one active ARK instance:
  - active: `arkserver` / Ragnarok
  - stopped: `arkserver2` / TheIsland
- Do not restart servers, edit marker files, change `/servidor/ark`, or activate
  ReflectionScanner without explicit operator permission and an isolated/debug instance.
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
- No confirmed isolated/debug ARK instance exists right now.
- Ops plan now recommends creating `arkserver-obelisk-debug` with isolated ports/saves,
  no live cluster, debug-only `OBELISK_LOG_DIR`, and wrapper-level Obelisk env instead of
  map marker reuse; see
  `docs/research/2026-05-27-isolated-debug-instance-plan.md`.
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
- Offline core UObject enumeration now works through `scripts/enumerate_core_uobjects.py`.
  It found real chat-related `Function` objects in `GObjects`, including `ServerChat`
  index `25447`, `ServerChatTo` index `25449`, and `ServerChatToPlayer` index `25452`;
  see `docs/research/2026-05-27-core-uobject-enumeration.md`.
- Offline `UFunction` property-chain inspection now works through
  `scripts/inspect_core_ufunctions.py`. Current chat evidence:
  `ServerChat.MessageText` offset `0x0`; `ServerChatTo.SteamID` offset `0x0` and
  `MessageText` offset `0x10`; `ServerChatToPlayer.PlayerName` offset `0x0` and
  `MessageText` offset `0x10`.
- `scripts/inspect_core_ufunctions.py` supports offline `--name-contains` and
  `--outer-contains` filters for Function/Struct discovery from core dumps. Use broad
  substring searches only for discovery; runtime filters should stay exact
  FName+outer+ParmsSize+property-chain matches.
- `scripts/verify_chat_reflection_constants.py` verifies the current
  `ue/ChatReflection.cpp` constants against offline core evidence for `ServerChat*`,
  `ServerSendChatMessage`, and the metadata-only `ShooterPlayerController` candidates
  `ClientChatMessage`, `ClientServerChatDirectMessage`, and `ClientServerChatMessage`.
  It passed against
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
  with `--max-object-scan 30000`; rerun it before promoting chat reflection constants for
  a new binary/core.
- Current best hypothesis for real incoming player chat is not the `ServerChat*`
  watchlist. `ServerChat`, `ServerChatTo`, and `ServerChatToPlayer` have
  `ShooterCheatManager` outer evidence, while
  `ShooterPlayerController.ServerSendChatMessage` has FName index `2697`,
  `StrProperty ChatMessage` offset `0x0`, `ByteProperty SendMode` offset `0x10`, and
  `ParmsSize=0x11`; `SendMode` is `EChatSendMode` with `0 GlobalChat`,
  `1 GlobalTribeChat`, `2 LocalChat`, `3 AllianceChat`, and `>=4` invalid for
  logging/dispatch. This recognizer was deployed to `/servidor/ark/obelisk` on commit
  `df332d7`. Commit `8281123` adds reflected `send_mode` and `send_mode_name` logging;
  current `arkserver` PID is `3289000` after the later `e1071a7` deployment. See
  `docs/research/2026-05-27-real-chat-ufunction-path-hypotheses.md`.
- Deployed code has gated metadata-only recognizers for exact `ShooterPlayerController`
  candidates `ClientChatMessage`, `ClientServerChatMessage`, and
  `ClientServerChatDirectMessage`. They log `metadata_only=true`, do not decode text, do
  not dispatch plugin events, and do not change public ABI.
- Read-only audit `docs/research/2026-05-27-chat-reflection-no-hit-audit.md` confirms
  stable hook/gate posture for PID `3289000` but zero recognized chat hits in reviewed
  snapshots through `20260527T101357Z`; later logs supersede the missing-evidence state.
- Later read-only log review found accepted runtime `ServerSendChatMessage` hits at
  `14:07:27`, `14:17:13`, `16:12:02`, and `16:12:45` with `fname_index=2697`,
  `metadata_only=false`, `send_mode=0`, `send_mode_name=GlobalChat`, and bounded
  `ChatMessage` / `SendMode` ranges. This confirms the experimental runtime path but not
  a public SDK event; see
  `docs/research/2026-05-27-server-send-chat-runtime-hit.md`.
- Core-pack tooling now supports direct FName entry reads and bounded
  `--gobjects-candidate` previews for the next `GUObjectArray` investigation.
- Read-only overnight snapshots are documented in `docs/SUPERVISION.md` and implemented by
  `scripts/obelisk_supervisor_snapshot.sh`. They write to
  `/servidor/ark/obelisk/dumps/supervisor/`, fail closed on unstable posture, record
  PID/stable posture summary, and separate chat counters for `Reflected chat ProcessEvent`,
  `ServerSendChatMessage`, exact metadata-only fallback names, `metadata_only=true`,
  rejections, and `send_mode_known=false`. They must not restart, install, edit markers,
  attach debuggers, enable scanners, commit, or push.
- UE4 type reconstruction planning is captured in
  `docs/research/2026-05-27-ue4-type-reconstruction-roadmap.md`; keep the milestone
  order as `FName`, `GObjects`, `UFunction`, then bounded params.
- Current local Ragnarok logs do not contain a usable ReflectionScanner capture. The
  current GNames evidence audit is inconclusive because scanner logs only show
  `ReflectionScanner disabled`; see
  `docs/research/2026-05-27-current-gname-evidence-pack-audit.md`.
- `scripts/check_obelisk_server_posture.sh --expect-stable` is the required read-only
  guardrail after server debug work. It checks expected env, requires `libobelisk.so` to be
  mapped, rejects deleted Obelisk mappings, and has offline procfs fixture coverage in
  `scripts/test_check_obelisk_server_posture.sh`.
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

- Never enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` on live servers.
- Never enable raw chat discovery on live Ragnarok as a normal test.
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

- Ops: get permission to create or designate the isolated ARK debug instance; preferred
  plan is `arkserver-obelisk-debug`.
- Runtime chat: wait for one real in-game chat message and confirm
  `Reflected chat ProcessEvent` in `/servidor/ark/obelisk/logs/arkserver/Obelisk.log`.
- After a real hit, wire `RuntimeReflection::TryDecodeFStringUtf32` into the experimental
  logger and keep it gated/rate-limited; dispatch must only accept `EChatSendMode` `0..3`.
- `ue/RuntimeReflection.{h,cpp}` exists as the internal gated reader for
  `UObject`/`UFunction`/`UProperty`, bounded parameter ranges, and UTF-32 `FString`
  decoding. It is tested and used by hook-side chat observation.
- `ue/ChatReflection.{h,cpp}` exists as the internal recognizer for `ServerChat`,
  `ServerChatTo`, `ServerChatToPlayer`, `ServerSendChatMessage`, and exact metadata-only
  `ShooterPlayerController` fallback shapes. It is tested, returns borrowed param ranges,
  logs accepted `send_mode`/`send_mode_name`, and does not decode `FString` in runtime
  logs yet.
- `ProcessEvent_Detour` has experimental chat observation wiring, disabled unless
  `OBELISK_ENABLE_CHAT_REFLECTION=1` and `OBELISK_CHAT_REFLECTION_BINARY_SHA256` matches
  the supported ARK SHA. It logs metadata/ranges only, not text.
- `packaging/linuxgsm/ObeliskRun.sh` supports the
  `state/instances/<id>/enable-chat-reflection` marker for restart-time activation.
- Latest deployed runtime on `arkserver` includes commits through `e1071a7`, has chat
  reflection enabled and plugins disabled, PID `3289000`. It reached the experimental gate
  log after first ProcessEvent and later logged accepted `ServerSendChatMessage` hits.
- `FString` candidate for this ARK Linux build is a 16-byte
  `{Data, ArrayNum, ArrayMax}` header with UTF-32LE `TCHAR`; see
  `docs/research/2026-05-27-fstring-layout.md`.
- Pushed `main` wires `RuntimeReflection::TryDecodeFStringUtf32` into experimental
  `ServerSendChatMessage` logging through `ProcessEventChatReflection::TryDecodeUtf32Field`.
  Decoded text requires the extra `OBELISK_CHAT_REFLECTION_LOG_TEXT=1` gate, logs only for
  known `EChatSendMode` values, and does not dispatch plugins or change ABI. This is
  validated locally but not deployed to `/servidor/ark/obelisk`.
- Pushed `main` includes the excluded `chat_reflection_benchmark` target for synthetic
  recognizer and UTF-32 decode timing. It is useful for local regressions, but it does not
  include hook-side `GetFunctionNameIndex()` / `Memory::IsReadable()` overhead.
- `chat_reflection_benchmark` reports tail latency and allocation counts. Disabled and
  enabled non-chat hook-like paths are allocation-free locally; matched chat paths still
  allocate three temporary vectors/strings after reserve hardening and need justification or
  bounded stack/small-vector storage before SDK promotion. Text decode is measured with a
  non-SSO fixture string and currently shows seven allocations in the hook-like text path.
- Evidence: after any isolated scanner capture, run
  `scripts/build_reflection_evidence_pack.py` against copied logs and the matching binary
  before promoting candidates.
- Build/QA: keep package/export validation tied to concrete external plugin consumption
  gaps.
- Core runtime: extend PluginManager coverage only if a new lifecycle risk is identified;
  the main missing test surface has moved from basic lifecycle to packaging/export.
