#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_obelisk.sh [options] [root]

Installs built Obelisk runtime artifacts into a centralized server root.

Options:
  --dry-run              Print actions without changing files.
  --enable-chat-plugin   Install ChatPlugin.so into plugins/ instead of plugins-disabled/.
  --backup-existing      Back up replaced runtime/plugin .so files with a timestamp suffix.
  --force-config         Replace generated plugin config files even if they already exist.
  -h, --help             Show this help.

Default root:
  /servidor/ark/obelisk
EOF
}

ROOT="/servidor/ark/obelisk"
DRY_RUN=0
ENABLE_CHAT_PLUGIN=0
BACKUP_EXISTING=0
FORCE_CONFIG=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --enable-chat-plugin)
            ENABLE_CHAT_PLUGIN=1
            shift
            ;;
        --backup-existing)
            BACKUP_EXISTING=1
            shift
            ;;
        --force-config)
            FORCE_CONFIG=1
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

write_chat_config() {
    local path="${ROOT}/config/plugins/chat/config.json"
    local legacy_path="${ROOT}/config/plugins/chat_config.json"
    if [[ "${FORCE_CONFIG}" != "1" && -f "${path}" ]]; then
        echo "Keeping existing ${path}"
        return
    fi

    if [[ "${DRY_RUN}" == "1" ]]; then
        echo "DRY-RUN: write ${path}"
        return
    fi

    mkdir -p "$(dirname "${path}")"
    cat > "${path}" <<'JSON'
{
    "ClientMessageIndex": -1,
    "ClientMessageTextOffset": 0,
    "ServerChatIndex": -1,
    "ServerChatMessageOffset": -1
}
JSON

    if [[ ! -f "${legacy_path}" ]]; then
        cp -a "${path}" "${legacy_path}"
    fi
}

run mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/plugins-disabled" \
    "${ROOT}/config/plugins" \
    "${ROOT}/config/instances" \
    "${ROOT}/logs" \
    "${ROOT}/state"

install_file 755 "${BUILD_DIR}/libobelisk.so" "${ROOT}/lib/libobelisk.so"
install_file 755 "${BUILD_DIR}/_deps/subhook-build/libsubhook.so" "${ROOT}/lib/libsubhook.so"

if [[ -f "${BUILD_DIR}/plugins/chat/ChatPlugin.so" ]]; then
    if [[ "${ENABLE_CHAT_PLUGIN}" == "1" ]]; then
        install_file 755 "${BUILD_DIR}/plugins/chat/ChatPlugin.so" "${ROOT}/plugins/ChatPlugin.so"
        echo "Installed ChatPlugin.so into plugins/ because --enable-chat-plugin was set."
    else
        install_file 755 "${BUILD_DIR}/plugins/chat/ChatPlugin.so" "${ROOT}/plugins-disabled/ChatPlugin.so"
        echo "Installed ChatPlugin.so into plugins-disabled/ by default."
    fi
else
    echo "ChatPlugin.so not built; skipping optional chat plugin."
fi

write_chat_config

echo "Obelisk installed to ${ROOT}"
