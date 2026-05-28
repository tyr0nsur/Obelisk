#!/usr/bin/env bash
set -euo pipefail

export OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
export OBELISK_PLUGIN_DIR="${OBELISK_PLUGIN_DIR:-${OBELISK_ROOT}/plugins}"
export OBELISK_CONFIG_DIR="${OBELISK_CONFIG_DIR:-${OBELISK_ROOT}/config}"
export OBELISK_LOG_DIR="${OBELISK_LOG_DIR:-${OBELISK_ROOT}/logs/isolated-debug}"
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

exec ./ShooterGameServer "$@"
