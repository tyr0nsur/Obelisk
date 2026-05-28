# Current Agent Handoff

Updated: 2026-05-28

## Active Operating Objective

- fact: The persistent leader objective is tracked in the goal tool, not repeated in skills
  or default sub-agent prompts.
- agent context rule: pass sub-agents only the scoped objective, ownership, relevant skills,
  safety baseline, and deliverable for their assigned task.
- agent lifecycle rule: every new supervised agent round starts by checking for stale
  stand-by agents; close completed/obsolete agents before spawning replacements and keep a
  polling/integration plan for any intentionally active agent.
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
  `.so` is published into `/servidor/ark/obelisk/plugins/` with
  `scripts/install_obelisk_plugin.sh`; inactive plugins stay outside the install root.
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
- fact: The normal LinuxGSM wrapper pins `OBELISK_PLUGIN_DIR` to
  `${OBELISK_ROOT}/plugins` so inherited parent environments cannot redirect plugin
  loading outside the central install root. The live wrapper was refreshed without
  restart; backup: `/home/flowcommunity-ark/backups/ObeliskRun.sh.20260528-031006.bak`.
- fact: Runtime-side debug/scanner gates now require env+instance marker, so direct
  `LD_PRELOAD` launches cannot enable ProcessEvent hook, ptrace, debug-control,
  ReflectionScanner, or native exec probes by env alone. Marker names:
  `enable-process-event-hook`, `allow-ptrace`, `enable-debug-control`,
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
- fact: Plugin API ProcessEvent registration wrappers reject null callbacks and negative
  filtered FName indices before registering callbacks. `-1` remains a runtime sentinel for
  unknown function names, not a valid plugin subscription target.
- fact: Plugin API ProcessEvent registration wrappers also reject callbacks whose owner
  cannot be attributed to the currently initializing plugin or an already-loaded Obelisk
  plugin shared object. This prevents ownerless callbacks from surviving plugin unload;
  helper-module/background-thread callbacks must use the append-only owner-token API.
- fact: `ObeliskPluginInitContext` now appends `plugin_owner_token`, and `ObeliskApi`
  appends owner-token ProcessEvent registration functions guarded by
  `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS`. Tokens are removed on init failure and
  unload.
