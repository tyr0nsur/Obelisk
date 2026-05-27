#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh"
TMP_DIR="$(mktemp -d /tmp/obelisk-wrapper-markers.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT
LIBC_SO="$(ldconfig -p | awk '/libc\.so\.6/{print $NF; exit}')"
if [[ -z "${LIBC_SO}" ]]; then
    echo "Could not locate libc.so.6 for harmless LD_PRELOAD fixture" >&2
    exit 1
fi

assert_contains() {
    local file="$1"
    local pattern="$2"
    if ! grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

assert_not_contains() {
    local file="$1"
    local pattern="$2"
    if grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} not to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

cat > "${TMP_DIR}/ShooterGameServer" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
{
    printf 'args=%s\n' "$*"
    env | sort
} > "${OBELISK_WRAPPER_CAPTURE}"
SH
chmod +x "${TMP_DIR}/ShooterGameServer"

run_wrapper() {
    local root="$1"
    local capture="$2"
    shift 2

    (
        cd "${TMP_DIR}"
        OBELISK_ROOT="${root}" \
        OBELISK_WRAPPER_CAPTURE="${capture}" \
        "${WRAPPER}" "$@"
    )
}

run_wrapper_with_instance() {
    local root="$1"
    local capture="$2"
    local instance="$3"
    shift 3

    (
        cd "${TMP_DIR}"
        OBELISK_ROOT="${root}" \
        OBELISK_INSTANCE_ID="${instance}" \
        OBELISK_WRAPPER_CAPTURE="${capture}" \
        "${WRAPPER}" "$@"
    )
}

prepare_root() {
    local root="$1"
    mkdir -p "${root}/lib" "${root}/state/instances/arkserver2"
    ln -sf "${LIBC_SO}" "${root}/lib/libobelisk.so"
}

root_no_marker="${TMP_DIR}/root-no-marker"
capture_no_marker="${TMP_DIR}/no-marker.env"
prepare_root "${root_no_marker}"
run_wrapper "${root_no_marker}" "${capture_no_marker}" TheIsland?listen

assert_contains "${capture_no_marker}" '^OBELISK_INSTANCE_ID=arkserver2$'
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='
assert_not_contains "${capture_no_marker}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_no_marker}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT='

root_marker="${TMP_DIR}/root-marker"
capture_marker="${TMP_DIR}/marker.env"
prepare_root "${root_marker}"
: > "${root_marker}/state/instances/arkserver2/enable-structure-reflection"
: > "${root_marker}/state/instances/arkserver2/enable-inventory-reflection"
run_wrapper "${root_marker}" "${capture_marker}" TheIsland?listen

assert_contains "${capture_marker}" '^OBELISK_INSTANCE_ID=arkserver2$'
assert_contains "${capture_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION=1$'
assert_contains "${capture_marker}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_marker}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0$'
assert_contains "${capture_marker}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION=1$'
assert_contains "${capture_marker}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_marker}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0$'

root_override="${TMP_DIR}/root-override"
capture_override="${TMP_DIR}/override.env"
prepare_root "${root_override}"
: > "${root_override}/state/instances/arkserver2/enable-structure-reflection"
: > "${root_override}/state/instances/arkserver2/enable-inventory-reflection"
(
    cd "${TMP_DIR}"
    OBELISK_ROOT="${root_override}" \
    OBELISK_WRAPPER_CAPTURE="${capture_override}" \
    OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5 \
    OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=7 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_override}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5$'
assert_contains "${capture_override}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=7$'

root_invalid="${TMP_DIR}/root-invalid"
capture_wrong_instance="${TMP_DIR}/wrong-instance.env"
prepare_root "${root_invalid}"
mkdir -p "${root_invalid}/state/instances/not-arkserver2"
: > "${root_invalid}/state/instances/not-arkserver2/enable-inventory-reflection"
: > "${root_invalid}/state/instances/not-arkserver2/enable-structure-reflection"
run_wrapper "${root_invalid}" "${capture_wrong_instance}" TheIsland?listen

assert_not_contains "${capture_wrong_instance}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_wrong_instance}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='

capture_directory_marker="${TMP_DIR}/directory-marker.env"
mkdir -p "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
run_wrapper "${root_invalid}" "${capture_directory_marker}" TheIsland?listen
assert_not_contains "${capture_directory_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='

capture_symlink_marker="${TMP_DIR}/symlink-marker.env"
rm -rf "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
: > "${TMP_DIR}/external-inventory-marker"
ln -s "${TMP_DIR}/external-inventory-marker" "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
run_wrapper "${root_invalid}" "${capture_symlink_marker}" TheIsland?listen
assert_not_contains "${capture_symlink_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='

capture_traversal="${TMP_DIR}/traversal.env"
run_wrapper_with_instance "${root_marker}" "${capture_traversal}" '../arkserver2' TheIsland?listen
assert_not_contains "${capture_traversal}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_traversal}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='

capture_symlink_instance="${TMP_DIR}/symlink-instance.env"
root_symlink_instance="${TMP_DIR}/root-symlink-instance"
mkdir -p "${root_symlink_instance}/lib" "${root_symlink_instance}/real-instance" "${root_symlink_instance}/state/instances"
ln -sf "${LIBC_SO}" "${root_symlink_instance}/lib/libobelisk.so"
: > "${root_symlink_instance}/real-instance/enable-inventory-reflection"
ln -s "${root_symlink_instance}/real-instance" "${root_symlink_instance}/state/instances/arkserver2"
run_wrapper "${root_symlink_instance}" "${capture_symlink_instance}" TheIsland?listen
assert_not_contains "${capture_symlink_instance}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='

echo "test_linuxgsm_wrapper_markers passed"
