# Release Process

This project is not ready for a production-stable release yet. Use this checklist for the
first public `0.1.0` tag. Version labels and pre-release rules are defined in
[VERSIONING.md](VERSIONING.md).

## Scope

Included:

- Runtime bootstrap.
- ProcessEvent hook.
- C plugin ABI, after an explicit first-stable ABI freeze decision.
- Central install script and LinuxGSM wrappers.
- `oBaseEvents`.
- `OBELISK_INSTANCE_ID` logs and state markers.
- Filtered, non-mutating `ProcessEvent` callback infrastructure as the stable runtime
  observation model. Target-specific gameplay/module surfaces remain experimental unless
  explicitly promoted through the documented gates.
- `GameplayPolicyEvent` as the promoted v0.1 gameplay policy callback family, with copied
  POD scalar payloads and no identity, lookup, mutation, or return override authority.
- `DescribeResourceKind` as metadata-only resource category descriptors, not
  `ResourceHandle`, resource lookup, object identity, or cross-event correlation.
- `DescribeGameplayPolicyEventKind` as metadata-only descriptors for promoted
  `GameplayPolicyEvent` kinds, not UE lookup, module-specific SDK, mutation, or
  return-override authority.
- `ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI: copied UTF-8 message
  text, send mode, copied-payload flag, and process-local sequence only. It is a
  notification contract for plugins that parse their own text locally, not a command SDK,
  chat send/moderation API, sender identity API, UE lookup path, mutation surface, or
  return-override authority. Runtime producer hookup remains a separate gate and must not
  be implied by the SDK ABI alone.

Excluded:

- Stable gameplay module interception APIs.
- Full UE4 reflection.
- Higher-level gameplay SDK APIs outside `GameplayPolicyEvent` and the minimal
  `ChatMessageEvent` notification surface.
- `ResourceHandle`, GNames/GObjects promotion, public Inventory SDK, public
  `StructureEvents`, command SDKs, chat APIs beyond `ChatMessageEvent`, and
  player/tribe/dino/buff/mission/transfer APIs.
- Experimental first-party plugins such as `oPolicyAudit`, which require
  `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON` and are not published by the release gate.
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
   example.
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

When a release or preview promotes reflected gameplay module surfaces beyond the
core-first API, run the stricter promotion gate:

```bash
scripts/check_release_readiness.sh --require-second-source-readiness
```

With no explicit UFunction target set, this intentionally fails until the default
`minimal-second-source-intake` has complete, distinct second-source evidence. Explicit
`--ufunction-second-source-target-set` values replace that default, so include
`minimal-second-source-intake` explicitly when a broader promotion should keep the
core-first intake in the same gate.

When sanitized second-source snapshot roots exist, pass them into the same gate and keep
JSON reports as promotion artifacts. Write the report directory outside the repository
or under an ignored artifact path; unignored in-repo report paths are rejected before the
release build starts so the final clean-worktree check stays meaningful:

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
`structure-observer-intake` evidence plus the accepted compact inventory/structure layouts
from `minimal-second-source-intake`, and declared in `docs/public_gameplay_events.json`.
It exposes only copied POD scalar fields and keeps `StructureEvents`, separate Inventory
APIs, UE pointers, raw params, FName/GObjects indices, pincode values, player identity,
inventory identity, item identity, object identity, mutation, and return overrides outside
the public SDK. Inventory-backed signals are published only as
`GameplayPolicyEvent` masks/kinds/fields with `INVENTORY_BACKED`; they are not a separate
Inventory SDK.

The default second-source gate is intentionally scoped to the core-first UFunction intake:
`minimal-second-source-intake`. Mission target sets such as `mission-compact-intake` are
not part of the default gate, and scalar-candidate summaries are review aids only, not RC
scope. ScriptStruct promotion, including transfer structs, is not part of the default gate
and must be opted in explicitly. A release or PR that promotes another reflected module
family must name each promoted target set explicitly, for example:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set buff-compact-intake \
  --ufunction-second-source-target-set dino-compact-intake \
  --scriptstruct-second-source-target-set transfer-scriptstruct \
  --ufunction-second-source-root <second-source-ufunction-snapshots> \
  --scriptstruct-second-source-root <second-source-scriptstruct-snapshots>
```

Runtime-observer log summaries are a separate review artifact, not a release gate and not
second-source promotion evidence. Use them only on copied or sanitized logs when reviewing
an approved observer capture:

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
`GameplayPolicyEvent` is the promoted gameplay policy callback family in the v0.1 scope.
`ChatMessageEvent` is separately tracked as a minimal v0.1-rc copied-notification ABI for
chat-text plugins. It is declared in `docs/public_gameplay_events.json` so public event
capabilities stay audited, but it does not promote a command SDK, sender/player identity,
chat sending, moderation/blocking, raw `FString`, `UObject`, `UFunction`, FName/GObjects
indices, raw params, mutation, or return overrides. SDK acceptance for this event is ABI
layout coverage, `ChatEventDispatcher` copy/lifetime tests, plugin-manager owner-token
registration/unregister tests, and installed SDK consumer coverage. Runtime producer
hookup remains a separate gate; runtime-observer summaries and chat reflection logs do not
promote additional chat fields or prove end-to-end delivery.

5. Confirm `scripts/test_install_obelisk_layout.sh` covered runtime backup reinstall:
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

10. If this release candidate followed an approved runtime experiment, confirm quiet stable
   posture on the same approved validation adapter target. If no runtime experiment was
   part of the release validation, keep this release check offline and skip live harness
   inspection.

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>
```

11. For a release candidate, tag the validated candidate first. Release tags and release
    ref pushes are release-manager/lead-only; contributors should not tag or push release
    refs from ordinary development branches.

```bash
git tag -a v0.1.0-rc.1 -m "Obelisk 0.1.0-rc.1"
git push origin v0.1.0-rc.1
```

After the release candidate is validated and no RC blockers remain, tag the stable
release in a focused release-prep pass:

```bash
git tag -a v0.1.0 -m "Obelisk 0.1.0"
git push origin v0.1.0
```
