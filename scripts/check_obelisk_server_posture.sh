#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/check_obelisk_server_posture.sh [options]

Checks a running ARK/Obelisk process posture without changing server state.

Options:
  --map <name>              Map argument prefix to find. Default: Ragnarok.
  --instance <id>           Expected OBELISK_INSTANCE_ID. Default: arkserver.
  --instance-id <id>        Alias for --instance.
  --pid <pid>               Check a specific process id instead of using pgrep.
  --proc-root <path>        Procfs root. Default: /proc. Intended for offline tests.
  --expect-stable           Require stable dev posture: ProcessEvent on, plugins off,
                            ReflectionScanner/debug control/native exec probes and
                            structure reflection off.
  --forbid-chat-reflection  Also require chat reflection and chat text logging to be off.
                            Use this for production/performance posture checks.
  --allow-scanner           Allow OBELISK_ENABLE_REFLECTION_SCANNER=1.
  -h, --help                Show this help.
EOF
}

MAP="Ragnarok"
INSTANCE="arkserver"
PID=""
PROC_ROOT="/proc"
EXPECT_STABLE=0
FORBID_CHAT_REFLECTION=0
ALLOW_SCANNER=0

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
        --expect-stable)
            EXPECT_STABLE=1
            shift
            ;;
        --forbid-chat-reflection)
            FORBID_CHAT_REFLECTION=1
            shift
            ;;
        --allow-scanner)
            ALLOW_SCANNER=1
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

if [[ -z "${PID}" ]]; then
    PID="$(pgrep -f "^./ShooterGameServer ${MAP}" | head -n1 || true)"
fi

if [[ -z "${PID}" ]]; then
    echo "No ShooterGameServer process found for map prefix '${MAP}'." >&2
    exit 1
fi

proc_pid_dir="${PROC_ROOT%/}/${PID}"
env_file="${proc_pid_dir}/environ"
maps_file="${proc_pid_dir}/maps"

if [[ ! -r "${env_file}" ]]; then
    echo "Cannot read ${env_file}." >&2
    exit 1
fi

if [[ ! -r "${maps_file}" ]]; then
    echo "Cannot read ${maps_file}." >&2
    exit 1
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

require_mapped_library() {
    local library="$1"
    if ! printf '%s\n' "${maps_dump}" | grep -F -- "${library}" >/dev/null; then
        echo "Expected mapped library matching '${library}' in ${maps_file}." >&2
        return 1
    fi
}

forbid_deleted_obelisk_mapping() {
    if printf '%s\n' "${maps_dump}" | grep -E 'libobelisk[^[:space:]]*[[:space:]].*\(deleted\)' >/dev/null; then
        echo "Found deleted libobelisk mapping in ${maps_file}." >&2
        return 1
    fi
}

echo "pid=${PID}"
printf '%s\n' "${env_dump}" | grep -E '^(OBELISK_|LD_PRELOAD=|LD_LIBRARY_PATH=)' || true

if [[ "${EXPECT_STABLE}" == "1" ]]; then
    obelisk_root="$(get_env OBELISK_ROOT)"
    obelisk_root="${obelisk_root:-/servidor/ark/obelisk}"
    expected_runtime="${obelisk_root%/}/lib/libobelisk.so"

    require_env OBELISK_INSTANCE_ID "${INSTANCE}"
    require_env OBELISK_ENABLE_PROCESS_EVENT_HOOK 1
    require_env OBELISK_DISABLE_PLUGINS 1
    require_env_path_list_contains LD_PRELOAD "${expected_runtime}"
    require_mapped_library "${expected_runtime}"
    forbid_deleted_obelisk_mapping
    forbid_env OBELISK_DEBUG_ALLOW_PTRACE
    forbid_env OBELISK_ENABLE_DEBUG_CONTROL
    forbid_env OBELISK_ENABLE_NATIVE_EXEC_PROBES
    forbid_env OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS
    forbid_env OBELISK_ENABLE_INVENTORY_REFLECTION
    forbid_env OBELISK_INVENTORY_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_INVENTORY_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_ENABLE_STRUCTURE_REFLECTION
    forbid_env OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT

    if [[ "${ALLOW_SCANNER}" != "1" ]]; then
        forbid_env OBELISK_ENABLE_REFLECTION_SCANNER
        forbid_env OBELISK_REFLECTION_STATIC_FNAME_ROOTS
        forbid_env OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS
        forbid_env OBELISK_REFLECTION_LOG_FNAME_REJECTS
    fi
fi

if [[ "${FORBID_CHAT_REFLECTION}" == "1" ]]; then
    forbid_env OBELISK_ENABLE_CHAT_REFLECTION
    forbid_env OBELISK_CHAT_REFLECTION_BINARY_SHA256
    forbid_env OBELISK_CHAT_REFLECTION_LOG_LIMIT
    forbid_env OBELISK_CHAT_REFLECTION_LOG_TEXT
fi
