#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/servidor/ark/obelisk}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${REPO_DIR}/build"

mkdir -p \
    "${ROOT}/lib" \
    "${ROOT}/plugins" \
    "${ROOT}/config/plugins" \
    "${ROOT}/logs" \
    "${ROOT}/state"

install -m 755 "${BUILD_DIR}/libobelisk.so" "${ROOT}/lib/libobelisk.so"
install -m 755 "${BUILD_DIR}/_deps/subhook-build/libsubhook.so" "${ROOT}/lib/libsubhook.so"

if [[ -f "${BUILD_DIR}/plugins/chat/ChatPlugin.so" ]]; then
    install -m 755 "${BUILD_DIR}/plugins/chat/ChatPlugin.so" "${ROOT}/plugins/ChatPlugin.so"
fi

if [[ ! -f "${ROOT}/config/plugins/chat_config.json" ]]; then
    cat > "${ROOT}/config/plugins/chat_config.json" <<'JSON'
{
    "ClientMessageIndex": -1,
    "ClientMessageTextOffset": 0,
    "ServerChatIndex": -1,
    "ServerChatMessageOffset": -1
}
JSON
fi

echo "Obelisk installed to ${ROOT}"
