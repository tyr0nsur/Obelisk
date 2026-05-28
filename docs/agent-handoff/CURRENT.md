# Current Agent Handoff

Updated: 2026-05-28

## Active Operating Objective

- objetivo literal del leader: Llevar Obelisk hacia una versión estable de producción
  mediante rondas continuas de auditoría, desarrollo, investigación, conocimiento y
  aprendizaje sobre ARK: Survival Evolved mediante ingenieria inversa del dump, análisis
  del proyecto y coordinación de agentes bajo supervisión central.
- objective: Move Obelisk toward a production-stable version through continuous supervised
  rounds of audit, development, investigation, knowledge capture, and learning about ARK:
  Survival Evolved from dump reverse engineering, project analysis, and centrally
  coordinated agents. Each round should produce one concrete outcome: audited evidence,
  offline reversing/tooling improvement, runtime/API hardening, recognizer/test coverage,
  documentation/skill updates, or a validated checkpoint.
- priorities: preserve live server safety first; strengthen UE4 reflection and
  second-source evidence; keep module recognizers candidate-only until promotion gates are
  met; optimize tooling/tests that make future reverse engineering faster and more
  reviewable.
- guardrails: do not restart servers, edit `/servidor/ark`, change markers, run
  ReflectionScanner, attach ptrace/gcore, enable broad `ProcessEvent` tracing, or publish
  runtime observations without explicit operator approval for that run.
- cadence: use focused agent rounds, integrate findings into repo files, validate with
  safe offline tests, and commit/push stable checkpoints. Send Discord community updates
  only for major Obelisk milestones relevant to future mod/plugin creators, not routine
  development checkpoints.

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
- fact: Operator direction changed on 2026-05-28: RAM is tight, `arkserver2` / TheIsland
  should stay stopped, and `arkserver` / Ragnarok is now available as the Obelisk
  development/test harness. Use controlled gates, copied evidence, and rollback posture.
- fact: Operational correction on 2026-05-28: `arkserver2` stop was requested and confirmed
  already stopped; `arkserver` was restarted after removing
  `/servidor/ark/obelisk/state/instances/arkserver/enable-chat-reflection`. Current
  Ragnarok PID after restart: `1820244`. Read-only posture passes with
  `scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map
  Ragnarok --instance arkserver`.
- fact: The LinuxGSM wrapper now scrubs inherited marker-managed Obelisk env vars before
  selecting an instance profile. ProcessEvent hook, plugin-disable, ptrace/debug-control,
  native exec probes, global callbacks, and chat/inventory/structure reflection env must be
  reintroduced by instance markers instead of leaking from the parent environment. The live
  wrapper was updated without restart; backup:
  `/home/flowcommunity-ark/backups/ObeliskRun.sh.20260528-024702.bak`.
- fact: Runtime-side debug/scanner gates now require env+instance marker, so direct
  `LD_PRELOAD` launches cannot enable ptrace, debug-control, ReflectionScanner, or native
  exec probes by env alone. Marker names: `allow-ptrace`, `enable-debug-control`,
  `enable-reflection-scanner`, and `enable-native-exec-probes`. The live wrapper was
  refreshed without restart; backup:
  `/home/flowcommunity-ark/backups/ObeliskRun.sh.20260528-025602.bak`.
- fact: Operator explicitly approved a Ragnarok gameplay config change on 2026-05-27:
  `AllowCaveBuildingPvP=True` was applied to `GameUserSettings.ini`, pre-change backup is
  `/home/flowcommunity-ark/backups/ark-config-manual/GameUserSettings.ini.allow-cave-20260527-184547.bak`,
  `arkserver` was restarted successfully. A later read-only-agent protocol violation
  repeated the backup/restart; current `ark-config-latest` is
  `/home/flowcommunity-ark/backups/ark-config-20260527-190558`. Historical PID `3940524`
  was replaced by PID `1820244` after the 2026-05-28 RAM/posture restart.
- fact: Active debug target is now `arkserver` / Ragnarok. Do not start `arkserver2` for
  Obelisk work while RAM is constrained. Risky probes still need explicit approval for the
  exact `arkserver` window and rollback plan.
- fact: `sdk.structures` runtime observation now requires both env/SHA/budget gates and
  `/servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection`.
  The LinuxGSM wrapper exports structure reflection env only from that marker, and the
  hook rejects env-only activation. Default observation budget remains `0`.
