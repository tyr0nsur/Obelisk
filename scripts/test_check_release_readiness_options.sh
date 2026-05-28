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
    "--second-source-report-dir" \
    "OBELISK_UFUNCTION_SECOND_SOURCE_ROOT" \
    "OBELISK_SCRIPTSTRUCT_SECOND_SOURCE_ROOT" \
    "OBELISK_SECOND_SOURCE_REPORT_DIR"; do
    if ! grep -Fq -- "${expected}" <<<"${help_output}"; then
        printf 'missing help text: %s\n' "${expected}" >&2
        exit 1
    fi
done

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

if ! grep -Fq -- "Second-source roots or report dirs require --require-second-source-readiness." <<<"${error_output}"; then
    printf 'missing second-source option validation error\n%s\n' "${error_output}" >&2
    exit 1
fi

echo "test_check_release_readiness_options passed"
