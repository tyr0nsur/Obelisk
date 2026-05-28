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

Runtime-observer log summaries are a separate review artifact, not a release gate and not
second-source promotion evidence. Use them only on copied or sanitized logs when reviewing
an approved observer capture:

```bash
python3 scripts/analyze_runtime_observer_log.py --fail-on-quality-blockers <copied-log>
```

The analyzer emits `obelisk.runtime-observer-log-summary.v1` JSON with
`review_scope=runtime_observer_evidence_summary`, `readiness_gate=none`, and
`promotion_gate.gate_type=runtime_observer_observational_only`. It fails quality checks
when a copied log has no observer evidence, is missing observer gates, mixes binary SHA
values, contains malformed observer lines, or requires redaction. Even a clean summary
remains observational until the second-source and SDK ownership gates are satisfied.

3. Confirm `scripts/test_install_obelisk_layout.sh` covered runtime backup reinstall:
   one backup each for `libobelisk.so` and `libsubhook.so`, no `.incoming.*` files, no
   `.install-runtime.*` staging directory, invalid install roots rejected, failed runtime
   rename cleanup, and installed `RUNPATH=$ORIGIN`.
4. Confirm no generated artifacts are staged:

```bash
git status --short --ignored
```

5. Update `CHANGELOG.md`.
6. Confirm docs and wrappers use `state/instances/<instance-id>/` markers only.
7. For the protected Ragnarok harness, confirm quiet stable posture after any approved
   runtime experiment:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map Ragnarok --instance arkserver
```

8. Tag:

```bash
git tag -a v0.1.0 -m "Obelisk 0.1.0"
git push origin v0.1.0
```
