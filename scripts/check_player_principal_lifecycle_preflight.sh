#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/check_player_principal_lifecycle_preflight.sh [options]

Read-only preflight for a future player-principal lifecycle evidence window. It does not
start, stop, restart, or modify ARK/Obelisk state.

Options:
  --instance <id>                 Obelisk instance id. Required.
  --map <name>                    Map prefix for running-process posture checks.
  --mode <stable|observer-window> Marker posture to verify. Default: stable.
  --obelisk-root <path>           Obelisk root. Default: /servidor/ark/obelisk.
  --installed-wrapper <path>      Installed LinuxGSM wrapper path.
  --server-binary <path>          ShooterGameServer binary path.
  --expected-binary-sha256 <sha>  Required ShooterGameServer SHA256.
  --proc-root <path>              Procfs root for posture checks. Default: /proc.
  --allow-stopped                 Accept no running process after marker/SHA checks.
  -h, --help                      Show this help.
EOF
}

INSTANCE=""
MAP=""
MODE="stable"
OBELISK_ROOT="/servidor/ark/obelisk"
INSTALLED_WRAPPER="/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh"
SERVER_BINARY="/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"
EXPECTED_BINARY_SHA256=""
PROC_ROOT="/proc"
ALLOW_STOPPED=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --instance|--instance-id)
            INSTANCE="${2:?missing instance}"
            shift 2
            ;;
        --map)
            MAP="${2:?missing map}"
            shift 2
            ;;
        --mode)
            MODE="${2:?missing mode}"
            shift 2
            ;;
        --obelisk-root)
            OBELISK_ROOT="${2:?missing obelisk root}"
            shift 2
            ;;
        --installed-wrapper)
            INSTALLED_WRAPPER="${2:?missing installed wrapper}"
            shift 2
            ;;
        --server-binary)
            SERVER_BINARY="${2:?missing server binary}"
            shift 2
            ;;
        --expected-binary-sha256)
            EXPECTED_BINARY_SHA256="${2:?missing expected SHA256}"
            shift 2
            ;;
        --proc-root)
            PROC_ROOT="${2:?missing proc root}"
            shift 2
            ;;
        --allow-stopped)
            ALLOW_STOPPED=1
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

[[ -n "${INSTANCE}" ]] || { echo "--instance is required." >&2; exit 2; }
[[ "${INSTANCE}" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "Invalid instance id: ${INSTANCE}" >&2; exit 1; }
[[ "${MODE}" == "stable" || "${MODE}" == "observer-window" ]] || {
    echo "--mode must be stable or observer-window." >&2
    exit 2
}
[[ -n "${EXPECTED_BINARY_SHA256}" ]] || { echo "--expected-binary-sha256 is required." >&2; exit 2; }
[[ "${EXPECTED_BINARY_SHA256}" =~ ^[0-9a-f]{64}$ ]] || {
    echo "--expected-binary-sha256 must be lowercase SHA256 hex." >&2
    exit 2
}

require_regular_file() {
    local label="$1"
    local path="$2"
    if [[ -L "${path}" || ! -f "${path}" ]]; then
        echo "${label} must be a regular non-symlink file: ${path}" >&2
        exit 1
    fi
}

require_marker_dir() {
    if [[ -L "${MARKER_DIR}" || ! -d "${MARKER_DIR}" ]]; then
        echo "Marker directory must be a real non-symlink directory: ${MARKER_DIR}" >&2
        exit 1
    fi
}

require_marker() {
    local marker="$1"
    local path="${MARKER_DIR}/${marker}"
    if [[ -L "${path}" || ! -f "${path}" ]]; then
        echo "Required marker is missing or symlinked: ${path}" >&2
        exit 1
    fi
}

forbid_marker() {
    local marker="$1"
    local path="${MARKER_DIR}/${marker}"
    if [[ -e "${path}" || -L "${path}" ]]; then
        echo "Forbidden marker exists for player-principal preflight: ${path}" >&2
        exit 1
    fi
}

require_regular_file "Server binary" "${SERVER_BINARY}"
actual_sha="$(sha256sum "${SERVER_BINARY}" | awk '{print $1}')"
if [[ "${actual_sha}" != "${EXPECTED_BINARY_SHA256}" ]]; then
    echo "ShooterGameServer SHA256 mismatch: expected ${EXPECTED_BINARY_SHA256}, got ${actual_sha}." >&2
    exit 1
fi

scripts/check_linuxgsm_wrapper_drift.sh --installed "${INSTALLED_WRAPPER}" >/dev/null

MARKER_DIR="${OBELISK_ROOT%/}/state/instances/${INSTANCE}"
require_marker_dir
require_marker enable-process-event-hook
require_marker disable-plugins

for marker in \
    allow-ptrace \
    enable-debug-control \
    enable-reflection-scanner \
    enable-native-exec-probes \
    allow-global-process-event-callbacks \
    allow-filtered-process-event-callbacks \
    allow-call-process-event \
    allow-process-event-blocking \
    enable-chat-events \
    enable-chat-reflection \
    enable-chat-route-observer \
    enable-inventory-reflection \
    enable-structure-reflection \
    enable-item-return-events
do
    forbid_marker "${marker}"
done

if [[ "${MODE}" == "stable" ]]; then
    forbid_marker allow-observer-debug-window
    forbid_marker allow-experimental-observers
    forbid_marker enable-player-principal-lifecycle-observer
else
    require_marker allow-observer-debug-window
    require_marker allow-experimental-observers
    require_marker enable-player-principal-lifecycle-observer
fi

if [[ -n "${MAP}" ]]; then
    if pgrep -f "(^|/)ShooterGameServer ${MAP}" >/dev/null; then
        if [[ "${MODE}" != "stable" ]]; then
            echo "Running observer-window posture is not checked by this preflight; use it before launch or after rollback." >&2
            exit 1
        fi
        scripts/check_obelisk_server_posture.sh \
            --expect-stable \
            --map "${MAP}" \
            --instance "${INSTANCE}" \
            --proc-root "${PROC_ROOT}" >/dev/null
    elif [[ "${ALLOW_STOPPED}" != "1" ]]; then
        echo "No running ShooterGameServer found for ${MAP}; pass --allow-stopped if this is expected." >&2
        exit 1
    fi
fi

printf 'player_principal_lifecycle_preflight=ok mode=%s instance=%s binary_sha256=%s\n' \
    "${MODE}" "${INSTANCE}" "${actual_sha}"
