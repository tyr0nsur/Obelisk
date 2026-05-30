# RC Checkpoint Slicing Plan

## Historical Status

This note is historical dirty-tree recovery context from 2026-05-29. It is not active
routing for the current head, not a request to stage checkpoints, and not current chat or
release authorization. For active routing use `docs/agent-handoff/CURRENT.md`; for the
published RC gate and accepted minimal copied `ChatMessageEvent` evidence use
`docs/research/2026-05-30-rc-second-source-release-gate-check.md` and
`docs/research/2026-05-29-chat-message-second-source-readiness.md`.

## Objective

Record how the then-current broad dirty worktree could be split into reviewable local
checkpoints toward
`v0.1.0-rc.1` without pushing to GitHub or mixing post-RC research into the first public
release candidate.

## Historical Dirty Gate

The core-first release gate passed locally in dirty mode with the accepted minimal
second-source root:

```bash
scripts/check_release_readiness.sh \
  --allow-dirty \
  --require-second-source-readiness \
  --ufunction-second-source-root /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/ufunction-snapshots \
  --second-source-report-dir /tmp/obelisk-rc-second-source-current
```

This was a point-in-time dirty-mode validation for an earlier integration state. It did
not prove later worktree state satisfied the technical gate, and it did not prove RC
readiness. The later published RC baseline is documented separately in
`docs/research/2026-05-30-rc-second-source-release-gate-check.md`.

## Historical Checkpoint Order

The subsections below preserve the old recovery sequence for audit context only. Do not
use them as current checkpoint routing; use `docs/agent-handoff/CURRENT.md` for current
priorities.

### 0-pre. Local Guardrail Prelude: Staged-Path Helper

Purpose: make later checkpoint scope checks reproducible from a clean checkout.

Include only:

- `scripts/check_staged_paths.py`
- `scripts/test_check_staged_paths.py`

Validate:

```bash
python3 scripts/test_check_staged_paths.py
python3 -m py_compile scripts/check_staged_paths.py scripts/test_check_staged_paths.py
git diff --check -- scripts/check_staged_paths.py scripts/test_check_staged_paths.py
```

Keep this helper separate from artifact-gate/runtime/API changes. If this prelude is not
checkpointed first, do not treat `scripts/check_staged_paths.py` as a checkout-clean
requirement for 0a; compare `git diff --cached --name-only` manually instead.

### 0a. Local Guardrail Prelude: Artifact Gate

Purpose: make the local review surface deterministic before slicing runtime/API changes.
This checkpoint was the recommended first local checkpoint for the then-broad worktree.
Keep it narrow: artifact hygiene only, so it can be reviewed without staging API,
runtime, public docs, handoff, skills, or research-evidence changes. It assumes 0-pre has
already made `scripts/check_staged_paths.py` available in the checkout if the staged-path
helper is used.

Include only:

- `scripts/scan_resource_handle_serials.py`
- `scripts/test_scan_resource_handle_serials.py`
- `scripts/validate_offline_artifact_gate.py`
- `scripts/test_validate_offline_artifact_gate.py`

Validate:

```bash
python3 scripts/test_scan_resource_handle_serials.py
python3 scripts/test_validate_offline_artifact_gate.py
git add -N \
  scripts/scan_resource_handle_serials.py \
  scripts/test_scan_resource_handle_serials.py \
  scripts/validate_offline_artifact_gate.py \
  scripts/test_validate_offline_artifact_gate.py
git diff --check -- \
  scripts/scan_resource_handle_serials.py \
  scripts/test_scan_resource_handle_serials.py \
  scripts/validate_offline_artifact_gate.py \
  scripts/test_validate_offline_artifact_gate.py
```

For the actual staged checkpoint, verify the staged scope explicitly:

```bash
git diff --cached --check -- \
  scripts/scan_resource_handle_serials.py \
  scripts/test_scan_resource_handle_serials.py \
  scripts/validate_offline_artifact_gate.py \
  scripts/test_validate_offline_artifact_gate.py
scripts/check_staged_paths.py \
  scripts/scan_resource_handle_serials.py \
  scripts/test_scan_resource_handle_serials.py \
  scripts/validate_offline_artifact_gate.py \
  scripts/test_validate_offline_artifact_gate.py
```

