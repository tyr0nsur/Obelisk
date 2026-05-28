#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${OBELISK_BUILD_DIR:-build}"
JOBS="${OBELISK_BUILD_JOBS:-$(nproc)}"
RELEASE_CHECK_ROOT="$(mktemp -d /tmp/obelisk-release-check.XXXXXX)"
LAYOUT_CHECK_ROOT="$(mktemp -d /tmp/obelisk-layout-check.XXXXXX)"

cleanup() {
    if [[ "${OBELISK_KEEP_RELEASE_CHECK_ROOTS:-0}" != "1" ]]; then
        rm -rf "${RELEASE_CHECK_ROOT}" "${LAYOUT_CHECK_ROOT}"
    else
        printf 'keeping release check roots:\n  %s\n  %s\n' "${RELEASE_CHECK_ROOT}" "${LAYOUT_CHECK_ROOT}"
    fi
}
trap cleanup EXIT

run_step() {
    printf '\n==> %s\n' "$*"
    "$@"
}

run_step cmake -S . -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=RelWithDebInfo
run_step cmake --build "${BUILD_DIR}" -j"${JOBS}"
run_step ctest --test-dir "${BUILD_DIR}" --output-on-failure
run_step scripts/run_script_tests.sh
run_step scripts/test_install_obelisk_layout.sh "${LAYOUT_CHECK_ROOT}"
run_step scripts/obelisk.py --root "${LAYOUT_CHECK_ROOT}" status
run_step scripts/install_obelisk.sh --dry-run "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so" "${RELEASE_CHECK_ROOT}"
run_step git diff --check

printf '\n==> git status --short --ignored\n'
git status --short --ignored

printf '\nRelease readiness checks completed.\n'
