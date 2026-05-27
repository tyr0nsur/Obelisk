#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/check_obelisk_server_posture.sh [options]

Checks a running ARK/Obelisk process posture without changing server state.

Options:
  --map <name>              Map argument prefix to find. Default: Ragnarok.
  --instance <id>           Expected OBELISK_INSTANCE_ID. Default: arkserver.
  --expect-stable           Require stable dev posture: ProcessEvent on, plugins off,
                            ReflectionScanner/static sampling/native exec probes off.
  --allow-scanner           Allow OBELISK_ENABLE_REFLECTION_SCANNER=1.
  -h, --help                Show this help.
EOF
}

MAP="Ragnarok"
INSTANCE="arkserver"
EXPECT_STABLE=0
ALLOW_SCANNER=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --map)
            MAP="${2:?missing map}"
            shift 2
            ;;
        --instance)
            INSTANCE="${2:?missing instance}"
            shift 2
            ;;
        --expect-stable)
            EXPECT_STABLE=1
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

pid="$(pgrep -f "^./ShooterGameServer ${MAP}" | head -n1 || true)"
if [[ -z "${pid}" ]]; then
    echo "No ShooterGameServer process found for map prefix '${MAP}'." >&2
    exit 1
fi

env_dump="$(tr '\0' '\n' < "/proc/${pid}/environ" | sort)"

get_env() {
    local name="$1"
    printf '%s\n' "${env_dump}" | sed -n "s/^${name}=//p" | tail -n1
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

forbid_env() {
    local name="$1"
    local actual
    actual="$(get_env "${name}")"
    if [[ -n "${actual}" ]]; then
        echo "Forbidden ${name} is set to '${actual}'." >&2
        return 1
    fi
}

echo "pid=${pid}"
printf '%s\n' "${env_dump}" | grep -E '^(OBELISK_|LD_PRELOAD=|LD_LIBRARY_PATH=)' || true

if [[ "${EXPECT_STABLE}" == "1" ]]; then
    require_env OBELISK_INSTANCE_ID "${INSTANCE}"
    require_env OBELISK_ENABLE_PROCESS_EVENT_HOOK 1
    require_env OBELISK_DISABLE_PLUGINS 1
    forbid_env OBELISK_ENABLE_NATIVE_EXEC_PROBES

    if [[ "${ALLOW_SCANNER}" != "1" ]]; then
        forbid_env OBELISK_ENABLE_REFLECTION_SCANNER
        forbid_env OBELISK_REFLECTION_STATIC_FNAME_ROOTS
        forbid_env OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS
        forbid_env OBELISK_REFLECTION_LOG_FNAME_REJECTS
    fi
fi