The staged path helper should print exactly the four 0a scripts and fail on missing or
extra staged paths. Keep `scripts/check_staged_paths.py` itself outside 0a; introduce it
through 0-pre if the checkout does not already have it.

Keep out:

- runtime/API implementation changes;
- broad release/public-scope guardrails that read public API/docs/handoff/skills;
- analyzer output, offline evidence packs, generated snapshots, logs, copied server
  configs, or other artifacts;
- any statement that the current dirty worktree passes the release gate.

### 0b. Release-Gate Options Prelude

Purpose: keep release-check option/default behavior self-contained before staging
API/docs slices. Unlike broad release/public-scope guardrails, these tests should read only
the release gate script and its option fixtures, so checkpoint 0b can be reviewed without
staging public API, docs, handoff, skills, research notes, or evidence packs. Run the broad
public-scope guardrails with the later API/docs checkpoint that stages the inputs they
assert.

Include:

- `scripts/check_release_readiness.sh` only for option/default and in-repo report-dir ignored-path validation alignment
- `scripts/test_check_release_readiness_options.sh` only for option/default and in-repo report-dir ignored-path validation alignment

Validate:

```bash
bash scripts/test_check_release_readiness_options.sh
git diff --cached --check -- scripts/check_release_readiness.sh scripts/test_check_release_readiness_options.sh
scripts/check_staged_paths.py \
  scripts/check_release_readiness.sh \
  scripts/test_check_release_readiness_options.sh
```

The staged path helper should print exactly the two 0b script paths and fail on missing or
extra staged paths.

Keep out:

- runtime/API implementation changes;
- public docs, public metadata JSON, handoff, skills, research-note changes, or broad
  public-scope guardrail edits;
- offline evidence packs, generated snapshots, logs, copied server configs, or other
  artifacts;
- any claim that broad guardrail success proves RC readiness.

### 1. RC API: Public Callback And Metadata Surface

