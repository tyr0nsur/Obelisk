#!/usr/bin/env bash
set -euo pipefail

wrapper_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"

require_no_symlink_path_escape() {
    local label="$1"
    local path="$2"
    local absolute_path
    local resolved_path

    absolute_path="$(realpath -s -m "${path}")"
    resolved_path="$(realpath -m "${path}")"
    if [[ "${absolute_path}" != "${resolved_path}" ]]; then
        echo "${label} must not resolve through symlink path components: ${path} -> ${resolved_path}" >&2
        exit 1
    fi
}

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
    require_no_symlink_path_escape "OBELISK_ROOT" "${OBELISK_ROOT}"

    local required_dir
    for required_dir in lib plugins config logs state state/instances; do
        if [[ -L "${OBELISK_ROOT}/${required_dir}" || ! -d "${OBELISK_ROOT}/${required_dir}" ]]; then
            echo "Obelisk runtime directory must be real and non-symlink: ${OBELISK_ROOT}/${required_dir}" >&2
            exit 1
        fi
        require_no_symlink_path_escape \
            "Obelisk runtime directory ${OBELISK_ROOT}/${required_dir}" \
            "${OBELISK_ROOT}/${required_dir}"
    done

    if [[ -L "${OBELISK_ROOT}/lib/libobelisk.so" || ! -f "${OBELISK_ROOT}/lib/libobelisk.so" ]]; then
        echo "Obelisk runtime library must be a regular non-symlink file: ${OBELISK_ROOT}/lib/libobelisk.so" >&2
        exit 1
    fi
    require_no_symlink_path_escape \
        "Obelisk runtime library ${OBELISK_ROOT}/lib/libobelisk.so" \
        "${OBELISK_ROOT}/lib/libobelisk.so"

    if [[ -L "${wrapper_dir}/ShooterGameServer" || ! -f "${wrapper_dir}/ShooterGameServer" ]]; then
        echo "ShooterGameServer must be a regular non-symlink file beside the Obelisk wrapper: ${wrapper_dir}/ShooterGameServer" >&2
        exit 1
    fi
    require_no_symlink_path_escape \
        "ShooterGameServer ${wrapper_dir}/ShooterGameServer" \
        "${wrapper_dir}/ShooterGameServer"
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
inherited_player_principal_lifecycle_binary_sha256="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256:-}"
inherited_player_principal_lifecycle_log_limit="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT:-}"
inherited_player_principal_lifecycle_dispatch_limit="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT:-}"
inherited_player_principal_lifecycle_diagnostic_candidates="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES:-}"
inherited_player_principal_lifecycle_function_fname_near_miss_diagnostics="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS:-}"
inherited_player_principal_lifecycle_function_fname_near_miss_scan_limit="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT:-}"
inherited_player_principal_lifecycle_route_sampling="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING:-}"
inherited_player_principal_lifecycle_route_sample_limit="${OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT:-}"
inherited_inventory_action_redacted_observer_binary_sha256="${OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256:-}"
inherited_inventory_action_redacted_observer_log_limit="${OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT:-}"
inherited_inventory_action_redacted_observer_dispatch_limit="${OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT:-}"

declare -a inherited_stable_forbidden_env_names=()
declare -a inherited_player_principal_lifecycle_env_names=()

record_inherited_stable_forbidden_env() {
    local name="$1"
    if [[ "${!name+x}" == "x" ]]; then
        inherited_stable_forbidden_env_names+=("${name}")
    fi
}

record_inherited_player_principal_lifecycle_env() {
    local name="$1"
    if [[ "${!name+x}" == "x" ]]; then
        inherited_player_principal_lifecycle_env_names+=("${name}")
    fi
}

