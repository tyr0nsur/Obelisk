#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_obelisk.sh [options] <root>

Installs built Obelisk runtime artifacts into a centralized server root.
Runtime .so files are staged under temporary names in the destination directory and then
published with atomic renames, so ARK restarts do not observe partial shared libraries.
The install root must be supplied as a positional argument.

Options:
  --dry-run              Print actions without changing files.
  --backup-existing      Back up replaced runtime .so files with a timestamp suffix.
  --build-dir <dir>      Use a specific CMake build directory (default: build or OBELISK_BUILD_DIR).
  -h, --help             Show this help.

EOF
}

ROOT=""
DRY_RUN=0
BACKUP_EXISTING=0
BUILD_DIR_INPUT="${OBELISK_BUILD_DIR:-build}"
ROOT_SET=0

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
        --build-dir)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "Missing value for --build-dir" >&2
                usage >&2
                exit 2
            fi
            BUILD_DIR_INPUT="$2"
            shift 2
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
            if [[ "${ROOT_SET}" == "1" ]]; then
                echo "Unexpected extra argument: $1" >&2
                usage >&2
                exit 2
            fi
            ROOT="$1"
            ROOT_SET=1
            shift
            ;;
    esac
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${BUILD_DIR_INPUT}" == /* ]]; then
    BUILD_DIR="${BUILD_DIR_INPUT}"
else
    BUILD_DIR="${REPO_DIR}/${BUILD_DIR_INPUT}"
fi
STAMP="$(date +%Y%m%d-%H%M%S)"
STAGE_ROOT="${ROOT}/.install-runtime.${STAMP}.$$"
SDK_STAGE_ROOT="${ROOT}/.install-sdk.${STAMP}.$$"
ROLLBACK_ROOT="${ROOT}/.install-rollback.${STAMP}.$$"
TEMP_PATHS=()
PUBLISHED_RUNTIME_PATHS=()
PUBLISHED_SDK_PATHS=()
declare -A RUNTIME_ROLLBACK_SNAPSHOTS=()
declare -A RUNTIME_ROLLBACK_EXISTED=()
declare -A SDK_ROLLBACK_SNAPSHOTS=()
declare -A SDK_ROLLBACK_EXISTED=()

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

validate_managed_subpaths() {
    local subpath
    for subpath in "$@"; do
        if [[ -L "${ROOT}/${subpath}" ]]; then
            echo "Managed install path must not be a symlink: ${ROOT}/${subpath}" >&2
            exit 2
        fi
    done
}

cleanup_temp_paths() {
    if [[ "${DRY_RUN}" != "1" ]]; then
        for temp_path in "${TEMP_PATHS[@]}"; do
            rm -f "${temp_path}"
        done
        rm -rf "${STAGE_ROOT}"
        rm -rf "${SDK_STAGE_ROOT}"
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

snapshot_sdk_destination() {
    local dst="$1"
    local snapshot="${ROLLBACK_ROOT}/sdk/$(printf '%s' "${dst#${ROOT}/}" | tr '/' '_')"
    mkdir -p "$(dirname "${snapshot}")"
    if [[ -e "${dst}" || -L "${dst}" ]]; then
        cp -a "${dst}" "${snapshot}"
        SDK_ROLLBACK_EXISTED["${dst}"]=1
        SDK_ROLLBACK_SNAPSHOTS["${dst}"]="${snapshot}"
    else
        SDK_ROLLBACK_EXISTED["${dst}"]=0
        SDK_ROLLBACK_SNAPSHOTS["${dst}"]=""
    fi
}

rollback_sdk_publish() {
    local dst
    for ((idx=${#PUBLISHED_SDK_PATHS[@]} - 1; idx >= 0; --idx)); do
        dst="${PUBLISHED_SDK_PATHS[$idx]}"
        if [[ "${SDK_ROLLBACK_EXISTED["${dst}"]}" == "1" ]]; then
            cp -a "${SDK_ROLLBACK_SNAPSHOTS["${dst}"]}" "${dst}"
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

publish_sdk_file() {
    local src="$1"
    local dst="$2"
    local tmp="${dst}.incoming.$$"

    if [[ ! -f "${src}" ]]; then
        echo "Required staged SDK artifact not found: ${src}" >&2
        return 1
    fi
    TEMP_PATHS+=("${tmp}")
    install -m 644 "${src}" "${tmp}"
    mv -f "${tmp}" "${dst}" || return
    PUBLISHED_SDK_PATHS+=("${dst}")
}

publish_runtime_pair() {
    local subhook_tmp="$1"
    local subhook_dst="$2"
    local obelisk_tmp="$3"
    local obelisk_dst="$4"

    publish_runtime_file "${subhook_tmp}" "${subhook_dst}" &&
        publish_runtime_file "${obelisk_tmp}" "${obelisk_dst}"
}

validate_build_artifacts() {
    require_file "${BUILD_DIR}/libobelisk.so"
    require_file "${BUILD_DIR}/_deps/subhook-build/libsubhook.so"
    require_file "${BUILD_DIR}/ObeliskConfig.cmake"
    require_file "${BUILD_DIR}/ObeliskConfigVersion.cmake"
}

install_runtime_package() {
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
    local sdk_files=(
        "include/obelisk/ObeliskApi.h"
        "lib/cmake/Obelisk/ObeliskConfig.cmake"
        "lib/cmake/Obelisk/ObeliskConfigVersion.cmake"
        "lib/cmake/Obelisk/ObeliskTargets.cmake"
    )
    run rm -rf "${SDK_STAGE_ROOT}"
    if ! run cmake --install "${BUILD_DIR}" --prefix "${SDK_STAGE_ROOT}" --component SDK; then
        return 1
    fi

    local relative
    if [[ "${DRY_RUN}" != "1" ]]; then
        for relative in "${sdk_files[@]}"; do
            if [[ ! -f "${SDK_STAGE_ROOT}/${relative}" ]]; then
                echo "Required staged SDK artifact not found: ${SDK_STAGE_ROOT}/${relative}" >&2
                return 1
            fi
        done
    fi

    run mkdir -p "${ROOT}/include/obelisk" "${ROOT}/lib/cmake/Obelisk"

    if [[ "${DRY_RUN}" == "1" ]]; then
        for relative in "${sdk_files[@]}"; do
            run install -m 644 "${SDK_STAGE_ROOT}/${relative}" "${ROOT}/${relative}.incoming.$$"
            run mv -f "${ROOT}/${relative}.incoming.$$" "${ROOT}/${relative}"
        done
    else
        for relative in "${sdk_files[@]}"; do
            snapshot_sdk_destination "${ROOT}/${relative}"
        done
        for relative in "${sdk_files[@]}"; do
            if ! publish_sdk_file "${SDK_STAGE_ROOT}/${relative}" "${ROOT}/${relative}"; then
                rollback_sdk_publish
                return 1
            fi
        done
    fi

    run rm -rf "${SDK_STAGE_ROOT}"
}

validate_root
validate_managed_subpaths \
    "lib" \
    "plugins" \
    "include" \
    "include/obelisk" \
    "lib/cmake" \
    "lib/cmake/Obelisk" \
    "config" \
    "logs" \
    "state" \
    "state/instances"

run mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/include/obelisk" \
    "${ROOT}/lib/cmake/Obelisk" \
    "${ROOT}/config" \
    "${ROOT}/logs" \
    "${ROOT}/state/instances"

validate_build_artifacts
install_runtime_package
if ! install_sdk_package; then
    if [[ "${DRY_RUN}" != "1" ]]; then
        rollback_runtime_publish
    fi
    exit 1
fi

echo "Obelisk installed to ${ROOT}"
