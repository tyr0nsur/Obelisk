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

Set OBELISK_PROTECTED_SERVER_ROOT to your game installation root to protect it
from writes. To permit the exact obelisk subdirectory, also set
OBELISK_ALLOW_SERVER_ROOT_WRITES=1.

EOF
}

ROOT=""
DRY_RUN=0
BACKUP_EXISTING=0
BUILD_DIR_INPUT="${OBELISK_BUILD_DIR:-build}"
ROOT_SET=0
SERVER_ROOT="${OBELISK_PROTECTED_SERVER_ROOT:-}"

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
STAMP=""
STAGE_ROOT=""
SDK_STAGE_ROOT=""
ROLLBACK_ROOT=""
TEMP_PATHS=()
PUBLISHED_RUNTIME_PATHS=()
PUBLISHED_SDK_PATHS=()
declare -A RUNTIME_ROLLBACK_SNAPSHOTS=()
declare -A RUNTIME_ROLLBACK_EXISTED=()
declare -A SDK_ROLLBACK_SNAPSHOTS=()
declare -A SDK_ROLLBACK_EXISTED=()

is_under_path() {
    local path="$1"
    local parent="$2"

    [[ "${path}" == "${parent}" || "${path}" == "${parent}/"* ]]
}

reject_protected_path() {
    local label="$1"
    local action="$2"
    local path="$3"
    local absolute_path
    local resolved_path
    local allowed_live_root

    [[ -n "${SERVER_ROOT}" ]] || return 0
    absolute_path="$(realpath -s -m "${path}")"
    resolved_path="$(realpath -m "${path}")"
    allowed_live_root=0
    if [[ "${OBELISK_ALLOW_SERVER_ROOT_WRITES:-0}" == "1" &&
          "${label}" == "Install root" &&
          "${absolute_path}" == "${SERVER_ROOT}/obelisk" &&
          "${resolved_path}" == "${SERVER_ROOT}/obelisk" ]]; then
        allowed_live_root=1
    fi

    if [[ "${allowed_live_root}" != "1" ]] && is_under_path "${absolute_path}" "${SERVER_ROOT}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${absolute_path}" >&2
        exit 2
    fi

    if [[ "${allowed_live_root}" != "1" ]] && is_under_path "${resolved_path}" "${SERVER_ROOT}"; then
        printf '%s must not %s protected server root %s: %s\n' \
            "${label}" "${action}" "${SERVER_ROOT}" "${resolved_path}" >&2
        exit 2
    fi
}

reject_symlink_path_components() {
    local label="$1"
    local path="$2"
    local lexical_path
    local resolved_path

    lexical_path="$(realpath -s -m "${path}")"
    resolved_path="$(realpath -m "${path}")"
    if [[ "${lexical_path}" != "${resolved_path}" ]]; then
        printf '%s must not resolve through symlink path components: %s -> %s\n' \
            "${label}" "${path}" "${resolved_path}" >&2
        exit 2
    fi
}

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

    reject_protected_path "Install root" "write under" "${ROOT}"

    if [[ -L "${ROOT}" ]]; then
        echo "Install root must not be a symlink: ${ROOT}" >&2
        exit 2
    fi
    reject_symlink_path_components "Install root" "${ROOT}"
    if [[ -e "${ROOT}" && ! -d "${ROOT}" ]]; then
        echo "Install root must be a directory or absent path: ${ROOT}" >&2
        exit 2
    fi
}

validate_build_dir() {
    reject_protected_path "Build dir" "read from" "${BUILD_DIR}"
}

initialize_install_paths() {
    STAMP="$(date +%Y%m%d-%H%M%S)"
    STAGE_ROOT="${ROOT}/.install-runtime.${STAMP}.$$"
    SDK_STAGE_ROOT="${ROOT}/.install-sdk.${STAMP}.$$"
    ROLLBACK_ROOT="${ROOT}/.install-rollback.${STAMP}.$$"
}

