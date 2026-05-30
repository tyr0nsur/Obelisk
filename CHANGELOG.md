# Changelog

## Unreleased

- Kept raw `EventManager`, `PluginManager`, and dispatcher test helpers out of production
  shared-library builds while preserving wraparound and capability regression coverage.
- Hardened timer id allocation and offline artifact validation so timer handles skip zero
  and live ids after wrap, Transfer ScriptStruct fields all carry transfer blockers, and
  relative provenance paths are resolved against their sidecar before protected-root checks.
- Kept `PluginManager` cleanup-failure injection hooks out of production shared-library
  builds while preserving the test-only retry coverage.
- Hardened raw `EventManager` snapshot setup-failure handling so a global callback
  snapshot failure also suppresses the filtered callback phase for that hook dispatch, and
  kept the injection hook out of the production shared-library surface.
- Hardened raw `EventManager` ProcessEvent dispatch so snapshot setup failures are
  contained in the hook-facing trigger path without invoking partial callback snapshots.
- Hardened raw ProcessEvent blocking so plugin pre-callbacks can block only when that
  plugin owner's init-time capability snapshot advertised ProcessEvent blocking and the
  live debug gate remains enabled.
- Hardened release readiness and offline evidence guardrails so non-release target sets
  are rejected through the shared classifier, Transfer ScriptStruct payload fields stay
  redacted-only, ResourceHandle reports its missing runtime artifact schemas explicitly,
  and rejected Mission copied observations prove stale output is cleared.
- Hardened installed SDK package metadata so CMake exports all public ABI version macros
  and installed consumers verify package/header ABI parity.
- Hardened plugin API rejection paths so no-throw warning logging is used across callback
  validation, debug-gated registration rejection, timer/chat/gameplay registration
  rejection, and `CallProcessEvent` gating.
- Hardened internal Mission copied-bool recognition so recognition-only
  `GetPlayerUsableItems` no longer retains raw parameter pointers or sizes.
- Clarified UFunction target-set listing and Structure build-policy guidance so
  release-readiness target sets, internal/layout-only sets, and planning-only sets are
  machine-readable and exact snapshot inputs stay separate from evidence-pack manifests.
- Clarified Plugin Hub support tiers so production-supported seeds, experimental examples,
  and blocked/backlog lanes are explicit for plugin authors.
- Hardened `EventManager` owned callback registration so null raw ProcessEvent callbacks
  fail closed without creating inert handles or owner-cleanup state.
- Hardened UFunction reflection promotion gates so internal/layout-only target sets cannot
  satisfy release-readiness just because their second-source layout comparison is accepted.
- Hardened offline artifact gates so JSON manifests, provenance sidecars, and artifact
  checksums are opened without following symlinks after protected-path prechecks.
- Clarified SDK/plugin-author docs so installed CMake package variables are distinct from
  public C header macros and current production-supported plugin seeds stay explicit.
- Hardened timer core registration so repeating timers with zero interval are rejected at
  `TimerManager`, matching the public plugin ABI contract.
- Hardened SDK consumer guardrails for append-only API slots: consumers must check
  `abi_version`, `struct_size`, capability bits, terminal slot offsets, and non-null
  function pointers before optional API use.
- Hardened offline evidence gates so plural path-like sidecar fields such as
  `source_artifacts` cannot hide relative protected-root paths.
- Hardened target guidance so duplicate explicit `--target` filters fail closed.
- Clarified v1 research routing and Plugin Hub docs so production seeds stay limited to
  lifecycle/config/logging, descriptor/catalog, and process-local timers while copied chat
  and copied policy examples remain experimental patterns.
- Hardened SDK packaging so install layout publishes only the allowlisted public
  `include/obelisk/ObeliskApi.h` header instead of the full `include/` tree.
- Hardened PluginManager init-failure cleanup coverage so owner-token timer registration
  attempted during close is rejected and leaves no live timer for that owner.
