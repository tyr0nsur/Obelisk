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

Excluded:

- Stable gameplay module interception APIs.
- Full UE4 reflection.
- Higher-level gameplay SDK APIs.
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
7. Tag:

```bash
git tag -a v0.1.0 -m "Obelisk 0.1.0"
git push origin v0.1.0
```
