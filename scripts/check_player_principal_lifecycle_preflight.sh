#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: scripts/check_player_principal_lifecycle_preflight.sh [options]

Read-only preflight for a future player-principal lifecycle evidence window. It does not
start, stop, restart, or modify ARK/Obelisk state.

Options:
  --instance <id>                 Obelisk instance id. Required.
  --map <name>                    Map prefix for running-process posture checks.
  --target-map <name>             Target map to bind into --json sidecar without procfs checks.
  --mode <stable|observer-window> Marker posture to verify. Default: stable.
  --obelisk-root <path>           Obelisk root. Default: /servidor/ark/obelisk.
  --installed-wrapper <path>      Installed LinuxGSM wrapper path.
  --server-binary <path>          ShooterGameServer binary path.
  --expected-binary-sha256 <sha>  Required ShooterGameServer SHA256.
  --env-file <path>               Effective key=value env snapshot for observer-window mode.
  --run-id <id>                   Runtime window run id to bind into --json sidecar.
  --window-manifest <path>        Expected copied window manifest path for --json sidecar.
  --copied-log <path>             Expected copied Obelisk log path for --json sidecar.
  --evidence-dir <path>           Expected copied evidence directory for --json sidecar.
  --proc-root <path>              Procfs root for posture checks. Default: /proc.
  --allow-stopped                 Accept no running process after marker/SHA checks.
  --offline-only                  Reject live server paths and running-process checks.
  --json                          Emit a stable JSON sidecar instead of text.
  -h, --help                      Show this help.
EOF
}

INSTANCE=""
MAP=""
TARGET_MAP=""
MODE="stable"
OBELISK_ROOT="/servidor/ark/obelisk"
INSTALLED_WRAPPER="/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh"
SERVER_BINARY="/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer"
EXPECTED_BINARY_SHA256=""
ENV_FILE=""
RUN_ID=""
WINDOW_MANIFEST=""
COPIED_LOG=""
EVIDENCE_DIR=""
PROC_ROOT="/proc"
ALLOW_STOPPED=0
OFFLINE_ONLY=0
JSON_OUTPUT=0
SERVER_ROOT="/servidor/ark"
APPROVED_OFFLINE_ROOT="/servidor/ark/workspace-offline"

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
        --target-map)
            TARGET_MAP="${2:?missing target map}"
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
        --env-file)
            ENV_FILE="${2:?missing env file}"
            shift 2
            ;;
        --run-id)
            RUN_ID="${2:?missing run id}"
            shift 2
            ;;
        --window-manifest)
            WINDOW_MANIFEST="${2:?missing window manifest path}"
            shift 2
            ;;
        --copied-log)
            COPIED_LOG="${2:?missing copied log path}"
            shift 2
            ;;
        --evidence-dir|--copied-evidence-dir)
            EVIDENCE_DIR="${2:?missing evidence directory path}"
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
        --offline-only)
            OFFLINE_ONLY=1
            shift
            ;;
        --json)
            JSON_OUTPUT=1
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
if [[ -n "${MAP}" && ! "${MAP}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid map name: ${MAP}" >&2
    exit 1
fi
if [[ -n "${TARGET_MAP}" && ! "${TARGET_MAP}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid target map name: ${TARGET_MAP}" >&2
    exit 1
fi
if [[ -n "${MAP}" && -n "${TARGET_MAP}" && "${MAP}" != "${TARGET_MAP}" ]]; then
    echo "--map and --target-map must match when both are supplied." >&2
    exit 1
fi
if [[ -n "${RUN_ID}" && ! "${RUN_ID}" =~ ^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$ ]]; then
    echo "Invalid run id: ${RUN_ID}" >&2
    exit 1
fi
EFFECTIVE_TARGET_MAP="${TARGET_MAP:-${MAP}}"

binding_count=0
for binding_value in "${RUN_ID}" "${TARGET_MAP}" "${WINDOW_MANIFEST}" "${COPIED_LOG}" "${EVIDENCE_DIR}"; do
    if [[ -n "${binding_value}" ]]; then
        binding_count=$((binding_count + 1))
    fi
done
binding_complete=0
if [[ "${binding_count}" -eq 5 ]]; then
    binding_complete=1
elif [[ "${binding_count}" -eq 4 && -n "${MAP}" && -z "${TARGET_MAP}" ]]; then
    binding_complete=1
fi
if [[ "${binding_count}" -ne 0 && "${binding_complete}" -ne 1 ]]; then
    echo "Evidence binding requires --run-id, --target-map or matching --map, --window-manifest, --copied-log, and --evidence-dir together." >&2
    exit 2
fi
if [[ "${binding_complete}" -eq 1 ]]; then
    case "${EVIDENCE_DIR}" in
        */live-validation-logs/"${RUN_ID}")
            ;;
        *)
            echo "--evidence-dir must end with live-validation-logs/${RUN_ID}." >&2
            exit 1
            ;;
    esac
    if [[ "${COPIED_LOG}" != "${EVIDENCE_DIR%/}/Obelisk.log" ]]; then
        echo "--copied-log must equal --evidence-dir/Obelisk.log." >&2
        exit 1
    fi
    if [[ "${WINDOW_MANIFEST}" != "${EVIDENCE_DIR%/}/window-manifest.env" ]]; then
        echo "--window-manifest must equal --evidence-dir/window-manifest.env." >&2
        exit 1
    fi
fi
[[ "${MODE}" == "stable" || "${MODE}" == "observer-window" ]] || {
    echo "--mode must be stable or observer-window." >&2
    exit 2
}
[[ -n "${EXPECTED_BINARY_SHA256}" ]] || { echo "--expected-binary-sha256 is required." >&2; exit 2; }
[[ "${EXPECTED_BINARY_SHA256}" =~ ^[0-9a-f]{64}$ ]] || {
    echo "--expected-binary-sha256 must be lowercase SHA256 hex." >&2
    exit 2
}

resolved_existing_path() {
    local path="$1"
    if command -v realpath >/dev/null 2>&1; then
        realpath -e -- "${path}"
    else
        readlink -f -- "${path}"
    fi
}

reject_protected_live_path() {
    local label="$1"
    local path="$2"
    local resolved
    case "${path}" in
        "${SERVER_ROOT}"|"${SERVER_ROOT}/"*)
            case "${path}" in
                "${APPROVED_OFFLINE_ROOT}"|"${APPROVED_OFFLINE_ROOT}/"*)
                    ;;
                *)
                    echo "${label} must be an offline copy, not a live server path: ${path}" >&2
                    exit 1
                    ;;
            esac
            ;;
    esac
    resolved="$(resolved_existing_path "${path}" 2>/dev/null || printf '%s' "${path}")"
    case "${resolved}" in
        "${SERVER_ROOT}"|"${SERVER_ROOT}/"*)
            case "${resolved}" in
                "${APPROVED_OFFLINE_ROOT}"|"${APPROVED_OFFLINE_ROOT}/"*)
                    ;;
                *)
                    echo "${label} must be an offline copy, not a live server path: ${path}" >&2
                    exit 1
                    ;;
            esac
            ;;
    esac
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

