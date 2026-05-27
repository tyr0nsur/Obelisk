# FetchContent Reproducibility Pins

## Objective

Resolve the reproducibility risk where the top-level CMake build could fetch dependencies
from moving refs or mutable tags.

## Environment

- Obelisk commit: `6afb27040cdc3644ee70bf883ee54bb4e94e72c7`
- Workspace: `/home/flowcommunity-ark/Obelisk`
- Dependency checkouts inspected:
  - `build/_deps/fmt-src`
  - `build/_deps/spdlog-src`
  - `build/_deps/subhook-src`
- Network: not used; evidence came from the existing local FetchContent checkout.

## Hypothesis

The current build can be made more reproducible by pinning FetchContent dependencies to the
exact commits already resolved in local checkouts.

## Method

Inspected the local dependency checkout with:

```bash
git -C build/_deps/fmt-src rev-parse HEAD
git -C build/_deps/fmt-src tag --points-at HEAD
git -C build/_deps/spdlog-src rev-parse HEAD
git -C build/_deps/spdlog-src tag --points-at HEAD
git -C build/_deps/subhook-src status --short --branch
git -C build/_deps/subhook-src rev-parse HEAD
git -C build/_deps/subhook-src log -1 --format='%H%n%ci%n%s'
git -C build/_deps/subhook-src tag --points-at HEAD
git -C build/_deps/subhook-src remote -v
```

## Evidence

- `fmt` tag `10.1.1` resolved locally to
  `f5e54359df4c26b6230fc61d38aa294581393084`.
- `spdlog` tag `v1.12.0` resolved locally to
  `7e635fca68d014934b4af8a1cf874f63989352b7`.
- `build/_deps/subhook-src` reported `## master...origin/master`.
- `HEAD` was `568d2e5a5d6013907e8008857968906b33ef3b7d`.
- The commit date was `2015-01-16 18:23:52 +0500`.
- The commit subject was `Add build status badge`.
- `git tag --points-at HEAD` produced no tag.
- The configured remote was `https://github.com/wyrover/subhook.git`.

## Result

`CMakeLists.txt` now pins:

- `fmt` to `f5e54359df4c26b6230fc61d38aa294581393084` instead of tag `10.1.1`;
- `spdlog` to `7e635fca68d014934b4af8a1cf874f63989352b7` instead of tag `v1.12.0`;
- `subhook` to `568d2e5a5d6013907e8008857968906b33ef3b7d` instead of `master`.

`scripts/test_dependency_pins.py` guards these FetchContent refs so they remain full
commit SHAs.

## Risks

- The selected pins are based on already-fetched local checkouts, not a fresh upstream
  audit.
- If upstream history is rewritten or the repository disappears, a future clean build may
  still need a mirror or vendored archive for full supply-chain resilience.

## Next Steps

- Consider mirroring or vendoring critical third-party dependencies if builds must remain
  possible without GitHub availability.
