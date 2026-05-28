#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${OBELISK_BUILD_DIR:-build}"
JOBS="${OBELISK_BUILD_JOBS:-$(nproc)}"
RELEASE_CHECK_ROOT="$(mktemp -d /tmp/obelisk-release-check.XXXXXX)"
LAYOUT_CHECK_ROOT="$(mktemp -d /tmp/obelisk-layout-check.XXXXXX)"
ALLOW_DIRTY=0
REQUIRE_SECOND_SOURCE_READINESS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: scripts/check_release_readiness.sh [--allow-dirty] [--require-second-source-readiness]

Runs the local first-stable core release gate. By default the command fails if tracked or
untracked non-ignored files are present before or after validation. Ignored build/cache
directories are allowed. Gameplay/module second-source promotion gates run only when
--require-second-source-readiness is supplied.

Options:
  --allow-dirty                     Permit a dirty worktree while developing the release gate itself.
  --require-second-source-readiness Fail if focused reflection promotion target sets lack complete
                                    second-source evidence.
  -h, --help                        Show this help.
EOF
            exit 0
            ;;
        --require-second-source-readiness)
            REQUIRE_SECOND_SOURCE_READINESS=1
            shift
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
if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" ]]; then
    run_step python3 scripts/compare_reflection_snapshots.py \
        --base-root tests/fixtures/ufunction_snapshots \
        --readiness-report \
        --target-set minimal-second-source-intake \
        --fail-on-readiness-gaps
    run_step python3 scripts/compare_reflection_snapshots.py \
        --base-root tests/fixtures/scriptstruct_snapshots \
        --readiness-report \
        --target-set transfer-scriptstruct \
        --fail-on-readiness-gaps
fi
run_step env OBELISK_BUILD_DIR="${BUILD_DIR}" scripts/test_install_obelisk_layout.sh "${LAYOUT_CHECK_ROOT}"
run_step scripts/obelisk.py --root "${LAYOUT_CHECK_ROOT}" status
run_step scripts/install_obelisk.sh --build-dir "${BUILD_DIR}" --dry-run "${RELEASE_CHECK_ROOT}"
run_step scripts/install_obelisk_plugin.sh --dry-run \
    "${BUILD_DIR}/plugins/oBaseEvents/oBaseEvents.so" "${RELEASE_CHECK_ROOT}"
run_step git diff --check

printf '\n==> git status --short --ignored\n'
git status --short --ignored
check_clean_tree

if [[ "${REQUIRE_SECOND_SOURCE_READINESS}" == "1" ]]; then
    printf '\nCore-first release readiness and gameplay/module second-source promotion checks completed.\n'
else
    printf '\nCore-first release readiness checks completed; gameplay/module second-source promotion gate was not run.\n'
fi
