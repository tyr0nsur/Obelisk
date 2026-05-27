# Current Agent Handoff

Updated: 2026-05-27

## Stable Baseline

- fact: Compact recovery context is stored in `docs/agent-handoff/COMPACT_CONTEXT.md` for
  resuming after conversation compaction.
- fact: ARK config restore notes are in `docs/SERVER_RESTORE.md`; latest config backup
  symlink is `/home/flowcommunity-ark/backups/ark-config-latest`.
- fact: Obelisk central install root is `/servidor/ark/obelisk`.
- fact: Stable installer deploys runtime libraries only. Plugins activate only when their
  `.so` is copied into `/servidor/ark/obelisk/plugins/`; inactive plugins stay outside the
  install root.
- fact: Contributor-facing stability matrix is documented in `docs/STATUS.md`.
- fact: Ragnarok stable baseline is ProcessEvent hook enabled with plugins disabled.
  Preferred markers are
  `/servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook` and
  `/servidor/ark/obelisk/state/instances/arkserver/disable-plugins`.
- fact: Operator direction changed on 2026-05-27: `arkserver` / Ragnarok is reserved for
  player performance testing. Do not restart, redeploy, change markers, enable extra
  logging, scan, ptrace, or run debug experiments there without an explicit maintenance
  window.
- fact: Operator explicitly approved a Ragnarok gameplay config change on 2026-05-27:
  `AllowCaveBuildingPvP=True` was applied to `GameUserSettings.ini`, pre-change backup is
  `/home/flowcommunity-ark/backups/ark-config-manual/GameUserSettings.ini.allow-cave-20260527-184547.bak`,
  `arkserver` was restarted successfully. A later read-only-agent protocol violation
  repeated the backup/restart; current `ark-config-latest` is
  `/home/flowcommunity-ark/backups/ark-config-20260527-190558`, and Ragnarok is up as PID
  `3940524`.
- fact: `arkserver2` / TheIsland is now the designated Obelisk debug/development target.
  Use it for controlled runtime validation and research harness work instead of Ragnarok,
  while still requiring explicit per-run approval for ReflectionScanner, native exec,
  ptrace/gcore, broad ProcessEvent traces, or chat text logging.
- fact: Runtime/chat baseline is documented in
  `docs/research/2026-05-27-runtime-and-chat-baseline.md`.
- fact: Reflection/chat metadata audit added shared UE probe layouts and gated
  ReflectionScanner object/UFunction tail logging; see
  `docs/research/2026-05-27-reflection-chat-metadata-audit.md`.
- fact: ReflectionScanner now logs bounded UObject candidate validation scores and avoids
  unchecked executable-field reads past verified memory; see
  `docs/research/2026-05-27-reflection-scanner-candidate-validation.md`.
- fact: ReflectionScanner now includes a bounded FName indirect-table candidate probe for
  already-discovered globals; see
  `docs/research/2026-05-27-fname-indirect-table-probe.md`.
- fact: The next isolated ReflectionScanner capture has a reproducible runbook with
  flags, expected logs, GNames accept/reject criteria, and rollback; see
  `docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md`.
- fact: Earlier read-only ops audit found no confirmed isolated/debug ARK instance on
  `/servidor/ark`; the operator has now designated `arkserver2` / TheIsland for debug and
  development, but historical caveats still apply for high-risk scanners unless a specific
  run window is approved. See
  `docs/research/2026-05-27-reflectionscanner-isolated-instance-audit.md`.
- fact: Ops planning recommends a new `arkserver-obelisk-debug` LinuxGSM instance with
  isolated ports, saves, cluster posture, `OBELISK_LOG_DIR`, and wrapper-level Obelisk
  env instead of shared map markers; see
  `docs/research/2026-05-27-isolated-debug-instance-plan.md`.
- fact: Runtime and wrapper were redeployed from the central install root after removing
  legacy marker fallbacks. Historical audit recorded `arkserver` active and `arkserver2`
  stopped; current operational policy is to avoid Ragnarok for development and use
  `arkserver2` for future debug windows. See
  `docs/research/2026-05-27-ops-restart-audit-instance-id.md`.
- fact: `scripts/analyze_reflectionscanner_capture.py` passively summarizes copied
  ReflectionScanner logs for UObject scores, FName `matched_clues`, delayed globals, and
  reject markers; it does not touch server state.
- fact: Commit `c890c2a` tightened FName probe confirmation. ReflectionScanner now logs
  `source_global` for FName indirect-table probes, and the analyzer only treats exact
  hits as repeat-confirmed when the same table appears from distinct source globals or
  distinct targets; see `docs/research/2026-05-27-reflectionscanner-analyzer-review.md`.
- fact: Top-level CMake now pins FetchContent dependencies to full local checkout SHAs:
  `fmt` `f5e54359df4c26b6230fc61d38aa294581393084`, `spdlog`
  `7e635fca68d014934b4af8a1cf874f63989352b7`, and `subhook`
  `568d2e5a5d6013907e8008857968906b33ef3b7d`; see
  `docs/research/2026-05-27-subhook-reproducibility.md`.
