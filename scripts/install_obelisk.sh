#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_obelisk.sh [options] [root]

Installs built Obelisk runtime artifacts into a centralized server root.

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

install_file() {
    local mode="$1"
    local src="$2"
    local dst="$3"
    require_file "${src}"
    backup_existing "${dst}"
    run install -m "${mode}" "${src}" "${dst}"
}

run mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/config" \
    "${ROOT}/logs" \
    "${ROOT}/state/instances"

install_file 755 "${BUILD_DIR}/libobelisk.so" "${ROOT}/lib/libobelisk.so"
install_file 755 "${BUILD_DIR}/_deps/subhook-build/libsubhook.so" "${ROOT}/lib/libsubhook.so"

echo "Obelisk installed to ${ROOT}"
