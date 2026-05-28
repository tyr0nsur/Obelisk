#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/check_linuxgsm_wrapper_drift.sh"
TMP_DIR="$(mktemp -d /tmp/obelisk-wrapper-drift.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

assert_contains() {
    local file="$1"
    local pattern="$2"
    if ! grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

expect_failure() {
    local label="$1"
    shift

    if "$@" > "${TMP_DIR}/${label}.out" 2> "${TMP_DIR}/${label}.err"; then
        echo "Expected failure for ${label}" >&2
        cat "${TMP_DIR}/${label}.out" >&2
        cat "${TMP_DIR}/${label}.err" >&2
        exit 1
    fi
}

expected="${TMP_DIR}/expected/ObeliskRun.sh"
installed="${TMP_DIR}/installed/ObeliskRun.sh"
mkdir -p "$(dirname "${expected}")" "$(dirname "${installed}")"
printf '#!/usr/bin/env bash\nexit 0\n' > "${expected}"
chmod +x "${expected}"
cp "${expected}" "${installed}"

"${SCRIPT}" --expected "${expected}" --installed "${installed}" > "${TMP_DIR}/match.out"
assert_contains "${TMP_DIR}/match.out" '^LinuxGSM wrapper matches versioned template: '
assert_contains "${TMP_DIR}/match.out" '^sha256='

printf '#!/usr/bin/env bash\nexit 1\n' > "${installed}"
expect_failure drift "${SCRIPT}" --expected "${expected}" --installed "${installed}"
assert_contains "${TMP_DIR}/drift.err" '^LinuxGSM wrapper drift detected\.'
assert_contains "${TMP_DIR}/drift.err" '^expected_sha256:  '
assert_contains "${TMP_DIR}/drift.err" '^installed_sha256: '

rm -f "${installed}"
expect_failure missing-installed "${SCRIPT}" --expected "${expected}" --installed "${installed}"
assert_contains "${TMP_DIR}/missing-installed.err" '^Installed wrapper must be a regular file: '

target="${TMP_DIR}/external-wrapper"
printf 'external\n' > "${target}"
ln -s "${target}" "${installed}"
expect_failure symlink-installed "${SCRIPT}" --expected "${expected}" --installed "${installed}"
assert_contains "${TMP_DIR}/symlink-installed.err" '^Installed wrapper must not be a symlink: '

rm -f "${installed}"
cp "${expected}" "${installed}"
missing_expected="${TMP_DIR}/missing-expected/ObeliskRun.sh"
expect_failure missing-expected "${SCRIPT}" --expected "${missing_expected}" --installed "${installed}"
assert_contains "${TMP_DIR}/missing-expected.err" '^Expected wrapper must be a regular file: '

symlink_expected="${TMP_DIR}/symlink-expected/ObeliskRun.sh"
mkdir -p "$(dirname "${symlink_expected}")"
ln -s "${target}" "${symlink_expected}"
expect_failure symlink-expected "${SCRIPT}" --expected "${symlink_expected}" --installed "${installed}"
assert_contains "${TMP_DIR}/symlink-expected.err" '^Expected wrapper must not be a symlink: '

expect_failure unknown-option "${SCRIPT}" --unknown-option
assert_contains "${TMP_DIR}/unknown-option.err" '^Unknown option: --unknown-option'

"${SCRIPT}" --help > "${TMP_DIR}/help.out"
assert_contains "${TMP_DIR}/help.out" '^Usage: scripts/check_linuxgsm_wrapper_drift.sh'

echo "test_check_linuxgsm_wrapper_drift passed"