- Blocked `transfer-baccept-only-policy-slice` from release/public promotion gates while
  preserving it as internal transfer evidence guidance.
- Hardened offline artifact gates with explicit coverage for symlinked workspace roots.
- Tightened Plugin Hub and first-party plugin wording so seed examples do not imply
  category graduation, storage/database/webhook services, or unpromoted SDK surfaces.
- Hardened release readiness so required UFunction second-source roots are preflighted
  before build/test/install work for complete artifact identity, current BoolProperty tail
  metadata, and unambiguous public RC target coverage.
- Hardened raw `EventManager` snapshot dispatch so reused registration ids do not
  reactivate stale raw callbacks unless the same id and callback pointer are still present
  in the same callback family.
- Hardened snapshot regeneration and evidence guardrails: UFunction regeneration now
  requires complete artifact identity or an evidence-pack manifest, ScriptStruct
  regeneration tests verify selected evidence-pack labels, and ResourceHandle blocker
  interpretation is checked against evaluator constants.
- Hardened Discord embed sending so forbidden secret/webhook/player-text phrases are
  rejected from both embed fields and top-level content.
- Clarified post-RC Plugin Hub terminology so production-supported seeds are limited to
  lifecycle/config/logging, descriptor/catalog, and process-local timer examples, while
  copied chat and copied policy examples remain experimental seed patterns.
- Hardened offline snapshot/artifact tooling: `inspect_core_ufunctions.py --snapshot-json`
  now requires complete evidence metadata and 64-character SHA256 inputs, and artifact
  pack normalization reports invalid timestamp-derived artifact ids without a traceback.
- Added PluginManager coverage that retained init-failure cleanup keeps both chat and
  filtered ProcessEvent callbacks registered until the later cleanup retry succeeds.
- Reduced raw `EventManager` granular unregister blocking so a targeted unregister can
  take effect while an unrelated ProcessEvent callback is in flight, while owner cleanup
  still waits as the plugin unload barrier.
- Clarified Mission, Structure, and ResourceHandle offline evidence routing: Mission
  copied-bool stays consume-only/planning-only, Structure build-policy uses focused
  snapshot inputs instead of evidence-pack manifests, and ResourceHandle remains a
  semantic blocker rather than another broad scan target.
- Hardened release/public guardrails so planning-only Mission lanes cannot back release
  target-set promotion, public SDK docs, or Plugin Hub production claims.
- Hardened plugin init-failure cleanup so a callback-cleanup failure still avoids
  `dlclose` if retry-retention tracking itself fails.
- Fixed experimental `oChatLogger` safe-disabled initialization so it reads config before
  requiring/registering chat callbacks, and added active/disabled SDK fixture coverage.
- Added a protected-path-aware static tooling checker for optional radare2/Ghidra
  availability and smoke evidence.
- Added a candidate-only `players-identity-lifecycle-intake` target-set guidance lane
  without promoting player identity, lookup, runtime work, or SDK surface.
- Hardened static tooling checks so Ghidra headless usage output is treated as installed
  tooling evidence and smoke outputs reject symlink races.
- Blocked guidance-only target sets such as `players-identity-lifecycle-intake` and
  NextGen/Plugin Hub planning lanes from release readiness target-set promotion.
- Marked `mission-copied-bool-policy-slice` as an internal planning-only lane and blocked
  it from release/public promotion while preserving consume-side guidance.
- Hardened offline artifact tooling so symlinked parent directories fail closed for
  critical manifests, core paths, static-tool binaries, and smoke output roots.
- Added characterization coverage for current raw `EventManager` unregister behavior when
  a ProcessEvent callback is already in flight.
- Mark post-RC installed SDK packages as `0.1.0-dev` / `dev` so development builds do not
  masquerade as the published `v0.1.0-rc.2` tag.
- Hardened the internal Mission copied-bool recognizer to validate Unreal `BoolProperty`
  tail metadata for the five approved copied bools before exposing parameter ranges.