- fact: Commit `f755c43` repositioned public docs around Obelisk as a Linux
  modding runtime/API/SDK. ARK/LinuxGSM are now framed as debug harness/adapters,
  not the project center.
- fact: Commit `27de1fb` enabled CTest and added offline `PluginConfigTests`.
  The suite covers safe-disabled default creation, metadata rejection, corrupt JSON,
  `instance_allowlist` typing, and preserving existing valid config.
- fact: Commit `e9dfbaf` added the canonical SDK header at
  `include/obelisk/ObeliskApi.h`, kept `api/ObeliskApi.h` as a transition wrapper,
  made `oBaseEvents` consume `obelisk_sdk`, and added `AbiLayoutTests`.
- fact: Commit `065d68d` refreshed the top-level README around the current SDK/runtime
  direction, stable/experimental boundaries, install layout, plugin ABI, and roadmap.
- fact: Commit `ef6cfc5` added an SDK consumer fixture that builds a minimal external
  plugin against `obelisk_sdk`, loads it with `dlopen`, validates the metadata/config ABI,
  and runs under CTest. CI now also runs CTest and `git diff --check`.
- fact: Commit `1cacbca` added analyzer-level GNames table triage. The analyzer groups
  FName indirect-table probes by table pointer, labels table groups as
  `research-candidate` or `rejected`, and keeps strict mode tied to repeat-confirmed table
  evidence.
- fact: Commit `ea2f63f` added `EventManagerTests` for global/filtered pre callbacks,
  blocking behavior, post callbacks, owner cleanup, and null callback handling.
- fact: Commit `f5ab352` runs installed SDK layout validation in CI through
  `scripts/test_install_obelisk_layout.sh`.
- fact: Development versioning policy is documented in `docs/VERSIONING.md`. The current
  line is `0.1.0-dev`, not a release tag; use alpha/rc tags only when external testing or
  release-candidate validation needs a fixed checkpoint.
- fact: `README.md`, `docs/STATUS.md`, `docs/RELEASE.md`, and
  `scripts/test_versioning_guardrails.py` now link/enforce the pre-release versioning
  policy so `0.1.0-dev` is not presented as a stable release.
- fact: `scripts/test_secret_guardrails.py` and CI now reject committed Discord webhook
  URLs, keeping community update endpoints out of versioned files.
- fact: Commit `fc837a0` added passive static xref annotation to
  `scripts/analyze_reflectionscanner_capture.py`. Use `--objdump-xrefs` with a
  pre-generated `objdump -d` text file to annotate candidate globals; this is supporting
  evidence only, not offset acceptance.
- fact: Commit `ac6eada` added `PluginManagerTests` using an injectable fake library
  loader. The suite covers valid load/unload, missing `GetInfo`, missing `Init`, invalid
  metadata, init failure, callback cleanup, shutdown, and close behavior.
- fact: Plugin activation is now runtime-gated: `PreparePluginConfig` returns
  `enabled` and `instance_allowed`, `PluginManager` skips `ObeliskPlugin_Init` for
  `enabled=false` or non-matching `instance_allowlist`, duplicate `plugin_id` values are
  rejected, and default config creation uses a temp file plus rename.
- fact: Commit `882f0d7` hardened `scripts/test_install_obelisk_layout.sh` so the installed
  SDK consumer validates config dir/path, instance id, installed-header dependency, and
  plugin placement under the install root.
- fact: Commit `3760f3b` clarified that sub-agents may recommend skill changes, but the
  team lead owns skill edits, commits, pushes, and handoff updates.
- fact: Commit `2420e82` added the static/reversing workflow skills:
  `obelisk-static-binary-analysis`, `obelisk-tooling-discipline`, and
  `obelisk-ue4-type-reconstruction`.
- fact: Commit `502752f` makes `PluginManager::UnloadAll()` unload plugins in reverse
  load order and adds a multi-plugin order test.
- fact: Commit `ff245d4` installs the public SDK as a CMake package export
  (`ObeliskTargets.cmake`, `ObeliskConfig.cmake`, and version file), updates the installer
  SDK component, and validates installed consumption through `find_package`.
- fact: The installed layout test now consumes the installed SDK through
  `find_package(Obelisk CONFIG REQUIRED)` and `Obelisk::obelisk_sdk`, so package export
  regressions are covered by `scripts/test_install_obelisk_layout.sh`.
- fact: Commit `f24152f` adds analyzer evidence pack metadata. Use
  `scripts/analyze_reflectionscanner_capture.py --json --binary <ShooterGameServer>
  --objdump-xrefs <objdump.txt> <Obelisk.log>` to record Obelisk commit, binary SHA256,
  copied logs, objdump artifact, candidate counts, reject markers, and promotion gate.
  The workflow is documented in
  `docs/research/2026-05-27-gname-evidence-pack-workflow.md`.
