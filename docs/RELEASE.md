# Release Process

This project is not ready for a production-stable release yet. Use this checklist for the
first public `0.1.0` tag. Version labels and pre-release rules are defined in
[VERSIONING.md](VERSIONING.md).

## Scope

Included:

- Runtime bootstrap.
- ProcessEvent hook.
- C plugin ABI.
- Central install script and LinuxGSM wrappers.
- `oBaseEvents`.
- `OBELISK_INSTANCE_ID` logs and state markers.
- Filtered, non-mutating `ProcessEvent` observation as the only stable game-facing
  interaction pattern.

Excluded:

- Stable gameplay module interception APIs.
- Full UE4 reflection.
- Higher-level gameplay SDK APIs.
- Gameplay mutation, return overrides, arbitrary UE4 function calls, and public
  `CallProcessEvent`-based plugin behavior.
- Production HTTP plugins.

## Checklist

1. Run CI on `main`.
2. Build locally:

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

This intentionally fails until the focused UFunction and ScriptStruct target sets have
complete, distinct second-source evidence.

When sanitized second-source snapshot roots exist, pass them into the same gate and keep
JSON reports as promotion artifacts. Write the report directory outside the repository
or under an ignored artifact path; unignored in-repo report paths are rejected before the
release build starts so the final clean-worktree check stays meaningful:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-root <second-source-ufunction-snapshots> \
  --scriptstruct-second-source-root <second-source-scriptstruct-snapshots> \
  --second-source-report-dir <artifact-dir>
```

The default second-source gate is intentionally scoped to the core-first intake:
`minimal-second-source-intake` for UFunctions and `transfer-scriptstruct` for
ScriptStructs. A release or PR that promotes another reflected module family must name
each promoted target set explicitly, for example:

```bash
scripts/check_release_readiness.sh \
  --require-second-source-readiness \
  --ufunction-second-source-target-set buff-compact-intake \
  --ufunction-second-source-target-set dino-compact-intake \
  --scriptstruct-second-source-target-set transfer-scriptstruct \
  --ufunction-second-source-root <second-source-ufunction-snapshots>
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
satisfied.

3. Confirm `scripts/test_install_obelisk_layout.sh` covered runtime backup reinstall:
   one backup each for `libobelisk.so` and `libsubhook.so`, no `.incoming.*` files, no
   `.install-runtime.*` staging directory, invalid install roots rejected, failed runtime
   rename cleanup, required positional install roots even when `OBELISK_ROOT` is set, and
   installed `RUNPATH=$ORIGIN`.
4. Confirm no generated artifacts are staged:

```bash
git status --short --ignored
```

5. Update `CHANGELOG.md`.
6. Confirm docs and wrappers use `state/instances/<instance-id>/` markers only.
7. Before a maintenance-window deploy or restart, confirm the installed LinuxGSM wrapper
   matches the versioned template:

```bash
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

8. If this release candidate followed an approved runtime experiment, confirm quiet stable
   posture on the same approved validation adapter target. If no runtime experiment was
   part of the release validation, keep this release check offline and skip live harness
   inspection.

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>
```

9. Tag:

```bash
git tag -a v0.1.0 -m "Obelisk 0.1.0"
git push origin v0.1.0
```