- Fixed experimental `oChatAudit` safe-disabled initialization so it does not require chat
  or timer capabilities until its config actually enables audit registration.
- Tightened offline evidence gates so GObjects two-core manifests must carry a canonical
  artifact identity hash and ScriptStruct inventory packs must preserve bool-tail metadata.
- Added EventManager owner-cleanup coverage for in-flight global pre and filtered post
  callbacks.
- Hardened plugin unload/init-failure cleanup so a callback cleanup failure prevents
  `dlclose`, retains the plugin for retry, and avoids repeating plugin shutdown on the
  retained unload attempt.
- Added `oDescriptorCatalog` as a release-scope metadata-only reference plugin for
  descriptor discovery and routing validation without callbacks or ABI expansion.
- Promoted three item return-only checks as append-only `GameplayPolicyEvent` kinds for
  copied `ReturnValue` observation: allow-equip, can-repair, and use-item-onto-item. This
  does not add a public Items SDK, Inventory SDK, identity, mutation, or return override.

## 0.1.0-rc.2

- Published a refreshed core-first release candidate with the same public copied-data API
  boundary as `v0.1.0-rc.1`.
- Added owner-token process-local timers and the `oProcessTimer` first-party example as a
  v0.1 core primitive without UE/gameplay timer, identity, persistence, or command
  semantics.
- Refreshed the RC UFunction second-source evidence for the intended ref: all 12 public
  RC snapshots across the four public target sets compare as accepted with preserved
  BoolProperty tail metadata.
- Preserved explicit snapshot artifact identity in the UFunction inspector CLI so future
  second-source roots can satisfy strict readiness gates.

## 0.1.0-rc.1

Published release candidate. RC public scope remains limited to
`GameplayPolicyEvent`, the minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
`DescribeGameplayPolicyEventKind`. This entry is not a production-stable release claim.
Post-RC development should target the broader `v1.0` production core and eventual
ArkApi-style plugin replacement without retroactively expanding this RC scope.

## 0.1.0-dev

Active development toward a future `v0.1.0`. This is not a release tag and does not promise
stable plugin or reflection compatibility yet. See `docs/VERSIONING.md`.

Current baseline:

- Promoted the owner-token timer API as the first non-UE-dependent v0.1 core primitive:
  process-local one-shot/repeating callbacks, zero-failure handles, explicit owner-scoped
  unregister, plugin init-failure/unload cleanup, and ABI/layout tests. Timer handles are
  not persistent, shared-cluster state, UE identity, lookup, mutation, or command routing.

- Linux `LD_PRELOAD` runtime bootstrap validated through the ARK: Survival Evolved
  dedicated server debug harness.
- Absolute x86_64 `UObject::ProcessEvent` hook with guarded validation.
- C plugin ABI with logging, debug-gated filtered ProcessEvent callbacks, owner cleanup,
  owner-token callback handles, owner-scoped unregister, and optional plugin shutdown.
- Public plugin C ABI v1 is the intended first-stable compatibility contract for
  `v0.1.0`; any ABI v2 must ship with an explicit migration plan.
- Runtime default-deny gates for filtered/global ProcessEvent callbacks, the unpromoted
  `CallProcessEvent` escape hatch, and plugin callback blocking of the original
  ProcessEvent path. These require explicit debug-window env, marker, and capability
  posture before they behave as active features.
- Fail-closed ProcessEvent hook removal: restore/reprotect failures now preserve hook
  state and trampoline ownership instead of claiming a clean removal.
- Central install layout under an operator-chosen Obelisk root, with runtime libraries
  staged before atomic publication.
- Plugin publication through `scripts/install_obelisk_plugin.sh`, using a staged non-`.so`
  copy before atomic rename into the shared plugin directory.
- Multi-instance shared-root posture: plugin binaries and configs may be shared, while
  `OBELISK_INSTANCE_ID` scopes logs, markers, plugin activation, and process-local runtime
  handles.