- fact: `ObeliskApi` now also appends owner-token ProcessEvent registration functions that
  return process-local `uint64_t` handles, guarded by
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES`. Public granular unregister is
  owner-scoped through `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)`;
  do not expose or document bare unregister-by-id across the plugin ABI.
- fact: `oBaseEvents` C exports catch plugin-side exceptions before returning across the
  runtime/plugin ABI. `ObeliskPlugin_Init` resets plugin state on config failure or thrown
  exception, and `ObeliskPlugin_Shutdown` is idempotent.
- fact: Contributor-facing organization is intentionally lightweight: `main` plus
  short-lived topic branches, current source directories kept stable, agent-only process
  moved out of contributor workflow, SDK install/package validation documented, and the
  legacy MVP moved to `docs/archive/`.
- fact: Obelisk's intended production cluster posture is one shared Obelisk root for
  runtime libraries, plugin binaries, and shared plugin config, with unique
  `OBELISK_INSTANCE_ID` values, per-instance logs, and per-instance markers/runtime state.
  Mutable shared plugin state requires explicit plugin-level locking/atomic-write design.
- fact: Operator CLI lifecycle/mutation commands are intentionally post-first-stable TODOs,
  not current production requirements. The current CLI remains read-only; future
  `plugins enable/disable/start/stop/restart` commands must wrap instance-scoped
  LinuxGSM/staged-installer operations, reject unsafe per-instance mutations from
  `allow_all_instances=true`, and use dry-run/backups/symlink rejection/atomic writes.
- fact: First-stable release readiness is now consolidated in
  `scripts/check_release_readiness.sh`. It builds RelWithDebInfo, runs CTest and script
  tests, validates installed runtime/SDK layout, exercises read-only operator CLI status,
  dry-runs runtime/plugin installers, and runs `git diff --check` without touching live
  ARK server roots.
- fact: Release readiness now fails closed on tracked or untracked non-ignored worktree
  changes unless `--allow-dirty` is used while developing the gate. CTest also loads the
  real `oBaseEvents` plugin through the SDK consumer fixture, validating its exported
  `GetInfo`/`Init`/optional `Shutdown` path against the public ABI.
- fact: First-stable hardening now covers the active `oBaseEvents` callback path: SDK
  consumer CTest enables `oBaseEvents` with `process_event.enabled=true` and verifies one
  owner-token handle registration plus one owner-scoped unregister during shutdown.
  `oBaseEvents` no longer publishes `map_allowlist` in its default config; non-empty
  legacy `map_allowlist` values are rejected until a reliable map identity contract exists,
  and SDK consumer CTest now covers that fail-closed path directly.
  `scripts/install_obelisk_plugin.sh` uses the same non-root absolute path and symlink-root
  validation as the runtime installer.
- fact: The CMake package version remains numeric `0.1.0` as the SDK compatibility floor
  while the public development line stays `0.1.0-dev`. Installed
  `ObeliskConfig.cmake` exports `Obelisk_DEVELOPMENT_LINE`,
  `Obelisk_RELEASE_CHANNEL`, and public ABI version variables so consumers and tests can
  distinguish a dev package from a tagged release. Official examples use plugin metadata
  version `0.1.0-dev` until the stable tag exists.
- fact: Plugin lifecycle hardening now has offline regression coverage for owner-token
  ProcessEvent callbacks registered from init-time helper threads when `Init` returns
  false or throws. Both paths must run shutdown, unregister callbacks, invalidate the
  owner token, and close the library once. `UnloadAll` also has coverage for plugins whose
  `Shutdown` throws while ProcessEvent and chat callbacks are still registered.
- fact: `EventManagerTests` now initialize the runtime logger and cover throwing
  pre/post callbacks. Exceptions are logged, do not propagate, and do not stop later
  callbacks from running; only an explicit `false` pre-callback blocks dispatch.
- fact: Plugin init now receives a per-plugin copy of the `ObeliskApi` table. A plugin
  that mutates its received function table cannot corrupt the manager template or poison
  later plugin loads; `PluginManagerTests` covers this with a mutating plugin followed by
  a clean plugin.
- fact: Runtime installer publication now stages both runtime libraries before publishing
  and rolls back any already-published runtime file if the paired publish fails. Layout
  tests force failure on the second runtime rename and verify the original
  `libsubhook.so`/`libobelisk.so` pair remains intact with no temporary files left behind.
- fact: The public SDK header now exposes C typedef names for `ObeliskPluginMetadata`,
  `ObeliskPluginInitContext`, and `ObeliskApi`, and the build includes a C-language SDK
  consumer plugin loaded through the same fixture path. This covers the documented C entry
  points with a real C compiler instead of only C++ consumers.
- fact: `scripts/install_obelisk.sh` now accepts `--build-dir` and honors
  `OBELISK_BUILD_DIR`; release readiness passes the same build directory into layout and
  dry-run install validation. Runtime and plugin installers reject unexpected extra
  positional arguments instead of silently redirecting the target root.
- fact: Public `CallProcessEvent` remains in the ABI table for compatibility but is now
  default-deny. It requires `OBELISK_ALLOW_CALL_PROCESS_EVENT=1` plus the per-instance
  marker `allow-call-process-event`; only then does the runtime advertise
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT` and call the original trampoline.
- fact: `ObeliskApi*` and `ObeliskPluginInitContext*` are borrowed for
  `ObeliskPlugin_Init` only. Public examples, `oBaseEvents`, and SDK consumer fixtures must
  copy `ObeliskApi` by value before using runtime functions during shutdown or callbacks.
  The SDK consumer fixture clears its local init table before shutdown to catch dangling
  pointer patterns.
- fact: `ObeliskPluginMetadata` string fields must point to static or plugin-owned storage
  that remains valid until the plugin shared object is closed.
