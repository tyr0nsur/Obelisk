#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/check_obelisk_server_posture.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
TEST_OBELISK_ROOT="${TMP_DIR}/obelisk-root"
mkdir -p "${TEST_OBELISK_ROOT}/state/instances/arkserver"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-process-event-hook"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/disable-plugins"

write_proc_fixture() {
    local pid="$1"
    local maps="$2"
    shift 2

    mkdir -p "${TMP_DIR}/proc/${pid}"
    printf '%s\0' "OBELISK_ROOT=${TEST_OBELISK_ROOT}" "$@" > "${TMP_DIR}/proc/${pid}/environ"
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

stable_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"

write_proc_fixture 101 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_success stable-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
expect_success stable-posture-instance-id-alias \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance-id arkserver
expect_success stable-posture-legacy-chat-forbidden-flag-clean \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection --instance arkserver

write_proc_fixture 118 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=stable"
expect_success stable-wrapper-profile-allowed \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 118 --expect-stable --instance arkserver

write_proc_fixture 119 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug"
expect_failure observer-debug-profile-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 119 --expect-stable --instance arkserver

expect_failure missing-explicit-instance \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable
expect_failure missing-map-without-pid \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --expect-stable --instance arkserver

rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-process-event-hook"
expect_failure missing-process-event-marker-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-process-event-hook"

rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/disable-plugins"
expect_failure missing-disable-plugins-marker-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/disable-plugins"

mv "${TEST_OBELISK_ROOT}/state/instances/arkserver" "${TEST_OBELISK_ROOT}/state/instances/real-arkserver"
ln -s "${TEST_OBELISK_ROOT}/state/instances/real-arkserver" "${TEST_OBELISK_ROOT}/state/instances/arkserver"
expect_failure symlink-instance-dir-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver"
mv "${TEST_OBELISK_ROOT}/state/instances/real-arkserver" "${TEST_OBELISK_ROOT}/state/instances/arkserver"

expect_failure unsafe-instance-id-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance '../arkserver'

write_proc_fixture 114 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure missing-ld-preload-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 114 --expect-stable --instance arkserver

write_proc_fixture 115 "${stable_maps}" \
    "LD_PRELOAD=./libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure relative-ld-preload-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 115 --expect-stable --instance arkserver

write_proc_fixture 109 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_EVENTS=1" \
    "OBELISK_CHAT_EVENTS_BINARY_SHA256=abc123" \
    "OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=25"
expect_failure chat-events-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 109 --expect-stable --instance arkserver
expect_failure chat-events-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 109 --expect-stable --forbid-chat-reflection --instance arkserver

write_proc_fixture 121 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_REFLECTION=1" \
    "OBELISK_CHAT_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_CHAT_REFLECTION_LOG_LIMIT=25"
expect_failure chat-reflection-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 121 --expect-stable --instance arkserver
expect_failure chat-reflection-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 121 --expect-stable --forbid-chat-reflection --instance arkserver

write_proc_fixture 110 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_CHAT_REFLECTION_LOG_TEXT=1"
expect_failure chat-text-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 110 --expect-stable --instance arkserver

write_proc_fixture 111 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_STRUCTURE_REFLECTION=1" \
    "OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=25" \
    "OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=25"
expect_failure structure-reflection-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 111 --expect-stable --instance arkserver

write_proc_fixture 112 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_INVENTORY_REFLECTION=1" \
    "OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=abc123" \
    "OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=25" \
    "OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=25"
expect_failure inventory-reflection-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 112 --expect-stable --instance arkserver

write_proc_fixture 120 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=25"
expect_failure inventory-dispatch-limit-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 120 --expect-stable --instance arkserver

write_proc_fixture 113 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1"
expect_failure global-process-event-callbacks-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 113 --expect-stable --instance arkserver

write_proc_fixture 114 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ALLOW_CALL_PROCESS_EVENT=1"
expect_failure call-process-event-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 114 --expect-stable --instance arkserver

write_proc_fixture 115 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ALLOW_PROCESS_EVENT_BLOCKING=1"
expect_failure process-event-blocking-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 115 --expect-stable --instance arkserver

write_proc_fixture 102 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_REFLECTION_SCANNER=1"
expect_failure scanner-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 102 --expect-stable --instance arkserver

write_proc_fixture 107 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_REFLECTION_SCANNER="
expect_failure scanner-empty-env-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 107 --expect-stable --instance arkserver

write_proc_fixture 116 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_PE_TRACE_LIMIT=25"
expect_failure pe-trace-limit-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 116 --expect-stable --instance arkserver

write_proc_fixture 117 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_PE_TRACE_LIMIT=0"
expect_success pe-trace-limit-zero-allowed \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 117 --expect-stable --instance arkserver

write_proc_fixture 103 "7f000000-7f001000 r-xp 00000000 00:00 0 /usr/lib/libc.so" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure missing-runtime-mapping \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 103 --expect-stable --instance arkserver

write_proc_fixture 104 "${stable_maps} (deleted)" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure deleted-runtime-mapping \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 104 --expect-stable --instance arkserver

write_proc_fixture 105 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_NATIVE_EXEC_PROBES=1"
expect_failure native-exec-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 105 --expect-stable --instance arkserver

write_proc_fixture 106 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_DEBUG_ALLOW_PTRACE=1"
expect_failure debug-ptrace-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 106 --expect-stable --instance arkserver

write_proc_fixture 108 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_DEBUG_CONTROL=1"
expect_failure debug-control-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 108 --expect-stable --instance arkserver

for marker in \
    allow-ptrace \
    allow-observer-debug-window \
    allow-experimental-observers \
    enable-debug-control \
    enable-native-exec-probes \
    allow-global-process-event-callbacks \
    allow-call-process-event \
    allow-process-event-blocking \
    enable-chat-events \
    enable-chat-reflection \
    enable-inventory-reflection \
    enable-structure-reflection \
    enable-reflection-scanner
do
    : > "${TEST_OBELISK_ROOT}/state/instances/arkserver/${marker}"
    expect_failure "forbidden-marker-${marker}" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
    rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/${marker}"
done

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe"
expect_failure active-debug-request-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
mv "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe.done.1234"
expect_success completed-debug-request-marker-allowed-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe.done.1234"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-reflection"
expect_failure chat-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
expect_failure chat-marker-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-reflection"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"
expect_failure chat-events-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
expect_failure chat-events-marker-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"

echo "check_obelisk_server_posture offline tests passed"
