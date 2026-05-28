#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${OBELISK_BUILD_DIR:-build}"
JOBS="${OBELISK_BUILD_JOBS:-$(nproc)}"
RELEASE_CHECK_ROOT=""
LAYOUT_CHECK_ROOT=""
ALLOW_DIRTY=0
REQUIRE_SECOND_SOURCE_READINESS=0
UFUNCTION_SECOND_SOURCE_ROOT="${OBELISK_UFUNCTION_SECOND_SOURCE_ROOT:-}"
SCRIPTSTRUCT_SECOND_SOURCE_ROOT="${OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT:-}"
SECOND_SOURCE_REPORT_DIR="${OBELISK_SECOND_SOURCE_REPORT_DIR:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        -h|--help)
            cat <<'EOF'
Usage: scripts/check_release_readiness.sh [--allow-dirty] [--require-second-source-readiness]
                                          [--ufunction-second-source-root <path>]
                                          [--scriptstruct-second-source-root <path>]
                                          [--second-source-report-dir <path>]

Runs the local first-stable core release gate. By default the command fails if tracked or
untracked non-ignored files are present before or after validation. Ignored build/cache
directories are allowed. Gameplay/module second-source promotion gates run only when
--require-second-source-readiness is supplied.

Options:
  --allow-dirty                     Permit a dirty worktree while developing the release gate itself.
  --require-second-source-readiness Fail if focused reflection promotion target sets lack complete
                                    second-source evidence.
  --ufunction-second-source-root    Candidate UFunction snapshot root for second-source promotion.
  --scriptstruct-second-source-root Candidate ScriptStruct snapshot root for second-source promotion.
  --second-source-report-dir        Directory where JSON second-source readiness reports are written.
  -h, --help                        Show this help.

Environment alternatives:
  OBELISK_UFUNCTION_SECOND_SOURCE_ROOT
  OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT
  OBELISK_SECOND_SOURCE_REPORT_DIR
EOF
            exit 0
            ;;
        --require-second-source-readiness)
            REQUIRE_SECOND_SOURCE_READINESS=1
            shift
            ;;
        --ufunction-second-source-root)
            UFUNCTION_SECOND_SOURCE_ROOT="${2:?--ufunction-second-source-root requires a path}"
            shift 2
            ;;
        --scriptstruct-second-source-root)
            SCRIPTSTRUCT_SECOND_SOURCE_ROOT="${2:?--scriptstruct-second-source-root requires a path}"
            shift 2
            ;;
        --second-source-report-dir)
            SECOND_SOURCE_REPORT_DIR="${2:?--second-source-report-dir requires a path}"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
done

if [[ -n "${UFUNCTION_SECOND_SOURCE_ROOT}${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}${SECOND_SOURCE_REPORT_DIR}" \
    && "${REQUIRE_SECOND_SOURCE_READINESS}" != "1" ]]; then
    echo "Second-source roots or report dirs require --require-second-source-readiness." >&2
    exit 2
fi

if [[ -n "${SECOND_SOURCE_REPORT_DIR}" ]]; then
    report_dir_abs="$(realpath -m "${SECOND_SOURCE_REPORT_DIR}")"
    repo_abs="$(realpath -m "${REPO_ROOT}")"
    if [[ "${report_dir_abs}" == "${repo_abs}" || "${report_dir_abs}" == "${repo_abs}/"* ]]; then
        report_dir_rel="${report_dir_abs#${repo_abs}/}"
        if ! git check-ignore -q -- "${report_dir_rel}" "${report_dir_rel}/"; then
            printf 'Second-source report dir inside the repository must be ignored: %s\n' \
                "${SECOND_SOURCE_REPORT_DIR}" >&2
            exit 2
        fi
    fi
fi

cleanup() {
    if [[ "${OBELISK_KEEP_RELEASE_CHECK_ROOTS:-0}" != "1" ]]; then
        if [[ -n "${RELEASE_CHECK_ROOT}" ]]; then
            rm -rf "${RELEASE_CHECK_ROOT}"
        fi
        if [[ -n "${LAYOUT_CHECK_ROOT}" ]]; then
            rm -rf "${LAYOUT_CHECK_ROOT}"
        fi
    else
        printf 'keeping release check roots:\n  %s\n  %s\n' "${RELEASE_CHECK_ROOT}" "${LAYOUT_CHECK_ROOT}"
    fi
}
trap cleanup EXIT

RELEASE_CHECK_ROOT="$(mktemp -d /tmp/obelisk-release-check.XXXXXX)"
LAYOUT_CHECK_ROOT="$(mktemp -d /tmp/obelisk-layout-check.XXXXXX)"

run_step() {
    printf '\n==> %s\n' "$*"
    "$@"
}

run_second_source_readiness() {
    local label="$1"
    local base_root="$2"
    local target_set="$3"
    local candidate_root="$4"

    local command=(
        python3 scripts/compare_reflection_snapshots.py
        --base-root "${base_root}"
        --readiness-report
        --target-set "${target_set}"
    )
    if [[ -n "${candidate_root}" ]]; then
        command+=(--candidate-root "${candidate_root}")
    fi

    if [[ -n "${SECOND_SOURCE_REPORT_DIR}" ]]; then
        mkdir -p "${SECOND_SOURCE_REPORT_DIR}"
        local report_path="${SECOND_SOURCE_REPORT_DIR}/${label}-second-source-readiness.json"
        set +e
        "${command[@]}" --fail-on-readiness-gaps --json > "${report_path}"
        local report_status=$?
        set -e
        if [[ "${report_status}" -eq 0 ]]; then
            printf 'wrote %s\n' "${report_path}"
        else
            printf 'wrote %s (gate exit=%s)\n' "${report_path}" "${report_status}"
        fi
    fi

    set +e
    run_step "${command[@]}" --fail-on-readiness-gaps
    local text_status=$?
    return "${text_status}"
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
    second_source_status=0
    set +e
    run_second_source_readiness \
        ufunction \
        tests/fixtures/ufunction_snapshots \
        minimal-second-source-intake \
        "${UFUNCTION_SECOND_SOURCE_ROOT}"
    status=$?
    set -e
    if [[ "${status}" -ne 0 ]]; then
        second_source_status="${status}"
    fi
    set +e
    run_second_source_readiness \
        scriptstruct \
        tests/fixtures/scriptstruct_snapshots \
        transfer-scriptstruct \
        "${SCRIPTSTRUCT_SECOND_SOURCE_ROOT}"
    status=$?
    set -e
    if [[ "${status}" -ne 0 && "${second_source_status}" -eq 0 ]]; then
        second_source_status="${status}"
    fi
    if [[ "${second_source_status}" -ne 0 ]]; then
        exit "${second_source_status}"
    fi
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
