#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT="${REPO_ROOT}/scripts/obelisk_supervisor_snapshot.sh"
LOOP="${REPO_ROOT}/scripts/obelisk_supervisor_loop.sh"
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

write_obelisk_fixture() {
    local root="$1"

    mkdir -p "${root}/logs/arkserver2" "${root}/state/instances/arkserver2"
    : > "${root}/state/instances/arkserver2/enable-chat-reflection"
    cat > "${root}/logs/arkserver2/Obelisk.log" <<'EOF'
[2026-05-27 01:00:00.000] [warning] Experimental chat reflection enabled for ShooterGameServer SHA256 abc123.
[2026-05-27 01:00:01.000] [info] Reflected chat ProcessEvent #1 function=ServerSendChatMessage fname_index=2697 params=0x123 fields=2
[2026-05-27 01:00:01.001] [info] Reflected chat ServerSendChatMessage send_mode=4 send_mode_name=Unknown send_mode_known=false
[2026-05-27 01:00:01.002] [info] Reflected chat field ChatMessage offset=0x0 size=16 has_range=true
[2026-05-27 01:00:01.003] [info] Reflected chat rejected #1 fname_index=2697 function=0x456 reason=bad_parms_size
[2026-05-27 01:00:01.004] [info] Reflected chat ProcessEvent #2 function=ClientServerChatMessage fname_index=1984 params=0x789 fields=3 metadata_only=true
[2026-05-27 01:00:01.005] [info] Reflected chat ProcessEvent #3 function=ClientChatMessage fname_index=1865 params=0xabc fields=1 metadata_only=true
[2026-05-27 01:00:01.006] [info] Reflected chat ProcessEvent #4 function=ClientServerChatDirectMessage fname_index=1983 params=0xdef fields=3 metadata_only=true
EOF
}

run_snapshot() {
    local root="$1"
    local out="$2"
    local pid="$3"

    OBELISK_ROOT="${root}" \
    OBELISK_SUPERVISOR_OUT="${out}" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_PID="${pid}" \
    "${SNAPSHOT}"
}

run_loop_once() {
    local root="$1"
    local out="$2"
    local pid="$3"

    OBELISK_ROOT="${root}" \
    OBELISK_SUPERVISOR_OUT="${out}" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_PID="${pid}" \
    "${LOOP}" --interval 1 --count 1
}

assert_file_contains() {
    local file="$1"
    local pattern="$2"
    if ! grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

assert_file_not_contains() {
    local file="$1"
    local pattern="$2"
    if grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} not to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

stable_maps="7f000000-7f001000 r-xp 00000000 00:00 0 /servidor/ark/obelisk/lib/libobelisk.so"

stable_root="${TMP_DIR}/stable-root"
stable_out="${TMP_DIR}/stable-out"
write_obelisk_fixture "${stable_root}"
write_proc_fixture 4242 "${stable_maps}" \
    "LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver2" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_REFLECTION=1" \
    "OBELISK_CHAT_REFLECTION_BINARY_SHA256=abc123"

snapshot_dir="$(run_snapshot "${stable_root}" "${stable_out}" 4242)"
assert_file_contains "${snapshot_dir}/summary.txt" '^pid=4242$'
assert_file_contains "${snapshot_dir}/summary.txt" '^posture_status=ok$'
assert_file_contains "${snapshot_dir}/summary.txt" '^quiet_posture_status=failed$'
assert_file_contains "${snapshot_dir}/summary.txt" '^stable_posture_summary=stable;'
assert_file_contains "${snapshot_dir}/summary.txt" '^quiet_posture_summary=not_quiet;'
assert_file_contains "${snapshot_dir}/quiet-posture.txt" 'Forbidden OBELISK_ENABLE_CHAT_REFLECTION'
assert_file_contains "${snapshot_dir}/summary.txt" '^chat_reflection_gate_env=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^chat_reflection_marker=enabled$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^chat_reflection_env=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^experimental_gate_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^reflected_chat_process_event_lines=4$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^server_send_chat_message_lines=2$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^client_chat_message_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^client_server_chat_message_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^client_server_chat_direct_message_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^metadata_only_lines=3$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^chat_candidate_lines=5$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^rejected_chat_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^rejected_or_unknown_send_mode_lines=2$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^send_mode_unknown_lines=1$'
assert_file_contains "${snapshot_dir}/chat-reflection.txt" '^last_relevant_line=.*ClientServerChatDirectMessage'
assert_file_not_contains "${snapshot_dir}/disk.txt" '/servidor/ark '

loop_out="${TMP_DIR}/loop-out"
run_loop_once "${stable_root}" "${loop_out}" 4242 >/dev/null
assert_file_contains "${loop_out}/latest/summary.txt" '^posture_status=ok$'
assert_file_contains "${loop_out}/latest/summary.txt" '^quiet_posture_status=failed$'

unstable_root="${TMP_DIR}/unstable-root"
unstable_out="${TMP_DIR}/unstable-out"
write_obelisk_fixture "${unstable_root}"
write_proc_fixture 4343 "${stable_maps}" \
    "OBELISK_INSTANCE_ID=arkserver2" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_DEBUG_CONTROL=1"

if run_snapshot "${unstable_root}" "${unstable_out}" 4343 >/dev/null 2>"${TMP_DIR}/unstable.err"; then
    echo "Expected unstable snapshot to fail" >&2
    exit 1
fi
assert_file_contains "${TMP_DIR}/unstable.err" 'unstable Obelisk posture'
assert_file_contains "${unstable_out}/latest/summary.txt" '^posture_status=failed$'
assert_file_contains "${unstable_out}/latest/summary.txt" '^stable_posture_summary=unstable;'
assert_file_contains "${unstable_out}/latest/chat-reflection.txt" '^skipped_unstable_posture=true$'

if OBELISK_ROOT="${unstable_root}" \
    OBELISK_SUPERVISOR_OUT="${TMP_DIR}/loop-fail-out" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_PID=4343 \
    "${LOOP}" --interval 1 --count 2 >/dev/null 2>"${TMP_DIR}/loop-fail.err"; then
    echo "Expected supervisor loop to stop on snapshot failure" >&2
    exit 1
fi
assert_file_contains "${TMP_DIR}/loop-fail.err" 'snapshot failed; stopping supervisor loop'

echo "obelisk_supervisor_snapshot offline tests passed"