for inherited_stable_forbidden_env_name in \
    OBELISK_DEBUG_ALLOW_PTRACE \
    OBELISK_ENABLE_DEBUG_CONTROL \
    OBELISK_ENABLE_REFLECTION_SCANNER \
    OBELISK_REFLECTION_STATIC_FNAME_ROOTS \
    OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS \
    OBELISK_REFLECTION_LOG_FNAME_REJECTS \
    OBELISK_ENABLE_NATIVE_EXEC_PROBES \
    OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS \
    OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS \
    OBELISK_ALLOW_CALL_PROCESS_EVENT \
    OBELISK_ALLOW_PROCESS_EVENT_BLOCKING \
    OBELISK_PE_TRACE_LIMIT \
    OBELISK_ENABLE_CHAT_EVENTS \
    OBELISK_CHAT_EVENTS_BINARY_SHA256 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT \
    OBELISK_ENABLE_CHAT_REFLECTION \
    OBELISK_CHAT_REFLECTION_BINARY_SHA256 \
    OBELISK_CHAT_REFLECTION_LOG_LIMIT \
    OBELISK_CHAT_REFLECTION_LOG_TEXT \
    OBELISK_ENABLE_CHAT_ROUTE_OBSERVER \
    OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256 \
    OBELISK_CHAT_ROUTE_OBSERVER_LIMIT \
    OBELISK_ENABLE_INVENTORY_REFLECTION \
    OBELISK_INVENTORY_REFLECTION_BINARY_SHA256 \
    OBELISK_INVENTORY_REFLECTION_LOG_LIMIT \
    OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT \
    OBELISK_ENABLE_STRUCTURE_REFLECTION \
    OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256 \
    OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT \
    OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT \
    OBELISK_ENABLE_ITEM_RETURN_EVENTS \
    OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256 \
    OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT \
    OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT \
    OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT \
    OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER \
    OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256 \
    OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT \
    OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT
do
    record_inherited_stable_forbidden_env "${inherited_stable_forbidden_env_name}"
done
unset inherited_stable_forbidden_env_name

for inherited_player_principal_lifecycle_env_name in \
    OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT
do
    record_inherited_player_principal_lifecycle_env "${inherited_player_principal_lifecycle_env_name}"
done
unset inherited_player_principal_lifecycle_env_name

unset OBELISK_ENABLE_PROCESS_EVENT_HOOK
unset OBELISK_DISABLE_PLUGINS
unset OBELISK_DEBUG_ALLOW_PTRACE
unset OBELISK_ENABLE_DEBUG_CONTROL
unset OBELISK_ENABLE_REFLECTION_SCANNER
unset OBELISK_REFLECTION_STATIC_FNAME_ROOTS
unset OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS
unset OBELISK_REFLECTION_LOG_FNAME_REJECTS
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
unset OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING
unset OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT
unset OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER
unset OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256
unset OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT
unset OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT

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

validate_instance_marker_scope() {
    local instance="${OBELISK_INSTANCE_ID:-}"
    local instance_dir

    if [[ -z "${instance}" ]]; then
        return 0
    fi
    if [[ ! "${instance}" =~ ^[A-Za-z0-9_-]+$ ]]; then
        echo "OBELISK_INSTANCE_ID must be a safe marker-scope token [A-Za-z0-9_-]+: ${instance}" >&2
        exit 1
    fi

    instance_dir="${OBELISK_ROOT}/state/instances/${instance}"
    if [[ -L "${instance_dir}" || ( -e "${instance_dir}" && ! -d "${instance_dir}" ) ]]; then
        echo "Obelisk instance marker directory must be a real non-symlink directory when present: ${instance_dir}" >&2
        exit 1
    fi
    if [[ -d "${instance_dir}" ]]; then
        require_no_symlink_path_escape \
            "Obelisk instance marker directory ${instance_dir}" \
            "${instance_dir}"
    fi
}

validate_scoped_observer_debug_marker_entries() {
    local marker
    local found_marker=0

    for marker in \
        enable-chat-events \
        enable-chat-reflection \
        enable-chat-route-observer \
        enable-inventory-reflection \
        enable-structure-reflection \
        enable-item-return-events \
        enable-player-principal-lifecycle-observer \
        enable-inventory-action-redacted-observer
    do
        if marker_entry_exists "${marker}"; then
            if ! enable_marker "${marker}"; then
                echo "Experimental observer marker ${marker} must be a regular non-symlink file for ${OBELISK_INSTANCE_ID}." >&2
                exit 1
            fi
            found_marker=1
        fi
    done

    if [[ "${found_marker}" != "1" ]]; then
        echo "OBELISK_WRAPPER_PROFILE=observer-debug requires a scoped experimental observer marker for ${OBELISK_INSTANCE_ID}; unset the profile before stable starts." >&2
        exit 1
    fi
}