marker_is_allowed() {
    local marker="$1"
    local allowed
    shift

    for allowed in "$@"; do
        if [[ "${marker}" == "${allowed}" ]]; then
            return 0
        fi
    done
    return 1
}

require_exact_marker_set() {
    while IFS= read -r -d '' path; do
        local marker
        marker="$(basename -- "${path}")"
        if ! marker_is_allowed "${marker}" "$@"; then
            echo "Unexpected marker exists for player-principal preflight: ${path}" >&2
            exit 1
        fi
        if [[ -L "${path}" || ! -f "${path}" ]]; then
            echo "Marker must be a regular non-symlink file: ${path}" >&2
            exit 1
        fi
    done < <(find "${MARKER_DIR}" -mindepth 1 -maxdepth 1 -print0)
}

ENV_KEYS=()
ENV_VALUES=()

load_env_file() {
    local line key value existing line_number=0

    require_regular_file "Env file" "${ENV_FILE}"
    while IFS= read -r line || [[ -n "${line}" ]]; do
        line_number=$((line_number + 1))
        line="${line%$'\r'}"
        [[ -z "${line}" || "${line}" == \#* ]] && continue
        if [[ "${line}" == export\ * ]]; then
            echo "Env file must use bare KEY=VALUE lines, not export syntax: ${ENV_FILE}:${line_number}" >&2
            exit 1
        fi
        if [[ "${line}" != *=* ]]; then
            echo "Env file line must be KEY=VALUE: ${ENV_FILE}:${line_number}" >&2
            exit 1
        fi
        key="${line%%=*}"
        value="${line#*=}"
        if [[ ! "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            echo "Env file key is unsafe: ${ENV_FILE}:${line_number}: ${key}" >&2
            exit 1
        fi
        for existing in "${ENV_KEYS[@]}"; do
            if [[ "${existing}" == "${key}" ]]; then
                echo "Env file contains duplicate key: ${key}" >&2
                exit 1
            fi
        done
        ENV_KEYS+=("${key}")
        ENV_VALUES+=("${value}")
    done < "${ENV_FILE}"
}

env_value() {
    local key="$1"
    local index

    for index in "${!ENV_KEYS[@]}"; do
        if [[ "${ENV_KEYS[${index}]}" == "${key}" ]]; then
            printf '%s' "${ENV_VALUES[${index}]}"
            return 0
        fi
    done
    return 1
}

require_env_value() {
    local key="$1"
    local expected="$2"
    local actual

    if ! actual="$(env_value "${key}")"; then
        echo "Required env is missing from ${ENV_FILE}: ${key}" >&2
        exit 1
    fi
    if [[ "${actual}" != "${expected}" ]]; then
        echo "Env ${key} must be '${expected}' for player-principal preflight; got '${actual}'." >&2
        exit 1
    fi
}

forbid_env_key() {
    local key="$1"

    if env_value "${key}" >/dev/null; then
        echo "Forbidden env exists for player-principal preflight: ${key}" >&2
        exit 1
    fi
}

env_key_is_allowed_window_posture() {
    local key="$1"

    case "${key}" in
        OBELISK_INSTANCE_ID|\
        OBELISK_ENABLE_PROCESS_EVENT_HOOK|\
        OBELISK_DISABLE_PLUGINS|\
        OBELISK_WRAPPER_PROFILE|\
        OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT|\
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT|\
        OBELISK_PE_TRACE_LIMIT)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
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

require_no_extra_gate_env_keys() {
    local key

    for key in "${ENV_KEYS[@]}"; do
        if env_key_is_allowed_window_posture "${key}"; then
            continue
        fi
        if env_key_is_gate_or_observer_control "${key}"; then
            echo "Unexpected env key for exact player-principal preflight: ${key}" >&2
            exit 1
        fi
    done
}

require_observer_window_env() {
    [[ -n "${ENV_FILE}" ]] || {
        echo "--mode observer-window requires --env-file with the exact effective window env posture." >&2
        exit 2
    }

    load_env_file
    require_env_value OBELISK_INSTANCE_ID "${INSTANCE}"
    require_env_value OBELISK_ENABLE_PROCESS_EVENT_HOOK 1
    require_env_value OBELISK_DISABLE_PLUGINS 1
    require_env_value OBELISK_WRAPPER_PROFILE observer-debug
    require_env_value OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER 1
    require_env_value OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 "${EXPECTED_BINARY_SHA256}"
    require_env_value OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT 10
    require_env_value OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT 0
    require_env_value OBELISK_PE_TRACE_LIMIT 0

    for key in \
        LD_PRELOAD \
        LD_LIBRARY_PATH \
        OBELISK_ROOT \
        OBELISK_PLUGIN_DIR \
        OBELISK_CONFIG_DIR \
        OBELISK_LOG_DIR \
        OBELISK_STATE_DIR \
        OBELISK_DEBUG_ALLOW_PTRACE \
        OBELISK_ENABLE_DEBUG_CONTROL \
        OBELISK_ENABLE_REFLECTION_SCANNER \
        OBELISK_ENABLE_NATIVE_EXEC_PROBES \
        OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS \
        OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS \
        OBELISK_ALLOW_CALL_PROCESS_EVENT \
        OBELISK_ALLOW_PROCESS_EVENT_BLOCKING \
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
        OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT
    do
        forbid_env_key "${key}"
    done

    require_no_extra_gate_env_keys
}

find_shooter_pid_for_map() {
    local map="$1"
    local proc_dir pid cmdline

    if [[ "${PROC_ROOT}" == "/proc" ]]; then
        PGREP_BIN="${PGREP_BIN:-pgrep}"
        "${PGREP_BIN}" -f "(^|/)ShooterGameServer ${map}" | head -n1 || true
        return 0
    fi

    for proc_dir in "${PROC_ROOT%/}"/*; do
        [[ -d "${proc_dir}" ]] || continue
        pid="$(basename -- "${proc_dir}")"
        [[ "${pid}" =~ ^[0-9]+$ ]] || continue
        [[ -r "${proc_dir}/cmdline" ]] || continue
        cmdline="$(tr '\0' ' ' < "${proc_dir}/cmdline")"
        if [[ "${cmdline}" =~ (^|/)ShooterGameServer[[:space:]]+${map} ]]; then
            printf '%s\n' "${pid}"
            return 0
        fi
    done
}

if [[ "${OFFLINE_ONLY}" == "1" ]]; then
    reject_protected_live_path "Obelisk root" "${OBELISK_ROOT}"
    reject_protected_live_path "Installed wrapper" "${INSTALLED_WRAPPER}"
    reject_protected_live_path "Server binary" "${SERVER_BINARY}"
    if [[ -n "${ENV_FILE}" ]]; then
        reject_protected_live_path "Env file" "${ENV_FILE}"
    fi
    if [[ -n "${WINDOW_MANIFEST}" ]]; then
        reject_protected_live_path "Window manifest" "${WINDOW_MANIFEST}"
    fi
    if [[ -n "${COPIED_LOG}" ]]; then
        reject_protected_live_path "Copied log" "${COPIED_LOG}"
    fi
    if [[ -n "${EVIDENCE_DIR}" ]]; then
        reject_protected_live_path "Evidence directory" "${EVIDENCE_DIR}"
    fi
    if [[ -n "${MAP}" ]]; then
        echo "--offline-only rejects --map because it would inspect live process posture." >&2
        exit 1
    fi
fi

require_regular_file "Server binary" "${SERVER_BINARY}"
actual_sha="$(sha256sum "${SERVER_BINARY}" | awk '{print $1}')"
if [[ "${actual_sha}" != "${EXPECTED_BINARY_SHA256}" ]]; then
    echo "ShooterGameServer SHA256 mismatch: expected ${EXPECTED_BINARY_SHA256}, got ${actual_sha}." >&2
    exit 1
fi

"${SCRIPT_DIR}/check_linuxgsm_wrapper_drift.sh" --installed "${INSTALLED_WRAPPER}" >/dev/null

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
    request-static-fname-probe \
    enable-chat-events \
    enable-chat-reflection \
    enable-chat-route-observer \
    enable-inventory-reflection \
    enable-inventory-action-redacted-observer \
    enable-structure-reflection \
    enable-item-return-events
do
    forbid_marker "${marker}"
done

if [[ "${MODE}" == "stable" ]]; then
    forbid_marker allow-observer-debug-window
    forbid_marker allow-experimental-observers
    forbid_marker enable-player-principal-lifecycle-observer
    require_exact_marker_set \
        enable-process-event-hook \
        disable-plugins
else
    require_marker allow-observer-debug-window
    require_marker allow-experimental-observers
    require_marker enable-player-principal-lifecycle-observer
    require_exact_marker_set \
        enable-process-event-hook \
        disable-plugins \
        allow-observer-debug-window \
        allow-experimental-observers \
        enable-player-principal-lifecycle-observer
    require_observer_window_env
fi

if [[ -n "${MAP}" ]]; then
    shooter_pid="$(find_shooter_pid_for_map "${MAP}")"
    if [[ -n "${shooter_pid}" ]]; then
        if [[ "${MODE}" != "stable" ]]; then
            echo "Running observer-window posture is not checked by this preflight; use it before launch or after rollback." >&2
            exit 1
        fi
        "${SCRIPT_DIR}/check_obelisk_server_posture.sh" \
            --expect-stable \
            --pid "${shooter_pid}" \
            --instance "${INSTANCE}" \
            --proc-root "${PROC_ROOT}" >/dev/null
    elif [[ "${ALLOW_STOPPED}" != "1" ]]; then
        echo "No running ShooterGameServer found for ${MAP}; pass --allow-stopped if this is expected." >&2
        exit 1
    fi
fi

wrapper_sha="$(sha256sum "${INSTALLED_WRAPPER}" | awk '{print $1}')"
env_sha=""
if [[ -n "${ENV_FILE}" ]]; then
    env_sha="$(sha256sum "${ENV_FILE}" | awk '{print $1}')"
fi

if [[ "${JSON_OUTPUT}" == "1" ]]; then
    export OBELISK_PREFLIGHT_MODE="${MODE}"
    export OBELISK_PREFLIGHT_INSTANCE="${INSTANCE}"
    export OBELISK_PREFLIGHT_MAP="${EFFECTIVE_TARGET_MAP}"
    export OBELISK_PREFLIGHT_BINARY="${SERVER_BINARY}"
    export OBELISK_PREFLIGHT_BINARY_SHA="${actual_sha}"
    export OBELISK_PREFLIGHT_ROOT="${OBELISK_ROOT}"
    export OBELISK_PREFLIGHT_WRAPPER="${INSTALLED_WRAPPER}"
    export OBELISK_PREFLIGHT_WRAPPER_SHA="${wrapper_sha}"
    export OBELISK_PREFLIGHT_ENV="${ENV_FILE}"
    export OBELISK_PREFLIGHT_ENV_SHA="${env_sha}"
    export OBELISK_PREFLIGHT_RUN_ID="${RUN_ID}"
    export OBELISK_PREFLIGHT_WINDOW_MANIFEST="${WINDOW_MANIFEST}"
    export OBELISK_PREFLIGHT_COPIED_LOG="${COPIED_LOG}"
    export OBELISK_PREFLIGHT_EVIDENCE_DIR="${EVIDENCE_DIR}"
    export OBELISK_PREFLIGHT_MARKER_DIR="${MARKER_DIR}"
    export OBELISK_PREFLIGHT_OFFLINE_ONLY="${OFFLINE_ONLY}"
    export OBELISK_PREFLIGHT_ALLOW_STOPPED="${ALLOW_STOPPED}"
    python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

def optional_file(path: str, sha256: str) -> dict | None:
    if not path:
        return None
    return {"path": path, "sha256": sha256}

payload = {
    "schema": "obelisk.player-principal-lifecycle-preflight.v1",
    "ready": True,
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
    "request_pack_counts_as_approved_runtime_evidence": False,
    "preflight_counts_as_approved_runtime_evidence": False,
    "window_manifest_counts_as_approved_runtime_evidence": False,
    "completed_receipt_counts_as_approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "public_abi_ready": False,
    "promotion_ready": False,
    "public_header_allowed": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "route_ready": False,
    "observer_env_counts_as_approved_runtime_evidence": False,
    "operator_request_counts_as_approved_runtime_evidence": False,
    "copied_log_metadata_counts_as_approved_runtime_evidence": False,
    "bundle_output_counts_as_approved_runtime_evidence": False,
    "sdk_accounting_counts_as_completed_surface": False,
    "p0_accounting_counts_as_promoted_surface": False,
    "authorization_source": "none_preflight_sidecar_only",
    "approved_runtime_evidence_source": "none_preflight_sidecar_only",
    "mode": os.environ["OBELISK_PREFLIGHT_MODE"],
    "run_id": os.environ["OBELISK_PREFLIGHT_RUN_ID"] or None,
    "instance": os.environ["OBELISK_PREFLIGHT_INSTANCE"],
    "map": os.environ["OBELISK_PREFLIGHT_MAP"] or None,
    "target": {
        "instance": os.environ["OBELISK_PREFLIGHT_INSTANCE"],
        "map": os.environ["OBELISK_PREFLIGHT_MAP"] or None,
    },
    "window_manifest_path": os.environ["OBELISK_PREFLIGHT_WINDOW_MANIFEST"] or None,
    "copied_log_path": os.environ["OBELISK_PREFLIGHT_COPIED_LOG"] or None,
    "copied_evidence_dir": os.environ["OBELISK_PREFLIGHT_EVIDENCE_DIR"] or None,
    "server_binary": {
        "path": os.environ["OBELISK_PREFLIGHT_BINARY"],
        "sha256": os.environ["OBELISK_PREFLIGHT_BINARY_SHA"],
    },
    "obelisk_root": os.environ["OBELISK_PREFLIGHT_ROOT"],
    "installed_wrapper": {
        "path": os.environ["OBELISK_PREFLIGHT_WRAPPER"],
        "sha256": os.environ["OBELISK_PREFLIGHT_WRAPPER_SHA"],
    },
    "env_file": optional_file(
        os.environ["OBELISK_PREFLIGHT_ENV"],
        os.environ["OBELISK_PREFLIGHT_ENV_SHA"],
    ),
    "marker_dir": os.environ["OBELISK_PREFLIGHT_MARKER_DIR"],
    "offline_only": os.environ["OBELISK_PREFLIGHT_OFFLINE_ONLY"] == "1",
    "allow_stopped": os.environ["OBELISK_PREFLIGHT_ALLOW_STOPPED"] == "1",
    "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "posture_check": "accepted",
    "non_claim": "preflight only; not runtime approval, not approved runtime evidence, and not permission to touch servers",
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY
else
    printf 'player_principal_lifecycle_preflight=ok mode=%s instance=%s binary_sha256=%s\n' \
        "${MODE}" "${INSTANCE}" "${actual_sha}"
fi