- fact: Contributor-facing status now defines the current game interaction boundary:
  filtered, non-mutating `ProcessEvent` observation is the stable game-facing pattern for
  first-stable work. Gameplay mutation, return overrides, arbitrary UE4 calls, public
  `CallProcessEvent` behavior, borrowed UE4 object/string/param exposure, and higher-level
  gameplay SDK modules remain blocked until promoted with reflection-backed decoding,
  ownership policy, and isolated runtime evidence.
- fact: Stable posture no longer has a scanner escape hatch: `--expect-stable` rejects
  ReflectionScanner env, non-zero `OBELISK_PE_TRACE_LIMIT`, global ProcessEvent callbacks,
  public `CallProcessEvent`, and module observer env. Use `--forbid-chat-reflection` for
  quiet Ragnarok/post-release checks; release docs now require that command explicitly.
- fact: Older TheIsland/`arkserver2` research runbooks are marked historical/superseded
  while RAM is constrained. The operational doc guardrail now scans research docs with live
  marker/restart snippets and requires an explicit historical or approved-runbook banner.
- fact: Second-source snapshot comparison now rejects partial identity reuse. Missing
  identity, fully matching identity, or shared `artifact_sha256`, `capture_id`, or
  `evidence_pack_id` is `inconclusive`, even if the sanitized layout matches. A promoted
  module shape needs distinct capture and evidence-pack identity, not just a changed commit
  or path.
- fact: Snapshot regenerators now require the full artifact identity quartet together:
  `artifact_kind`, `artifact_sha256`, `capture_id`, and `evidence_pack_id`. Partial identity
  is rejected before writing snapshots, and artifact identity still requires an explicit
  `--fname-root-slot`.
- fact: `build_core_dump_evidence_pack.py --gobjects-sample-index` uses only explicit
  `--fname-root-slot` values for sampled UObject/class name resolution. Default primary
  FName roots are not mixed into second-source GObjects sampling.
- fact: The LinuxGSM production wrapper scrubs inherited `OBELISK_ALLOW_CALL_PROCESS_EVENT`
  and `OBELISK_PE_TRACE_LIMIT` alongside the other marker-managed debug env vars before
  deriving runtime env from per-instance markers.
- fact: Runtime and plugin installers reject symlinked managed install paths before
  writing. Runtime install checks `lib`, `plugins`, `include`, `include/obelisk`, `config`,
  `logs`, `state`, and `state/instances`; plugin install checks `plugins`. This prevents
  atomic publication from escaping the central Obelisk root through pre-existing symlinks.
- fact: Commit `c0d1e4c` pushed the hardened first-stable gates. On 2026-05-28,
  `scripts/check_release_readiness.sh` passed from a clean tracked/untracked worktree
  (ignored `build/` and `scripts/__pycache__/` only), and the read-only Ragnarok posture
  check passed with `--expect-stable --forbid-chat-reflection --map Ragnarok --instance
  arkserver`.
- fact: Shared plugin config default creation is hardened for concurrent multi-instance
  startup: each process uses a unique temporary file and atomically installs the default
  only if the config path is still absent, with coverage in `PluginConfigTests`.
- fact: Enabled plugin configs fail closed for shared clusters: `enabled=true` now
  requires either a matching non-empty `instance_allowlist` or explicit
  `allow_all_instances=true`. Missing/empty allowlists are skipped instead of activating
  on every ARK process sharing the config. Do not publish map-scoped config fields until a
  reliable map identity enters the ABI or plugin contract.
- fact: Plugin metadata `default_config_json` must declare the shared-cluster activation
  envelope explicitly: `enabled=false`, an `instance_allowlist` array, and
  `allow_all_instances=false`. Existing configs may omit `allow_all_instances`; enabled
  configs still fail closed unless scoped to the current instance or explicitly all-instance.
- fact: Plugin loading now fails closed before discovery when `OBELISK_INSTANCE_ID` is
  missing, empty, or contains anything outside letters, digits, `_`, or `-`. Config
  `instance_allowlist` entries use the same safe-token rule.
