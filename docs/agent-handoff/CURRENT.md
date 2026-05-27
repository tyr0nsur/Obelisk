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
- fact: Read-only ops audit found no confirmed isolated/debug ARK instance on
  `/servidor/ark`; treat both observed instances as live/non-isolated unless an operator
  confirms otherwise. See
  `docs/research/2026-05-27-reflectionscanner-isolated-instance-audit.md`.
- fact: Ops planning recommends a new `arkserver-obelisk-debug` LinuxGSM instance with
  isolated ports, saves, cluster posture, `OBELISK_LOG_DIR`, and wrapper-level Obelisk
  env instead of shared map markers; see
  `docs/research/2026-05-27-isolated-debug-instance-plan.md`.
- fact: Runtime and wrapper were redeployed from the central install root after removing
  legacy marker fallbacks. Only `arkserver` / Ragnarok is active for development;
  `arkserver2` / TheIsland is stopped. See
  `docs/research/2026-05-27-ops-restart-audit-instance-id.md`.
- fact: `scripts/analyze_reflectionscanner_capture.py` passively summarizes copied
  ReflectionScanner logs for UObject scores, FName `matched_clues`, delayed globals, and
  reject markers; it does not touch server state.
- fact: Commit `c890c2a` tightened FName probe confirmation. ReflectionScanner now logs
  `source_global` for FName indirect-table probes, and the analyzer only treats exact
  hits as repeat-confirmed when the same table appears from distinct source globals or
  distinct targets; see `docs/research/2026-05-27-reflectionscanner-analyzer-review.md`.
- fact: Top-level CMake now pins `subhook` to local FetchContent commit
  `568d2e5a5d6013907e8008857968906b33ef3b7d` instead of `master`; see
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
- fact: Commit `fc837a0` added passive static xref annotation to
  `scripts/analyze_reflectionscanner_capture.py`. Use `--objdump-xrefs` with a
  pre-generated `objdump -d` text file to annotate candidate globals; this is supporting
  evidence only, not offset acceptance.
- fact: Commit `ac6eada` added `PluginManagerTests` using an injectable fake library
  loader. The suite covers valid load/unload, missing `GetInfo`, missing `Init`, invalid
  metadata, init failure, callback cleanup, shutdown, and close behavior.
- fact: Commit `882f0d7` hardened `scripts/test_install_obelisk_layout.sh` so the installed
  SDK consumer validates config dir/path, instance id, installed-header dependency, and
  plugin placement under the install root.
- fact: Commit `3760f3b` clarified that sub-agents may recommend skill changes, but the
  team lead owns skill edits, commits, pushes, and handoff updates.
- fact: Commit `2420e82` added the static/reversing workflow skills:
  `obelisk-static-binary-analysis`, `obelisk-tooling-discipline`, and
  `obelisk-ue4-type-reconstruction`.
- fact: Commit `1e62968` makes `PluginManager::UnloadAll()` unload plugins in reverse
  load order and adds a multi-plugin order test.
- fact: Commit `6da5c9c` installs the public SDK as a CMake package export
  (`ObeliskTargets.cmake`, `ObeliskConfig.cmake`, and version file) through the installer's
  SDK component.
- fact: The installed layout test now consumes the installed SDK through
  `find_package(Obelisk CONFIG REQUIRED)` and `Obelisk::obelisk_sdk`, so package export
  regressions are covered by `scripts/test_install_obelisk_layout.sh`.
- fact: Commit `a986a57` adds analyzer evidence pack metadata. Use
  `scripts/analyze_reflectionscanner_capture.py --json --binary <ShooterGameServer>
  --objdump-xrefs <objdump.txt> <Obelisk.log>` to record Obelisk commit, binary SHA256,
  copied logs, objdump artifact, candidate counts, reject markers, and promotion gate.
  The workflow is documented in
  `docs/research/2026-05-27-gname-evidence-pack-workflow.md`.

## Rejected Or Unsafe

- rejected: ProcessEvent candidate `0x1d11cb0` did not receive gameplay events.
- risk: Raw FString scanning/discovery must not be enabled on live Ragnarok as
  the normal test path.
- risk: Native exec probes must remain disabled on live servers.
- risk: The `subhook` pin was selected from the existing local checkout without internet
  verification; full offline resilience still needs a mirror or vendored archive.

## Priority Next Steps

- fact: ProcessEvent hook installation now requires a unique validated signature match.
  Direct offset fallback has been removed from active runtime code. See
  `docs/research/2026-05-27-processevent-target-validation.md`.
- fact: Plugin ProcessEvent callbacks now carry owner tokens and are unregistered on init
  failure and before unload/`dlclose`; see
  `docs/research/2026-05-27-plugin-callback-ownership-hardening.md`.
- fact: Runtime now supports optional `extern "C" void ObeliskPlugin_Shutdown()`,
  resolved outside `ObeliskApi` and called before callback owner cleanup and `dlclose`;
  see `docs/research/2026-05-27-plugin-shutdown-lifecycle.md`.
- fact: Commit `6f20a2c` introduced the strict plugin metadata/config ABI. Plugins must
  export `ObeliskPlugin_GetInfo`, the runtime creates/validates
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`, and `ObeliskPlugin_Init` receives an
  `ObeliskPluginInitContext`.
- fact: Top-level CMake builds `plugins/oBaseEvents/oBaseEvents.so` as the first official
  plugin example. `oBaseEvents` has migrated to the metadata/config ABI; legacy
  chat/monitor prototype source has been removed from the release tree.
- fact: Plugin structure and promotion rules are now documented in
  `docs/PLUGIN_ARCHITECTURE.md`; `plugins/README.md` records the intended
  `examples/` and `experimental/` split without moving code or changing CMake.
- fact: Full build completed after fixing `ue/ReflectionScanner.cpp` pointer formatting in
  the reflection/chat metadata audit.
- next-step: Resolve `FName` indices through `GNames` or `FNamePool`.
- next-step: Locate `GUObjectArray`/`GObjects` and enumerate `UFunction` metadata.
- next-step: Get operator permission to create or designate an isolated/debug instance
  before running ReflectionScanner; preferred plan is `arkserver-obelisk-debug`.
- next-step: Use isolated ReflectionScanner captures to compare UObject validation scores
  before accepting any `GObjects`, `GNames`, or `UFunction` offset.
- next-step: In the next isolated ReflectionScanner capture, compare any
  `FName indirect-table probe` lines against `None`, `ClientMessage`, and `ServerChat`;
  require `matched_clues=3/3` plus repeat confirmation through distinct `source_global`
  values or distinct targets before treating a table as a `GNames` research candidate.
- next-step: After a repeat-confirmed `GNames` research candidate appears, generate
  `objdump -d -M intel` for the matching ShooterGameServer binary and run the analyzer with
  `--binary` plus `--objdump-xrefs`; inspect whether candidate `source_global` references
  are real load/store paths before designing runtime name-resolution code.
- next-step: Replace raw chat parameter probing with reflected parameter decoding.
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
