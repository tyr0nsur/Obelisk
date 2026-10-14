#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/check_obelisk_server_posture.sh [options]

Checks a running ARK/Obelisk process posture without changing server state.

Options:
  --map <name>              Map argument prefix to find. Required unless --pid is used.
  --instance <id>           Expected OBELISK_INSTANCE_ID. Required.
  --instance-id <id>        Alias for --instance.
  --pid <pid>               Check a specific process id instead of map discovery.
  --proc-root <path>        Procfs root. Default: /proc. Intended for offline tests.
  --allow-live-procfs-read  Permit reading the real /proc tree. This is not live-ops
                            authorization; use only with separate current-turn approval.
  --allow-protected-root    Permit validating OBELISK_ROOT=/servidor/ark/obelisk. This is
                            not live-ops authorization, does not allow other protected
                            roots, and does not allow protected --proc-root fixtures.
  --json                    Emit a stable non-authorizing JSON sidecar instead of text.
  --expect-stable           Require stable dev posture: ProcessEvent on, plugins off,
                            ReflectionScanner/debug control/native exec probes,
                            broad ProcessEvent tracing, and experimental observers off.
  --expect-observer-debug   Require approved passive observer-debug posture: stable
                            core on, plugins off, runtime mapped, observer-debug
                            profile/approval markers present, and at least one
                            matching experimental observer marker/env pair present.
  --forbid-chat-reflection  Compatibility flag. Chat reflection is already forbidden by
                            --expect-stable.
  -h, --help                Show this help.
EOF
}

MAP=""
INSTANCE=""
PID=""
PROC_ROOT="/proc"
EXPECT_STABLE=0
EXPECT_OBSERVER_DEBUG=0
FORBID_CHAT_REFLECTION=0
ALLOW_LIVE_PROCFS_READ=0
ALLOW_PROTECTED_ROOT=0
JSON_OUTPUT=0
SERVER_ROOT="/servidor/ark"
SUPPORTED_BINARY_SHA256="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --map)
            MAP="${2:?missing map}"
            shift 2
            ;;
        --instance|--instance-id)
            INSTANCE="${2:?missing instance}"
            shift 2
            ;;
        --pid)
            PID="${2:?missing pid}"
            shift 2
            ;;
        --proc-root)
            PROC_ROOT="${2:?missing proc root}"
            shift 2
            ;;
        --allow-live-procfs-read)
            ALLOW_LIVE_PROCFS_READ=1
            shift
            ;;
        --allow-protected-root)
            ALLOW_PROTECTED_ROOT=1
            shift
            ;;
        --json)
            JSON_OUTPUT=1
            shift
            ;;
        --expect-stable)
            EXPECT_STABLE=1
            shift
            ;;
        --expect-observer-debug)
            EXPECT_OBSERVER_DEBUG=1
            shift
            ;;
        --forbid-chat-reflection)
            FORBID_CHAT_REFLECTION=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "${EXPECT_STABLE}" == "1" && "${EXPECT_OBSERVER_DEBUG}" == "1" ]]; then
    echo "--expect-stable and --expect-observer-debug are mutually exclusive." >&2
    usage >&2
    exit 2
fi

if [[ -z "${INSTANCE}" ]]; then
    echo "--instance is required. Pass the explicit Obelisk instance id to avoid checking the wrong server." >&2
    usage >&2
    exit 2
fi

if [[ -z "${PID}" && -z "${MAP}" ]]; then
    echo "--map is required when --pid is not provided." >&2
    usage >&2
    exit 2
fi

