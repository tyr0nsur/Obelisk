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
    local map="$2"

    [[ -n "${instance}" && -f "${OBELISK_ROOT}/state/instances/${instance}/${feature}" ]] && return 0
    [[ -n "${instance}" && -f "${OBELISK_ROOT}/state/${feature}-${instance}" ]] && return 0
    [[ -f "${OBELISK_ROOT}/state/${feature}-${map}" ]] && return 0
    return 1
}

case "${1:-}" in
    Ragnarok*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver}"
        enable_marker "enable-process-event-hook" "ragnarok" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" "ragnarok" && export OBELISK_DISABLE_PLUGINS=1
        ;;
    TheIsland*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver2}"
        enable_marker "enable-process-event-hook" "theisland" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" "theisland" && export OBELISK_DISABLE_PLUGINS=1
        ;;
esac

unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

exec ./ShooterGameServer "$@"