- fact: stable posture checks now reject `OBELISK_ENABLE_STRUCTURE_REFLECTION`,
  `OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256`, and
  `OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT`; supervisor snapshots write
  `structure-reflection.txt` so structure observation is reported as its own runtime
  observer family.
- fact: structure observation budget is now reserved only after the cheap exact structure
  FName filter passes. Non-structure `ProcessEvent` calls no longer consume the bounded
  observation budget.
- fact: `sdk.inventory` now has an internal hook-side observer behind
  `enable-inventory-reflection`, env/SHA, and explicit non-zero budget gates. It logs
  metadata only, filters exact inventory FNames before reserving budget, and has no public
  SDK callback or gameplay mutation path.
- fact: Chat, inventory, and structure ProcessEvent observers all require runtime-side
  env+instance-marker gates plus binary SHA validation before activation. Chat now matches
  the inventory/structure marker discipline with `enable-chat-reflection`.
- fact: Runtime observer marker checks use `runtime/RuntimeMarkers.*`, which rejects empty
  components, path traversal, slashes, dots, spaces, directory markers, symlink markers, and
  symlink instance directories before checking `state/instances/<instance>/<marker>`.
- fact: Second-source reversing gates are centralized in
  `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`. Current
  `FName`/`GObjects`/`UObject`/`UFunction` evidence remains single-core or otherwise
  candidate-only until a second isolated core or independent static path satisfies that
  matrix.
- fact: `ue/BuffReflection.*` adds an offline internal `sdk.buffs` recognizer for exact
  compact `PrimalBuff` fixtures. It has no runtime hook, no public callback, no return
  override, and exposes only bounded bool ranges; object/class pointer ranges stay
  internal.
- fact: `scripts/compare_reflection_snapshots.py` compares sanitized UFunction and
  ScriptStruct snapshot sets offline and reports `accepted`, `rejected`, or `inconclusive`
  per target. Use `--target Outer.Name` for focused module checks. It does not read cores
  or touch servers.
- fact: `scripts/regenerate_ufunction_snapshots.py --check-layout` now supports
  UFunction layout-only verification for second-source intake. It ignores unstable
  identity/evidence indices while preserving target identity, UFunction fields, and
  property-chain layout drift.
- fact: Commit `f3a47d1` runs reflection snapshot comparison and ScriptStruct fixture
  tests in CI and release validation.
- fact: Commit `3451a19` aligns README and `docs/STATUS.md` around module-first runtime
  observers and candidate-only snapshot tooling instead of a chat-centered roadmap.
- fact: Commit `74b123d` covers mixed UFunction/ScriptStruct target-filter behavior so
  short `Outer.Name` filters can match both schemas and schema-qualified filters select
  exactly one.
- fact: Commit `7ccd7a6` refocused `obelisk-ue4-reflection` around the general
  module-recognizer promotion ladder, second-source checks, and debug-instance live-ops.
- fact: Commit `707cbba` aligned reversing/type-reconstruction skills with module-first
  reconstruction, candidate-only recognizers, and no marker/restart commands without
  explicit approval.
- fact: Commit `6d0f783` extends public SDK guardrails so gameplay module APIs
  (inventory, structures, buffs, dinos, tribes, missions, transfers, admin, player, item)
  cannot appear before intentional promotion.
- fact: Commit `b401df4` removed direct TheIsland marker/restart commands from core and
  Linux hooking skills; live validation now requires explicit approval and posture checks.
- fact: Commit `7a7a307` gates documented debug marker and rollback commands in
  `docs/INSTALL.md` and `docs/SUPERVISION.md`.
- fact: Commit `a884b3f` adds `scripts/test_operational_doc_guardrails.py` to CI/release
  so docs and skills outside `docs/research/` cannot reintroduce active marker/restart
  commands.
- fact: Commit `ffa3269` makes `scripts/test_public_sdk_guardrails.py` the canonical
  module-first public SDK guardrail test and keeps `test_public_sdk_chat_guardrails.py` as
  a legacy wrapper.
- fact: Commit `cd57189` aligned debug policy toward
  `arkserver-obelisk-debug` by default, added CI coverage for
  `scripts/test_obelisk_supervisor_snapshot.sh`, and hardened `PluginManager::LoadPlugins`
  so repeated loads of an already-loaded `plugin_id` skip initialization and close the
  duplicate handle instead of duplicating callbacks.
