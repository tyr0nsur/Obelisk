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

- Stable chat command interception.
- Full UE4 reflection.
- Higher-level gameplay SDK APIs.
- Production HTTP plugins.

## Checklist

1. Run CI on `main`.
2. Build locally:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j"$(nproc)"
python3 scripts/test_analyze_reflectionscanner_capture.py
python3 scripts/test_scan_core_fname_tables.py
python3 scripts/test_enumerate_core_uobjects.py
python3 scripts/test_inspect_core_ufunctions.py
python3 scripts/test_build_core_dump_evidence_pack.py
python3 scripts/test_verify_chat_reflection_constants.py
python3 scripts/test_summarize_core_ufunction_inventory.py
python3 scripts/test_compare_reflection_snapshots.py
python3 scripts/test_ufunction_snapshot_fixtures.py
python3 scripts/test_regenerate_ufunction_snapshots.py
python3 scripts/test_scriptstruct_snapshot_fixtures.py
python3 scripts/test_regenerate_scriptstruct_snapshots.py
python3 scripts/test_research_doc_guardrails.py
python3 scripts/test_operational_doc_guardrails.py
python3 scripts/test_public_sdk_chat_guardrails.py
python3 scripts/test_dependency_pins.py
python3 scripts/test_versioning_guardrails.py
python3 scripts/test_secret_guardrails.py
python3 scripts/test_repo_hygiene.py
scripts/install_obelisk.sh --dry-run /tmp/obelisk-release-check
```

3. Confirm no generated artifacts are staged:

```bash
git status --short --ignored
```

4. Update `CHANGELOG.md`.
5. Confirm docs and wrappers use `state/instances/<instance-id>/` markers only.
6. Tag:

```bash
git tag -a v0.1.0 -m "Obelisk 0.1.0"
git push origin v0.1.0
```
