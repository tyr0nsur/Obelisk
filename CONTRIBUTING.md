# Contributing to Obelisk

Use GitHub Issues for bugs and plugin proposals. Describe the expected behavior and provide the commit or tag, Linux distribution, and game version that apply. Report security issues privately through [SECURITY.md](SECURITY.md).

1. Fork the repository and create a focused branch from `main`.
2. Keep plugin ABI changes compatible with the existing table layout. Add a fixture for a behavior change when existing tests cannot cover it.
3. Build and run CTest using the [README](README.md). Run `git diff --check` and include your validation results in the pull request.
4. Open a pull request against `main`. Identify any test that requires a dedicated ARK instance.

Use `good first issue` for scoped changes with a clear acceptance test and `help wanted` when a maintainer is looking for a contributor. Snapshot tags identify development baselines.