- fact: `scripts/build_reflection_evidence_pack.py` builds a reproducible offline evidence
  pack from a ShooterGameServer binary and copied Obelisk logs. It copies logs, records
  SHA256/file/readelf/objdump artifacts, runs analyzer JSON with `--binary` and
  `--objdump-xrefs`, writes `manifest.json`, and refuses to write artifacts under
  `/servidor/ark`.
- fact: `scripts/check_obelisk_server_posture.sh --expect-stable` now fails closed if
  `libobelisk.so` is not mapped, if a deleted `libobelisk` mapping remains, or if scanner
  / native-exec env vars are present. Offline procfs fixture coverage is in
  `scripts/test_check_obelisk_server_posture.sh`.
- fact: `scripts/check_obelisk_server_posture.sh --forbid-chat-reflection` adds a
  production/performance posture guard that rejects experimental chat reflection and chat
  text logging env. Use it with `--expect-stable` for Ragnarok player-performance checks
  and for TheIsland Phase A / rollback checks.
- fact: Read-only quiet-posture audit at commit `5da65d6` found Ragnarok PID `3940524`
  still has `OBELISK_ENABLE_CHAT_REFLECTION=1`, so it fails the stricter
  production/performance guard. TheIsland was not running. Do not auto-fix this without an
  operator-approved restart window; see
  `docs/research/2026-05-27-quiet-posture-readonly-audit.md`.
- fact: `scripts/obelisk_supervisor_snapshot.sh` now writes `quiet-posture.txt` and
  `quiet_posture_status` so debug-stable snapshots do not hide active chat reflection from
  production/performance review.
- fact: Current available Ragnarok logs are not enough for a GNames/FNamePool candidate:
  ReflectionScanner is disabled and analyzer output is `inconclusive`; see
  `docs/research/2026-05-27-current-gname-evidence-pack-audit.md`.
- fact: Runtime installation now uses the CMake `Runtime` component for `libobelisk.so`,
  so the installed shared library gets `RUNPATH=$ORIGIN` instead of leaking build-tree
  dependency paths.
- fact: Commit `96b53d2` hardened installed SDK package validation by requiring
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED)` and rejecting source/build tree
  path leaks in installed CMake package files.
- fact: Commit `06a75c4` classifies static objdump xrefs as load, store, address,
  call, jump, or other in analyzer output and evidence-pack counts. It also adds
  `docs/research/2026-05-27-ue4-type-reconstruction-roadmap.md` for the staged
  `FName -> GObjects -> UFunction -> params` reconstruction path.
- fact: ReflectionScanner now has opt-in FName rejection evidence behind
  `OBELISK_REFLECTION_LOG_FNAME_REJECTS=1`, and the analyzer records
  `fname_reject_count`, `fname_reject_reason_counts`, and `fname_rejects`; see
  `docs/research/2026-05-27-fname-reject-evidence-logging.md`.
- fact: Commit `8cb3bbe` was deployed to `/servidor/ark/obelisk` and a controlled Ragnarok
  dev capture produced 22 UObject validation hits, 22 FName rejects, and zero positive
  FName probes. Current evidence says the chat UObject globals are not plausible GNames
  roots under the indirect-table model. See
  `docs/research/2026-05-27-live-fname-reject-capture.md`.
- fact: A delayed static-root retry capture for `0x5956f30` stayed inconclusive. The slot
  becomes non-null after startup and reads names with `header_index_ok=3/3`, but the
  expected clues do not match (`9619 -> ServerChat`, `9622 -> SetActiveMissionDebugFlags`)
  and counts remain zero. Do not promote `0x5956f30` as accepted GNames; see
  `docs/research/2026-05-27-static-fname-root-live-capture.md`.
- fact: Static analysis found a stronger FName root research-candidate in the current ARK
  binary: global pointer slot `0x5956f30`, bucket array `0x594e020`, mutex slot
  `0x5956f38`, init flag `0x5956f40`, and name-table code around `0x1c88e70`,
  `0x1c89a70`, and `0x1c990d0`. Treat it as binary-hash-specific and unpromoted until an
  isolated runtime probe confirms known indices through `*0x5956f30`; see
  `docs/research/2026-05-27-static-fname-root-candidate.md`.
- fact: ReflectionScanner now has an explicit env-supplied static FName root probe via
  `OBELISK_REFLECTION_STATIC_FNAME_ROOTS`, including startup and one-minute delayed retry
  checks. The analyzer parses static-root probes and rejects. A static-root research
  candidate requires exact `None`/`ClientMessage`/`ServerChat`, `header_index_ok=3/3`,
  plausible counts, and no reject markers; see
  `docs/research/2026-05-27-static-fname-root-probe.md`.
- fact: ReflectionScanner also has opt-in observed-index static-root sampling via
  `OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS=1`. It samples only already discovered
  plausible `UObject` candidates against env-supplied static roots, and the analyzer
  records sample JSON plus status/reason/target counts. Samples do not satisfy `--strict`
  by themselves; see `docs/research/2026-05-27-static-fname-root-sampling.md`.
- fact: First Ragnarok sample capture after `fa76213` produced 44 static-root samples, all
  rejected by `implausible_num_elements`. This does not disprove the table because earlier
  retry evidence showed entries can be readable while `+0x800/+0x804` counters are zero.
  The sampler gate is currently too strict for `0x5956f30`; see
  `docs/research/2026-05-27-static-fname-root-sampling.md`.
- fact: Commit `9f320a0` added an opt-in debug ptrace workflow. `OBELISK_DEBUG_ALLOW_PTRACE=1`
  calls `prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY)` for authorized core dumps, and stable
  posture checks reject that env after debug work.
- fact: An authorized `arkserver` core dump confirmed static FName slot `0x5956f30` points
  to a plausible table for binary SHA256
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`: table
  `0x2ae5c660`, `num_elements=0x4516e`, `num_chunks=0x12`, index `0 -> None`,
  `4884 -> ClientMessage`, and `9619 -> ServerChat`. See
  `docs/research/2026-05-27-arkserver-core-fname-evidence.md`.
