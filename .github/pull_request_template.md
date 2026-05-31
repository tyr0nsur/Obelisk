# Pull Request Checklist

## Scope

- [ ] This PR stays within the stated subsystem or documentation scope.
- [ ] I did not touch live server roots or commit server-local artifacts.
- [ ] I did not commit build outputs, `.so` files, logs, cores, local config, or state markers.
- [ ] I did not include Discord webhook URLs/tokens, copied secrets, operator absolute paths, or server-local roots; operator webhooks stay only in ignored `local/discord-webhooks.env`.
- [ ] Runtime/reversing changes include a matching research note or public documentation update.
- [ ] Plugin Hub seed/example changes started from `docs/PLUGIN_HUB_FOUNDATION_V1.md` and `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`; installing or documenting a plugin `.so` does not promote new public SDK scope, and ArkServerApi/AseApi/NextGen inputs stayed names and demand dictionaries only.
- [ ] This PR does not promote chat beyond minimal `ChatMessageEvent` or any gameplay module to public SDK/release scope unless `docs/STATUS.md`, `docs/RELEASE.md`, `docs/public_gameplay_events.json`, `CHANGELOG.md`, installed SDK evidence, and explicitly named second-source gates are updated.
- [ ] This PR does not expose public Inventory SDKs, `ResourceHandle`, resource/object identity, UE pointers, raw `FString`, raw params, FName/GObjects indices, mutation, or return overrides without a separately named promotion gate.
- [ ] If this PR claims runtime `ChatMessageEvent` delivery, the evidence uses the `enable-chat-events` path during an approved operator-selected beta-test window after an operator-approved notice; historical `enable-chat-reflection` observer logs are not counted as delivery evidence.

## Safety

- [ ] Experimental scanners, runtime observers, and native exec probes remain disabled by default.
- [ ] New plugin or hook behavior is gated by explicit flags or marker files.
- [ ] Global `ProcessEvent` callbacks are avoided unless the risk is documented and bounded.
- [ ] Live-server changes include rollback notes.

## Validation

- [ ] `git diff --check`
- [ ] `cmake -S . -B build`
- [ ] `cmake --build build -j"$(nproc)"`
- [ ] `ctest --test-dir build --output-on-failure`
- [ ] `scripts/run_script_tests.sh`
- [ ] `scripts/test_install_obelisk_layout.sh` for install, SDK, packaging, or CMake export changes.
- [ ] `scripts/check_release_readiness.sh` for runtime/shared-library symbol-surface, installer, SDK package, or first-stable scope changes that are not release-candidate publication.
- [ ] Production `libobelisk.so` remains free of test-only/internal symbols through the canonical release gate; no parallel CI `nm` check with different defaults was added.
- [ ] Release-candidate publication PRs rerun `scripts/check_release_readiness.sh --require-second-source-readiness` on a clean worktree with the accepted second-source root and preserved report directory.
- [ ] `scripts/check_release_readiness.sh --require-second-source-readiness` for PRs that promote reflected gameplay/module surfaces; name every promoted target set with `--ufunction-second-source-target-set` or `--scriptstruct-second-source-target-set`, pass `--ufunction-second-source-root` for promoted UFunction snapshots, pass `--scriptstruct-second-source-root` only when a ScriptStruct target set is explicitly named, and set `--second-source-report-dir` when keeping readiness reports.
- [ ] Release tags and release-ref pushes have explicit release-manager/lead authorization for this PR/turn.
- [ ] Any local or unpublished release tag was verified with exact tag/ref comparison using `python3 scripts/check_release_tag_state.py --tag <tag> --ref HEAD` against the intended validated release ref; stale local tags are recreated only after rerunning the gate on that ref and are not reused or pushed.
- [ ] `python3 scripts/analyze_runtime_observer_log.py --fail-on-quality-blockers <copied-log>` for approved runtime-observer capture reviews; this is observational only, not release readiness or second-source promotion evidence.
- [ ] New runtime-observer modules include per-function analyzer fixture coverage and/or approved sanitized observer capture/research-note coverage; module-level field aggregates are not used as promotion evidence.
- [ ] Docs-only changes explain why the build was skipped.

## Documentation

- [ ] `docs/research/` captures reusable evidence from investigations.
- [ ] `docs/STATUS.md` still matches the stable and experimental posture.
