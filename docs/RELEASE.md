# Release Process

This project is not ready for a production-stable release yet. `v0.1.0-rc.2` is the
published core-first RC baseline. Use this checklist for future RC/stable candidates and
the eventual first public stable `0.1.0` tag. Version labels and pre-release rules are
defined in [VERSIONING.md](VERSIONING.md).

Read scope labels literally:

- Published RC baseline means the already-tagged `v0.1.0-rc.2` contract; later docs,
  examples, or release-gate hardening do not expand that tag retroactively.
- Current post-RC candidate means `HEAD` work for a future RC/stable candidate. It must
  pass a fresh clean release gate before any tag or release-ref push.
- Plugin Hub seed means post-SDK-complete planning only. Plugin Hub examples, packaging,
  intake tooling, installed plugin `.so` files, or popular plugin-family names do not
  promote public SDK surface or completion. Plugin Hub is not an ArkApi compatibility
  layer, module SDK roadmap, identity/lookup surface, mutation path, or return-override
  authority while the complete-SDK blockers remain open. Start archived Plugin Hub
  planning from `docs/PLUGIN_HUB_FOUNDATION_V1.md` and
  `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`; adding a first-party example or naming a popular plugin
  family does not promote public SDK surface.
- Planning-only lanes and target sets are guidance or demand signals. They are not release
  evidence, not public SDK surface, and are rejected by the release gate until replaced by
  a separately promoted target set.

Current release-scope non-authorization: this document grants no current-turn exact
live-op scope, no current-turn exact approval for operations, Discord send, server/log
read, marker/env change, protected live-server filesystem access, deploy/restart,
GitHub/release publication, Plugin Hub publication, public SDK readiness, or stable v1
claim. Historical TheIsland/Ragnarok/Genesis2 material, historical server names, the
latest release-readiness pass, public reachability, request packs, status reports,
`progress_normalization_trace`, source_overclaim diagnostics,
`source_overclaim_total_flag_count=0`, release-readiness passes, passive observation,
the latest validation pass, six-agent closure notes, Codex cache cleanup,
passive player evidence, passive player summaries, passive summaries,
passive snapshots, passive monitor ticks, passive monitor output, passive monitors,
passive triplets, beta tester notices, beta notices, future beta notices, Discord notice
drafts, package-shape installs, package installs, explicit-version non-`EXACT`
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
install/package success, package-shape install success, install/package-shape checks,
support-tier labels, package shape, package-shape/public package readiness, Plugin Hub
planning, scoped non-complete release statements, side-lane candidates/accounting, prior
approvals, historical live approvals/map names, historical approvals/map names, closure requests,
and tests
are not live authorization, runtime evidence, SDK evidence, approved in-game evidence,
SDK/P0 progress, live-op authorization, Discord authorization, publication authority,
runtime readiness, public SDK readiness, stable SDK readiness, Plugin Hub readiness,
support-tier activation, stable SDK claims, or stable claims. They may be cited only as
chronology/request context; they remain non-authorizing/non-evidence unless a claim names
both the current-turn exact approval for the scoped action and the accepted checker
evidence for the evidence result.
Current route state remains SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`, and
`approved_runtime_evidence_missing`.
A separately recorded standing live authority, if one exists for named operations, is
authorization only; it does not supply runtime evidence, SDK/P0 progress, public SDK
readiness, publication authority, stable SDK readiness, Plugin Hub readiness,
support-tier activation, package-shape/public package readiness, or a stable/complete SDK
claim.

## Scope

Release scope is intentionally narrower than the active research roadmap. Post-RC
recognizers, runtime-observer summaries, artifact packs, and internal dispatch helpers are
review inputs unless a release or PR explicitly promotes them through the gates below.

Included:

- Runtime bootstrap.
- ProcessEvent hook.
- C plugin ABI, after an explicit first-stable ABI freeze decision.
- Central install script and LinuxGSM wrappers.
- `oBaseEvents`, `oProcessTimer`, and `oDescriptorCatalog` as the built-by-default
  first-party reference plugin set included by the release gate for the current post-RC
  candidate; this does not retroactively add `oDescriptorCatalog` to the frozen
  `v0.1.0-rc.2` tag.
- `OBELISK_INSTANCE_ID` logs and state markers.
- Filtered raw `ProcessEvent` callback infrastructure as debug-gated runtime plumbing.
  Stable plugin paths should use copied Obelisk-owned events. Target-specific gameplay/module
  surfaces remain experimental unless explicitly promoted through the
  documented gates.
- Dispatcher callback cleanup that is safe across the current callback families:
  unregister/owner cleanup initiated from gameplay callbacks avoids dispatcher cleanup
  waits to prevent callback-to-callback deadlocks, while non-callback owner/plugin cleanup
  still waits for in-flight dispatch and deferred `DestroyUserData` cleanup.
- `GameplayPolicyEvent` as the promoted v0.1 gameplay policy callback family, with copied
  POD scalar payloads and no identity, no lookup, no mutation, and no return override
  authority. In the v1 compatibility inventory this remains `promoted-experimental-only`
  and is not a v1 completion claim.
  Structure-backed claims point to the fresh
  [`structure-observer-intake` evidence](research/2026-05-29-structure-observer-intake-refresh.md).
- `DescribeResourceKind` as metadata-only resource category descriptors, not
  `ResourceHandle`, resource lookup, object identity, or cross-event correlation.
- `DescribeGameplayPolicyEventKind` as metadata-only descriptors for promoted
  `GameplayPolicyEvent` kinds, not UE lookup, module-specific SDK, mutation, or
  return-override authority.
- `ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI: copied UTF-8 message
  text, send mode, copied-payload flag, and process-local sequence only. It is a
  notification contract for plugins that parse their own text locally, not a command SDK,
  chat send/moderation API, sender identity API, UE lookup path, mutation surface, or
  return-override authority. Historical, surface-local runtime producer delivery has
  accepted copied-log validation with 18 accepted delivery events covering send modes
  `0,1,2,3` through the `enable-chat-events` path during an operator-selected beta-test
  window, with no privacy blockers. This is v0.1-rc chat delivery evidence only, not
  current P0 approved runtime evidence, current-turn live-op approval, SDK/P0 progress,
  public SDK readiness, or v1 completion; historical `enable-chat-reflection` observer
  logs do not satisfy that gate.