Purpose: freeze the public v1 API surface for the first RC around copied POD
`GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, metadata-only
`DescribeResourceKind`, and metadata-only `DescribeGameplayPolicyEventKind`.

Include:

- `include/obelisk/ObeliskApi.h`
- `core/PluginManager.cpp`
- `core/ChatEventDispatcher.{h,cpp}`
- `core/StructureEventDispatcher.{h,cpp}`
- `core/InventoryPolicyEventDispatcher.{h,cpp}`
- `tests/abi/AbiLayoutTests.cpp`
- `tests/abi/CAbiLayoutTests.c`
- `tests/core/PluginManagerTests.cpp`
- `tests/core/ChatEventDispatcherTests.cpp`
- `tests/core/StructureEventDispatcherTests.cpp`
- `tests/core/InventoryPolicyEventDispatcherTests.cpp`
- `tests/sdk_consumer/*`
- `tests/sdk_installed_consumer/*`
- `docs/public_gameplay_events.json`
- `docs/PLUGIN_ARCHITECTURE.md`
- `scripts/test_versioning_guardrails.py`

Validate:

```bash
ctest --test-dir build --output-on-failure -R 'Abi|Sdk|PluginManager|InventoryPolicy|StructureEventDispatcher'
python3 -m json.tool docs/public_gameplay_events.json
python3 scripts/test_versioning_guardrails.py
git diff --check -- <focused paths>
```

Keep out:

- public Inventory SDK;
- public StructureEvents SDK;
- ResourceHandle, object identity, lookup, mutation, return overrides;
- resource cross-event correlation;
- richer chat APIs beyond the minimal copied `ChatMessageEvent`;
- chat delivery-log analyzer route-field support, route coverage plan, and route evidence
  docs;
- dino/buff/mission/tribe public APIs;
- public `CallProcessEvent` behavior.

Review note: `GameplayPolicyEvent` became the stable public subscription surface for the
RC, while `ChatMessageEvent` became a minimal copied notification ABI. Its accepted
second-source and beta delivery evidence is recorded in
`docs/research/2026-05-29-chat-message-second-source-readiness.md`; this old checkpoint
plan is not current chat routing. Keep the public claim scoped to copied notification ABI
only; no richer chat APIs, identity, moderation, mutation, return override, route
evidence, or UE internals are promoted. Runtime producers for structure/inventory/chat
remain exact-target, marker-gated, and budgeted.

### 2. Runtime Observer Safety

Purpose: keep ProcessEvent and internal observer gates stable while preserving default-deny
runtime behavior. Preserve the dispatcher callback cleanup rule: unregister/owner cleanup
initiated from gameplay callbacks avoids dispatcher cleanup waits to prevent
callback-to-callback deadlocks, while non-callback owner/plugin cleanup still waits for
in-flight dispatch and deferred `DestroyUserData` cleanup.

Include:

- `CMakeLists.txt` hunks that add only dispatcher/runtime tests required by checkpoint 1
  or existing internal observer tests;
- `core/GameplayCallbackScope.h` and dispatcher cleanup hunks needed by the
  callback-safe cleanup rule;
- `hooks/ProcessEventHook.cpp`;
- `hooks/ProcessEventStructureReflection.*`;
- `hooks/ProcessEventInventoryReflection.*`;
- focused ProcessEvent structure/inventory tests.

Validate:

```bash
ctest --test-dir build --output-on-failure -R 'ProcessEvent|StructureReflection|InventoryReflection|EventManager'
git diff --check -- <focused paths>
```

Keep out or split:

- `ue/DinoReflection.*`, `tests/core/DinoReflectionTests.cpp`, and the matching
  `CMakeLists.txt` hunks unless making a separate internal-recognizer checkpoint. Dino has
  accepted layout evidence, but no hook or public API path is promoted for RC. If it stays
  compiled into `libobelisk.so`, record that as internal-only code with no public surface
  and validate it with `DinoReflectionTests`.
- Apply the same split rule to `MissionReflection`, `ItemReflection`, `BuffReflection`,
  `TransferReflection`, and candidate-only rollups: accepted layout evidence or
  `candidate_only` signatures must not enter checkpoint 1 unless the surface has a public
  manifest entry, ABI/lifecycle tests, installed SDK consumer tests, and explicit
  redaction docs.

### 3. Script Harness Prelude

Purpose: make local script validation deterministic before committing the heavy offline
tooling changes.

Include:

- `scripts/run_script_tests.sh`
- `scripts/test_run_script_tests.sh`

Validate:

```bash
bash scripts/test_run_script_tests.sh
scripts/run_script_tests.sh --python-tests-only
git diff --check -- scripts/run_script_tests.sh scripts/test_run_script_tests.sh
```

### 4. Offline Evidence Tooling

Purpose: land protected-path guards, direct FName-root intake, second-source readiness,
transfer layout evidence, static global evidence, and redacted ResourceHandle
revalidation/blocker tooling. This is mostly RC-supporting infrastructure and post-RC
research support, not a public SDK expansion.

Include by sub-slice:

- FName manifest tooling:
  - `scripts/validate_fname_index_manifest.py`
  - `scripts/test_validate_fname_index_manifest.py`
  - `tests/fixtures/fname_index_manifests/*`
  - `docs/oBaseEvents.md` only for manifest-related docs.
- Direct-root second-source intake:
  - `scripts/scan_core_fname_tables.py`
  - `scripts/run_second_source_core_intake.py`
  - matching tests.
- Snapshot/readiness/protected-path guards:
  - `scripts/compare_reflection_snapshots.py`
  - `scripts/regenerate_ufunction_snapshots.py`
  - `scripts/regenerate_scriptstruct_snapshots.py`
  - `scripts/snapshot_evidence_pack.py`
  - matching tests.
- Transfer evidence slicing:
  - `transfer-ufunction-intake` and `transfer-scriptstruct` fixture/snapshot or research
    updates only when they stay layout-only/offline;
  - keep accepted transfer evidence out of checkpoint 1 unless a later post-RC promotion
    explicitly adds a copied public surface, target-set gates, ABI tests, and privacy
    review;
  - no public Transfer SDK, payload decoding, object identity, runtime hook, mutation,
    return override, or `ResourceHandle` claim.
- Offline artifact gate and redacted signature hygiene:
  - `scripts/validate_offline_artifact_gate.py` only if it was not isolated in
    checkpoint 0a;
  - `scripts/test_validate_offline_artifact_gate.py` only if it was not isolated in
    checkpoint 0a;
  - `scripts/build_redacted_ufunction_signatures.py`
  - `scripts/test_build_redacted_ufunction_signatures.py`
- Chat route analyzer/plan:
  - chat delivery-log analyzer route-field support and tests;
  - docs/research route plan or coverage notes that preserve diagnostic route evidence
    without changing the public chat ABI.
- Static/GObjects/ResourceHandle tooling:
  - `scripts/build_static_global_promotion_evidence.py`
  - `scripts/build_uobject_flag_transition_matrix.py`
  - `scripts/reconcile_gobjects_samples.py`
  - `scripts/evaluate_resource_handle_revalidation.py`
  - matching tests.
  - Consume-mode UObject flag matrix/provenance packs may close artifact-history gaps, but
    they remain candidate-only until promote-mode gates and lifecycle/validity semantics
    are accepted. Semantic helper predicates, caller mode, mutation windows,
    rejected-object samples, and a fail-closed lookup contract are still required before
    ResourceHandle promotion.

Validate:

```bash
PYTHONPATH=scripts python3 -m unittest \
  scripts/test_validate_fname_index_manifest.py \
  scripts/test_scan_core_fname_tables.py \
  scripts/test_run_second_source_core_intake.py \
  scripts/test_compare_reflection_snapshots.py \
  scripts/test_regenerate_ufunction_snapshots.py \
  scripts/test_regenerate_scriptstruct_snapshots.py \
  scripts/test_snapshot_evidence_pack.py \
  scripts/test_validate_offline_artifact_gate.py \
  scripts/test_build_redacted_ufunction_signatures.py \
  scripts/test_build_static_global_promotion_evidence.py \
  scripts/test_reconcile_gobjects_samples.py \
  scripts/test_evaluate_resource_handle_revalidation.py
git diff --check -- <focused paths>
```

### 5. Release Docs And Guardrails

Purpose: align public docs and release gates with the RC scope.

Include:

- `CHANGELOG.md`
- `.github/pull_request_template.md`
- `README.md`
- `CONTRIBUTING.md`
- `docs/RELEASE.md`
- `docs/STATUS.md`
- `docs/VERSIONING.md`
- `docs/ARCHITECTURE.md`
- `docs/INSTALL.md`
- `docs/OPERATOR_CLI.md`
- `scripts/check_rc_layout_evidence_smoke.sh`
- `scripts/check_release_readiness.sh`
- `scripts/test_check_release_readiness_options.sh`
- `scripts/test_release_scope_guardrails.py`
- public-scope guardrail tests.

Validate:

```bash
python3 scripts/test_release_scope_guardrails.py
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_versioning_guardrails.py
# Second-source layout smoke; this requires the assembled RC candidate root.
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root /tmp/obelisk-rc-ufunction-second-source-root
bash scripts/test_check_release_readiness_options.sh
python3 -m json.tool docs/public_gameplay_events.json
git diff --check -- <focused paths>
```

### 6. Research Evidence

Purpose: preserve reusable evidence without making it part of the public RC API or active
handoff state.

Include:

- `docs/research/*`
- `docs/research/README.md`

Validate:

```bash
python3 scripts/test_research_doc_guardrails.py
git diff --check -- docs/research
```

Keep out:

- active routing, agent balance, prompt wording, or leader cadence;
- skill edits unless the research changes a repeatable rule.

### 7. Handoff Refresh

Purpose: keep resume files small after the durable research notes exist.

Include:

- `docs/agent-handoff/CURRENT.md`
- `docs/agent-handoff/COMPACT_CONTEXT.md`
- `docs/agent-handoff/README.md` only if handoff policy wording changes.

Validate:

```bash
python3 scripts/test_agent_handoff_guardrails.py
git diff --check -- docs/agent-handoff
```

Keep out:

- copied research logs, review transcripts, offsets, sample tables, and long command logs;
- broad sub-agent prompts. Handoff may name only the scoped objective, ownership, safety
  baseline, allowed paths, required skills, expert role, and expected decision.

### 8. Skills Only If Rules Changed

Purpose: keep skills operational and avoid inflating them with one-off evidence.

Include:

- `agent-skills/*/SKILL.md` only when a repeatable workflow, safety rule, or coordination
  rule changed.

Validate:

```bash
git diff --check -- agent-skills
```

Keep out:

- experiment records, rejected hypotheses, and evidence packs; link those to
  `docs/research/`.

## RC Exclusions

The following are explicit post-RC or research tracks unless a later focused promotion gate
changes the scope:

- ResourceHandle and public object identity;
- promoted GNames/GObjects runtime globals;
- public Inventory SDK;
- public StructureEvents SDK;
- public mission, tribe, buff, dino, transfer, player, admin, command, or permission APIs;
- richer chat APIs beyond the minimal copied `ChatMessageEvent`;
- gameplay mutation or return overrides;
- public `CallProcessEvent` behavior;
- background-worker, HTTP, socket, or long-lived ingress plugins;
- ScriptStruct/transfer promotion;
- UObject flag-policy or transition-matrix promotion from consume-mode evidence.

Post-RC internal recognizer work, if reopened after the RC, should proceed in this order:
Item return-only policy, Mission copied-bool observer, then Transfer `bAccept`. That sequence
is an internal planning order only; it does not change the RC public API or release gate.

## Final RC Validation (Historical Recipe)

The commands below document the old final validation recipe. They are preserved as
historical audit context only; do not treat them as current authorization to assemble,
stage, tag, or publish an RC. The later accepted release-gate result is recorded in
`docs/research/2026-05-30-rc-second-source-release-gate-check.md`.

The recipe assembled the UFunction second-source root from the accepted per-target-set
roots before running the final release gate. The helper copies existing sanitized
snapshots only and does not regenerate evidence. The valid manifest for that final flow
was the fresh
path-redacted manifest written by the helper; do not reuse or publish older `/tmp`
manifests that captured absolute source roots or other non-redacted input paths:

```bash
python3 scripts/assemble_rc_ufunction_second_source_root.py \
  --minimal-root /servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z/ufunction-snapshots \
  --structure-root /servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/ufunction-snapshots \
  --item-return-root /home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z/ufunction-snapshots \
  --chat-root /servidor/ark/workspace-offline/chat-message-intake-20260529T000000Z/ufunction-snapshots \
  --output-root /tmp/obelisk-rc-ufunction-second-source-root
