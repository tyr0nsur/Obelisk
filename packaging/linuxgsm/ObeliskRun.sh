#!/usr/bin/env bash
set -euo pipefail

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
export OBELISK_PLUGIN_DIR="${OBELISK_PLUGIN_DIR:-${OBELISK_ROOT}/plugins}"
export OBELISK_CONFIG_DIR="${OBELISK_CONFIG_DIR:-${OBELISK_ROOT}/config}"
export OBELISK_LOG_DIR="${OBELISK_LOG_DIR:-${OBELISK_ROOT}/logs}"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so${LD_PRELOAD:+:${LD_PRELOAD}}"

inherited_chat_reflection_binary_sha256="${OBELISK_CHAT_REFLECTION_BINARY_SHA256:-}"
inherited_chat_reflection_log_limit="${OBELISK_CHAT_REFLECTION_LOG_LIMIT:-}"
inherited_chat_reflection_log_text="${OBELISK_CHAT_REFLECTION_LOG_TEXT:-}"
inherited_inventory_reflection_binary_sha256="${OBELISK_INVENTORY_REFLECTION_BINARY_SHA256:-}"
inherited_inventory_reflection_log_limit="${OBELISK_INVENTORY_REFLECTION_LOG_LIMIT:-}"
inherited_structure_reflection_binary_sha256="${OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256:-}"
inherited_structure_reflection_log_limit="${OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT:-}"

unset OBELISK_ENABLE_PROCESS_EVENT_HOOK
unset OBELISK_DISABLE_PLUGINS
unset OBELISK_DEBUG_ALLOW_PTRACE
unset OBELISK_ENABLE_DEBUG_CONTROL
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
unset OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS
unset OBELISK_ENABLE_CHAT_REFLECTION
unset OBELISK_CHAT_REFLECTION_BINARY_SHA256
unset OBELISK_CHAT_REFLECTION_LOG_LIMIT
unset OBELISK_CHAT_REFLECTION_LOG_TEXT
unset OBELISK_ENABLE_INVENTORY_REFLECTION
unset OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
unset OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
unset OBELISK_ENABLE_STRUCTURE_REFLECTION
unset OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
unset OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT

enable_marker() {
    local feature="$1"
    local instance="${OBELISK_INSTANCE_ID:-}"
    local instance_dir="${OBELISK_ROOT}/state/instances/${instance}"
    local marker="${instance_dir}/${feature}"

    [[ "${instance}" =~ ^[A-Za-z0-9_-]+$ ]] || return 1
    [[ "${feature}" =~ ^[A-Za-z0-9_-]+$ ]] || return 1
    [[ -d "${instance_dir}" && ! -L "${instance_dir}" ]] || return 1
    [[ -f "${marker}" && ! -L "${marker}" ]] && return 0
    return 1
}

configure_chat_reflection() {
    enable_marker "enable-chat-reflection" || return 0

    export OBELISK_ENABLE_CHAT_REFLECTION=1
    export OBELISK_CHAT_REFLECTION_BINARY_SHA256="${inherited_chat_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_CHAT_REFLECTION_LOG_LIMIT="${inherited_chat_reflection_log_limit:-25}"
    if [[ -n "${inherited_chat_reflection_log_text}" ]]; then
        export OBELISK_CHAT_REFLECTION_LOG_TEXT="${inherited_chat_reflection_log_text}"
    fi
}

configure_structure_reflection() {
    enable_marker "enable-structure-reflection" || return 0

    export OBELISK_ENABLE_STRUCTURE_REFLECTION=1
    export OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256="${inherited_structure_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT="${inherited_structure_reflection_log_limit:-0}"
}

configure_inventory_reflection() {
    enable_marker "enable-inventory-reflection" || return 0

    export OBELISK_ENABLE_INVENTORY_REFLECTION=1
    export OBELISK_INVENTORY_REFLECTION_BINARY_SHA256="${inherited_inventory_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_INVENTORY_REFLECTION_LOG_LIMIT="${inherited_inventory_reflection_log_limit:-0}"
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

exec ./ShooterGameServer "$@"