- Process-local owner-token timers as a v0.1 core primitive: one-shot/repeating callbacks,
  zero-failure handles, explicit unregister, exception containment, and owner cleanup on
  plugin init failure/unload. They are not UE/gameplay timers, gameplay/module timer APIs,
  shared scheduler state, persistent handles, identity, lookup, permissions, commands, or
  cluster coordination. `oProcessTimer` is the first-party timer example and is included
  by the release gate.
- `oDescriptorCatalog` as a metadata-only descriptor reference plugin. It validates
  `DescribeResourceKind` and `DescribeGameplayPolicyEventKind` consumption without
  callbacks, timers, chat, identity, lookup, mutation, return override, or ABI expansion,
  and is included by the release gate.

RC public scope remains limited to `GameplayPolicyEvent`, the minimal copied
`ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
`v0.1.0-rc.2` additionally includes the process-local owner-token timer primitive as core
runtime API, without changing the copied gameplay/chat boundary.

Excluded:

- Stable gameplay module interception APIs.
- Full UE4 reflection.
- Higher-level gameplay SDK APIs outside `GameplayPolicyEvent` and the minimal
  `ChatMessageEvent` notification surface.
- `ResourceHandle`, GNames/GObjects promotion, public Inventory SDK, public
  `StructureEvents`, command SDKs, chat APIs beyond `ChatMessageEvent`, and
  player/tribe/dino/buff/mission/transfer APIs.
- Experimental first-party plugins such as `oPolicyAudit`, `oChatLogger`, and
  `oChatAudit`, which require `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON` and are not
  included by the release gate.
- Gameplay mutation, return overrides, arbitrary UE4 function calls, and public
  `CallProcessEvent`-based plugin behavior.
- Plugin callback blocking of the original `ProcessEvent` outside an explicit
  debug/experimental gate.
- Plugins with background workers, sockets, HTTP listeners/clients, long-lived file
  readers, or other external ingress unless they pass the documented background-work
  promotion gate.
- Production HTTP plugins.

## Checklist

1. Run CI on `main`.
2. Verify the ABI v1 freeze artifacts before tagging. For `v0.1.0`, Obelisk freezes the
   current append-only `ObeliskApi` ABI v1 layout as the first stable compatibility
   contract. Any ABI v2 must use an explicit migration plan. Do not expand public plugin
   APIs before the v1 freeze is reflected in `CHANGELOG.md`, ABI layout tests, in-tree SDK
   consumer validation, installed SDK consumer validation, and the `oBaseEvents` release
   example. Owner-token public registrations must keep using the plugin owner's init-time
   capability snapshot; later `PluginManager` construction must not widen callbacks for
   an already-loaded plugin.
3. Confirm first-stable plugin scope excludes background-work plugins unless their
   promotion evidence proves all of the following:
   idempotent shutdown through `ObeliskPlugin_Shutdown`, copied API/init-context data
   before post-init use, safe-disabled and instance-gated startup, workers started only
   after init and callback registration succeed, ingress stopped before unregister,
   owner-token callback handles unregistered before unload, queues drained, threads
   joined, sockets/files closed, no detached workers, and no persisted runtime handles.
4. Build locally:

```bash
scripts/check_release_readiness.sh
```

The script requires a clean worktree by default. Use `--allow-dirty` only while developing
the release gate itself. Set `OBELISK_KEEP_RELEASE_CHECK_ROOTS=1` to keep the temporary
install roots for manual inspection after the script completes.

Treat this command as the canonical core-first release gate, not just a local smoke/build
gate. It builds with experimental plugins off, runs CTest and script tests, rejects
production `libobelisk.so` builds that expose test-only/internal symbol patterns, validates
the install/SDK layout and dry-runs, checks the read-only CLI status path, and enforces a
clean worktree. Keep those checks in this script instead of adding parallel CI release
checks with different defaults. A final RC or stable candidate must also pass the
second-source readiness gate below on a clean worktree with the accepted snapshot root
configured.
The default CI release-readiness job runs this core-first baseline without the v1
completion option. Do not add `--require-v1-sdk-completion` to that default job; use it
only for an explicit stable SDK claim attempt with a reviewed release statement and
current gate evidence.

This core-first gate is necessary package/readiness evidence for `v0.1.x` RC/stable
candidates, but it is not a `v1.0` complete-SDK gate. A `v1.0` claim must still satisfy
[`SDK_V1_COMPATIBILITY.md`](SDK_V1_COMPATIBILITY.md) and the blocker map in
[`public_sdk_surfaces.json`](public_sdk_surfaces.json).
Use the explicit v1 gate when preparing a stable SDK claim:

```bash
scripts/check_release_readiness.sh \
  --require-v1-sdk-completion \
  --v1-sdk-release-statement <reviewed-v1-sdk-release-statement.md>
