#!/usr/bin/env bash
set -euo pipefail

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
export OBELISK_PLUGIN_DIR="${OBELISK_PLUGIN_DIR:-${OBELISK_ROOT}/plugins}"
export OBELISK_CONFIG_DIR="${OBELISK_CONFIG_DIR:-${OBELISK_ROOT}/config}"
export OBELISK_LOG_DIR="${OBELISK_LOG_DIR:-${OBELISK_ROOT}/logs}"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so${LD_PRELOAD:+:${LD_PRELOAD}}"

enable_marker() {
    local feature="$1"
    local instance="${OBELISK_INSTANCE_ID:-}"

    [[ -n "${instance}" && -f "${OBELISK_ROOT}/state/instances/${instance}/${feature}" ]] && return 0
    return 1
}

configure_chat_reflection() {
    enable_marker "enable-chat-reflection" || return 0

    export OBELISK_ENABLE_CHAT_REFLECTION=1
    export OBELISK_CHAT_REFLECTION_BINARY_SHA256="${OBELISK_CHAT_REFLECTION_BINARY_SHA256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_CHAT_REFLECTION_LOG_LIMIT="${OBELISK_CHAT_REFLECTION_LOG_LIMIT:-25}"
}

configure_structure_reflection() {
    enable_marker "enable-structure-reflection" || return 0

    export OBELISK_ENABLE_STRUCTURE_REFLECTION=1
    export OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256="${OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT="${OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT:-0}"
}

configure_inventory_reflection() {
    enable_marker "enable-inventory-reflection" || return 0

    export OBELISK_ENABLE_INVENTORY_REFLECTION=1
    export OBELISK_INVENTORY_REFLECTION_BINARY_SHA256="${OBELISK_INVENTORY_REFLECTION_BINARY_SHA256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_INVENTORY_REFLECTION_LOG_LIMIT="${OBELISK_INVENTORY_REFLECTION_LOG_LIMIT:-0}"
}

case "${1:-}" in
    Ragnarok*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver}"
        enable_marker "enable-process-event-hook" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" && export OBELISK_DISABLE_PLUGINS=1
        enable_marker "allow-ptrace" && export OBELISK_DEBUG_ALLOW_PTRACE=1
        enable_marker "enable-debug-control" && export OBELISK_ENABLE_DEBUG_CONTROL=1
        configure_chat_reflection
        configure_inventory_reflection
        configure_structure_reflection
        ;;
    TheIsland*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver2}"
        enable_marker "enable-process-event-hook" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" && export OBELISK_DISABLE_PLUGINS=1
        enable_marker "allow-ptrace" && export OBELISK_DEBUG_ALLOW_PTRACE=1
        enable_marker "enable-debug-control" && export OBELISK_ENABLE_DEBUG_CONTROL=1
        configure_chat_reflection
        configure_inventory_reflection
        configure_structure_reflection
        ;;
esac

unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

exec ./ShooterGameServer "$@"
