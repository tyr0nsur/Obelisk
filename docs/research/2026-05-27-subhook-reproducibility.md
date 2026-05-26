# Subhook Reproducibility Pin

## Objective

Resolve the reproducibility risk where the top-level CMake build fetched `subhook` from
the moving `master` branch.

## Environment

- Obelisk commit: `6afb27040cdc3644ee70bf883ee54bb4e94e72c7`
- Workspace: `/home/flowcommunity-ark/Obelisk`
- Dependency checkout inspected: `build/_deps/subhook-src`
- Network: not used; evidence came from the existing local FetchContent checkout.

## Hypothesis

The current build can be made reproducible by pinning `subhook` to the exact commit already
resolved in the local FetchContent checkout.

## Method

Inspected the local dependency checkout with:

```bash
git -C build/_deps/subhook-src status --short --branch
git -C build/_deps/subhook-src rev-parse HEAD
git -C build/_deps/subhook-src log -1 --format='%H%n%ci%n%s'
git -C build/_deps/subhook-src tag --points-at HEAD
git -C build/_deps/subhook-src remote -v
```

## Evidence

- `build/_deps/subhook-src` reported `## master...origin/master`.
- `HEAD` was `568d2e5a5d6013907e8008857968906b33ef3b7d`.
- The commit date was `2015-01-16 18:23:52 +0500`.
- The commit subject was `Add build status badge`.
- `git tag --points-at HEAD` produced no tag.
- The configured remote was `https://github.com/wyrover/subhook.git`.

## Result

`CMakeLists.txt` now pins `subhook` to
`568d2e5a5d6013907e8008857968906b33ef3b7d` instead of `master`.

## Risks

- The selected pin is based on the already-fetched local checkout, not a fresh upstream
  audit.
- If upstream history is rewritten or the repository disappears, a future clean build may
  still need a mirror or vendored archive for full supply-chain resilience.

## Next Steps

- Consider mirroring or vendoring critical third-party dependencies if builds must remain
  possible without GitHub availability.