scripts/check_rc_layout_evidence_smoke.sh \
  --candidate-root /tmp/obelisk-rc-ufunction-second-source-root
```

The historical clean-gate command was:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root /tmp/obelisk-rc-ufunction-second-source-root \
  --ufunction-second-source-target-set minimal-second-source-intake \
  --ufunction-second-source-target-set structure-observer-intake \
  --ufunction-second-source-target-set item-return-only-policy-slice \
  --ufunction-second-source-target-set chat-message-intake \
  --second-source-report-dir /tmp/obelisk-rc-second-source
git status --short --ignored
```

The historical tag condition was a release gate passing without `--allow-dirty`, no
generated artifacts staged, and a public scope limited to `GameplayPolicyEvent`, minimal
copied `ChatMessageEvent`, `DescribeResourceKind`, and
`DescribeGameplayPolicyEventKind` as RC public callback/metadata surfaces.
`DescribeGameplayPolicyEventKind` remained metadata-only: no module SDK, UE lookup,
mutation, identity, or return override. In short: no module SDK, UE lookup, mutation,
identity, or return override. This means no module SDK, UE lookup, mutation, identity, or return override.
The final UFunction second-source root must contain the candidate snapshots for all four
public RC target sets; a minimal-only root is not valid for the structure, item-return, or
chat gates.
