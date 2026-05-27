#!/usr/bin/env bash
set -euo pipefail

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
export OBELISK_PLUGIN_DIR="${OBELISK_PLUGIN_DIR:-${OBELISK_ROOT}/plugins}"
export OBELISK_CONFIG_DIR="${OBELISK_CONFIG_DIR:-${OBELISK_ROOT}/config}"
export OBELISK_LOG_DIR="${OBELISK_LOG_DIR:-${OBELISK_ROOT}/logs}"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so${LD_PRELOAD:+:${LD_PRELOAD}}"

case "${1:-}" in
    Ragnarok*)
        [[ -f "${OBELISK_ROOT}/state/enable-process-event-hook-ragnarok" ]] && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        [[ -f "${OBELISK_ROOT}/state/disable-plugins-ragnarok" ]] && export OBELISK_DISABLE_PLUGINS=1
        [[ -f "${OBELISK_ROOT}/state/enable-chat-discovery-ragnarok" ]] && export OBELISK_CHAT_DISCOVERY=1
        ;;
    TheIsland*)
        [[ -f "${OBELISK_ROOT}/state/enable-process-event-hook-theisland" ]] && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        [[ -f "${OBELISK_ROOT}/state/disable-plugins-theisland" ]] && export OBELISK_DISABLE_PLUGINS=1
        [[ -f "${OBELISK_ROOT}/state/enable-chat-discovery-theisland" ]] && export OBELISK_CHAT_DISCOVERY=1
        ;;
esac

unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

exec ./ShooterGameServer "$@"