if [[ -n "${MAP}" && ! "${MAP}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid map name '${MAP}'. Expected [A-Za-z0-9_.-]+." >&2
    exit 1
fi

is_under_path() {
    local path="$1"
    local parent="$2"

    [[ "${path}" == "${parent}" || "${path}" == "${parent}/"* ]]
}

reject_live_procfs_read_path() {
    local label="$1"
    local path="$2"
    local absolute_path
    local resolved_path

    if [[ "${ALLOW_LIVE_PROCFS_READ}" == "1" ]]; then
        return 0
    fi

    absolute_path="$(realpath -s -m "${path}")"
    if is_under_path "${absolute_path}" "/proc"; then
        echo "${label} must not read the live /proc tree without --allow-live-procfs-read: ${absolute_path}" >&2
        exit 2
    fi

    resolved_path="$(realpath -m "${path}")"
    if is_under_path "${resolved_path}" "/proc"; then
        echo "${label} must not resolve into the live /proc tree without --allow-live-procfs-read: ${path} -> ${resolved_path}" >&2
        exit 2
    fi
}

reject_protected_read_path() {
    local label="$1"
    local path="$2"
    local absolute_path
    local resolved_path

    absolute_path="$(realpath -s -m "${path}")"
    if is_under_path "${absolute_path}" "${SERVER_ROOT}"; then
        echo "${label} must not read from protected server root ${SERVER_ROOT}: ${absolute_path}" >&2
        exit 2
    fi

    resolved_path="$(realpath -m "${path}")"
    if is_under_path "${resolved_path}" "${SERVER_ROOT}"; then
        echo "${label} must not read from protected server root ${SERVER_ROOT}: ${path} -> ${resolved_path}" >&2
        exit 2
    fi
}

reject_protected_read_path "--proc-root" "${PROC_ROOT}"
reject_live_procfs_read_path "--proc-root" "${PROC_ROOT}"

cmdline_matches_map() {
    local cmdline_path="$1"
    local map="$2"
    local arg
    local -a args=()

    while IFS= read -r -d '' arg; do
        args+=("${arg}")
    done < "${cmdline_path}" || true

    [[ "${#args[@]}" -ge 2 ]] || return 1
    [[ "$(basename -- "${args[0]}")" == "ShooterGameServer" ]] || return 1
    [[ "${args[1]}" == "${map}" || "${args[1]}" == "${map}"\?* ]]
}

count_shooter_processes() {
    local proc_dir pid cmdline_path arg0 count=0

    for proc_dir in "${PROC_ROOT%/}"/*; do
        [[ -d "${proc_dir}" ]] || continue
        pid="$(basename -- "${proc_dir}")"
        [[ "${pid}" =~ ^[0-9]+$ ]] || continue
        cmdline_path="${proc_dir}/cmdline"
        [[ -r "${cmdline_path}" ]] || continue
        reject_live_procfs_read_path "proc cmdline fixture" "${cmdline_path}"
        reject_protected_read_path "proc cmdline fixture" "${cmdline_path}"
        arg0=""
        IFS= read -r -d '' arg0 < "${cmdline_path}" || true
        if [[ "$(basename -- "${arg0}")" == "ShooterGameServer" ]]; then
            count=$((count + 1))
        fi
    done

    printf '%s\n' "${count}"
}

find_shooter_pid_for_map() {
    local map="$1"
    local proc_dir pid cmdline_path

    for proc_dir in "${PROC_ROOT%/}"/*; do
        [[ -d "${proc_dir}" ]] || continue
        pid="$(basename -- "${proc_dir}")"
        [[ "${pid}" =~ ^[0-9]+$ ]] || continue
        cmdline_path="${proc_dir}/cmdline"
        [[ -r "${cmdline_path}" ]] || continue
        reject_live_procfs_read_path "proc cmdline fixture" "${cmdline_path}"
        reject_protected_read_path "proc cmdline fixture" "${cmdline_path}"
        if cmdline_matches_map "${cmdline_path}" "${map}"; then
            printf '%s\n' "${pid}"
            return 0
        fi
    done
}

shooter_process_count="$(count_shooter_processes)"
if (( shooter_process_count > 2 )); then
    echo "Found ${shooter_process_count} ShooterGameServer processes in ${PROC_ROOT}; refusing posture pass because Obelisk policy forbids more than two ARK servers at once." >&2
    exit 1
fi

if [[ -z "${PID}" ]]; then
    PID="$(find_shooter_pid_for_map "${MAP}" | head -n1 || true)"
fi

if [[ -z "${PID}" ]]; then
    echo "No ShooterGameServer process found for map prefix '${MAP}'." >&2
    exit 1
fi

if [[ ! "${INSTANCE}" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Invalid instance id '${INSTANCE}'. Expected [A-Za-z0-9_-]+." >&2
    exit 1
fi

proc_pid_dir="${PROC_ROOT%/}/${PID}"
env_file="${proc_pid_dir}/environ"
maps_file="${proc_pid_dir}/maps"
cmdline_file="${proc_pid_dir}/cmdline"

reject_live_procfs_read_path "proc pid directory" "${proc_pid_dir}"
reject_live_procfs_read_path "proc environ fixture" "${env_file}"
reject_live_procfs_read_path "proc maps fixture" "${maps_file}"
reject_protected_read_path "proc pid directory" "${proc_pid_dir}"
reject_protected_read_path "proc environ fixture" "${env_file}"
reject_protected_read_path "proc maps fixture" "${maps_file}"

if [[ ! -r "${env_file}" ]]; then
    echo "Cannot read ${env_file}." >&2
    exit 1
fi

if [[ ! -r "${maps_file}" ]]; then
    echo "Cannot read ${maps_file}." >&2
    exit 1
fi

if [[ -n "${MAP}" ]]; then
    reject_live_procfs_read_path "proc cmdline fixture" "${cmdline_file}"
    reject_protected_read_path "proc cmdline fixture" "${cmdline_file}"
    if [[ ! -r "${cmdline_file}" ]]; then
        echo "Cannot read ${cmdline_file} to verify map prefix '${MAP}'." >&2
        exit 1
    fi
    if ! cmdline_matches_map "${cmdline_file}" "${MAP}"; then
        echo "Process ${PID} cmdline does not match map prefix '${MAP}'." >&2
        exit 1
    fi
fi

env_dump="$(tr '\0' '\n' < "${env_file}" | sort)"
maps_dump="$(cat "${maps_file}")"

get_env() {
    local name="$1"
    printf '%s\n' "${env_dump}" | sed -n "s/^${name}=//p" | tail -n1
}

has_env() {
    local name="$1"
    printf '%s\n' "${env_dump}" | grep -E "^${name}=" >/dev/null
}

require_env() {
    local name="$1"
    local expected="$2"
    local actual
    actual="$(get_env "${name}")"
    if [[ "${actual}" != "${expected}" ]]; then
        echo "Expected ${name}=${expected}, got '${actual:-<unset>}'." >&2
        return 1
    fi
}

require_env_path_list_contains() {
    local name="$1"
    local expected="$2"
    local actual
    actual="$(get_env "${name}")"
    if [[ -z "${actual}" ]]; then
        echo "Expected ${name} to contain '${expected}', got '<unset>'." >&2
        return 1
    fi

    local entry
    IFS=':' read -r -a entries <<< "${actual}"
    for entry in "${entries[@]}"; do
        if [[ "${entry}" == "${expected}" ]]; then
            return 0
        fi
    done

    echo "Expected ${name} to contain '${expected}', got '${actual}'." >&2
    return 1
}

forbid_env() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if has_env "${name}"; then
        echo "Forbidden ${name} is set to '${actual}'." >&2
        return 1
    fi
}

forbid_env_value() {
    local name="$1"
    local forbidden="$2"
    local actual
    actual="$(get_env "${name}")"
    if has_env "${name}" && [[ "${actual}" == "${forbidden}" ]]; then
        echo "Forbidden ${name} is set to '${actual}'." >&2
        return 1
    fi
}

forbid_nonzero_env() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if has_env "${name}" && [[ -n "${actual}" && "${actual}" != "0" ]]; then
        echo "Forbidden ${name} is set to non-zero value '${actual}'." >&2
        return 1
    fi
}

forbid_marker() {
    local marker="$1"
    local path="${marker_dir}/${marker}"
    if [[ -e "${path}" || -L "${path}" ]]; then
        echo "Forbidden marker ${path} exists." >&2
        return 1
    fi
}

require_marker() {
    local marker="$1"
    local path="${marker_dir}/${marker}"
    if [[ ! -f "${path}" || -L "${path}" ]]; then
        echo "Expected marker ${path} to exist as a regular non-symlink file." >&2
        return 1
    fi
}

require_env_value_if_set() {
    local name="$1"
    local expected="$2"
    local actual
    actual="$(get_env "${name}")"
    if has_env "${name}" && [[ "${actual}" != "${expected}" ]]; then
        echo "Expected ${name}=${expected} when set, got '${actual}'." >&2
        return 1
    fi
}

require_env_sha256_hex() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if [[ ! "${actual}" =~ ^[0-9a-f]{64}$ ]]; then
        echo "Expected ${name} to be an explicit lowercase SHA256 hex value, got '${actual:-<unset>}'." >&2
        return 1
    fi
}

require_env_supported_sha256() {
    local name="$1"
    local actual
    require_env_sha256_hex "${name}" || return 1
    actual="$(get_env "${name}")"
    if [[ "${actual}" != "${SUPPORTED_BINARY_SHA256}" ]]; then
        echo "Expected ${name}=${SUPPORTED_BINARY_SHA256}, got '${actual}'." >&2
        return 1
    fi
}

require_env_positive_integer() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if [[ ! "${actual}" =~ ^0*[1-9][0-9]*$ ]]; then
        echo "Expected ${name} to be an explicit positive integer, got '${actual:-<unset>}'." >&2
        return 1
    fi
}

require_env_positive_integer_at_most() {
    local name="$1"
    local max="$2"
    local actual
    require_env_positive_integer "${name}" || return 1
    actual="$(get_env "${name}")"
    if (( 10#${actual} > max )); then
        echo "Expected ${name} to be at most ${max}, got '${actual}'." >&2
        return 1
    fi
}

require_env_nonnegative_integer() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if [[ ! "${actual}" =~ ^[0-9]+$ ]]; then
        echo "Expected ${name} to be an explicit non-negative integer, got '${actual:-<unset>}'." >&2
        return 1
    fi
}

require_env_path_if_set() {
    local name="$1"
    local expected="$2"
    local actual
    actual="$(get_env "${name}")"

    if ! has_env "${name}"; then
        return 0
    fi

    case "${actual}" in
        /*) ;;
        *)
            echo "Expected ${name} to be absolute when set, got '${actual}'." >&2
            return 1
            ;;
    esac

    require_no_symlink_path_escape "${name}" "${actual}" || return 1

    if [[ "${actual}" != "${expected}" ]]; then
        echo "Expected ${name}=${expected} when set, got '${actual}'." >&2
        return 1
    fi
}

reject_protected_obelisk_root() {
    local root="$1"
    local absolute_path
    local resolved_path
    local allowed_live_root

    absolute_path="$(realpath -s -m "${root}")"
    resolved_path="$(realpath -m "${root}")"
    allowed_live_root=0
    if [[ "${ALLOW_PROTECTED_ROOT}" == "1" &&
          "${absolute_path}" == "${SERVER_ROOT}/obelisk" &&
          "${resolved_path}" == "${SERVER_ROOT}/obelisk" ]]; then
        allowed_live_root=1
    fi

    if [[ "${allowed_live_root}" != "1" && "${ALLOW_PROTECTED_ROOT}" == "1" ]] &&
        { is_under_path "${absolute_path}" "${SERVER_ROOT}" || is_under_path "${resolved_path}" "${SERVER_ROOT}"; }; then
        echo "--allow-protected-root only permits OBELISK_ROOT=${SERVER_ROOT}/obelisk, got ${root} -> ${resolved_path}" >&2
        return 1
    fi

    if [[ "${allowed_live_root}" != "1" ]] && is_under_path "${absolute_path}" "${SERVER_ROOT}"; then
        echo "OBELISK_ROOT must not resolve under protected server root ${SERVER_ROOT} without --allow-protected-root: ${absolute_path}" >&2
        return 1
    fi

    if [[ "${allowed_live_root}" != "1" ]] && is_under_path "${resolved_path}" "${SERVER_ROOT}"; then
        echo "OBELISK_ROOT must not resolve under protected server root ${SERVER_ROOT} without --allow-protected-root: ${resolved_path}" >&2
        return 1
    fi
}

require_no_symlink_path_escape() {
    local label="$1"
    local path="$2"
    local absolute_path
    local resolved_path

    absolute_path="$(realpath -s -m "${path}")"
    resolved_path="$(realpath -m "${path}")"
    if [[ "${absolute_path}" != "${resolved_path}" ]]; then
        echo "${label} must not resolve through symlink path components: ${path} -> ${resolved_path}" >&2
        return 1
    fi
}

require_marker_dir() {
    if [[ ! -d "${marker_dir}" || -L "${marker_dir}" ]]; then
        echo "Expected marker directory ${marker_dir} to exist as a non-symlink directory." >&2
        return 1
    fi
}

marker_name_is_allowed_stable() {
    local marker="$1"

    case "${marker}" in
        enable-process-event-hook|disable-plugins|request-static-fname-probe.done.*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

require_stable_marker_set() {
    local path marker

    while IFS= read -r -d '' path; do
        marker="$(basename -- "${path}")"
        if ! marker_name_is_allowed_stable "${marker}"; then
            echo "Unexpected marker exists for stable posture: ${path}" >&2
            return 1
        fi
        if [[ -L "${path}" || ! -f "${path}" ]]; then
            echo "Marker must be a regular non-symlink file for stable posture: ${path}" >&2
            return 1
        fi
    done < <(find "${marker_dir}" -mindepth 1 -maxdepth 1 -print0)
}

marker_name_is_allowed_player_principal_observer() {
    local marker="$1"

    case "${marker}" in
        enable-process-event-hook|\
        disable-plugins|\
        allow-observer-debug-window|\
        allow-experimental-observers|\
        enable-player-principal-lifecycle-observer)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

require_player_principal_observer_marker_set() {
    local path marker

    while IFS= read -r -d '' path; do
        marker="$(basename -- "${path}")"
        if ! marker_name_is_allowed_player_principal_observer "${marker}"; then
            echo "Unexpected marker exists for player-principal observer posture: ${path}" >&2
            return 1
        fi
        if [[ -L "${path}" || ! -f "${path}" ]]; then
            echo "Marker must be a regular non-symlink file for player-principal observer posture: ${path}" >&2
            return 1
        fi
    done < <(find "${marker_dir}" -mindepth 1 -maxdepth 1 -print0)
}

marker_name_is_allowed_observer_debug() {
    local marker="$1"

    case "${marker}" in
        enable-process-event-hook|\
        disable-plugins|\
        allow-observer-debug-window|\
        allow-experimental-observers|\
        enable-chat-events|\
        enable-chat-reflection|\
        enable-chat-route-observer|\
        enable-inventory-reflection|\
        enable-structure-reflection|\
        enable-item-return-events|\
        enable-player-principal-lifecycle-observer)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

require_observer_debug_marker_set() {
    local path marker

    while IFS= read -r -d '' path; do
        marker="$(basename -- "${path}")"
        if ! marker_name_is_allowed_observer_debug "${marker}"; then
            echo "Unexpected marker exists for observer-debug posture: ${path}" >&2
            return 1
        fi
        if [[ -L "${path}" || ! -f "${path}" ]]; then
            echo "Marker must be a regular non-symlink file for observer-debug posture: ${path}" >&2
            return 1
        fi
    done < <(find "${marker_dir}" -mindepth 1 -maxdepth 1 -print0)
}

require_obelisk_root_layout() {
    local root="${obelisk_root%/}"
    local required_dir

    case "${root}" in
        /*) ;;
        *)
            echo "Expected OBELISK_ROOT to be an absolute path, got '${obelisk_root}'." >&2
            return 1
            ;;
    esac

    if [[ "${root}" == "/" ]]; then
        echo "Expected OBELISK_ROOT ${root} to be a real non-symlink directory and not /." >&2
        return 1
    fi
    reject_protected_obelisk_root "${root}" || return 1

    if [[ ! -d "${root}" || -L "${root}" ]]; then
        echo "Expected OBELISK_ROOT ${root} to be a real non-symlink directory and not /." >&2
        return 1
    fi
    require_no_symlink_path_escape "OBELISK_ROOT" "${root}" || return 1

    for required_dir in lib plugins config logs state state/instances; do
        if [[ ! -d "${root}/${required_dir}" || -L "${root}/${required_dir}" ]]; then
            echo "Expected Obelisk managed directory ${root}/${required_dir} to be a real non-symlink directory." >&2
            return 1
        fi
        require_no_symlink_path_escape \
            "Obelisk managed directory ${root}/${required_dir}" \
            "${root}/${required_dir}" || return 1
    done

    if [[ ! -f "${root}/lib/libobelisk.so" || -L "${root}/lib/libobelisk.so" ]]; then
        echo "Expected Obelisk runtime library ${root}/lib/libobelisk.so to be a regular non-symlink file." >&2
        return 1
    fi
    require_no_symlink_path_escape \
        "Obelisk runtime library ${root}/lib/libobelisk.so" \
        "${root}/lib/libobelisk.so" || return 1
}

require_mapped_library() {
    local library="$1"
    local line
    local mapped_path
    local map_range
    local map_perms
    local map_offset
    local map_dev
    local map_inode
    local map_suffix

    while IFS= read -r line; do
        [[ -n "${line}" ]] || continue
        mapped_path=""
        read -r map_range map_perms map_offset map_dev map_inode mapped_path map_suffix <<< "${line}"
        if [[ "${mapped_path}" == "${library}" ]]; then
            return 0
        fi
    done <<< "${maps_dump}"

    echo "Expected mapped library path '${library}' in ${maps_file}." >&2
    return 1
}

forbid_deleted_obelisk_mapping() {
    if printf '%s\n' "${maps_dump}" | grep -E 'libobelisk[^[:space:]]*[[:space:]].*\(deleted\)' >/dev/null; then
        echo "Found deleted libobelisk mapping in ${maps_file}." >&2
        return 1
    fi
}

require_approved_observer_marker_env_pair() {
    local marker="$1"
    local env_name="$2"
    local path="${marker_dir}/${marker}"
    local marker_present=0
    local env_present=0
    local actual

    if [[ -e "${path}" || -L "${path}" ]]; then
        require_marker "${marker}"
        marker_present=1
    fi

    if has_env "${env_name}"; then
        actual="$(get_env "${env_name}")"
        if [[ "${actual}" != "1" ]]; then
            echo "Expected ${env_name}=1 for observer-debug posture, got '${actual}'." >&2
            return 1
        fi
        env_present=1
    fi

    if [[ "${marker_present}" == "1" && "${env_present}" != "1" ]]; then
        echo "Expected ${env_name}=1 because marker ${path} exists." >&2
        return 1
    fi

    if [[ "${env_present}" == "1" && "${marker_present}" != "1" ]]; then
        echo "Expected marker ${path} because ${env_name}=1 is set." >&2
        return 1
    fi

    if [[ "${marker_present}" == "1" && "${env_present}" == "1" ]]; then
        approved_observer_pairs=$((approved_observer_pairs + 1))
    fi
}

forbid_player_principal_lifecycle_env() {
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
}

env_key_is_gate_or_observer_control() {
    local key="$1"

    case "${key}" in
        OBELISK_ENABLE_*|\
        OBELISK_ALLOW_*|\
        OBELISK_DEBUG_*|\
        OBELISK_PE_TRACE_LIMIT|\
        OBELISK_*_BINARY_SHA256|\
        OBELISK_*_LOG_LIMIT|\
        OBELISK_*_DISPATCH_LIMIT|\
        OBELISK_*_LIMIT|\
        OBELISK_*OBSERVER*|\
        OBELISK_*REFLECTION*|\
        OBELISK_*PROCESS_EVENT*|\
        OBELISK_*TRACE*|\
        OBELISK_*SCANNER*|\
        OBELISK_*PTRACE*|\
        OBELISK_*NATIVE_EXEC*|\
        OBELISK_*PLAYER_PRINCIPAL*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

stable_env_key_is_allowed() {
    local key="$1"

    case "${key}" in
        OBELISK_ROOT|\
        OBELISK_INSTANCE_ID|\
        OBELISK_ENABLE_PROCESS_EVENT_HOOK|\
        OBELISK_DISABLE_PLUGINS|\
        OBELISK_WRAPPER_PROFILE|\
        OBELISK_PLUGIN_DIR|\
        OBELISK_CONFIG_DIR|\
        OBELISK_LOG_DIR|\
        OBELISK_PE_TRACE_LIMIT)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

player_principal_observer_env_key_is_allowed() {
    local key="$1"

    case "${key}" in
        OBELISK_ROOT|\
        OBELISK_INSTANCE_ID|\
        OBELISK_ENABLE_PROCESS_EVENT_HOOK|\
        OBELISK_DISABLE_PLUGINS|\
        OBELISK_WRAPPER_PROFILE|\
        OBELISK_PLUGIN_DIR|\
        OBELISK_CONFIG_DIR|\
        OBELISK_LOG_DIR|\
        OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT|\
        OBELISK_PE_TRACE_LIMIT)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

observer_debug_env_key_is_allowed() {
    local key="$1"

    case "${key}" in
        OBELISK_ROOT|\
        OBELISK_INSTANCE_ID|\
        OBELISK_ENABLE_PROCESS_EVENT_HOOK|\
        OBELISK_DISABLE_PLUGINS|\
        OBELISK_WRAPPER_PROFILE|\
        OBELISK_PLUGIN_DIR|\
        OBELISK_CONFIG_DIR|\
        OBELISK_LOG_DIR|\
        OBELISK_ENABLE_CHAT_EVENTS|\
        OBELISK_CHAT_EVENTS_BINARY_SHA256|\
        OBELISK_CHAT_EVENTS_DISPATCH_LIMIT|\
        OBELISK_ENABLE_CHAT_REFLECTION|\
        OBELISK_CHAT_REFLECTION_BINARY_SHA256|\
        OBELISK_CHAT_REFLECTION_LOG_LIMIT|\
        OBELISK_CHAT_REFLECTION_LOG_TEXT|\
        OBELISK_ENABLE_CHAT_ROUTE_OBSERVER|\
        OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256|\
        OBELISK_CHAT_ROUTE_OBSERVER_LIMIT|\
        OBELISK_ENABLE_INVENTORY_REFLECTION|\
        OBELISK_INVENTORY_REFLECTION_BINARY_SHA256|\
        OBELISK_INVENTORY_REFLECTION_LOG_LIMIT|\
        OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT|\
        OBELISK_ENABLE_STRUCTURE_REFLECTION|\
        OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256|\
        OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT|\
        OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT|\
        OBELISK_ENABLE_ITEM_RETURN_EVENTS|\
        OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256|\
        OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT|\
        OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT|\
        OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT|\
        OBELISK_PE_TRACE_LIMIT)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

require_no_extra_gate_env_keys() {
    local posture="$1"
    local line key

    while IFS= read -r line; do
        [[ -n "${line}" ]] || continue
        key="${line%%=*}"
        case "${posture}" in
            stable)
                stable_env_key_is_allowed "${key}" && continue
                ;;
            player-principal-observer)
                player_principal_observer_env_key_is_allowed "${key}" && continue
                ;;
            observer-debug)
                observer_debug_env_key_is_allowed "${key}" && continue
                ;;
        esac
        if env_key_is_gate_or_observer_control "${key}"; then
            echo "Unexpected env key for ${posture} posture: ${key}" >&2
            return 1
        fi
    done <<< "${env_dump}"
}

forbid_non_player_principal_observer_env_and_markers() {
    forbid_marker enable-chat-events
    forbid_marker enable-chat-reflection
    forbid_marker enable-chat-route-observer
    forbid_marker enable-inventory-reflection
    forbid_marker enable-structure-reflection
    forbid_marker enable-item-return-events
    forbid_marker enable-inventory-action-redacted-observer

    forbid_env OBELISK_ENABLE_CHAT_EVENTS
    forbid_env OBELISK_CHAT_EVENTS_BINARY_SHA256
    forbid_env OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_CHAT_REFLECTION
    forbid_env OBELISK_CHAT_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_CHAT_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_CHAT_REFLECTION_LOG_TEXT
    forbid_env OBELISK_ENABLE_CHAT_ROUTE_OBSERVER
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
    forbid_env OBELISK_ENABLE_INVENTORY_REFLECTION
    forbid_env OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_STRUCTURE_REFLECTION
    forbid_env OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_ITEM_RETURN_EVENTS
    forbid_env OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256
    forbid_env OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT
    forbid_env OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT
}

observer_pair_active() {
    local marker="$1"
    local env_name="$2"
    local path="${marker_dir}/${marker}"

    [[ -f "${path}" && ! -L "${path}" ]] && has_env "${env_name}"
}

forbid_observer_family_env_without_marker() {
    local marker="$1"
    shift
    local path="${marker_dir}/${marker}"
    local env_name

    if [[ -e "${path}" || -L "${path}" ]]; then
        return 0
    fi

    for env_name in "$@"; do
        forbid_env "${env_name}"
    done
}

require_active_observer_env_budgets() {
    if observer_pair_active enable-chat-events OBELISK_ENABLE_CHAT_EVENTS; then
        require_env_sha256_hex OBELISK_CHAT_EVENTS_BINARY_SHA256
        require_env_positive_integer OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
    fi

    if observer_pair_active enable-chat-reflection OBELISK_ENABLE_CHAT_REFLECTION; then
        require_env_supported_sha256 OBELISK_CHAT_REFLECTION_BINARY_SHA256
        require_env_nonnegative_integer OBELISK_CHAT_REFLECTION_LOG_LIMIT
    fi

    if observer_pair_active enable-chat-route-observer OBELISK_ENABLE_CHAT_ROUTE_OBSERVER; then
        require_env_supported_sha256 OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256
        require_env_positive_integer OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
    fi

    if observer_pair_active enable-inventory-reflection OBELISK_ENABLE_INVENTORY_REFLECTION; then
        require_env_supported_sha256 OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
        require_env_nonnegative_integer OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
        require_env_nonnegative_integer OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT
    fi

    if observer_pair_active enable-structure-reflection OBELISK_ENABLE_STRUCTURE_REFLECTION; then
        require_env_supported_sha256 OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
        require_env_nonnegative_integer OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT
        require_env_nonnegative_integer OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT
    fi

    if observer_pair_active enable-item-return-events OBELISK_ENABLE_ITEM_RETURN_EVENTS; then
        require_env_sha256_hex OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256
        require_env_positive_integer OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT
        require_env_nonnegative_integer OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT
    fi
}

forbid_inactive_observer_family_env() {
    forbid_observer_family_env_without_marker \
        enable-chat-events \
        OBELISK_ENABLE_CHAT_EVENTS \
        OBELISK_CHAT_EVENTS_BINARY_SHA256 \
        OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
    forbid_observer_family_env_without_marker \
        enable-chat-reflection \
        OBELISK_ENABLE_CHAT_REFLECTION \
        OBELISK_CHAT_REFLECTION_BINARY_SHA256 \
        OBELISK_CHAT_REFLECTION_LOG_LIMIT \
        OBELISK_CHAT_REFLECTION_LOG_TEXT
    forbid_observer_family_env_without_marker \
        enable-chat-route-observer \
        OBELISK_ENABLE_CHAT_ROUTE_OBSERVER \
        OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256 \
        OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
    forbid_observer_family_env_without_marker \
        enable-inventory-reflection \
        OBELISK_ENABLE_INVENTORY_REFLECTION \
        OBELISK_INVENTORY_REFLECTION_BINARY_SHA256 \
        OBELISK_INVENTORY_REFLECTION_LOG_LIMIT \
        OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT
    forbid_observer_family_env_without_marker \
        enable-structure-reflection \
        OBELISK_ENABLE_STRUCTURE_REFLECTION \
        OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256 \
        OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT \
        OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT
    forbid_observer_family_env_without_marker \
        enable-item-return-events \
        OBELISK_ENABLE_ITEM_RETURN_EVENTS \
        OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256 \
        OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT \
        OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT
    forbid_observer_family_env_without_marker \
        enable-player-principal-lifecycle-observer \
        OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
}

obelisk_root="$(get_env OBELISK_ROOT)"
obelisk_root="${obelisk_root:-/servidor/ark/obelisk}"
marker_dir="${obelisk_root%/}/state/instances/${INSTANCE}"
posture_mode="unspecified"

if [[ "${EXPECT_STABLE}" == "1" ]]; then
    posture_mode="stable"
    expected_runtime="${obelisk_root%/}/lib/libobelisk.so"

    require_env OBELISK_INSTANCE_ID "${INSTANCE}"
    require_env OBELISK_ENABLE_PROCESS_EVENT_HOOK 1
    require_env OBELISK_DISABLE_PLUGINS 1
    require_obelisk_root_layout
    require_env_path_if_set OBELISK_PLUGIN_DIR "${obelisk_root%/}/plugins"
    require_env_path_if_set OBELISK_CONFIG_DIR "${obelisk_root%/}/config"
    require_env_path_if_set OBELISK_LOG_DIR "${obelisk_root%/}/logs"
    require_env_path_list_contains LD_PRELOAD "${expected_runtime}"
    require_mapped_library "${expected_runtime}"
    require_marker_dir
    require_marker enable-process-event-hook
    require_marker disable-plugins
    forbid_deleted_obelisk_mapping
    forbid_env OBELISK_DEBUG_ALLOW_PTRACE
    forbid_env OBELISK_ENABLE_DEBUG_CONTROL
    forbid_env OBELISK_ENABLE_NATIVE_EXEC_PROBES
    forbid_env OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS
    forbid_env OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS
    forbid_env OBELISK_ALLOW_CALL_PROCESS_EVENT
    forbid_env OBELISK_ALLOW_PROCESS_EVENT_BLOCKING
    require_env_value_if_set OBELISK_WRAPPER_PROFILE stable
    forbid_env OBELISK_ENABLE_CHAT_EVENTS
    forbid_env OBELISK_CHAT_EVENTS_BINARY_SHA256
    forbid_env OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
    forbid_nonzero_env OBELISK_PE_TRACE_LIMIT
    forbid_env OBELISK_ENABLE_CHAT_REFLECTION
    forbid_env OBELISK_CHAT_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_CHAT_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_CHAT_REFLECTION_LOG_TEXT
    forbid_env OBELISK_ENABLE_CHAT_ROUTE_OBSERVER
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
    forbid_env OBELISK_ENABLE_INVENTORY_REFLECTION
    forbid_env OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_STRUCTURE_REFLECTION
    forbid_env OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_ITEM_RETURN_EVENTS
    forbid_env OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256
    forbid_env OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT
    forbid_env OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT
    forbid_env OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING
    forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT
    forbid_env OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT

    forbid_env OBELISK_ENABLE_REFLECTION_SCANNER
    forbid_env OBELISK_REFLECTION_STATIC_FNAME_ROOTS
    forbid_env OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS
    forbid_env OBELISK_REFLECTION_LOG_FNAME_REJECTS

    forbid_marker allow-ptrace
    forbid_marker allow-observer-debug-window
    forbid_marker allow-experimental-observers
    forbid_marker enable-debug-control
    forbid_marker enable-native-exec-probes
    forbid_marker allow-global-process-event-callbacks
    forbid_marker allow-filtered-process-event-callbacks
    forbid_marker allow-call-process-event
    forbid_marker allow-process-event-blocking
    forbid_marker enable-chat-events
    forbid_marker enable-chat-reflection
    forbid_marker enable-chat-route-observer
    forbid_marker enable-inventory-reflection
    forbid_marker enable-structure-reflection
    forbid_marker enable-item-return-events
    forbid_marker enable-player-principal-lifecycle-observer
    forbid_marker enable-inventory-action-redacted-observer
    forbid_marker enable-reflection-scanner
    forbid_marker request-static-fname-probe
    require_stable_marker_set
    require_no_extra_gate_env_keys stable
fi

if [[ "${EXPECT_OBSERVER_DEBUG}" == "1" ]]; then
    posture_mode="observer-debug"
    expected_runtime="${obelisk_root%/}/lib/libobelisk.so"

    require_env OBELISK_INSTANCE_ID "${INSTANCE}"
    require_env OBELISK_ENABLE_PROCESS_EVENT_HOOK 1
    require_env OBELISK_DISABLE_PLUGINS 1
    require_env OBELISK_WRAPPER_PROFILE observer-debug
    require_obelisk_root_layout
    require_env_path_if_set OBELISK_PLUGIN_DIR "${obelisk_root%/}/plugins"
    require_env_path_if_set OBELISK_CONFIG_DIR "${obelisk_root%/}/config"
    require_env_path_if_set OBELISK_LOG_DIR "${obelisk_root%/}/logs"
    require_env_path_list_contains LD_PRELOAD "${expected_runtime}"
    require_mapped_library "${expected_runtime}"
    require_marker_dir
    require_marker enable-process-event-hook
    require_marker disable-plugins
    require_marker allow-observer-debug-window
    require_marker allow-experimental-observers
    require_observer_debug_marker_set
    forbid_deleted_obelisk_mapping
    forbid_env OBELISK_DEBUG_ALLOW_PTRACE
    forbid_env OBELISK_ENABLE_DEBUG_CONTROL
    forbid_env OBELISK_ENABLE_NATIVE_EXEC_PROBES
    forbid_env OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS
    forbid_env OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS
    forbid_env OBELISK_ALLOW_CALL_PROCESS_EVENT
    forbid_env OBELISK_ALLOW_PROCESS_EVENT_BLOCKING
    forbid_nonzero_env OBELISK_PE_TRACE_LIMIT
    forbid_env OBELISK_ENABLE_REFLECTION_SCANNER
    forbid_env OBELISK_REFLECTION_STATIC_FNAME_ROOTS
    forbid_env OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS
    forbid_env OBELISK_REFLECTION_LOG_FNAME_REJECTS
    forbid_marker allow-ptrace
    forbid_marker enable-debug-control
    forbid_marker enable-native-exec-probes
    forbid_marker allow-global-process-event-callbacks
    forbid_marker allow-filtered-process-event-callbacks
    forbid_marker allow-call-process-event
    forbid_marker allow-process-event-blocking
    forbid_marker enable-reflection-scanner
    forbid_marker request-static-fname-probe
    forbid_marker enable-inventory-action-redacted-observer
    forbid_env OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT
    forbid_env OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT

    approved_observer_pairs=0
    require_approved_observer_marker_env_pair enable-chat-events OBELISK_ENABLE_CHAT_EVENTS
    require_approved_observer_marker_env_pair enable-chat-reflection OBELISK_ENABLE_CHAT_REFLECTION
    require_approved_observer_marker_env_pair enable-chat-route-observer OBELISK_ENABLE_CHAT_ROUTE_OBSERVER
    require_approved_observer_marker_env_pair enable-inventory-reflection OBELISK_ENABLE_INVENTORY_REFLECTION
    require_approved_observer_marker_env_pair enable-structure-reflection OBELISK_ENABLE_STRUCTURE_REFLECTION
    require_approved_observer_marker_env_pair enable-item-return-events OBELISK_ENABLE_ITEM_RETURN_EVENTS
    require_approved_observer_marker_env_pair enable-player-principal-lifecycle-observer OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER
    forbid_inactive_observer_family_env
    require_active_observer_env_budgets
    require_no_extra_gate_env_keys observer-debug

    if (( approved_observer_pairs == 0 )); then
        echo "Expected at least one approved experimental observer marker/env pair for observer-debug posture." >&2
        exit 1
    fi

    if [[ -f "${marker_dir}/enable-player-principal-lifecycle-observer" ]] && has_env OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER; then
        posture_mode="player-principal-lifecycle-observer-debug"
        require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 "${SUPPORTED_BINARY_SHA256}"
        require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT 10
        require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT 0
        require_env_value_if_set OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES 1
        if has_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS; then
            require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES 1
            require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS 1
        require_env_positive_integer_at_most \
            OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT \
            10000
        else
            forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
        fi
        if has_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING; then
            require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES 1
            require_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING 1
            require_env_positive_integer_at_most \
                OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT \
                10000
        else
            forbid_env OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT
        fi
        forbid_non_player_principal_observer_env_and_markers
        require_player_principal_observer_marker_set
        require_no_extra_gate_env_keys player-principal-observer
    else
        forbid_player_principal_lifecycle_env
    fi
fi

if [[ "${FORBID_CHAT_REFLECTION}" == "1" ]]; then
    forbid_env OBELISK_ENABLE_CHAT_EVENTS
    forbid_env OBELISK_CHAT_EVENTS_BINARY_SHA256
    forbid_env OBELISK_CHAT_EVENTS_DISPATCH_LIMIT
    forbid_env OBELISK_ENABLE_CHAT_REFLECTION
    forbid_env OBELISK_CHAT_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_CHAT_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_CHAT_REFLECTION_LOG_TEXT
    forbid_env OBELISK_ENABLE_CHAT_ROUTE_OBSERVER
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256
    forbid_env OBELISK_CHAT_ROUTE_OBSERVER_LIMIT
    forbid_marker enable-chat-events
    forbid_marker enable-chat-reflection
    forbid_marker enable-chat-route-observer
fi

if [[ "${JSON_OUTPUT}" == "1" ]]; then
    export OBELISK_POSTURE_PID="${PID}"
    export OBELISK_POSTURE_MAP="${MAP}"
    export OBELISK_POSTURE_INSTANCE="${INSTANCE}"
    export OBELISK_POSTURE_MODE="${posture_mode}"
    export OBELISK_POSTURE_PROC_ROOT="${PROC_ROOT}"
    export OBELISK_POSTURE_ROOT="${obelisk_root}"
    export OBELISK_POSTURE_MARKER_DIR="${marker_dir}"
    export OBELISK_POSTURE_LIVE_PROCFS_READ_ACK="${ALLOW_LIVE_PROCFS_READ}"
    export OBELISK_POSTURE_PROTECTED_ROOT_ACK="${ALLOW_PROTECTED_ROOT}"
    python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

payload = {
    "schema": "obelisk.server-posture.v1",
    "status": "posture_passed_no_runtime_approval_or_evidence",
    "posture_check_passed": True,
    "ready": False,
    "ready_scope": "posture_observation_only",
    "sdk_readiness_claim_allowed": False,
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
    "runtime_capture_authorized": False,
    "current_turn_authorized": False,
    "current_turn_operator_approval_required": True,
    "posture_counts_as_current_turn_approval": False,
    "posture_counts_as_approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "public_sdk_ready": False,
    "stable_claim_allowed": False,
    "authorization_source": "none_posture_sidecar_only",
    "approved_runtime_evidence_source": "none_posture_sidecar_only",
    "mode": os.environ["OBELISK_POSTURE_MODE"],
    "pid": os.environ["OBELISK_POSTURE_PID"],
    "instance": os.environ["OBELISK_POSTURE_INSTANCE"],
    "map": os.environ["OBELISK_POSTURE_MAP"] or None,
    "proc_root": os.environ["OBELISK_POSTURE_PROC_ROOT"],
    "obelisk_root": os.environ["OBELISK_POSTURE_ROOT"],
    "marker_dir": os.environ["OBELISK_POSTURE_MARKER_DIR"],
    "live_procfs_read_acknowledged": os.environ["OBELISK_POSTURE_LIVE_PROCFS_READ_ACK"] == "1",
    "protected_root_validation_acknowledged": os.environ["OBELISK_POSTURE_PROTECTED_ROOT_ACK"] == "1",
    "live_read_acknowledgement_counts_as_authorization": False,
    "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "non_claim": "posture check only; not runtime approval, not approved runtime evidence, and not permission to touch servers",
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY
else
    echo "pid=${PID}"
    printf '%s\n' "${env_dump}" | grep -E '^(OBELISK_|LD_PRELOAD=|LD_LIBRARY_PATH=)' || true
fi
