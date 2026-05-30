#!/usr/bin/env bash
set -euo pipefail

wrapper_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"

validate_runtime_layout() {
    case "${OBELISK_ROOT}" in
        /*) ;;
        *)
            echo "OBELISK_ROOT must be an absolute path: ${OBELISK_ROOT}" >&2
            exit 1
            ;;
    esac

    if [[ "${OBELISK_ROOT}" == "/" || -L "${OBELISK_ROOT}" || ! -d "${OBELISK_ROOT}" ]]; then
        echo "OBELISK_ROOT must be a real non-symlink directory and must not be /: ${OBELISK_ROOT}" >&2
        exit 1
    fi

    local required_dir
    for required_dir in lib plugins config logs state state/instances; do
        if [[ -L "${OBELISK_ROOT}/${required_dir}" || ! -d "${OBELISK_ROOT}/${required_dir}" ]]; then
            echo "Obelisk runtime directory must be real and non-symlink: ${OBELISK_ROOT}/${required_dir}" >&2
            exit 1
        fi
    done

    if [[ -L "${OBELISK_ROOT}/lib/libobelisk.so" || ! -f "${OBELISK_ROOT}/lib/libobelisk.so" ]]; then
        echo "Obelisk runtime library must be a regular non-symlink file: ${OBELISK_ROOT}/lib/libobelisk.so" >&2
        exit 1
    fi

    if [[ -L "${wrapper_dir}/ShooterGameServer" || ! -f "${wrapper_dir}/ShooterGameServer" ]]; then
        echo "ShooterGameServer must be a regular non-symlink file beside the Obelisk wrapper: ${wrapper_dir}/ShooterGameServer" >&2
        exit 1
    fi
}

validate_runtime_layout

export OBELISK_PLUGIN_DIR="${OBELISK_ROOT}/plugins"
export OBELISK_CONFIG_DIR="${OBELISK_ROOT}/config"
export OBELISK_LOG_DIR="${OBELISK_ROOT}/logs"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so${LD_PRELOAD:+:${LD_PRELOAD}}"

inherited_chat_reflection_binary_sha256="${OBELISK_CHAT_REFLECTION_BINARY_SHA256:-}"
inherited_chat_reflection_log_limit="${OBELISK_CHAT_REFLECTION_LOG_LIMIT:-}"
inherited_chat_reflection_log_text="${OBELISK_CHAT_REFLECTION_LOG_TEXT:-}"
inherited_chat_events_binary_sha256="${OBELISK_CHAT_EVENTS_BINARY_SHA256:-}"
inherited_chat_events_dispatch_limit="${OBELISK_CHAT_EVENTS_DISPATCH_LIMIT:-}"
inherited_chat_route_observer_binary_sha256="${OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256:-}"
inherited_chat_route_observer_limit="${OBELISK_CHAT_ROUTE_OBSERVER_LIMIT:-}"
inherited_inventory_reflection_binary_sha256="${OBELISK_INVENTORY_REFLECTION_BINARY_SHA256:-}"
inherited_inventory_reflection_log_limit="${OBELISK_INVENTORY_REFLECTION_LOG_LIMIT:-}"
inherited_inventory_reflection_dispatch_limit="${OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT:-}"
inherited_structure_reflection_binary_sha256="${OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256:-}"
inherited_structure_reflection_log_limit="${OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT:-}"
inherited_structure_reflection_dispatch_limit="${OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT:-}"
inherited_item_return_events_binary_sha256="${OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256:-}"
inherited_item_return_events_dispatch_limit="${OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT:-}"
inherited_item_return_events_log_limit="${OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT:-}"

unset OBELISK_ENABLE_PROCESS_EVENT_HOOK
unset OBELISK_DISABLE_PLUGINS
unset OBELISK_DEBUG_ALLOW_PTRACE
unset OBELISK_ENABLE_DEBUG_CONTROL
unset OBELISK_ENABLE_REFLECTION_SCANNER
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
unset OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS
unset OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS
unset OBELISK_ALLOW_CALL_PROCESS_EVENT
unset OBELISK_ALLOW_PROCESS_EVENT_BLOCKING
unset OBELISK_PE_TRACE_LIMIT
unset OBELISK_ENABLE_CHAT_EVENTS
unset OBELISK_CHAT_EVENTS_BINARY_SHA256
unset OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
unset OBELISK_ENABLE_CHAT_REFLECTION
unset OBELISK_CHAT_REFLECTION_BINARY_SHA256
unset OBELISK_CHAT_REFLECTION_LOG_LIMIT
unset OBELISK_CHAT_REFLECTION_LOG_TEXT
unset OBELISK_ENABLE_CHAT_ROUTE_OBSERVER
unset OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256
unset OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
unset OBELISK_ENABLE_INVENTORY_REFLECTION
unset OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
unset OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
unset OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT
unset OBELISK_ENABLE_STRUCTURE_REFLECTION
unset OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
unset OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT
unset OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT
unset OBELISK_ENABLE_ITEM_RETURN_EVENTS
unset OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256
unset OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT
unset OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT

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

marker_entry_exists() {
    local feature="$1"
    local instance="${OBELISK_INSTANCE_ID:-}"
    local instance_dir="${OBELISK_ROOT}/state/instances/${instance}"
    local marker="${instance_dir}/${feature}"

    [[ "${instance}" =~ ^[A-Za-z0-9_-]+$ ]] || return 1
    [[ "${feature}" =~ ^[A-Za-z0-9_-]+$ ]] || return 1
    [[ -d "${instance_dir}" && ! -L "${instance_dir}" ]] || return 1
    [[ -e "${marker}" || -L "${marker}" ]]
}

require_sha256_hex() {
    local name="$1"
    local value="$2"

    if [[ ! "${value}" =~ ^[0-9a-f]{64}$ ]]; then
        echo "${name} must be an explicit lowercase SHA256 hex value for observer-debug observer gates." >&2
        exit 1
    fi
}

require_supported_sha256() {
    local name="$1"
    local value="$2"
    local supported_sha256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"

    require_sha256_hex "${name}" "${value}"
    if [[ "${value}" != "${supported_sha256}" ]]; then
        echo "${name} must match the supported ShooterGameServer SHA256 for observer-debug route observation." >&2
        exit 1
    fi
}

require_positive_integer() {
    local name="$1"
    local value="$2"

    if [[ ! "${value}" =~ ^0*[1-9][0-9]*$ ]]; then
        echo "${name} must be an explicit positive integer for observer-debug observer gates." >&2
        exit 1
    fi
}

require_nonnegative_integer() {
    local name="$1"
    local value="$2"

    if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
        echo "${name} must be an explicit non-negative integer for observer-debug observer gates." >&2
        exit 1
    fi
}

validate_observer_wrapper_profile() {
    local profile="${OBELISK_WRAPPER_PROFILE:-stable}"

    case "${profile}" in
        stable)
            local marker
            for marker in \
                allow-observer-debug-window \
                allow-experimental-observers \
                enable-chat-events \
                enable-chat-reflection \
                enable-chat-route-observer \
                enable-inventory-reflection \
                enable-structure-reflection \
                enable-item-return-events
            do
                if marker_entry_exists "${marker}"; then
                    echo "Experimental observer marker ${marker} is present for ${OBELISK_INSTANCE_ID}; refusing stable wrapper launch." >&2
                    exit 1
                fi
            done
            ;;
        observer-debug)
            if ! enable_marker "allow-observer-debug-window"; then
                echo "OBELISK_WRAPPER_PROFILE=observer-debug requires allow-observer-debug-window marker for ${OBELISK_INSTANCE_ID}." >&2
                exit 1
            fi
            ;;
        *)
            echo "Unknown OBELISK_WRAPPER_PROFILE '${profile}'. Expected stable or observer-debug." >&2
            exit 1
            ;;
    esac
}

configure_chat_events() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-chat-events" || return 0

    require_sha256_hex "OBELISK_CHAT_EVENTS_BINARY_SHA256" "${inherited_chat_events_binary_sha256}"
    require_positive_integer "OBELISK_CHAT_EVENTS_DISPATCH_LIMIT" "${inherited_chat_events_dispatch_limit}"

    export OBELISK_ENABLE_CHAT_EVENTS=1
    export OBELISK_CHAT_EVENTS_BINARY_SHA256="${inherited_chat_events_binary_sha256}"
    export OBELISK_CHAT_EVENTS_DISPATCH_LIMIT="${inherited_chat_events_dispatch_limit}"
}

configure_chat_route_observer() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-chat-route-observer" || return 0

    require_supported_sha256 "OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256" "${inherited_chat_route_observer_binary_sha256}"
    require_positive_integer "OBELISK_CHAT_ROUTE_OBSERVER_LIMIT" "${inherited_chat_route_observer_limit}"

    export OBELISK_ENABLE_CHAT_ROUTE_OBSERVER=1
    export OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256="${inherited_chat_route_observer_binary_sha256}"
    export OBELISK_CHAT_ROUTE_OBSERVER_LIMIT="${inherited_chat_route_observer_limit}"
}

configure_chat_reflection() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-chat-reflection" || return 0

    export OBELISK_ENABLE_CHAT_REFLECTION=1
    export OBELISK_CHAT_REFLECTION_BINARY_SHA256="${inherited_chat_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_CHAT_REFLECTION_LOG_LIMIT="${inherited_chat_reflection_log_limit:-0}"
    if [[ -n "${inherited_chat_reflection_log_text}" ]]; then
        export OBELISK_CHAT_REFLECTION_LOG_TEXT="${inherited_chat_reflection_log_text}"
    fi
}

configure_structure_reflection() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-structure-reflection" || return 0

    export OBELISK_ENABLE_STRUCTURE_REFLECTION=1
    export OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256="${inherited_structure_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT="${inherited_structure_reflection_log_limit:-0}"
    export OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT="${inherited_structure_reflection_dispatch_limit:-0}"
}

configure_inventory_reflection() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-inventory-reflection" || return 0

    export OBELISK_ENABLE_INVENTORY_REFLECTION=1
    export OBELISK_INVENTORY_REFLECTION_BINARY_SHA256="${inherited_inventory_reflection_binary_sha256:-7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520}"
    export OBELISK_INVENTORY_REFLECTION_LOG_LIMIT="${inherited_inventory_reflection_log_limit:-0}"
    export OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT="${inherited_inventory_reflection_dispatch_limit:-0}"
}

configure_item_return_events() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-item-return-events" || return 0

    require_sha256_hex "OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256" "${inherited_item_return_events_binary_sha256}"
    require_positive_integer "OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT" "${inherited_item_return_events_dispatch_limit}"
    require_nonnegative_integer "OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT" "${inherited_item_return_events_log_limit:-0}"

    export OBELISK_ENABLE_ITEM_RETURN_EVENTS=1
    export OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256="${inherited_item_return_events_binary_sha256}"
    export OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT="${inherited_item_return_events_dispatch_limit}"
    export OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT="${inherited_item_return_events_log_limit:-0}"
}

case "${1:-}" in
    Ragnarok*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver}"
        validate_observer_wrapper_profile
        enable_marker "enable-process-event-hook" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" && export OBELISK_DISABLE_PLUGINS=1
        enable_marker "allow-ptrace" && export OBELISK_DEBUG_ALLOW_PTRACE=1
        enable_marker "enable-debug-control" && export OBELISK_ENABLE_DEBUG_CONTROL=1
        enable_marker "enable-reflection-scanner" && export OBELISK_ENABLE_REFLECTION_SCANNER=1
        enable_marker "enable-native-exec-probes" && export OBELISK_ENABLE_NATIVE_EXEC_PROBES=1
        configure_chat_events
        configure_chat_route_observer
        configure_chat_reflection
        configure_inventory_reflection
        configure_structure_reflection
        configure_item_return_events
        ;;
    TheIsland*)
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver2}"
        validate_observer_wrapper_profile
        enable_marker "enable-process-event-hook" && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        enable_marker "disable-plugins" && export OBELISK_DISABLE_PLUGINS=1
        enable_marker "allow-ptrace" && export OBELISK_DEBUG_ALLOW_PTRACE=1
        enable_marker "enable-debug-control" && export OBELISK_ENABLE_DEBUG_CONTROL=1
        enable_marker "enable-reflection-scanner" && export OBELISK_ENABLE_REFLECTION_SCANNER=1
        enable_marker "enable-native-exec-probes" && export OBELISK_ENABLE_NATIVE_EXEC_PROBES=1
        configure_chat_events
        configure_chat_route_observer
        configure_chat_reflection
        configure_inventory_reflection
        configure_structure_reflection
        configure_item_return_events
        ;;
esac

exec "${wrapper_dir}/ShooterGameServer" "$@"
