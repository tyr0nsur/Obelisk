#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/check_obelisk_server_posture.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

write_proc_fixture() {
    local pid="$1"
    local maps="$2"
    shift 2

    mkdir -p "${TMP_DIR}/proc/${pid}"
    printf '%s\0' "$@" > "${TMP_DIR}/proc/${pid}/environ"
    printf '%s\n' "${maps}" > "${TMP_DIR}/proc/${pid}/maps"
}

expect_success() {
    local name="$1"
    shift
    if ! "$@" >/dev/null 2>"${TMP_DIR}/${name}.err"; then
        echo "Expected success: ${name}" >&2
        cat "${TMP_DIR}/${name}.err" >&2
        exit 1
    fi
}

expect_failure() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>"${TMP_DIR}/${name}.err"; then
        echo "Expected failure: ${name}" >&2
        exit 1
    fi
}

stable_maps="7f000000-7f001000 r-xp 00000000 00:00 0 /servidor/ark/obelisk/lib/libobelisk.so"

write_proc_fixture 101 "${stable_maps}" \
    "LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_success stable-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable
expect_success stable-posture-instance-id-alias \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance-id arkserver
expect_success stable-posture-chat-forbidden-clean \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection

write_proc_fixture 109 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_REFLECTION=1" \
    "OBELISK_CHAT_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_CHAT_REFLECTION_LOG_LIMIT=25"
expect_success chat-reflection-allowed-in-debug-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 109 --expect-stable
expect_failure chat-reflection-forbidden-for-production \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 109 --expect-stable --forbid-chat-reflection

write_proc_fixture 110 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_CHAT_REFLECTION_LOG_TEXT=1"
expect_failure chat-text-forbidden-for-production \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 110 --expect-stable --forbid-chat-reflection

write_proc_fixture 111 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_STRUCTURE_REFLECTION=1" \
    "OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=25"
expect_failure structure-reflection-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 111 --expect-stable

write_proc_fixture 112 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_INVENTORY_REFLECTION=1" \
    "OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=25"
expect_failure inventory-reflection-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 112 --expect-stable

write_proc_fixture 102 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_REFLECTION_SCANNER=1"
expect_failure scanner-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 102 --expect-stable

expect_success scanner-explicitly-allowed \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 102 --expect-stable --allow-scanner

write_proc_fixture 107 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_REFLECTION_SCANNER="
expect_failure scanner-empty-env-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 107 --expect-stable

write_proc_fixture 103 "7f000000-7f001000 r-xp 00000000 00:00 0 /usr/lib/libc.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure missing-runtime-mapping \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 103 --expect-stable

write_proc_fixture 104 "${stable_maps} (deleted)" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure deleted-runtime-mapping \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 104 --expect-stable

write_proc_fixture 105 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_NATIVE_EXEC_PROBES=1"
expect_failure native-exec-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 105 --expect-stable

write_proc_fixture 106 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_DEBUG_ALLOW_PTRACE=1"
expect_failure debug-ptrace-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 106 --expect-stable

write_proc_fixture 108 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_DEBUG_CONTROL=1"
expect_failure debug-control-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 108 --expect-stable

echo "check_obelisk_server_posture offline tests passed"