- finding: Runtime/API audit identified the next SDK-core hardening items: public callback
  unsubscribe handles, `CallProcessEvent` reentrancy contract/guard, safe hook removal
  with active-detour tracking, and owned debug-control thread shutdown. Treat these as
  future focused runtime rounds.
- fact: Commit `6b9fe8a` documents the `CallProcessEvent` reentrancy
  contract in the public SDK header, README, and plugin architecture docs without changing
  ABI layout. A pre-callback that calls `CallProcessEvent` must return `false`; returning
  `true` risks double execution by the detour. A runtime guard remains future work.
- fact: Commit `5cf3de7` adds internal `EventManager`
  registration IDs and `UnregisterCallback(id)` coverage. Public `ObeliskApi` callback
  registration remains unchanged for ABI v1; this prepares a future explicit unsubscribe
  capability without promoting it yet.
- fact: Commit `f5d1b0e` adds active ProcessEvent frame tracking around the detour and
  manual trampoline calls. Hook removal restores target bytes first, waits briefly for
  active frames to drain, and leaves the trampoline mapped with a warning instead of
  risking `munmap` while a frame may still be executing.
- fact: Commit `8519b2b` replaces the detached debug-control thread with owned thread
  state, stop flag, condition-variable wakeup, and join before logger shutdown on
  bootstrap failure or normal unload.
- fact: Commit `2095b1a` aligns ProcessEvent callback dispatch
  with the existing chat dispatcher self-unregister behavior by using a recursive dispatch
  mutex and adding coverage for a callback unregistering its own registration during
  dispatch. This is internal groundwork for future explicit public callback unsubscribe
  handles; public ABI remains unchanged.
- fact: Commit `228ef7e` snapshots the ProcessEvent original
  trampoline under a hook-state mutex, starts the active-frame guard before public
  `CallOriginalProcessEvent` observes hook state, and makes hook removal mark `removing`
  under the same mutex before restoring bytes or unmapping the trampoline. This addresses
  the audited race between `CallProcessEvent` and hook removal.
- fact: Commit `0994d3f` makes global ProcessEvent callbacks
  runtime default-deny. `RegisterPreProcessEvent` and `RegisterPostProcessEvent` no-op
  with a warning unless `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1` and the
  per-instance marker `allow-global-process-event-callbacks` are both active. Filtered
  name-index callbacks remain available by default, public ABI layout remains v1, and the
  new capability bit only advertises global callbacks when the gate is active.
- fact: Global ProcessEvent callback gate hardening is committed; stable posture checks
  reject `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS`.
- finding: Reflection tooling audit found UFunction snapshot fixture coverage is broad
  across module areas, but ScriptStruct coverage is the current bottleneck with only two
  transfer structs. Prioritize an offline second-source readiness report before any
  runtime capture or public API promotion.
- fact: Commit `4e4f5cf` adds
  `scripts/compare_reflection_snapshots.py --readiness-report`. It summarizes comparable
  snapshot coverage and second-source status by schema/module without requiring a live
  server. Current fixture readiness: UFunction `35/35` comparable, ScriptStruct `2/2`
  comparable, both blocked only by missing second-source roots; self-comparison accepts all
  fixtures.
- fact: `sdk.transfers` ScriptStruct fixtures now preserve target/property object and
  FName identity fields like UFunction fixtures. `regenerate_scriptstruct_snapshots.py
  --check-layout` stays semantic/layout-only so second-source gates do not depend on
  unstable FName/GObjects indices.
- next-step: Continue priority rounds on general reflection/API substrate. Immediate safe
  priorities are: use the minimal second-source intake in
  `docs/research/2026-05-28-second-source-reversing-gap-matrix.md` before expanding more
  gameplay surfaces. First targets are `PrimalItem.CanUse`,
  `PrimalItem.AllowRemoteAddToInventory`, `PrimalStructure.AllowStructureAccess`, and
  `PrimalStructure.IsAllowedToDemolish`; current readiness is `4/4` comparable and blocked
  only by missing second-source root.
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
  `/servidor/ark`; the preferred future target is now `arkserver-obelisk-debug`, with
  `arkserver2` / TheIsland only as an approved fallback. High-risk scanners still require
  a specific run window. See
  `docs/research/2026-05-27-reflectionscanner-isolated-instance-audit.md`.