```

That option runs `scripts/check_public_sdk_v1_completion.py` before the core build work.
On the current post-RC tree it must fail closed because `v1_completion_required=false`,
`stable_release_contract.claim_allowed=false`, unresolved experimental surfaces remain,
and v1 blocker IDs are still planning or not promoted/excluded by release statement. The
release-readiness wrapper still requires an explicit `--v1-sdk-release-statement`; the
checker CLI also uses `docs/SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md` by default when
that durable scoped statement exists. In either path, statement rows must name every
non-promoted blocker as excluded or post-v1 before they satisfy wording bookkeeping.
Current route state remains SDK blocker promotion `0/12`, P0 dependency chain `0/4`,
`stable_claim_allowed=false`, and active blocker `approved_runtime_evidence_missing`.
Core-first release gates, the latest release-readiness pass, package-shape installs,
package installs, explicit-version non-`EXACT`
`find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` package-shape checks,
install/package-shape checks, Plugin Hub planning, side-lane accounting, and scoped
non-complete release statement bookkeeping must not be reinterpreted as route completion,
runtime readiness, publication authority, support-tier activation, Plugin Hub readiness,
or a stable SDK claim. Nested/split report aliases for package shape, scoped
release-statement outcomes, passive evidence, passive player evidence, passive monitor
ticks, passive monitors, side lanes, Plugin Hub, CMake/header checks, public reachability,
`progress_normalization_trace`, source_overclaim diagnostics,
`source_overclaim_total_flag_count=0`, release-readiness passes, historical live
approvals/map names, historical approvals/map names, beta notices, or support-tier labels
must not increment SDK blocker or P0 dependency-chain progress.

To validate only the scoped wording of a draft statement while the full v1 gate remains
intentionally blocked, use:

```bash
python3 scripts/check_public_sdk_v1_completion.py \
  --release-statement release/v1/public-sdk/scoped-release-statement-template.md \
  --validate-release-statement-scope