- LinuxGSM wrapper templates for the current ARK debug harness.
- `oBaseEvents` as the first official plugin example, including owner-token handle
  registration and safe `instance_allowlist` validation.
- `GameplayPolicyEvent` as the promoted v0.1 gameplay policy callback family, exposing
  copied POD scalar policy signals through owner-token handle registration without
  resource identity, lookup, mutation, or return override authority.
- Internal inventory policy recognizers for `PrimalItem.CanUse` and
  `PrimalItem.AllowRemoteAddToInventory` now fail closed on exact UFunction class,
  outer object index, property class object index, and property flag mismatches before
  feeding copied scalar policy events.
- `DescribeResourceKind` as metadata-only descriptors for known resource categories,
  explicitly not `ResourceHandle`, object identity, lookup, or cross-event correlation.
- `DescribeGameplayPolicyEventKind` as metadata-only descriptors for promoted
  `GameplayPolicyEvent` kinds, explicitly not a module SDK, UE lookup, mutation, or
  return-override surface.
- `ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI surface with copied UTF-8
  message bytes, send mode, copied-payload flag, and process-local sequence only;
  explicitly not a command SDK, sender identity API, chat send/moderation surface, UE
  lookup, raw `FString`, raw params, UE pointers, mutation, or return-override surface.
  Actual plugin-facing delivery from real chat messages has accepted copied-log
  `enable-chat-events` validation with 18 accepted delivery events from an approved
  operator-selected beta-test window, covering send modes `0,1,2,3` with no privacy
  blockers.
- First-stable plugin scope now excludes background workers, sockets, HTTP
  listeners/clients, long-lived file readers, and other external ingress unless a future
  plugin passes explicit shutdown, unregister, drain, join, and close gates.
- Read-only operator CLI for install, instance, and plugin state inspection.
- Release readiness script covering build, CTest, script tests, second-source readiness
  when required, install layout validation, installed SDK consumer builds, read-only CLI
  status, installer dry-runs, and whitespace/clean-tree checks.
- Offline reflection capture analyzer, shared target-set snapshot comparison/regeneration,
  evidence-pack tooling, and dry-run UFunction target-set regeneration planning for
  second-source reflection research. The refreshed default `minimal-second-source-intake`
  remains layout-only with `promotion_ready=false` and does not promote public
  Inventory/Structure SDKs, `ResourceHandle`, GObjects lookup, mutation, or return
  overrides.
- Static-only global candidate evidence tooling for FName/GNames/GObjects promotion
  research, with fail-closed promotion gates, explicit candidate-kind handling,
  copied/generated artifact hashes, and per-target ELF/xref provenance.
- CTest coverage for plugin config, ABI layout, plugin lifecycle, callback ownership,
  runtime markers, module recognizers, and external SDK consumers.

Breaking/development changes:

- Legacy binary-local plugin fallback and map-marker fallback paths were removed.
- Legacy chat/monitor prototype code was removed from the release tree.
- Public plugin config is now runtime-owned under
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- Enabled plugin configs fail closed unless scoped to the current `OBELISK_INSTANCE_ID` or
  explicit `allow_all_instances=true`.
- Global `ProcessEvent` callbacks are default-denied and require explicit runtime and
  marker gates.

Not included yet:

- GNames/GObjects-backed reflection layer.
- `ResourceHandle`, public `StructureEvents`, public Inventory SDK, and player, tribe,
  inventory, item, structure, dino, buff, mission, transfer, admin, permission, command, or
  gameplay/module timer SDKs, including richer chat APIs and command APIs beyond
  `ChatMessageEvent`.
- Gameplay mutation, return override APIs, and public `CallProcessEvent`-based plugin
  behavior.
- Mutable operator lifecycle commands such as `obelisk restart` and
  `obelisk plugins enable/disable`; these are post-first-stable TODOs.
- Production-ready HTTP plugins.
- Background-work plugins without idempotent shutdown and worker/ingress cleanup evidence.
