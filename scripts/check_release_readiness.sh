#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${OBELISK_BUILD_DIR:-build}"
JOBS="${OBELISK_BUILD_JOBS:-$(nproc)}"
RELEASE_CHECK_ROOT="$(mktemp -d /tmp/obelisk-release-check.XXXXXX)"
LAYOUT_CHECK_ROOT="$(mktemp -d /tmp/obelisk-layout-check.XXXXXX)"
ALLOW_DIRTY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: scripts/check_release_readiness.sh [--allow-dirty]

Runs the local first-stable release gate. By default the command fails if tracked or
untracked non-ignored files are present before or after validation. Ignored build/cache
directories are allowed.

Options:
  --allow-dirty    Permit a dirty worktree while developing the release gate itself.
  -h, --help       Show this help.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

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

check_clean_tree() {
    if [[ "${ALLOW_DIRTY}" == "1" ]]; then
        return
    fi

    local status
    status="$(git status --porcelain --untracked-files=normal)"
    if [[ -n "${status}" ]]; then
        printf 'Release readiness requires a clean worktree. Current changes:\n%s\n' "${status}" >&2
        exit 1
    fi
}

check_clean_tree
run_step cmake -S . -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=RelWithDebInfo
run_step cmake --build "${BUILD_DIR}" -j"${JOBS}"
run_step ctest --test-dir "${BUILD_DIR}" --output-on-failure
run_step scripts/run_script_tests.sh
run_step env OBELISK_BUILD_DIR="${BUILD_DIR}" scripts/test_install_obelisk_layout.sh "${LAYOUT_CHECK_ROOT}"
run_step scripts/obelisk.py --root "${LAYOUT_CHECK_ROOT}" status
run_step scripts/install_obelisk.sh --build-dir "${BUILD_DIR}" --dry-run "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so" "${RELEASE_CHECK_ROOT}"
run_step git diff --check

printf '\n==> git status --short --ignored\n'
git status --short --ignored
check_clean_tree

printf '\nRelease readiness checks completed.\n'