```

That scoped check accepts reviewed post-v1 outcome wording for already post-v1 blockers,
but it still reports that no `v1.0 stable`, complete SDK, full SDK, or production SDK
claim is allowed while top-level blockers remain planning.

After assembling an RC second-source root, run the committed RC layout smoke. This checks
that the copied second-source snapshots compare cleanly against the in-repo sanitized
UFunction fixtures for the RC target sets without claiming runtime promotion,
`ResourceHandle`, identity, mutation, return override, or a public Inventory/Structure SDK:

```bash
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root <second-source-ufunction-snapshots>
```

For future RC/stable publication, the final local candidate gate is the canonical release
readiness script with second-source readiness enabled and the accepted target-set
UFunction snapshot root configured. The published `v0.1.0-rc.2` checkpoint passed this
gate with the refreshed root recorded in
[`2026-05-30-head-rc-second-source-refresh-gap.md`](research/2026-05-30-head-rc-second-source-refresh-gap.md).
That root is evidence for the published `v0.1.0-rc.2` tag only; do not reuse it as the
final root for any later candidate. Regenerate the second-source root for the intended
release ref, including current bool-tail metadata, then rerun the same gate immediately
before any release-manager tag/push:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root <second-source-ufunction-snapshots> \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set structure-observer-intake \
  --ufunction-second-source-target-set chat-message-intake \
  --second-source-report-dir /tmp/obelisk-rc-second-source
```

The gate rejects second-source snapshot roots whose `evidence.obelisk_commit` does not
match the current validated `HEAD`. Use `--allow-cross-ref-second-source-root` only for an
explicit historical tag recovery after review; do not use it for a new release candidate.
When second-source readiness is required, the release script also runs a pre-build
UFunction readiness metadata preflight against the configured root and public RC target
sets. Missing roots, stale/incomplete artifact identity, missing current `BoolProperty`
tail metadata, or ambiguous RC target coverage fail before the build/test/install steps.
This protects the current post-RC candidate only; it does not revalidate or expand a
published RC tag.

For future release candidates or explicit recovery of a published tag, an existing local
or unpublished RC tag is not proof that the intended validated head is tagged. It may
point behind the current validated head after later release-prep fixes. Before any
release-manager tag/push, perform exact tag/ref verification: verify that the RC tag
commit, if it already exists, is exactly the intended validated release ref; if it is not,
stop and resolve the stale tag state instead of reusing or pushing it. Do not recreate a
published release-candidate tag unless explicitly recovering a release error, and do not
push a stale tag.

The promotion check always includes the public RC UFunction target sets:
`minimal-second-source-intake`, `structure-observer-intake`,
and `chat-message-intake`. Item return-only evidence remains planning-only/internal
backing evidence and is not a public RC/default target set. The check still needs a
configured second-source snapshot root, either through
`OBELISK_UFUNCTION_SECOND_SOURCE_ROOT` or `--ufunction-second-source-root`; without one,
the gate fails closed with missing second-source evidence. Explicit
`--ufunction-second-source-target-set` values add promoted release-readiness module target
sets to the required RC target sets; they do not replace or omit the public RC gate.

The accepted default intake is layout-only evidence: reports may show
`promotion_gate.ready=true` with `promotion_gate.ready_scope=layout_only` and
`promotion_gate.promotion_ready=false`. That refresh applies only to the documented
core-first scope, and it does not by itself promote a public Inventory SDK, public StructureEvents SDK,
`ResourceHandle`, object identity, GObjects lookup, mutation, or return overrides. Optional
redacted signature manifests accepted in offline-artifact consume mode remain
candidate-only. It also does not prove resource cross-event correlation.