validate_managed_subpaths() {
    local subpath
    for subpath in "$@"; do
        if [[ -L "${ROOT}/${subpath}" ]]; then
            echo "Managed install path must not be a symlink: ${ROOT}/${subpath}" >&2
            exit 2
        fi
        if [[ -e "${ROOT}/${subpath}" && ! -d "${ROOT}/${subpath}" ]]; then
            echo "Managed install path must be a directory: ${ROOT}/${subpath}" >&2
            exit 2
        fi
    done
}

validate_managed_artifact_path() {
    local path="$1"

    if [[ -L "${path}" ]]; then
        echo "Managed install artifact must not be a symlink: ${path}" >&2
        return 1
    fi
    if [[ -e "${path}" && ! -f "${path}" ]]; then
        echo "Managed install artifact must be a regular file: ${path}" >&2
        return 1
    fi
}

validate_managed_artifact_paths() {
    local path
    for path in "$@"; do
        if ! validate_managed_artifact_path "${path}"; then
            exit 2
        fi
    done
}

validate_managed_install_layout() {
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

    validate_managed_artifact_paths \
        "${ROOT}/lib/libsubhook.so" \
        "${ROOT}/lib/libobelisk.so" \
        "${ROOT}/include/obelisk/ObeliskApi.h" \
        "${ROOT}/include/obelisk/ObeliskChatSessionApi.h" \
        "${ROOT}/include/obelisk/ObeliskCommandApi.h" \
        "${ROOT}/include/obelisk/ObeliskPlayerLifecycleApi.h" \
        "${ROOT}/lib/cmake/Obelisk/ObeliskConfig.cmake" \
        "${ROOT}/lib/cmake/Obelisk/ObeliskConfigVersion.cmake" \
        "${ROOT}/lib/cmake/Obelisk/ObeliskTargets.cmake"
}