- fact: Plugin config preparation rejects symlinked plugin config directories, symlinked
  `config.json`, and non-regular `config.json` files before parsing shared config.
- fact: `ObeliskPluginInitContext` string pointers are documented as borrowed only for
  `ObeliskPlugin_Init`; plugins must copy `config_dir`, `config_path`, or `instance_id`
  before using them from shutdown, worker threads, or later callbacks.
- fact: The public README example uses owner-token handle registration plus explicit
  `ObeliskPlugin_Shutdown` unregister instead of teaching legacy callback registration.
- fact: Owner-token ProcessEvent registrations now work during `ObeliskPlugin_Init` from
  helper/background threads that do not inherit the loader thread-local current owner. The
  runtime tracks an initializing-owner set for the init window and still removes token
  state/callbacks on init failure and unload.
- fact: SDK consumer fixture now treats `ObeliskPlugin_Shutdown` as optional, matching
  `PluginManager`; a no-shutdown minimal plugin fixture covers that contract.
- fact: `PluginManager` rejects `.so` symlink candidates during plugin directory scanning
  before `dlopen`, so `${OBELISK_PLUGIN_DIR}` cannot load a plugin through a symlink escape.
- fact: `PluginManager::LoadPlugins` now uses scope-exit cleanup after `dlopen`: exceptions
  during symbol resolution, init, logging, or insertion into `m_LoadedPlugins` close the
  handle, call optional plugin shutdown after an init attempt, and remove plugin-owned
  EventManager/ChatEventDispatcher callbacks before `dlclose`.
- fact: `PluginManager::UnloadAll` continues unloading remaining plugins if a loader close
  operation throws, logs the failure, and clears loaded plugin state so a later unload does
  not repeat shutdown/close on partially unloaded entries.
- fact: Plugin lifecycle tests now pin shutdown ordering: optional
  `ObeliskPlugin_Shutdown` runs while plugin-owned callbacks are still registered, and
  callbacks are removed before the library close step.
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
- fact: `scripts/compare_reflection_snapshots.py --target-set minimal-second-source-intake`
  expands the canonical first second-source UFunction intake:
  `PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory`,
  `PrimalStructure.AllowStructureAccess`, and `PrimalStructure.IsAllowedToDemolish`.
  `--target-set transfer-scriptstruct` expands the two transfer ScriptStruct fixtures.
  Use `--list-target-sets` to print the available named groups without reading snapshots.
- fact: `scripts/compare_reflection_snapshots.py` now requires sanitized artifact identity
  (`artifact_kind`, `artifact_sha256`, `capture_id`, `evidence_pack_id`) before accepting
  a second-source comparison. Missing or matching artifact identity is inconclusive, so
  self-comparison of the primary fixture root cannot masquerade as independent evidence.
  Readiness JSON includes per-target details for missing, inconclusive, rejected, or
  accepted targets.
- fact: Second-source workflow docs and offline tool help now warn that the primary-core
  FName root slot default is not reusable evidence for new artifacts. For second-source
  work, first derive or scan a per-artifact verified FName root/table and pass it
  explicitly before regenerating UObjects/UFunction/ScriptStruct evidence.
- fact: UFunction and ScriptStruct regenerators now enforce that rule when artifact
  identity flags are supplied: `--fname-root-slot` is required instead of silently using
  the primary-core default.
- fact: GObjects sample evidence now has the same guardrail:
  `build_core_dump_evidence_pack.py --gobjects-sample-index` requires an explicit
  `--fname-root-slot` for the sampled artifact so UObject/Class names are not resolved
  through a primary-core-only default.
- fact: `scripts/regenerate_ufunction_snapshots.py --check-layout` now supports
  UFunction layout-only verification for second-source intake. It ignores unstable
  identity/evidence indices while preserving target identity, UFunction fields, and
  property-chain layout drift.