Accepted transfer second-source extraction, including `transfer-ufunction-intake` and
`transfer-scriptstruct`, is layout-only offline evidence unless a later release or PR
promotes a separate release-readiness target set and passes the promotion gates. Existing
transfer target-set names are not release-readiness inputs. This does not promote a public
Transfer SDK, payload decoding, object identity, runtime hooks, mutation, return
overrides, or `ResourceHandle`.

UObject flag transition matrices and static flag-policy reports that pass the offline
artifact gate in consume mode are candidate evidence only. Consume-mode provenance does
not prove lifecycle/validity semantics, does not satisfy promote-mode artifact gates, and
must not unlock `ResourceHandle`, object lookup, GObjects promotion, mutation, or return
overrides. ResourceHandle semantic work must remain blocked until the helper predicate,
caller mode, mutation windows, rejected-object samples, and fail-closed lookup contract
are accepted through promote-mode gates.
Strict serial reuse/wraparound policy artifacts are also internal candidate-only
contracts. Consume-mode acceptance may narrow the design gap, but it does not prove
runtime reuse semantics, public lookup safety, persistent handles, identity, mutation,
return overrides, runtime negative samples, or public `ResourceHandle`.

Pass sanitized second-source snapshot roots into the same gate and keep JSON reports as
promotion artifacts. Write the report directory outside the repository
or under an ignored artifact path; unignored in-repo report paths are rejected before the
release build starts so the final clean-worktree check stays meaningful. The report
directory must be new or empty; the gate rejects stale generated report roots instead of
mixing historical JSON with a fresh candidate run:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root <second-source-ufunction-snapshots> \
  --second-source-report-dir <artifact-dir>
```

Second-source readiness reports must show `gate_mode=second_source_promotion` and
`promotion_gate.ready=true` before a reflected module surface can be considered accepted
for promotion review. Reports with `gate_mode=informational_gap_report` are gap reports
only, and even clean informational comparisons stay blocked with
`not_second_source_promotion_gate` instead of becoming promotable. Reports with
`gate_mode=base_fixture_readiness` only prove committed primary fixtures are present and
comparable.

Public gameplay event promotion has an additional SDK contract gate. A release that adds
any gameplay event callback to `include/obelisk/ObeliskApi.h` must update
`docs/public_gameplay_events.json` and prove the promoted event has all required artifacts:
accepted distinct second-source evidence, copied Obelisk-owned payload storage, no
`UObject`, `UFunction`, `FString`, raw parameter buffer, or UE property pointer in the
public header, append-only ABI fields with a capability bit, owner-token handle
registration, owner-scoped unregister, plugin-owner cleanup on init failure and unload,
ABI layout tests, installed SDK consumer tests, and release docs naming each promoted
target set. Runtime-observer summaries do not satisfy this SDK contract gate. The first
promoted event family is `GameplayPolicyEvent`, backed by the accepted
`structure-observer-intake` evidence plus the accepted compact inventory/structure
layouts from `minimal-second-source-intake`, and declared in
`docs/public_gameplay_events.json`. ReturnValue-only item-return evidence remains
planning-only/internal backing and does not count as a public RC/default target set.
The fresh structure-backed evidence is
[`2026-05-29-structure-observer-intake-refresh.md`](research/2026-05-29-structure-observer-intake-refresh.md)
and is layout-only support for copied/redacted policy backing.
It exposes only copied POD scalar fields and keeps `StructureEvents`, separate Inventory
APIs, UE pointers, raw params, FName/GObjects indices, pincode values, player identity,
inventory identity, item identity, object identity, mutation, and return overrides outside
the public SDK. Inventory-backed signals are published only as
`GameplayPolicyEvent` masks/kinds/fields with `INVENTORY_BACKED`; they are not a separate
Inventory SDK.

The v0.1.x resource programming shape is descriptor-driven and category-only:
`DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, then
`GameplayPolicyEvent` routing by `resource_kind`, `event_kind`, and `field_mask`.
In v0.1, `resource_kind` is a category only, not a game object identity. It must not be
treated as "this same structure/item", a lookup handle, a persistent ID, cross-event
correlation, coordinates, owner identity, or UE object access. Do not add `GetResource`,
`ResolveResource`, `ResourceHandle`, pointer-derived IDs, GNames/GObjects-derived IDs, or
mutation APIs without a new promotion gate that defines identity stability, privacy,
lifecycle, and cross-instance semantics.