cleanup_temp_paths() {
    if [[ "${DRY_RUN}" != "1" ]]; then
        for temp_path in "${TEMP_PATHS[@]}"; do
            rm -f "${temp_path}"
        done
        if [[ -n "${STAGE_ROOT}" ]]; then
            rm -rf "${STAGE_ROOT}"
        fi
        if [[ -n "${SDK_STAGE_ROOT}" ]]; then
            rm -rf "${SDK_STAGE_ROOT}"
        fi
        if [[ -n "${ROLLBACK_ROOT}" ]]; then
            rm -rf "${ROLLBACK_ROOT}"
        fi
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
    validate_managed_artifact_path "${dst}" || return
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
    validate_managed_artifact_path "${dst}" || return
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

sdk_package_files() {
    printf '%s\n' \
        "include/obelisk/ObeliskApi.h" \
        "include/obelisk/ObeliskChatSessionApi.h" \
        "include/obelisk/ObeliskCommandApi.h" \
        "include/obelisk/ObeliskPlayerLifecycleApi.h" \
        "lib/cmake/Obelisk/ObeliskConfig.cmake" \
        "lib/cmake/Obelisk/ObeliskConfigVersion.cmake" \
        "lib/cmake/Obelisk/ObeliskTargets.cmake"
}

validate_staged_sdk_package_shape() {
    local expected_files
    local actual_files
    local cmake_package_dir="${SDK_STAGE_ROOT}/lib/cmake/Obelisk"
    local targets_file="${cmake_package_dir}/ObeliskTargets.cmake"
    local private_export_offenders
    local readiness_claim_offenders

    expected_files="$(sdk_package_files | LC_ALL=C sort)"
    actual_files="$(
        cd "${SDK_STAGE_ROOT}" &&
            find include lib/cmake/Obelisk -type f -printf '%p\n' | LC_ALL=C sort
    )"
    if [[ "${actual_files}" != "${expected_files}" ]]; then
        echo "Staged SDK package published unexpected files" >&2
        echo "Expected:" >&2
        printf '%s\n' "${expected_files}" >&2
        echo "Actual:" >&2
        printf '%s\n' "${actual_files}" >&2
        return 1
    fi

    if ! grep -F 'add_library(Obelisk::obelisk_sdk INTERFACE IMPORTED)' "${targets_file}" >/dev/null; then
        echo "Staged SDK package did not export Obelisk::obelisk_sdk as an interface imported target" >&2
        cat "${targets_file}" >&2
        return 1
    fi

    private_export_offenders="$(
        grep -RInE \
            'IMPORTED_(IMPLIB|LINK_DEPENDENT_LIBRARIES|LOCATION|OBJECTS|SONAME)|INTERFACE_LINK_(LIBRARIES|OPTIONS)|Obelisk::obelisk([^_[:alnum:]]|$)|Obelisk::subhook([^_[:alnum:]]|$)|libobelisk[.]so|libsubhook[.]so|(^|[;"[:space:]])(-l)?(dl|pthread)([;"[:space:]]|$)|(^|[[:space:]])-pthread([[:space:]]|$)' \
            "${cmake_package_dir}" || true
    )"
    if [[ -n "${private_export_offenders}" ]]; then
        echo "Staged SDK CMake package exposed runtime/private linkage or imported binary locations" >&2
        printf '%s\n' "${private_export_offenders}" >&2
        return 1
    fi

    local required_package_shape_markers=(
        'set(Obelisk_INSTALLED_SDK_PACKAGE_SHAPE_STATUS "package-shape-evidence-only")'
        'set(Obelisk_RUNTIME_READINESS_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_RUNTIME_LIVE_OP_APPROVAL_ALLOWED FALSE)'
        'set(Obelisk_PLUGIN_HUB_PUBLICATION_ALLOWED FALSE)'
        'set(Obelisk_PLUGIN_HUB_READINESS_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_SUPPORT_TIER_ACTIVATION_ALLOWED FALSE)'
        'set(Obelisk_V1_COMPLETION_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED FALSE)'
        'set(Obelisk_SDK_BLOCKER_PROMOTION_COUNT 0)'
        'set(Obelisk_SDK_BLOCKER_PROMOTION_TOTAL 12)'
        'set(Obelisk_P0_DEPENDENCY_COUNT 0)'
        'set(Obelisk_P0_DEPENDENCY_TOTAL 4)'
        'set(Obelisk_ACTIVE_COMPLETION_BLOCKER "approved_runtime_evidence_missing")'
        'set(Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE)'
        'set(Obelisk_EXACT_VERSION_REQUESTS_ALLOWED FALSE)'
        'set(Obelisk_FIND_PACKAGE_VERSION_IS_STABLE_SDK_CLAIM FALSE)'
        'set(Obelisk_FIND_PACKAGE_SDK_IS_PUBLIC_PACKAGE_READINESS FALSE)'
        'set(Obelisk_FIND_PACKAGE_SDK_IS_V1_COMPLETION_EVIDENCE FALSE)'
    )
    local package_shape_marker
    for package_shape_marker in "${required_package_shape_markers[@]}"; do
        if ! grep -F "${package_shape_marker}" \
            "${cmake_package_dir}/ObeliskConfig.cmake" >/dev/null; then
            echo "Staged SDK CMake package missed package-shape non-claim marker: ${package_shape_marker}" >&2
            cat "${cmake_package_dir}/ObeliskConfig.cmake" >&2
            return 1
        fi
    done

    readiness_claim_offenders="$(
        grep -RInEi \
            'set\([[:space:]]*Obelisk_[A-Za-z0-9_]*(READY|READINESS|ACCEPTED|APPROVED|CONTRACT_REVIEW|COMPLETE|SDK_COMPLETE|CLAIM|PROMOTION|COUNTS_TOWARD|PACKAGE_PUBLICATION|PACKAGE_AVAILABLE|STABLE_SDK|V1_COMPLETION|SUPPORT_TIER|PLUGIN_HUB|PUBLIC_PACKAGE|PUBLIC_SDK|PUBLIC_HEADER|PACKAGE_SHAPE|SDK_CONSUMER|ABI_LAYOUT|C_ABI|STRUCT_SIZE)[A-Za-z0-9_]*[[:space:]]+(TRUE|ON|1)[[:space:]]*\)' \
            "${cmake_package_dir}" |
            grep -vF 'Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE' || true
    )"
    if [[ -n "${readiness_claim_offenders}" ]]; then
        echo "Staged SDK CMake package exposed positive readiness/public-claim markers" >&2
        printf '%s\n' "${readiness_claim_offenders}" >&2
        return 1
    fi
}