reject_observer_debug_escape_markers() {
    local marker

    for marker in \
        allow-ptrace \
        enable-debug-control \
        enable-reflection-scanner \
        enable-native-exec-probes \
        allow-global-process-event-callbacks \
        allow-filtered-process-event-callbacks \
        allow-call-process-event \
        allow-process-event-blocking \
        request-static-fname-probe
    do
        if marker_entry_exists "${marker}"; then
            echo "OBELISK_WRAPPER_PROFILE=observer-debug requires exact observer markers only; incompatible debug marker ${marker} is present for ${OBELISK_INSTANCE_ID}." >&2
            exit 1
        fi
    done
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

require_exact_integer() {
    local name="$1"
    local value="$2"
    local expected="$3"

    if [[ "${value}" != "${expected}" ]]; then
        echo "${name} must be exactly ${expected} for observer-debug player principal lifecycle evidence." >&2
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
            if ((${#inherited_stable_forbidden_env_names[@]} > 0)); then
                echo "Stale observer/debug environment is present for stable wrapper launch: ${inherited_stable_forbidden_env_names[*]}. Unset observer/debug env before a stable start." >&2
                exit 1
            fi

            local marker
            for marker in \
                allow-ptrace \
                allow-observer-debug-window \
                allow-experimental-observers \
                enable-debug-control \
                enable-reflection-scanner \
                enable-native-exec-probes \
                allow-global-process-event-callbacks \
                allow-filtered-process-event-callbacks \
                allow-call-process-event \
                allow-process-event-blocking \
                request-static-fname-probe \
                enable-chat-events \
                enable-chat-reflection \
                enable-chat-route-observer \
                enable-inventory-reflection \
                enable-structure-reflection \
                enable-item-return-events \
                enable-player-principal-lifecycle-observer \
                enable-inventory-action-redacted-observer
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
            if ! enable_marker "allow-experimental-observers"; then
                echo "OBELISK_WRAPPER_PROFILE=observer-debug requires allow-experimental-observers marker for ${OBELISK_INSTANCE_ID}." >&2
                exit 1
            fi
            reject_observer_debug_escape_markers
            validate_scoped_observer_debug_marker_entries
            if marker_entry_exists "enable-inventory-action-redacted-observer"; then
                echo "enable-inventory-action-redacted-observer is not implemented; refusing observer-debug launch until its marker/env/SHA/dispatch-limit-0 gate is promoted." >&2
                exit 1
            fi
            ;;
        *)
            echo "Unknown OBELISK_WRAPPER_PROFILE '${profile}'. Expected stable or observer-debug." >&2
            exit 1
            ;;
    esac
}

validate_player_principal_lifecycle_window_exclusive() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0

    marker_entry_exists "enable-player-principal-lifecycle-observer" || return 0
    enable_marker "enable-player-principal-lifecycle-observer" || {
        echo "enable-player-principal-lifecycle-observer marker must be a regular non-symlink file for player principal lifecycle observer windows." >&2
        exit 1
    }
    enable_marker "allow-experimental-observers" || {
        echo "allow-experimental-observers marker is required for player principal lifecycle observer windows." >&2
        exit 1
    }

    local marker
    for marker in \
        enable-chat-events \
        enable-chat-reflection \
        enable-chat-route-observer \
        enable-inventory-reflection \
        enable-structure-reflection \
        enable-item-return-events \
        enable-inventory-action-redacted-observer \
        allow-ptrace \
        enable-debug-control \
        enable-reflection-scanner \
        enable-native-exec-probes \
        allow-global-process-event-callbacks \
        allow-filtered-process-event-callbacks \
        allow-call-process-event \
        allow-process-event-blocking
    do
        if marker_entry_exists "${marker}"; then
            echo "Player principal lifecycle observer window must be exact; incompatible marker ${marker} is also present for ${OBELISK_INSTANCE_ID}." >&2
            exit 1
        fi
    done
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

    require_supported_sha256 "OBELISK_CHAT_REFLECTION_BINARY_SHA256" "${inherited_chat_reflection_binary_sha256}"
    require_nonnegative_integer "OBELISK_CHAT_REFLECTION_LOG_LIMIT" "${inherited_chat_reflection_log_limit}"

    export OBELISK_ENABLE_CHAT_REFLECTION=1
    export OBELISK_CHAT_REFLECTION_BINARY_SHA256="${inherited_chat_reflection_binary_sha256}"
    export OBELISK_CHAT_REFLECTION_LOG_LIMIT="${inherited_chat_reflection_log_limit}"
    if [[ -n "${inherited_chat_reflection_log_text}" ]]; then
        export OBELISK_CHAT_REFLECTION_LOG_TEXT="${inherited_chat_reflection_log_text}"
    fi
}

configure_structure_reflection() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-structure-reflection" || return 0

    require_supported_sha256 "OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256" "${inherited_structure_reflection_binary_sha256}"
    require_nonnegative_integer "OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT" "${inherited_structure_reflection_log_limit}"
    require_nonnegative_integer "OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT" "${inherited_structure_reflection_dispatch_limit}"

    export OBELISK_ENABLE_STRUCTURE_REFLECTION=1
    export OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256="${inherited_structure_reflection_binary_sha256}"
    export OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT="${inherited_structure_reflection_log_limit}"
    export OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT="${inherited_structure_reflection_dispatch_limit}"
}

configure_inventory_reflection() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0
    enable_marker "allow-observer-debug-window" || return 0
    enable_marker "allow-experimental-observers" || return 0
    enable_marker "enable-inventory-reflection" || return 0

    require_supported_sha256 "OBELISK_INVENTORY_REFLECTION_BINARY_SHA256" "${inherited_inventory_reflection_binary_sha256}"
    require_nonnegative_integer "OBELISK_INVENTORY_REFLECTION_LOG_LIMIT" "${inherited_inventory_reflection_log_limit}"
    require_nonnegative_integer "OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT" "${inherited_inventory_reflection_dispatch_limit}"

    export OBELISK_ENABLE_INVENTORY_REFLECTION=1
    export OBELISK_INVENTORY_REFLECTION_BINARY_SHA256="${inherited_inventory_reflection_binary_sha256}"
    export OBELISK_INVENTORY_REFLECTION_LOG_LIMIT="${inherited_inventory_reflection_log_limit}"
    export OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT="${inherited_inventory_reflection_dispatch_limit}"
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

configure_player_principal_lifecycle_observer() {
    [[ "${OBELISK_WRAPPER_PROFILE:-stable}" == "observer-debug" ]] || return 0

    if ! marker_entry_exists "enable-player-principal-lifecycle-observer"; then
        if ((${#inherited_player_principal_lifecycle_env_names[@]} > 0)); then
            echo "Player principal lifecycle observer env requires enable-player-principal-lifecycle-observer marker for ${OBELISK_INSTANCE_ID}: ${inherited_player_principal_lifecycle_env_names[*]}." >&2
            exit 1
        fi
        return 0
    fi

    enable_marker "allow-observer-debug-window" || {
        echo "allow-observer-debug-window marker is required for player principal lifecycle observer windows." >&2
        exit 1
    }
    enable_marker "allow-experimental-observers" || {
        echo "allow-experimental-observers marker is required for player principal lifecycle observer windows." >&2
        exit 1
    }
    enable_marker "enable-player-principal-lifecycle-observer" || {
        echo "enable-player-principal-lifecycle-observer marker must be a regular non-symlink file for player principal lifecycle observer windows." >&2
        exit 1
    }
    enable_marker "enable-process-event-hook" || {
        echo "enable-process-event-hook marker is required for player principal lifecycle observer windows." >&2
        exit 1
    }
    enable_marker "disable-plugins" || {
        echo "disable-plugins marker is required for player principal lifecycle observer windows." >&2
        exit 1
    }

    require_supported_sha256 "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256" "${inherited_player_principal_lifecycle_binary_sha256}"
    require_exact_integer "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT" "${inherited_player_principal_lifecycle_log_limit}" 10
    if [[ "${inherited_player_principal_lifecycle_dispatch_limit}" != "0" ]]; then
        echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT must be 0 for observer-debug player principal lifecycle evidence." >&2
        exit 1
    fi
    if [[ -n "${inherited_player_principal_lifecycle_diagnostic_candidates}" && "${inherited_player_principal_lifecycle_diagnostic_candidates}" != "1" ]]; then
        echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES must be 1 when set for observer-debug player principal lifecycle diagnostics." >&2
        exit 1
    fi
    if [[ -n "${inherited_player_principal_lifecycle_function_fname_near_miss_diagnostics}" ]]; then
        if [[ "${inherited_player_principal_lifecycle_function_fname_near_miss_diagnostics}" != "1" ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS must be 1 when set for observer-debug player principal lifecycle diagnostics." >&2
            exit 1
        fi
        if [[ "${inherited_player_principal_lifecycle_diagnostic_candidates}" != "1" ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS requires OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1." >&2
            exit 1
        fi
        if [[ ! "${inherited_player_principal_lifecycle_function_fname_near_miss_scan_limit}" =~ ^[1-9][0-9]*$ ||
              "${inherited_player_principal_lifecycle_function_fname_near_miss_scan_limit}" -gt 10000 ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT must be 1..10000 when function-FName near-miss diagnostics are enabled." >&2
            exit 1
        fi
    elif [[ -n "${inherited_player_principal_lifecycle_function_fname_near_miss_scan_limit}" ]]; then
        echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT requires OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1." >&2
        exit 1
    fi
    if [[ -n "${inherited_player_principal_lifecycle_route_sampling}" ]]; then
        if [[ "${inherited_player_principal_lifecycle_route_sampling}" != "1" ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING must be 1 when set for observer-debug player principal lifecycle diagnostics." >&2
            exit 1
        fi
        if [[ "${inherited_player_principal_lifecycle_diagnostic_candidates}" != "1" ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING requires OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1." >&2
            exit 1
        fi
        if [[ ! "${inherited_player_principal_lifecycle_route_sample_limit}" =~ ^[1-9][0-9]*$ ||
              "${inherited_player_principal_lifecycle_route_sample_limit}" -gt 10000 ]]; then
            echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT must be 1..10000 when route sampling is enabled." >&2
            exit 1
        fi
    elif [[ -n "${inherited_player_principal_lifecycle_route_sample_limit}" ]]; then
        echo "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT requires OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1." >&2
        exit 1
    fi

    export OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
    export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256="${inherited_player_principal_lifecycle_binary_sha256}"
    export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT="${inherited_player_principal_lifecycle_log_limit}"
    export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
    if [[ "${inherited_player_principal_lifecycle_diagnostic_candidates}" == "1" ]]; then
        export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1
    fi
    if [[ "${inherited_player_principal_lifecycle_function_fname_near_miss_diagnostics}" == "1" ]]; then
        export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1
        export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT="${inherited_player_principal_lifecycle_function_fname_near_miss_scan_limit}"
    fi
    if [[ "${inherited_player_principal_lifecycle_route_sampling}" == "1" ]]; then
        export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1
        export OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT="${inherited_player_principal_lifecycle_route_sample_limit}"
    fi
}

matched_supported_map=0

case "${1:-}" in
    Ragnarok*)
        matched_supported_map=1
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver}"
        validate_instance_marker_scope
        validate_observer_wrapper_profile
        validate_player_principal_lifecycle_window_exclusive
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
        configure_player_principal_lifecycle_observer
        ;;
    TheIsland*)
        matched_supported_map=1
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver2}"
        validate_instance_marker_scope
        validate_observer_wrapper_profile
        validate_player_principal_lifecycle_window_exclusive
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
        configure_player_principal_lifecycle_observer
        ;;
    Gen2*|Genesis2*)
        matched_supported_map=1
        export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver3}"
        validate_instance_marker_scope
        validate_observer_wrapper_profile
        validate_player_principal_lifecycle_window_exclusive
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
        configure_player_principal_lifecycle_observer
        ;;
esac

if [[ "${matched_supported_map}" != "1" ]]; then
    validate_instance_marker_scope
    validate_observer_wrapper_profile
    validate_player_principal_lifecycle_window_exclusive
    if [[ "${OBELISK_WRAPPER_PROFILE:-stable}" != "stable" ]]; then
        echo "OBELISK_WRAPPER_PROFILE=${OBELISK_WRAPPER_PROFILE} requires a supported map prefix for scoped observer-debug launch." >&2
        exit 1
    fi
fi

exec "${wrapper_dir}/ShooterGameServer" "$@"
