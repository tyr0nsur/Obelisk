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
export OBELISK_LOG_DIR="${OBELISK_ROOT}/logs/isolated-debug"
export OBELISK_INSTANCE_ID="${OBELISK_INSTANCE_ID:-arkserver-obelisk-debug}"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so${LD_PRELOAD:+:${LD_PRELOAD}}"

export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_PE_TRACE_LIMIT="${OBELISK_PE_TRACE_LIMIT:-0}"
# Ptrace/debug-control/scanner gates are runtime-side env+marker checks.
# Set OBELISK_DEBUG_ALLOW_PTRACE=1 only for an approved isolated run with the matching
# allow-ptrace instance marker.

unset OBELISK_ENABLE_NATIVE_EXEC_PROBES

# Set OBELISK_ENABLE_REFLECTION_SCANNER=1 only with enable-reflection-scanner marker.

exec "${wrapper_dir}/ShooterGameServer" "$@"
