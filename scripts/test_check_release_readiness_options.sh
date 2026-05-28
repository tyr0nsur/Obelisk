#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

count_temp_roots() {
    find /tmp -maxdepth 1 -type d \
        \( -name 'obelisk-release-check.*' -o -name 'obelisk-layout-check.*' \) \
        2>/dev/null | wc -l
}

before_help_roots="$(count_temp_roots)"
help_output="$(scripts/check_release_readiness.sh --help)"
after_help_roots="$(count_temp_roots)"
if [[ "${before_help_roots}" != "${after_help_roots}" ]]; then
    printf 'help path leaked release temp roots: before=%s after=%s\n' \
        "${before_help_roots}" "${after_help_roots}" >&2
    exit 1
fi

for expected in \
    "--require-second-source-readiness" \
    "--ufunction-second-source-root" \
    "--scriptstruct-second-source-root" \
    "--ufunction-second-source-target-set" \
    "--scriptstruct-second-source-target-set" \
    "--second-source-report-dir" \
    "OBELISK_UFUNCTION_SECOND_SOURCE_ROOT" \
    "OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT" \
    "OBELISK_SECOND_SOURCE_REPORT_DIR"; do
    if ! grep -Fq -- "${expected}" <<<"${help_output}"; then
        printf 'missing help text: %s\n' "${expected}" >&2
        exit 1
    fi
done

merge_function="$(sed -n '/^merge_second_source_status()/,/^}/p' scripts/check_release_readiness.sh)"
if [[ -z "${merge_function}" ]]; then
    printf 'missing merge_second_source_status function\n' >&2
    exit 1
fi
eval "${merge_function}"

assert_merged_status() {
    local current="$1"
    local next="$2"
    local expected="$3"
    local actual
    actual="$(merge_second_source_status "${current}" "${next}")"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'merge_second_source_status %s %s: expected %s got %s\n' \
            "${current}" "${next}" "${expected}" "${actual}" >&2
        exit 1
    fi
}

assert_merged_status 0 0 0
assert_merged_status 0 2 2
assert_merged_status 2 0 2
assert_merged_status 2 1 1
assert_merged_status 1 2 1
assert_merged_status 2 2 2

before_error_roots="$(count_temp_roots)"
set +e
error_output="$(scripts/check_release_readiness.sh --ufunction-second-source-root /tmp/obelisk-candidate 2>&1)"
status=$?
set -e
after_error_roots="$(count_temp_roots)"

if [[ "${before_error_roots}" != "${after_error_roots}" ]]; then
    printf 'option error path leaked release temp roots: before=%s after=%s\n' \
        "${before_error_roots}" "${after_error_roots}" >&2
    exit 1
fi

if [[ "${status}" -ne 2 ]]; then
    printf 'expected option validation to exit 2, got %s\n%s\n' "${status}" "${error_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${error_output}"; then
    printf 'missing second-source option validation error\n%s\n' "${error_output}" >&2
    exit 1
fi

set +e
target_set_error_output="$(
    scripts/check_release_readiness.sh \
        --ufunction-second-source-target-set buff-compact-intake 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected target-set validation to exit 2, got %s\n%s\n' \
        "${status}" "${target_set_error_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source roots, target sets, or report dirs require --require-second-source-readiness." <<<"${target_set_error_output}"; then
    printf 'missing target-set option validation error\n%s\n' "${target_set_error_output}" >&2
    exit 1
fi

set +e
report_dir_output="$(
    scripts/check_release_readiness.sh \
        --require-second-source-readiness \
        --second-source-report-dir second-source-reports 2>&1
)"
status=$?
set -e

if [[ "${status}" -ne 2 ]]; then
    printf 'expected in-repo report dir validation to exit 2, got %s\n%s\n' \
        "${status}" "${report_dir_output}" >&2
    exit 1
fi

if ! grep -Fq -- "Second-source report dir inside the repository must be ignored" <<<"${report_dir_output}"; then
    printf 'missing in-repo report dir validation error\n%s\n' "${report_dir_output}" >&2
    exit 1
fi

echo "test_check_release_readiness_options passed"