The default second-source gate is intentionally scoped to the public RC UFunction target
sets: `minimal-second-source-intake`, `structure-observer-intake`,
and `chat-message-intake`. Item-return, Mission, and Transfer target sets such as
`item-return-only-policy-slice`, `mission-compact-intake`, and
`transfer-ufunction-intake` are not part of that gate, and scalar-candidate summaries are
review aids only, not RC scope. ScriptStruct target sets such as
`transfer-scriptstruct` are internal/layout-only until a separate promoted target set is
classified as release readiness; passing `--scriptstruct-second-source-root` is valid only
with a ScriptStruct target set that has gone through that promotion.
Planning/guidance-only target sets such as `players-identity-lifecycle-intake` and
`mission-copied-bool-policy-slice` are not promotable release target sets and are rejected by `scripts/check_release_readiness.sh`.
The Mission copied-bool lane is a planning-only/internal observer lane, not a public
Mission SDK, runtime hook, mutation, return override, identity, lookup, or release/public
promotion evidence.
NextGen/Plugin Hub planning target sets are also guidance-only demand signals, not
release/public promotion evidence; replace guidance-only lanes with a separately promoted
release/public target set after the SDK and second-source gates are satisfied.
A release or PR that promotes another reflected module family must name each promoted
target set explicitly after the shared target-set classifier marks it
`release_readiness`; those named sets are added to the public RC target sets:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set <promoted-release-readiness-ufunction-target-set> \
  --scriptstruct-second-source-target-set <promoted-release-readiness-scriptstruct-target-set> \
  --ufunction-second-source-root <second-source-ufunction-snapshots> \
  --scriptstruct-second-source-root <second-source-scriptstruct-snapshots>
