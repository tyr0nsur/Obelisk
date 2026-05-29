# Pull Request Checklist

## Scope

- [ ] This PR stays within the stated subsystem or documentation scope.
- [ ] I did not touch live server roots or commit server-local artifacts.
- [ ] I did not commit build outputs, `.so` files, logs, cores, local config, or state markers.
- [ ] Runtime/reversing changes include a matching research note or public documentation update.
- [ ] This PR does not promote chat or any gameplay module to public SDK/release scope unless `docs/STATUS.md`, `docs/RELEASE.md`, and explicitly named second-source gates are updated.

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
- [ ] `scripts/check_release_readiness.sh` for release-candidate, installer, SDK package, or first-stable scope changes.
- [ ] `scripts/check_release_readiness.sh --require-second-source-readiness` for PRs that promote reflected gameplay/module surfaces; name every promoted target set with `--ufunction-second-source-target-set` or `--scriptstruct-second-source-target-set`, pass `--ufunction-second-source-root` for promoted UFunction snapshots, pass `--scriptstruct-second-source-root` only when a ScriptStruct target set is explicitly named, and set `--second-source-report-dir` when keeping readiness reports.
- [ ] `python3 scripts/analyze_runtime_observer_log.py --fail-on-quality-blockers <copied-log>` for approved runtime-observer capture reviews; this is observational only, not release readiness or second-source promotion evidence.
- [ ] New runtime-observer modules include per-function analyzer fixture coverage and/or approved sanitized observer capture/research-note coverage; module-level field aggregates are not used as promotion evidence.
- [ ] Docs-only changes explain why the build was skipped.

## Documentation

- [ ] `docs/research/` captures reusable evidence from investigations.
- [ ] `docs/STATUS.md` still matches the stable and experimental posture.
