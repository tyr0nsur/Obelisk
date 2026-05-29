# RC Checkpoint Slicing Plan

## Objective

Turn the current broad dirty worktree into reviewable local checkpoints toward
`v0.1.0-rc.1` without pushing to GitHub or mixing post-RC research into the first public
release candidate.

## Current Gate

The core-first release gate passed locally in dirty mode with the accepted minimal
second-source root:

```bash
scripts/check_release_readiness.sh \
  --allow-dirty \
  --require-second-source-readiness \
  --ufunction-second-source-root /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/ufunction-snapshots \
  --second-source-report-dir /tmp/obelisk-rc-second-source-current
```

This proves the current tree can satisfy the technical gate when dirty state is allowed.
It does not prove RC readiness; a real RC still requires focused checkpoints and a clean
worktree run without `--allow-dirty`.

## Checkpoint Order

### 1. RC API: GameplayPolicyEvent

Purpose: freeze the public v1 API surface for the first RC around copied POD policy
events and metadata-only resource category descriptors.

Include:

- `include/obelisk/ObeliskApi.h`
- `core/PluginManager.cpp`
- `core/StructureEventDispatcher.{h,cpp}`
- `core/InventoryPolicyEventDispatcher.{h,cpp}`
- `tests/abi/AbiLayoutTests.cpp`
- `tests/core/PluginManagerTests.cpp`
- `tests/core/StructureEventDispatcherTests.cpp`
- `tests/core/InventoryPolicyEventDispatcherTests.cpp`
- `tests/sdk_consumer/*`
- `tests/sdk_installed_consumer/*`
- `docs/public_gameplay_events.json`
- `docs/PLUGIN_ARCHITECTURE.md`

Validate:

```bash
ctest --test-dir build --output-on-failure -R 'Abi|Sdk|PluginManager|InventoryPolicy|StructureEventDispatcher'
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_release_scope_guardrails.py
python3 scripts/test_versioning_guardrails.py
scripts/test_install_obelisk_layout.sh
git diff --check -- <focused paths>
```

Keep out:

- public Inventory SDK;
- public StructureEvents SDK;
- ResourceHandle, object identity, lookup, mutation, return overrides;
- dino/buff/mission/tribe public APIs;
- public `CallProcessEvent` behavior.

Review note: `GameplayPolicyEvent` is a stable public subscription surface, but the
runtime producers for structure/inventory events remain exact-target, marker-gated,
budgeted observers. The RC API checkpoint must document this as "stable API, gated
production" rather than implying events are always produced on every install.

### 2. Runtime Observer Safety

Purpose: keep ProcessEvent and internal observer gates stable while preserving default-deny
runtime behavior.

Include:

- `CMakeLists.txt` hunks that add only dispatcher/runtime tests required by checkpoint 1
  or existing internal observer tests;
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
static global evidence, and redacted ResourceHandle readiness as tooling. This is mostly
RC-supporting infrastructure and post-RC research support, not a public SDK expansion.

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
- Static/GObjects/ResourceHandle tooling:
  - `scripts/build_static_global_promotion_evidence.py`
  - `scripts/reconcile_gobjects_samples.py`
  - `scripts/evaluate_resource_handle_revalidation.py`
  - matching tests.

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
- `scripts/check_release_readiness.sh`
- `scripts/test_check_release_readiness_options.sh`
- public-scope guardrail tests.

Validate:

```bash
python3 scripts/test_release_scope_guardrails.py
python3 scripts/test_public_sdk_guardrails.py
python3 scripts/test_versioning_guardrails.py
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
- public mission, tribe, buff, dino, transfer, chat, player, admin, command, or permission
  APIs;
- gameplay mutation or return overrides;
- public `CallProcessEvent` behavior;
- background-worker, HTTP, socket, or long-lived ingress plugins;
- ScriptStruct/transfer promotion.

## Final RC Validation

After all selected checkpoints are cleanly integrated:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/ufunction-snapshots \
  --second-source-report-dir /tmp/obelisk-rc-second-source
git status --short --ignored
```

Only tag `v0.1.0-rc.1` after the release gate passes without `--allow-dirty`, no generated
artifacts are staged, and the public scope still names only `GameplayPolicyEvent` and
`DescribeResourceKind` as promoted gameplay/resource surfaces.