- fact: Ops planning recommends a new `arkserver-obelisk-debug` LinuxGSM instance with
  isolated ports, saves, cluster posture, `OBELISK_LOG_DIR`, and wrapper-level Obelisk
  env instead of shared map markers; see
  `docs/research/2026-05-27-isolated-debug-instance-plan.md`.
- fact: Runtime and wrapper were redeployed from the central install root after removing
  legacy marker fallbacks. Historical audit recorded `arkserver` active and `arkserver2`
  stopped; current operational policy is to avoid Ragnarok for development, prefer
  `arkserver-obelisk-debug`, and use `arkserver2` only for approved fallback windows. See
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
- fact: `scripts/test_repo_hygiene.py` and CI now guard `.gitignore` coverage for build
  outputs, logs, shared libraries, cores, pycache, and local temp artifacts.
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
- fact: General function research has pivoted across the full modding surface. `scripts/summarize_core_ufunction_inventory.py`
  supports focused filters (`--outer-contains`, `--name-contains`, `--family`,
  `--min-params`, `--max-params`, `--include-functions`) and
  `docs/research/2026-05-27-shooterplayercontroller-function-inventory.md` identifies
  candidate-only player/controller surfaces for inventory, dinos, structures, tribe,
  transfer, notifications, and admin. Keep these offline until second-core/property-chain
  validation and SDK ownership gates are satisfied.
- fact: `docs/research/2026-05-27-primalitem-function-inventory.md` identifies
  candidate-only item surfaces for equip/use, remote inventory, crafting, repair,
  durability, and item NetExec. Narrow filters are required: broad `Use` matching pulled
  unrelated reflected objects with implausible property chains.
- fact: `docs/research/2026-05-27-primaldinocharacter-function-inventory.md` identifies
  candidate-only dino surfaces for passengers, carry checks, attacks, flight, tame status,
  and blueprint hooks. Favor compact offline fixtures such as `AddPassenger`,
  `AllowCarryCharacter`, `ServerRequestAttack`, and `SetCharacterStatusTameable`.
- fact: `docs/research/2026-05-27-sdk-module-taxonomy.md` defines the current module
  roadmap across the full modding surface: player, inventory, items, dinos, structures, tribes, transfer,
  admin, and internal UE reflection. Keep all gameplay modules candidate-only until they
  pass offline validation, fixture coverage, isolated runtime observation, copied-data
  ownership, and public C ABI gates.
- fact: `docs/research/2026-05-27-primalstructure-function-inventory.md` identifies
  candidate-only structure surfaces for access, snapping, demolish, pickup, variants,
  pincode, seating, and elevator controls. Favor small bool/object/int fixtures first;
  defer placement/build/range/string/array-heavy functions.
- fact: `docs/research/2026-05-27-missiontype-function-inventory.md` identifies
  candidate-only mission surfaces. `scripts/test_inspect_core_ufunctions.py` now has
  synthetic fixture coverage for `MissionType.AddPlayerToMission`,
  `BPAllowPlayerToLeaveMission`, `BPOnPlayerAddedToMission`, and a rejected string/array
  mission chain. Keep mission spawn/leaderboard/string/array-heavy paths deferred.
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
  found the existing Ragnarok-derived core and derivative packs. Current operator
  direction makes `arkserver` / Ragnarok available for Obelisk tests while RAM is tight
  and keeps `arkserver2` stopped. Follow
  `docs/research/2026-05-27-isolated-second-core-runbook.md` only after approval for the
  exact `arkserver` run window.
- fact: `scripts/inspect_core_ufunctions.py` can walk legacy `UStruct.Children +0x38` and
  `UField.Next +0x28` property chains from the core for UFunction and ScriptStruct
  evidence across module surfaces; see
  `docs/research/2026-05-27-core-ufunction-property-chain.md`.
- fact: `scripts/inspect_core_ufunctions.py` now validates inspected target, class, outer,
  and property objects with direct `GObjects[InternalIndex]` back-references; see
  `docs/research/2026-05-27-ufunction-membership-backrefs.md`.
- fact: `scripts/inspect_core_ufunctions.py` supports offline `--name-contains` and
  `--outer-contains` filters for Function/Struct discovery from core dumps. Broad
  substring searches are discovery-only and too noisy for runtime filters; exact
  candidates should use FName+outer+size+property-chain matches.
- fact: `scripts/inspect_core_ufunctions.py` now reports bounded enum candidates for
  `ByteProperty` through the observed `+0x70` enum pointer.