stage_sdk_package() {
    run rm -rf "${SDK_STAGE_ROOT}"
    if ! run cmake --install "${BUILD_DIR}" --prefix "${SDK_STAGE_ROOT}" --component SDK; then
        return 1
    fi

    local relative
    if [[ "${DRY_RUN}" != "1" ]]; then
        while IFS= read -r relative; do
            if [[ ! -f "${SDK_STAGE_ROOT}/${relative}" ]]; then
                echo "Required staged SDK artifact not found: ${SDK_STAGE_ROOT}/${relative}" >&2
                return 1
            fi
        done < <(sdk_package_files)
        validate_staged_sdk_package_shape
    fi
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
    validate_managed_artifact_path "${subhook_dst}" || return
    validate_managed_artifact_path "${obelisk_dst}" || return
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

publish_staged_sdk_package() {
    run mkdir -p "${ROOT}/include/obelisk" "${ROOT}/lib/cmake/Obelisk" || return

    local relative
    if [[ "${DRY_RUN}" == "1" ]]; then
        while IFS= read -r relative; do
            validate_managed_artifact_path "${ROOT}/${relative}" || return
            run install -m 644 "${SDK_STAGE_ROOT}/${relative}" "${ROOT}/${relative}.incoming.$$"
            run mv -f "${ROOT}/${relative}.incoming.$$" "${ROOT}/${relative}"
        done < <(sdk_package_files)
    else
        while IFS= read -r relative; do
            validate_managed_artifact_path "${ROOT}/${relative}" || return
            snapshot_sdk_destination "${ROOT}/${relative}"
        done < <(sdk_package_files)
        while IFS= read -r relative; do
            if ! publish_sdk_file "${SDK_STAGE_ROOT}/${relative}" "${ROOT}/${relative}"; then
                rollback_sdk_publish
                return 1
            fi
        done < <(sdk_package_files)
    fi

    run rm -rf "${SDK_STAGE_ROOT}"
}

validate_root
validate_build_dir
initialize_install_paths
validate_managed_install_layout

run mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/include/obelisk" \
    "${ROOT}/lib/cmake/Obelisk" \
    "${ROOT}/config" \
    "${ROOT}/logs" \
    "${ROOT}/state/instances"

validate_root
validate_managed_install_layout

validate_build_artifacts
stage_sdk_package
install_runtime_package
if ! publish_staged_sdk_package; then
    if [[ "${DRY_RUN}" != "1" ]]; then
        rollback_runtime_publish
    fi
    exit 1
fi

if [[ "${DRY_RUN}" == "1" ]]; then
    echo "DRY-RUN: Obelisk install would publish runtime/SDK package-shape artifacts to ${ROOT}"
else
    echo "Obelisk runtime/SDK package-shape artifacts installed to ${ROOT}"
fi
echo "Install layout/package-shape evidence only; no runtime/live-ops approval, Plugin Hub readiness/publication, support-tier activation, stable SDK claim, or v1 SDK completion is granted."
echo "Current complete-SDK route remains blocked: SDK blocker promotion 0/12, P0 dependency chain 0/4, stable_claim_allowed=false, active blocker approved_runtime_evidence_missing. Summary: SDK 0/12, P0 0/4, stable=false."