- fact: A runtime static-root scanner capture with corrected clues stayed inconclusive
  through the old 60s retry window: `0x5956f30` pointed to `0x30752660`, but counters and
  clue reads were still zero. Static-root retries now use the same 10-minute window as
  global watches; see `docs/research/2026-05-27-static-root-runtime-retry-capture.md`.
- fact: `scripts/build_core_dump_evidence_pack.py` now emits direct FName-entry GDB reads
  for known indices and accepts bounded `--gobjects-candidate LABEL=ADDR` previews for the
  next `GObjects` reconstruction step. See
  `docs/research/2026-05-27-core-gobjects-next-development.md`.
- fact: A controlled Ragnarok dev capture on commit `5754fca` tested
  `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`. Startup probe rejected it with
  `table=0x0` and `reason=unreadable_table_header`; the server was then restarted without
  scanner/static-root env. Treat this as inconclusive, not accepted; see
  `docs/research/2026-05-27-static-fname-root-live-capture.md`.
- fact: Commit `e2ef8e9` added debug-only runtime control. `enable-debug-control` watches
  per-instance marker requests, currently `request-static-fname-probe`, so probes can run
  after ARK is alive. Stable posture rejects `OBELISK_ENABLE_DEBUG_CONTROL`.
- rejected: The first post-start debug-control probe of `0x5956f30` mechanically worked but
  rejected the slot (`table=0x13733660`, `implausible_num_elements`). Do not keep extending
  bootstrap waits or promote that slot from one core-dump session; see
  `docs/research/2026-05-27-runtime-debug-control.md`.
- fact: `scripts/obelisk_supervisor_snapshot.sh` is the only approved unattended
  cron-style workflow for now. It is read-only and writes snapshots to
  `/servidor/ark/obelisk/dumps/supervisor/`; see `docs/SUPERVISION.md`. It now fails
  closed on unstable posture, records PID/stable posture summary, and separates chat
  counters for `Reflected chat ProcessEvent`, `ServerSendChatMessage`, exact metadata-only
  fallback names, `metadata_only=true`, rejections, and `send_mode_known=false`.