- fact: UFunction and ScriptStruct snapshot regenerators accept sanitized artifact
  identity flags (`--artifact-kind`, `--artifact-sha256`, `--capture-id`,
  `--evidence-pack-id`) for second-source evidence packs. The committed primary fixtures
  carry the primary core artifact SHA without storing absolute core paths.
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
- finding: Runtime/API audit items have mostly been closed: public owner-token callback
  handles are exposed, `CallProcessEvent` double-execution is guarded, hook removal tracks
  active frames, and debug-control shutdown is owned/joined.
- fact: Commit `6b9fe8a` documents the `CallProcessEvent` reentrancy
  contract in the public SDK header, README, and plugin architecture docs without changing
  ABI layout. A pre-callback that calls `CallProcessEvent` should return `false`; returning
  `true` used to risk double execution by the detour.
- fact: Runtime now tracks when `CallProcessEvent` is invoked from a pre-callback and
  skips the automatic original call if the callback returns `true`, logging a warning
  instead of executing the UE function twice. `ProcessEventCallGuardTests` cover nested
  and sibling pre-callback scopes.
- fact: Commit `5cf3de7` added internal `EventManager`
  registration IDs and `UnregisterCallback(id)` coverage. Later commit `7e405f8` promoted
  the safe public form as owner-token handle registration plus
  `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)`.
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
  dispatch. This now supports the owner-token handle unregister API added later in
  `7e405f8`.
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
  server. Current fixture readiness: UFunction `35/35` comparable and ScriptStruct `2/2`
  comparable. Second-source acceptance now additionally requires independent sanitized
  artifact identity; self-comparison is inconclusive.
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
- next-step: Runtime/API follow-up: keep expanding tests around plugin lifecycle and
  callback behavior before promoting plugins that manually invoke the original trampoline.
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
  stopped. Current operator direction on 2026-05-28 makes `arkserver` / Ragnarok the
  temporary Obelisk development/test harness while RAM is constrained and keeps
  `arkserver2` stopped; the preferred future target remains a dedicated
  `arkserver-obelisk-debug` instance when available. See
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
- fact: SDK consumer fixtures now validate the modern public owner-token handle path:
  external plugins compile against `Obelisk::obelisk_sdk`, receive a non-zero
  `plugin_owner_token`, register a filtered ProcessEvent callback through
  `RegisterPreProcessEventForNameIndexWithOwnerTokenHandle`, and unregister it through
  `UnregisterProcessEventCallbackWithOwnerToken` during shutdown. The installed layout
  test exercises the same contract from the installed CMake package.
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
  central `${OBELISK_ROOT}/lib/libobelisk.so` is not present in `LD_PRELOAD` and mapped, if
  a deleted `libobelisk` mapping remains, or if scanner/native-exec env vars are present.
  Offline procfs fixture coverage is in
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
- fact: Runtime installation stages `libobelisk.so` through the CMake `Runtime` component
  in a temporary install root, then publishes `libsubhook.so` and `libobelisk.so` with
  destination-local `.incoming.<pid>` names plus atomic rename. Backup reinstall coverage
  requires one matching backup each for both runtime libraries and no temporary leftovers.
- fact: `scripts/install_obelisk.sh` rejects empty, relative, `/`, and symlink install
  roots, and its cleanup trap removes destination `.incoming.<pid>` files plus the runtime
  staging root on failed runtime renames.
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
- fact: LinuxGSM wrappers must not inherit unsafe production config/log/plugin env from a
  shell session. The production wrapper pins plugin/config/log dirs under `OBELISK_ROOT`;
  the debug wrapper no longer enables `OBELISK_DEBUG_ALLOW_PTRACE=1` by default.
- fact: Plugin deployment has a staged installer: copy to a temporary non-`.so` filename
  in the destination plugin directory, then atomic rename to the final `.so`, so shared
  discovery cannot see partial plugin copies.
- fact: Initial operator CLI exists at `scripts/obelisk.py` with read-only `status`,
  `instances list`, `plugins list`, and `plugins show`. Lifecycle commands remain planned
  LinuxGSM wrappers; plugin restart means instance restart until hot reload is proven.
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
