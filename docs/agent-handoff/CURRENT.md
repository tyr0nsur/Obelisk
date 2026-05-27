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
- fact: A controlled Ragnarok dev capture on commit `5754fca` tested
  `OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30`. Startup probe rejected it with
  `table=0x0` and `reason=unreadable_table_header`; the server was then restarted without
  scanner/static-root env. Treat this as inconclusive, not accepted; see
  `docs/research/2026-05-27-static-fname-root-live-capture.md`.

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
- next-step: Stop trying to promote chat UObject globals directly into GNames. Next FName
  work should use static discovery of the name table global or a bounded alternate name
  storage scanner, then validate with the analyzer.
- next-step: Relax only the static-root sampler path to attempt bounded entry reads even
  when static-root table counters are zero, while logging counters and keeping samples out
  of analyzer `--strict`.
- next-step: After a repeat-confirmed `GNames` research candidate appears, generate
  `objdump -d -M intel` for the matching ShooterGameServer binary and run the analyzer with
  `--binary` plus `--objdump-xrefs`; inspect whether candidate `source_global` references
  are real load/store paths before designing runtime name-resolution code.
- next-step: To get a real GNames evidence pack, create or designate an isolated debug
  instance and run a short ReflectionScanner capture with plugins disabled and native exec
  probes unset.
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