```

If internal module recognizer work resumes after the RC, the remaining item
producer/runtime validation, Mission copied-bool observer, and Transfer `bAccept` lanes
stay internal unless a release names a separate promotion gate. For Transfer `bAccept`,
internal means offline/test-only evidence only: no runtime target source, no `PluginManager`
wiring, no marker/env activation, no installed plugin path, and no public manifest,
documentation, or example exposure. The three item return-only
checks are public only as copied `GameplayPolicyEvent` `ReturnValue` kinds; they do not
create an Inventory SDK, Items SDK, identity, lookup, mutation, return override, or
`ResourceHandle`; those remain absent.

Review artifacts:

Runtime-observer log summaries are review artifacts, not a release gate and not
second-source promotion evidence. Use them only on copied or sanitized logs when reviewing
a capture whose live collection was separately scoped and approved at the time:

```bash
python3 scripts/analyze_runtime_observer_log.py --fail-on-quality-blockers <copied-log>
```

The analyzer emits `obelisk.runtime-observer-log-summary.v1` JSON with
`review_scope=runtime_observer_evidence_summary`, `readiness_gate=none`, and
`promotion_gate.gate_type=runtime_observer_observational_only`. It also summarizes copied
runtime posture lines such as native LD_PRELOAD load, ProcessEvent hook install,
ReflectionScanner disabled state, and plugin-disabled state. Observer fields are reported
both as module-level aggregates and, when the log order provides enough context, as
per-function field layouts for chat, inventory, structure, or future module families. It
fails quality checks when a copied log has no observer evidence, is missing observer gates,
mixes binary SHA values, spans the same module across multiple source logs without
`--merge-module-sources`, has field-count/order problems, contains malformed observer
lines, or requires redaction. Module-level field aggregates are not promotable layouts and
are not used as promotion evidence; promotion evidence must be per target set/function and
come from second-source snapshot or static evidence, not runtime summaries. Even a clean
summary remains observational until the second-source and SDK ownership gates are
satisfied. Public `StructureEvents`, separate Inventory callback ABI/capability bits, SDK
structs, or plugin-facing Inventory registrations are outside the first stable release
scope unless a later release-prep pass promotes them through those gates.
`GameplayPolicyEvent` is the promoted gameplay policy callback family in the v0.1 scope;
in the v1 compatibility inventory it remains `promoted-experimental-only`, not a v1
completion claim.
`ChatMessageEvent` is separately tracked as a minimal v0.1-rc copied-notification ABI for
chat-text plugins. In the v1 compatibility inventory it also remains
`promoted-experimental-only`. It is declared in `docs/public_gameplay_events.json` so public event
capabilities stay audited, but it does not promote a command SDK, sender/player identity,
chat sending, moderation/blocking, raw `FString`, `UObject`, `UFunction`, FName/GObjects
indices, raw params, mutation, or return overrides. SDK acceptance for this event is ABI
layout coverage, accepted `chat-message-intake` second-source comparison,
`ChatEventDispatcher` copy/lifetime tests, plugin-manager owner-token
registration/unregister tests, and installed SDK consumer coverage. The runtime producer
exists only when a current-turn scoped observer-debug run also has the
`enable-chat-events` marker/env path, supported binary SHA, and positive dispatch budget.
Historical, surface-local accepted copied-log delivery
validation with 18 accepted delivery events covering send modes `0,1,2,3` exists for
that v0.1-rc path only; it is not current P0 approved runtime evidence, current-turn
live-op approval, SDK/P0 progress, public SDK readiness, or v1 completion. Further beta
observation is regression/revalidation only unless a new promotion gate is defined. It
still does not promote commands, identity, moderation/blocking, mutation, return
overrides, or UE internals. Do not count `enable-chat-reflection` observer evidence for
that claim.

5. Run `scripts/test_install_obelisk_layout.sh` with a fresh explicit install root, for
   example one created with `mktemp -d /tmp/obelisk-layout-check.XXXXXX`, and confirm it
   covered runtime backup reinstall:
   one backup each for `libobelisk.so` and `libsubhook.so`, no `.incoming.*` files, no
   `.install-runtime.*` staging directory, invalid install roots rejected, failed runtime
   rename cleanup, required positional install roots even when `OBELISK_ROOT` is set, and
   installed `RUNPATH=$ORIGIN`.
6. Confirm no generated artifacts are staged:

```bash
git status --short --ignored
```

7. Update `CHANGELOG.md`.
8. Confirm docs and wrappers use `state/instances/<instance-id>/` markers only.
9. Before a maintenance-window deploy or restart, confirm the installed LinuxGSM wrapper
   matches the versioned template:

```bash
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed <ark-binary-dir>/ObeliskRun.sh
```

10. If this release candidate followed a current-turn approved runtime experiment, confirm quiet stable
   posture on the same current-turn approved validation adapter target. If no runtime experiment was
   part of the release validation, keep this release check offline and skip live harness
   inspection.

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>
```

11. For a future release candidate, tag the validated candidate first. Release tags and
    release ref pushes are release-manager/lead-only; contributors should not tag or push
    release refs from ordinary development branches.
    No tag or release-ref push is authorized without explicit release-manager/lead
    authorization for the current turn.
    Replace `<rc-tag>` with the new release tag. Do not recreate a published
    release-candidate tag unless explicitly recovering a release error. If the target tag
    already exists locally, verify it points exactly at the intended validated ref; if it
    points elsewhere, recreate it only after rerunning the gate on that ref. Do not push a
    stale tag. Use the tag/ref checker before pushing the tag.

```bash
python3 scripts/check_release_tag_state.py --tag <rc-tag> --ref HEAD --allow-missing
git tag -a <rc-tag> -m "Obelisk <rc-version>"
python3 scripts/check_release_tag_state.py --tag <rc-tag> --ref HEAD
# Only after the explicit release-manager/lead authorization above:
# git push origin <rc-tag>
```

After RC feedback is resolved and the stable release gate passes on the intended ref, tag
the stable release in a focused release-prep pass with explicit release-manager approval.
Use the same exact tag/ref verification flow and keep publication as an explicit step:

```bash
python3 scripts/check_release_tag_state.py --tag <stable-tag> --ref HEAD --allow-missing
git tag -a <stable-tag> -m "Obelisk <stable-version>"
python3 scripts/check_release_tag_state.py --tag <stable-tag> --ref HEAD
# Only after explicit release-manager approval:
# git push origin <stable-tag>
```
