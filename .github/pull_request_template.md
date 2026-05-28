# Pull Request Checklist

## Scope

- [ ] This PR stays within the stated subsystem or documentation scope.
- [ ] I did not touch `/servidor/ark` or commit server-local artifacts.
- [ ] I did not commit build outputs, `.so` files, logs, cores, local config, or state markers.
- [ ] Runtime/reversing changes include a matching research note or an update to the relevant agent skill.

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
- [ ] Docs-only changes explain why the build was skipped.

## Handoff

- [ ] `docs/agent-handoff/CURRENT.md` is updated when active state changed.
- [ ] `docs/research/` captures reusable evidence from investigations.
- [ ] `docs/STATUS.md` still matches the stable and experimental posture.