- fact: `scripts/summarize_core_ufunction_inventory.py` now provides a broad offline
  `UFunction` inventory from core/evidence packs. On the current core it found `5269`
  Function objects in the first `30000` GObjects entries; top outers include
  `ShooterPlayerController`, `PrimalDinoCharacter`, `PrimalCharacter`,
  `ShooterCheatManager`, and `PrimalItem`. See
  `docs/research/2026-05-27-general-ufunction-inventory.md`.
- fact: `ue/RuntimeReflection.{h,cpp}` now provides an internal, binary-hash-gated
  reflection reader with tests for bounded `UFunction`/`UProperty` chains and borrowed
  parameter ranges. It is not public ABI; it is the shared internal substrate for
  module recognizers.
- historical module evidence: chat reflection produced useful patterns for exact
  UFunction/outer/`ParmsSize`/property-chain recognition, bounded FString decoding,
  marker/env/SHA gates, dispatcher ownership, ABI guardrails, and benchmark gates. Keep
  detailed module evidence in `docs/research/2026-05-27-*chat*.md`,
  `docs/research/2026-05-27-fstring-layout.md`, and
  `docs/research/2026-05-27-sdk-chat-event-ownership-plan.md`.
- fact: chat remains internal/experimental only. `include/obelisk/ObeliskApi.h` has no
  chat structs/capabilities/functions, runtime plugin dispatch is blocked, and tests guard
  accidental promotion. Treat chat as one module proving promotion gates, not the active
  project center.
- fact: `FString` for this ARK Linux build is a strong candidate for
  `{TCHAR* Data, int32 ArrayNum, int32 ArrayMax}` with `TCHAR=UTF-32LE`; see
  `docs/research/2026-05-27-fstring-layout.md`.
- fact: `RuntimeReflection::TryDecodeFStringUtf32` now implements the internal decoder
  candidate with synthetic tests and strict reject conditions.
- fact: Internal dispatcher/benchmark work from chat is reusable as a promotion pattern:
  copied callback-duration data, opaque registration ids, idempotent unregister, owner
  cleanup before `dlclose`, exception isolation, and hot-path allocation gates should be
  required before any gameplay module reaches public SDK dispatch.
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
- risk: Runtime/reversing experiments on `arkserver` / Ragnarok can still affect the only
  running ARK instance. Use one gate at a time, short windows, copied evidence, and
  rollback posture.
- risk: `arkserver2` / TheIsland should stay stopped while RAM is constrained. Do not
  start it for Obelisk work unless the operator explicitly reopens it.
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

- next-step: Prioritize the general UE4 reflection pipeline: `FName`/`GNames`,
  `GUObjectArray`, `UObject`, `UFunction`, `UProperty`, and `ScriptStruct` evidence that
  can serve every future ARK modding module.
- next-step: Before any second-source core or scanner capture, create or confirm
  `arkserver-obelisk-debug`; use TheIsland only as an explicit operator-approved fallback
  and record rollback/posture evidence.
- next-step: Use `scripts/compare_reflection_snapshots.py --target <Outer.Name>` for
  focused second-source checks across inventory, structures, buffs, dinos, tribes,
  missions, transfers, and admin surfaces.
- next-step: Keep all module recognizers candidate-only until second-source layout
  comparison, copied-data ownership, callback lifetime, ABI gates, and runtime safety
  policy are satisfied for that module.
- next-step: Keep reducing tooling debt that makes reversing faster and safer: snapshot
  comparators, manifest regeneration, sanitizer tests, evidence packs, and bounded
  property-chain validation.
- rollback: while RAM is constrained, rollback targets `arkserver` / Ragnarok only within
  an approved test/rollback window: remove the experimental marker/env, keep
  `disable-plugins`, restart only Ragnarok if restart was approved, and run
  `scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map
  Ragnarok --instance arkserver`. Keep `arkserver2` stopped unless the operator explicitly
  reopens it.
- next-step: Generalize the binary-hash-scoped reflection pipeline only after another
  capture or ARK binary hash validates the same fields.
- next-step: Add binary hash validation or an instruction decoder before accepting future
  ProcessEvent prologue changes.
- next-step: Keep expanding package/export validation only when external plugin
  consumption exposes a concrete missing contract.
- fact: README, STATUS, and RELEASE link the pre-release versioning policy; avoid claiming
  `0.1.0` is imminent until the release checklist is satisfied.

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
