#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_obelisk.sh [options] [root]

Installs built Obelisk runtime artifacts into a centralized server root.
Runtime .so files are staged under temporary names in the destination directory and then
published with atomic renames, so ARK restarts do not observe partial shared libraries.

Options:
  --dry-run              Print actions without changing files.
  --backup-existing      Back up replaced runtime .so files with a timestamp suffix.
  -h, --help             Show this help.

Default root:
  /servidor/ark/obelisk
EOF
}

ROOT="/servidor/ark/obelisk"
DRY_RUN=0
BACKUP_EXISTING=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --backup-existing)
            BACKUP_EXISTING=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            ROOT="$1"
            shift
            ;;
    esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${REPO_DIR}/build"
STAMP="$(date +%Y%m%d-%H%M%S)"
STAGE_ROOT="${ROOT}/.install-runtime.${STAMP}.$$"
ROLLBACK_ROOT="${ROOT}/.install-rollback.${STAMP}.$$"
TEMP_PATHS=()
PUBLISHED_RUNTIME_PATHS=()
declare -A RUNTIME_ROLLBACK_SNAPSHOTS=()
declare -A RUNTIME_ROLLBACK_EXISTED=()

run() {
    if [[ "${DRY_RUN}" == "1" ]]; then
        printf 'DRY-RUN:'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

require_file() {
    local path="$1"
    if [[ ! -f "${path}" ]]; then
        echo "Required build artifact not found: ${path}" >&2
        echo "Run: cmake --build build -j\"$(nproc)\"" >&2
        exit 1
    fi
}

backup_existing() {
    local path="$1"
    if [[ "${BACKUP_EXISTING}" == "1" && -e "${path}" ]]; then
        run cp -a "${path}" "${path}.${STAMP}.bak"
    fi
}

validate_root() {
    if [[ -z "${ROOT}" || "${ROOT}" != /* || "${ROOT}" == "/" ]]; then
        echo "Install root must be a non-root absolute path: ${ROOT:-<empty>}" >&2
        exit 2
    fi

    if [[ -L "${ROOT}" ]]; then
        echo "Install root must not be a symlink: ${ROOT}" >&2
        exit 2
    fi
}

cleanup_temp_paths() {
    if [[ "${DRY_RUN}" != "1" ]]; then
        for temp_path in "${TEMP_PATHS[@]}"; do
            rm -f "${temp_path}"
        done
        rm -rf "${STAGE_ROOT}"
        rm -rf "${ROLLBACK_ROOT}"
    fi
}
trap cleanup_temp_paths EXIT

prepare_staged_file() {
    local mode="$1"
    local src="$2"
    local dst="$3"
    local -n out_tmp="$4"
    local tmp="${dst}.incoming.$$"
    if [[ "${DRY_RUN}" != "1" || -f "${src}" ]]; then
        require_file "${src}"
    fi
    TEMP_PATHS+=("${tmp}")
    run install -m "${mode}" "${src}" "${tmp}"
    out_tmp="${tmp}"
}

snapshot_runtime_destination() {
    local dst="$1"
    local snapshot="${ROLLBACK_ROOT}/$(basename "${dst}")"
    mkdir -p "${ROLLBACK_ROOT}"
    if [[ -e "${dst}" ]]; then
        cp -a "${dst}" "${snapshot}"
        RUNTIME_ROLLBACK_EXISTED["${dst}"]=1
        RUNTIME_ROLLBACK_SNAPSHOTS["${dst}"]="${snapshot}"
    else
        RUNTIME_ROLLBACK_EXISTED["${dst}"]=0
        RUNTIME_ROLLBACK_SNAPSHOTS["${dst}"]=""
    fi
}

rollback_runtime_publish() {
    local dst
    for ((idx=${#PUBLISHED_RUNTIME_PATHS[@]} - 1; idx >= 0; --idx)); do
        dst="${PUBLISHED_RUNTIME_PATHS[$idx]}"
        if [[ "${RUNTIME_ROLLBACK_EXISTED["${dst}"]}" == "1" ]]; then
            cp -a "${RUNTIME_ROLLBACK_SNAPSHOTS["${dst}"]}" "${dst}"
        else
            rm -f "${dst}"
        fi
    done
}

publish_runtime_file() {
    local tmp="$1"
    local dst="$2"
    mv -f "${tmp}" "${dst}" || return
    PUBLISHED_RUNTIME_PATHS+=("${dst}")
}

publish_runtime_pair() {
    local subhook_tmp="$1"
    local subhook_dst="$2"
    local obelisk_tmp="$3"
    local obelisk_dst="$4"

    publish_runtime_file "${subhook_tmp}" "${subhook_dst}" &&
        publish_runtime_file "${obelisk_tmp}" "${obelisk_dst}"
}

install_runtime_package() {
    require_file "${BUILD_DIR}/libobelisk.so"
    require_file "${BUILD_DIR}/_deps/subhook-build/libsubhook.so"
    run rm -rf "${STAGE_ROOT}"
    run cmake --install "${BUILD_DIR}" --prefix "${STAGE_ROOT}" --component Runtime
    local subhook_dst="${ROOT}/lib/libsubhook.so"
    local obelisk_dst="${ROOT}/lib/libobelisk.so"
    local subhook_tmp
    local obelisk_tmp
    prepare_staged_file 755 "${BUILD_DIR}/_deps/subhook-build/libsubhook.so" "${subhook_dst}" subhook_tmp
    prepare_staged_file 755 "${STAGE_ROOT}/lib/libobelisk.so" "${obelisk_dst}" obelisk_tmp
    backup_existing "${subhook_dst}"
    backup_existing "${obelisk_dst}"
    if [[ "${DRY_RUN}" == "1" ]]; then
        run mv -f "${subhook_tmp}" "${subhook_dst}"
        run mv -f "${obelisk_tmp}" "${obelisk_dst}"
    else
        snapshot_runtime_destination "${subhook_dst}"
        snapshot_runtime_destination "${obelisk_dst}"
        if ! publish_runtime_pair "${subhook_tmp}" "${subhook_dst}" "${obelisk_tmp}" "${obelisk_dst}"; then
            rollback_runtime_publish
            return 1
        fi
    fi
    run rm -rf "${STAGE_ROOT}"
}

install_sdk_package() {
    require_file "${BUILD_DIR}/ObeliskConfig.cmake"
    require_file "${BUILD_DIR}/ObeliskConfigVersion.cmake"
    run cmake --install "${BUILD_DIR}" --prefix "${ROOT}" --component SDK
}

validate_root

run mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/include/obelisk" \
    "${ROOT}/config" \
    "${ROOT}/logs" \
    "${ROOT}/state/instances"

install_runtime_package
install_sdk_package

echo "Obelisk installed to ${ROOT}"