- fact: Core evidence promotes `0x595b7e0` to `GUObjectArray research-candidate` for ARK
  binary SHA256 `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
  The first object item resolves to `/Script/CoreUObject`, and its class resolves to
  `Package` through the confirmed FName table; see
  `docs/research/2026-05-27-core-gobjects-candidate.md`.
- fact: `scripts/build_core_dump_evidence_pack.py` now writes
  `gobjects-static-xrefs.json` for `--gobjects-candidate`, summarizing objdump xrefs for
  root, chunks, count, and serial fields. Its manifest records the Obelisk commit used for
  the pack. Offline validation for `0x595b7e0` found 3 root, 8016 chunks, 5870 count, and
  2 serial xrefs.
- fact: Static context anchors around `0x595b7e0` are now recorded: `0x79ce22` root store
  plus bounded walk, `0x7a27a7` helper/destructor registration, `0x81f118` startup reset,
  and `0x81f206` startup helper call. Treat labels as stripped-binary anchors, not accepted
  function names.
- fact: `gobjects-static-xrefs.json` groups objdump xrefs by function anchor, but broad
  nearest-symbol groups can be contaminated. The `0x12d1400` group is not a standalone
  decompiler target; prefer concrete instruction windows. Static classifications:
  `0x79ce22` lookup/bootstrap cache, `0x7a27a7` init/destructor registration, `0x81f118`
  startup reset, `0x81f206` startup helper; see
  `docs/research/2026-05-27-gobjects-static-anchor-classification.md`.
- fact: `scripts/build_core_dump_evidence_pack.py` now labels xref groups with
  interpretation metadata. Oversized nearest-symbol buckets are
  `contaminated-nearest-symbol-bucket` and `recommended_for_decompile=false`; anchor groups
  carry `anchor_span_bytes`, `oversized`, and `interpretation` so dense local windows can
  also be rejected.
- fact: `scripts/enumerate_core_uobjects.py` can enumerate UObjects from the core through
  `0x595b7e0` and `0x5956f30`. It found real chat-related `Function` objects including
  `ServerChat` at index `25447`, `ServerChatTo` at `25449`, and `ServerChatToPlayer` at
  `25452`; see `docs/research/2026-05-27-core-uobject-enumeration.md`.
- next-step: Do not restart the `GObjects` investigation by looking for another broad
  candidate. The priority is repeating the classified context checks on a second isolated
  core or future binary before promoting any runtime-stable reflection contract.
- next-step: No second isolated core is currently available; read-only dump inventory only
  found the existing Ragnarok-derived core and derivative packs. When the operator opens a
  core window, prefer dedicated `arkserver-obelisk-debug`; use `arkserver2` / TheIsland
  only as explicit fallback. Follow
  `docs/research/2026-05-27-isolated-second-core-runbook.md` and do not touch Ragnarok.
- fact: `scripts/inspect_core_ufunctions.py` can walk legacy `UStruct.Children +0x38` and
  `UField.Next +0x28` property chains from the core. Chat parameter evidence:
  `ServerChat.MessageText` offset `0x0`, `ServerChatTo.SteamID` offset `0x0`,
  `ServerChatTo.MessageText` offset `0x10`, `ServerChatToPlayer.PlayerName` offset `0x0`,
  and `ServerChatToPlayer.MessageText` offset `0x10`; see
  `docs/research/2026-05-27-core-ufunction-property-chain.md`.
- fact: `scripts/inspect_core_ufunctions.py` now validates inspected target, class, outer,
  and property objects with direct `GObjects[InternalIndex]` back-references. On the
  existing core, `ServerChat` and `SendServerChatMessage` plus their property chains pass;
  see `docs/research/2026-05-27-ufunction-membership-backrefs.md`.
- fact: `scripts/inspect_core_ufunctions.py` supports offline `--name-contains` and
  `--outer-contains` filters for Function/Struct discovery from core dumps. Broad
  `--name-contains Chat` is discovery-only and too noisy for runtime filters; exact
  candidates are documented in
  `docs/research/2026-05-27-real-chat-ufunction-path-hypotheses.md`.
- fact: `scripts/inspect_core_ufunctions.py` now reports bounded enum candidates for
  `ByteProperty` through the observed `+0x70` enum pointer. On the existing core,
  `ServerSendChatMessage.SendMode` resolves the six `EChatSendMode` names.
- fact: `scripts/verify_chat_reflection_constants.py` compares the local
  `ue/ChatReflection.cpp` constants to offline core evidence for `ServerChat`,
  `ServerChatTo`, `ServerChatToPlayer`, `ServerSendChatMessage`, `ClientChatMessage`,
  `ClientServerChatDirectMessage`, and `ClientServerChatMessage`. It now also cross-checks
  target/class/outer/property `GObjects[InternalIndex]` membership,
  `ServerSendChatMessage` native exec candidate `0x154a600`, executable segment
  membership, and `EChatSendMode` enum names. It passed against
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
  with `--max-object-scan 30000`.
- fact: `scripts/verify_chat_reflection_constants.py` now supports
  `--evidence-pack <dir-or-manifest>`. It reads `manifest.json`, takes the recorded core,
  first `gobjects_candidates` address, first `fname_root_slots` address, and verifies the
  manifest binary SHA256 and `core.sha256` when available. Raw `--core` remains
  legacy/synthetic mode.
- fact: `ue/RuntimeReflection.{h,cpp}` now provides an internal, binary-hash-gated
  reflection reader with tests for bounded `UFunction`/`UProperty` chains and borrowed
  parameter ranges. It is not public ABI; it is used by the experimental hook-side chat
  observation path.
- fact: Public chat SDK promotion remains blocked by design. `include/obelisk/ObeliskApi.h`
  has no chat structs/capability/functions, and `tests/abi/AbiLayoutTests.cpp` still fails
  if `OBELISK_API_CAPABILITY_CHAT_EVENTS` appears. The minimum future promotion path is
  failing ABI layout + installed SDK consumer tests first, then append-only C ABI wrappers
  over the internal `ChatEventDispatcher`.
- fact: `scripts/test_public_sdk_chat_guardrails.py` and CI now check that public SDK
  headers and the installed SDK consumer do not accidentally expose or consume experimental
  chat API symbols before intentional promotion.
- fact: `ue/ChatReflection.{h,cpp}` now recognizes `ServerChat`, `ServerChatTo`, and
  `ServerChatToPlayer` shapes on top of `RuntimeReflection` and returns borrowed parameter
  ranges when `params` is provided. Runtime text logging is handled through the gated
  `ProcessEventChatReflection` decode-and-sanitize path, not through public SDK dispatch.
- fact: `hooks/ProcessEventHook.cpp` has experimental chat reflection observation wiring,
  disabled unless `OBELISK_ENABLE_CHAT_REFLECTION=1` and
  `OBELISK_CHAT_REFLECTION_BINARY_SHA256` equals the supported ShooterGameServer SHA256.
  It logs metadata/ranges only, not text.
- fact: `ServerChat`, `ServerChatTo`, and `ServerChatToPlayer` are likely
  `ShooterCheatManager` command functions, not the normal player chat path. Current
  offline evidence points normal incoming player chat at
  `ShooterPlayerController.ServerSendChatMessage` with FName index `2697`,
  `StrProperty ChatMessage` offset `0x0`, `ByteProperty SendMode` offset `0x10`, and
  `ParmsSize=0x11`. `SendMode` maps to `EChatSendMode`: `0 GlobalChat`,
  `1 GlobalTribeChat`, `2 LocalChat`, `3 AllianceChat`; values `>=4` are invalid for
  logging/dispatch. See
  `docs/research/2026-05-27-real-chat-ufunction-path-hypotheses.md`.
- fact: Commit `e1071a7` adds gated, metadata-only recognizers for exact
  `ShooterPlayerController` fallback candidates `ClientChatMessage`,
  `ClientServerChatDirectMessage`, and `ClientServerChatMessage`. They log
  `metadata_only=true`, do not decode text, do not dispatch plugin events, and do not
  change public ABI.
- fact: `packaging/linuxgsm/ObeliskRun.sh` supports
  `state/instances/<id>/enable-chat-reflection` to set the experimental chat reflection
  gates and default log limit on restart.
- fact: Latest deployed runtime on `arkserver` includes commits through `e1071a7`
  (`metadata_only` chat fallback recognizers). Current PID `3289000` has
  `OBELISK_ENABLE_CHAT_REFLECTION=1`, matching SHA gate, ProcessEvent hook installed at
  `0x1d34e20`, plugins disabled, and stable posture confirmed.
- fact: Read-only no-hit audit found stable ProcessEvent/chat-reflection posture but zero
  recognized chat hits in snapshots through `20260527T101357Z`; absence of lines does not
  prove a real chat send occurred. See
  `docs/research/2026-05-27-chat-reflection-no-hit-audit.md`.
- fact: Later read-only log review found accepted runtime `ServerSendChatMessage` hits at
  `14:07:27`, `14:17:13`, `16:12:02`, and `16:12:45` with `fname_index=2697`,
  `metadata_only=false`, `send_mode=0`, `send_mode_name=GlobalChat`, and bounded
  `ChatMessage` / `SendMode` ranges. This confirms the experimental runtime path but not
  a public SDK event; see
  `docs/research/2026-05-27-server-send-chat-runtime-hit.md`.
- fact: Manual post-deploy `ServerSendChatMessage` chat validation commands, expected log
  lines, `reflected_chat_process_event_lines` / `server_send_chat_message_lines` /
  metadata-only fallback counters / `rejected_chat_lines` interpretation, and marker-only
  rollback are documented in `docs/SUPERVISION.md`.
- fact: The next isolated runtime chat validation should follow
  `docs/research/2026-05-27-theisland-chat-reflection-ab-runbook.md`: Phase A reflection
  off, Phase B metadata-only reflection on, Phase C text logging only with separate
  explicit approval, then rollback on `arkserver2` / TheIsland. Do not use Ragnarok for
  this A/B run.
- fact: `hooks/ProcessEventChatReflection.{h,cpp}` extracts gate/recognition logic from
  the hook for direct tests. `ProcessEventChatReflectionTests` cover disabled and non-chat
  short-circuit behavior plus valid borrowed param ranges.
- fact: `FString` for this ARK Linux build is a strong candidate for
  `{TCHAR* Data, int32 ArrayNum, int32 ArrayMax}` with `TCHAR=UTF-32LE`; see
  `docs/research/2026-05-27-fstring-layout.md`.
- fact: `RuntimeReflection::TryDecodeFStringUtf32` now implements the internal decoder
  candidate with synthetic tests and strict reject conditions.
- fact: Pushed `main` now wires `TryDecodeFStringUtf32` into the experimental
  `ServerSendChatMessage` logger through `ProcessEventChatReflection::TryDecodeUtf32Field`.
  Decoded text requires the extra `OBELISK_CHAT_REFLECTION_LOG_TEXT=1` gate, logs only for
  known `EChatSendMode` values, and does not dispatch plugin callbacks or change ABI. This
  is validated locally but not yet deployed to `/servidor/ark/obelisk`.
- fact: Public SDK chat event ownership is intentionally deferred. The current design note
  requires copied Obelisk-owned UTF-8 text, POD structs, opaque registration ids,
  `user_data`, callback owner cleanup, ABI layout tests, plugin fixture coverage, hot-path
  benchmark evidence, and runtime validation before adding `OnChatMessage`; see
  `docs/research/2026-05-27-sdk-chat-event-ownership-plan.md`.
- fact: `AbiLayoutTests` now fail if `OBELISK_API_CAPABILITY_CHAT_EVENTS` is added to the
  public SDK header before chat ABI promotion is intentional.
- fact: `docs/research/2026-05-27-chat-sdk-abi-preflight.md` records the test-first ABI
  and dispatcher gates for future `OnChatMessage` without changing the public SDK header.
- fact: `core/ChatEventDispatcher.{h,cpp}` is an internal, non-SDK dispatcher foundation
  for future chat events. `ChatEventDispatcherTests` cover copied callback-duration text,
  opaque registration ids, invalid registration rejection, idempotent unregister,
  owner cleanup, `send_mode >= 4` rejection, and exception isolation.
- fact: `ChatEventDispatcher::Dispatch()` holds its dispatch mutex across callback
  invocation so owner cleanup cannot race plugin `dlclose` while a copied callback is
  executing.
- fact: `ChatEventDispatcher` supports self-unregister from inside a chat callback without
  deadlock while still blocking cross-thread owner cleanup until dispatch completes.
- fact: `ChatEventDispatcherTests` now cover cross-thread owner cleanup waiting for an
  in-flight chat callback before unregister completes.
- fact: `PluginManager` now owns the internal chat dispatcher lifecycle backstop:
  plugin init failure and `UnloadAll()` unregister both ProcessEvent callbacks and
  `ChatEventDispatcher` subscriptions before `dlclose`. `PluginManagerTests` cover
  successful unload and init-failure cleanup with injected dispatcher ownership.
- fact: Commit `76356bf` adds `chat_reflection_benchmark`, an excluded-from-default-build
  local helper for synthetic `TryIdentifyInvocation()` and UTF-32 decode measurements. It
  does not cover hook-side `GetFunctionNameIndex()` / `Memory::IsReadable()` overhead.
- fact: `chat_reflection_benchmark` now reports p50/p95/p99 and
  `allocations_per_iter`, including hook-like disabled, enabled non-chat, matched
  `ServerSendChatMessage`, and text decode cases. The hook-side wrapper keeps disabled and
  non-chat attempts allocation-free in the synthetic benchmark. Fixed internal storage in
  `RuntimeReflection::TryReadUFunction()` / `ChatInvocation` and UTF-8 output reservation
  lower matched chat to zero allocations, standalone UTF-32 decode to one allocation, and
  hook-like text logging to one allocation per iteration locally.
  `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0`
  now short-circuits observation reflection work; see
  `docs/research/2026-05-27-chat-reflection-stack-cycle-guard.md`.
- fact: `scripts/check_chat_reflection_benchmark.py` gates local benchmark output so
  disabled/non-chat hook-like paths remain allocation-free and matched/text paths stay
  within documented reader-call/allocation ceilings. This is a regression gate, not
  runtime acceptance evidence.
- fact: CI runs deterministic parser/threshold tests for the benchmark gate and also
  builds/runs `chat_reflection_benchmark` with a short iteration count to enforce
  allocation/reader-call ceilings. The helper remains excluded from the default build.
- fact: `Memory::IsReadable` no longer uses `write(/dev/null)` because that probe returned
  success for invalid and `PROT_NONE` mappings on this host. It is now backed by cached
  readable ranges from `/proc/self/maps`, with `MemoryTests` covering invalid pointers,
  overflow, and `PROT_NONE`; see
  `docs/research/2026-05-27-isreadable-dev-null-hotpath.md`.
- fact: Commit `257f432` with maps-backed `Memory::IsReadable` is included in the deployed
  runtime at `/servidor/ark/obelisk`.

## Rejected Or Unsafe

- rejected: ProcessEvent candidate `0x1d11cb0` did not receive gameplay events.
- risk: Raw FString scanning/discovery must not be enabled on live Ragnarok as
  the normal test path.
- risk: Runtime/reversing experiments on Ragnarok can invalidate player performance
  testing; keep `arkserver` / Ragnarok protected unless the operator opens an explicit
  maintenance window.
- risk: `arkserver2` / TheIsland is the controlled debug/development fallback, not the
  default target for high-risk tooling. For `gcore`, `ptrace`, `ReflectionScanner`, broad
  tracing, and scanner-like captures, prefer a dedicated `arkserver-obelisk-debug`
  instance with separate ports/save/cluster/logs.
- fact: Historical Ragnarok runbooks for core dumps and runtime debug-control were
  rewritten as non-default guidance: future captures must use
  `docs/research/2026-05-27-isolated-second-core-runbook.md`,
  `arkserver-obelisk-debug` first, and TheIsland only as approved fallback.
- fact: Historical FName/ReflectionScanner capture notes that previously showed direct
  Ragnarok start commands now say not to repeat that workflow on `arkserver`; future
  retries target `arkserver-obelisk-debug` first.
- fact: Read-only supervisor snapshot `20260527T185153Z` found one Ragnarok process with
  stable posture passing, plugins disabled, ProcessEvent hook loaded, and scanner/debug
  env absent. Quiet posture still fails because chat reflection is active; do not change it
  without an operator maintenance window. See
  `docs/research/2026-05-27-ragnarok-readonly-posture-snapshot.md`.
- risk: Native exec probes must remain disabled on live servers.
- risk: FetchContent pins were selected from existing local checkouts without internet
  verification; full offline resilience still needs a mirror or vendored archive.
- fact: `scripts/test_dependency_pins.py` now guards `fmt`, `spdlog`, and `subhook`
  FetchContent declarations so they stay pinned to full commit SHAs instead of moving
  tags/branches; mirroring/vendor work remains a future resilience task.

## Priority Next Steps

- next-step: If runtime text evidence is needed, use a controlled `arkserver2` / TheIsland
  restart window with `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`, review bounded logs, then
  remove the text gate; use the TheIsland A/B runbook, keep dispatch blocked, and do not
  use Ragnarok.
- next-step: Before any second-source core or scanner capture, create or confirm
  `arkserver-obelisk-debug`; use TheIsland only as an explicit operator-approved fallback
  and record rollback/posture evidence.
- next-step: When an operator-approved Ragnarok maintenance window exists, remove the chat
  reflection gate and restart only `arkserver`, then validate with
  `--expect-stable --forbid-chat-reflection`.
- next-step: Design plugin-facing chat event ownership only after text is copied into
  Obelisk-owned memory and callback lifetime is covered by tests. Use
  `docs/research/2026-05-27-sdk-chat-event-ownership-plan.md` as the acceptance gate before
  touching `include/obelisk/ObeliskApi.h`.
- next-step: Run `scripts/verify_chat_reflection_constants.py` against any new core before
  accepting changed chat FName indices, parameter offsets, or `StrProperty` constants.
- next-step: Benchmark ProcessEvent overhead with chat reflection enabled vs disabled
  before keeping the marker active for long high-population sessions.
- next-step: Before drafting public chat API, justify or reduce the remaining one
  text-log allocation, then plan isolated runtime A/B
  separately.
- next-step: When chat API work resumes, add ABI layout tests and dispatcher ownership
  tests first; only then append public fields to `include/obelisk/ObeliskApi.h`.
- next-step: Do not connect `ChatEventDispatcher` to `ProcessEvent` or public SDK fields
  until the public ABI/capability gate is ready; PluginManager owner cleanup is now in
  place as the internal lifecycle backstop.
- rollback: on `arkserver2`, remove the experimental marker/env, keep
  `disable-plugins`, restart only TheIsland, and run
  `scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance
  arkserver2`; no plugin ABI or config migration is involved.
- next-step: Generalize the binary-hash-scoped reflection pipeline only after another
  capture or ARK binary hash validates the same fields.
- next-step: Add binary hash validation or an instruction decoder before accepting future
  ProcessEvent prologue changes.
- next-step: Keep expanding package/export validation only when external plugin
  consumption exposes a concrete missing contract.
- next-step: Later integrate `docs/VERSIONING.md` into README/STATUS/RELEASE once the
  versioning policy has settled; avoid claiming `0.1.0` is imminent.

## Agent Protocol

- fact: Agents should read `agent-skills/obelisk-agent-handoff/SKILL.md`,
  `agent-skills/obelisk-continuous-learning/SKILL.md`, and the subsystem-specific skill
  before starting multi-agent work.
- fact: Agent commits/pushes without explicit one-turn delegation are protocol violations.
  The lead may accept audited content, but future prompts should say
  "leave changes unstaged/uncommitted and report touched paths" when edits are allowed.
- fact: Agent rounds must be separated by expert focus as well as file ownership. Do not
  assign two editing agents to the same focus or shared integration file in the same round
  unless one is explicitly the integration owner and the other is read-only.
- fact: Ops/docs/QA work may use `.github/pull_request_template.md`,
  `.github/workflows/ci.yml`, `CONTRIBUTING.md`, and `docs/STATUS.md` for contributor
  checks before changing runtime or research scope.
- fact: Static/reversing rounds should read `obelisk-static-binary-analysis`,
  `obelisk-ue4-type-reconstruction`, and `obelisk-tooling-discipline` in addition to the
  UE4 reflection/reversing skills.
- next-step: After each investigation, update this file only with concise active context and
  put detailed evidence in `docs/research/`.
