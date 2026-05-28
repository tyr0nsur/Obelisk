#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT="${REPO_ROOT}/scripts/obelisk_supervisor_snapshot.sh"
LOOP="${REPO_ROOT}/scripts/obelisk_supervisor_loop.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
WRAPPER_EXPECTED_FIXTURE="${TMP_DIR}/expected-wrapper/ObeliskRun.sh"
WRAPPER_FIXTURE="${TMP_DIR}/installed-wrapper/ObeliskRun.sh"
mkdir -p "$(dirname "${WRAPPER_EXPECTED_FIXTURE}")" "$(dirname "${WRAPPER_FIXTURE}")"
cp "${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh" "${WRAPPER_EXPECTED_FIXTURE}"
cp "${WRAPPER_EXPECTED_FIXTURE}" "${WRAPPER_FIXTURE}"

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
    local instance="${2:-arkserver2}"
    local experimental_markers="${3:-all}"

    mkdir -p "${root}/logs/${instance}" "${root}/state/instances/${instance}"
    : > "${root}/state/instances/${instance}/enable-process-event-hook"
    : > "${root}/state/instances/${instance}/disable-plugins"
    case "${experimental_markers}" in
        all)
            : > "${root}/state/instances/${instance}/enable-chat-reflection"
            : > "${root}/state/instances/${instance}/enable-inventory-reflection"
            : > "${root}/state/instances/${instance}/enable-structure-reflection"
            ;;
        chat)
            : > "${root}/state/instances/${instance}/enable-chat-reflection"
            ;;
        none)
            ;;
        *)
            echo "Unknown experimental marker fixture mode: ${experimental_markers}" >&2
            exit 2
            ;;
    esac
    cat > "${root}/logs/${instance}/Obelisk.log" <<'EOF'
[2026-05-27 01:00:00.000] [warning] Experimental chat reflection enabled for ShooterGameServer SHA256 abc123.
[2026-05-27 01:00:01.000] [info] Reflected chat ProcessEvent #1 function=ServerSendChatMessage fname_index=2697 params=0x123 fields=2
[2026-05-27 01:00:01.001] [info] Reflected chat ServerSendChatMessage send_mode=4 send_mode_name=Unknown send_mode_known=false
[2026-05-27 01:00:01.002] [info] Reflected chat field ChatMessage offset=0x0 size=16 has_range=true
[2026-05-27 01:00:01.003] [info] Reflected chat rejected #1 fname_index=2697 function=0x456 reason=bad_parms_size
[2026-05-27 01:00:01.004] [info] Reflected chat ProcessEvent #2 function=ClientServerChatMessage fname_index=1984 params=0x789 fields=3 metadata_only=true
[2026-05-27 01:00:01.005] [info] Reflected chat ProcessEvent #3 function=ClientChatMessage fname_index=1865 params=0xabc fields=1 metadata_only=true
[2026-05-27 01:00:01.006] [info] Reflected chat ProcessEvent #4 function=ClientServerChatDirectMessage fname_index=1983 params=0xdef fields=3 metadata_only=true
[2026-05-27 01:00:01.500] [warning] Experimental inventory reflection enabled for ShooterGameServer SHA256 abc123.
[2026-05-27 01:00:01.501] [info] Reflected inventory ProcessEvent #1 function=CanUse fname_index=6252 outer_fname_index=6231 fields=2
[2026-05-27 01:00:01.502] [info] Reflected inventory field bIgnoreCooldown offset=0x0 size=1 has_range=true
[2026-05-27 01:00:01.503] [info] Reflected inventory rejected #2 fname_index=6252 reason=bad_parms_size
[2026-05-27 01:00:02.000] [warning] Experimental structure reflection enabled for ShooterGameServer SHA256 abc123.
[2026-05-27 01:00:02.001] [info] Reflected structure ProcessEvent #1 function=VerifyPinCode fname_index=7636 outer_fname_index=7617 fields=2
[2026-05-27 01:00:02.002] [info] Reflected structure field pinCode offset=0x0 size=4 sensitive=true has_range=false
[2026-05-27 01:00:02.003] [info] Reflected structure rejected #2 fname_index=7636 reason=bad_parms_size
EOF
}

run_snapshot() {
    local root="$1"
    local out="$2"
    local pid="$3"
    local allow_chat_reflection="${4:-0}"

    OBELISK_ROOT="${root}" \
    OBELISK_SUPERVISOR_OUT="${out}" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_INSTANCE=arkserver2 \
    OBELISK_SUPERVISOR_MAP=TheIsland \
    OBELISK_SUPERVISOR_PID="${pid}" \
    OBELISK_SUPERVISOR_ALLOW_CHAT_REFLECTION="${allow_chat_reflection}" \
    OBELISK_SUPERVISOR_WRAPPER_EXPECTED="${WRAPPER_EXPECTED_FIXTURE}" \
    OBELISK_SUPERVISOR_WRAPPER_INSTALLED="${WRAPPER_FIXTURE}" \
    "${SNAPSHOT}"
}

run_loop_once() {
    local root="$1"
    local out="$2"
    local pid="$3"

    OBELISK_ROOT="${root}" \
    OBELISK_SUPERVISOR_OUT="${out}" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_INSTANCE=arkserver2 \
    OBELISK_SUPERVISOR_MAP=TheIsland \
    OBELISK_SUPERVISOR_PID="${pid}" \
    OBELISK_SUPERVISOR_WRAPPER_EXPECTED="${WRAPPER_EXPECTED_FIXTURE}" \
    OBELISK_SUPERVISOR_WRAPPER_INSTALLED="${WRAPPER_FIXTURE}" \
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

default_root="${TMP_DIR}/default-root"
default_out="${TMP_DIR}/default-out"
write_obelisk_fixture "${default_root}" "arkserver-obelisk-debug" "none"
write_proc_fixture 4141 "7f000000-7f001000 r-xp 00000000 00:00 0 ${default_root}/lib/libobelisk.so" \
    "OBELISK_ROOT=${default_root}" \
    "LD_PRELOAD=${default_root}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver-obelisk-debug" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"

default_snapshot_dir="$(
    OBELISK_ROOT="${default_root}" \
    OBELISK_SUPERVISOR_OUT="${default_out}" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_PID=4141 \
    OBELISK_SUPERVISOR_WRAPPER_EXPECTED="${WRAPPER_EXPECTED_FIXTURE}" \
    OBELISK_SUPERVISOR_WRAPPER_INSTALLED="${WRAPPER_FIXTURE}" \
    "${SNAPSHOT}"
)"
assert_file_contains "${default_snapshot_dir}/summary.txt" '^instance=arkserver-obelisk-debug$'
assert_file_contains "${default_snapshot_dir}/summary.txt" '^posture_status=ok$'
assert_file_contains "${default_snapshot_dir}/summary.txt" '^linuxgsm_wrapper_drift_status=ok$'
assert_file_contains "${default_snapshot_dir}/wrapper-drift.txt" '^LinuxGSM wrapper matches versioned template: '
assert_file_contains "${default_snapshot_dir}/wrapper-drift.txt" '^sha256='

stable_root="${TMP_DIR}/stable-root"
stable_out="${TMP_DIR}/stable-out"
write_obelisk_fixture "${stable_root}" "arkserver2" "chat"
write_proc_fixture 4242 "7f000000-7f001000 r-xp 00000000 00:00 0 ${stable_root}/lib/libobelisk.so" \
    "OBELISK_ROOT=${stable_root}" \
    "LD_PRELOAD=${stable_root}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver2" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_REFLECTION=1" \
    "OBELISK_CHAT_REFLECTION_BINARY_SHA256=abc123"

chat_forbidden_out="${TMP_DIR}/chat-forbidden-out"
if run_snapshot "${stable_root}" "${chat_forbidden_out}" 4242 >/dev/null 2>"${TMP_DIR}/chat-forbidden.err"; then
    echo "Expected chat reflection to fail default supervisor posture" >&2
    exit 1
fi
assert_file_contains "${TMP_DIR}/chat-forbidden.err" 'unstable Obelisk posture'
assert_file_contains "${chat_forbidden_out}/latest/posture.txt" 'Forbidden OBELISK_ENABLE_CHAT_REFLECTION'
assert_file_contains "${chat_forbidden_out}/latest/summary.txt" '^posture_status=failed$'

snapshot_dir="$(run_snapshot "${stable_root}" "${stable_out}" 4242 1)"
assert_file_contains "${snapshot_dir}/summary.txt" '^pid=4242$'
assert_file_contains "${snapshot_dir}/summary.txt" '^linuxgsm_wrapper_drift_status=ok$'
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
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^inventory_reflection_marker=disabled$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^inventory_reflection_env=<unset>$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^inventory_reflection_binary_sha256=missing$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^experimental_gate_lines=1$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^reflected_inventory_process_event_lines=1$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^reflected_inventory_rejected_lines=1$'
assert_file_contains "${snapshot_dir}/inventory-reflection.txt" '^reflected_inventory_field_lines=1$'
assert_file_contains "${snapshot_dir}/summary.txt" '^inventory_reflection_gate_env=<unset>$'
assert_file_contains "${snapshot_dir}/summary.txt" '^inventory_reflection_binary_sha256=missing$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^structure_reflection_marker=disabled$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^structure_reflection_env=<unset>$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^structure_reflection_binary_sha256=missing$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^experimental_gate_lines=1$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^reflected_structure_process_event_lines=1$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^reflected_structure_rejected_lines=1$'
assert_file_contains "${snapshot_dir}/structure-reflection.txt" '^reflected_structure_field_lines=1$'
assert_file_contains "${snapshot_dir}/summary.txt" '^structure_reflection_gate_env=<unset>$'
assert_file_contains "${snapshot_dir}/summary.txt" '^structure_reflection_binary_sha256=missing$'
assert_file_not_contains "${snapshot_dir}/disk.txt" '/servidor/ark '

drift_wrapper="${TMP_DIR}/drift-wrapper/ObeliskRun.sh"
mkdir -p "$(dirname "${drift_wrapper}")"
printf '#!/usr/bin/env bash\nexit 0\n' > "${drift_wrapper}"
drift_snapshot_dir="$(
    OBELISK_ROOT="${stable_root}" \
    OBELISK_SUPERVISOR_OUT="${TMP_DIR}/drift-out" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_INSTANCE=arkserver2 \
    OBELISK_SUPERVISOR_MAP=TheIsland \
    OBELISK_SUPERVISOR_PID=4242 \
    OBELISK_SUPERVISOR_ALLOW_CHAT_REFLECTION=1 \
    OBELISK_SUPERVISOR_WRAPPER_EXPECTED="${WRAPPER_EXPECTED_FIXTURE}" \
    OBELISK_SUPERVISOR_WRAPPER_INSTALLED="${drift_wrapper}" \
    "${SNAPSHOT}"
)"
assert_file_contains "${drift_snapshot_dir}/summary.txt" '^posture_status=ok$'
assert_file_contains "${drift_snapshot_dir}/summary.txt" '^linuxgsm_wrapper_drift_status=failed$'
assert_file_contains "${drift_snapshot_dir}/wrapper-drift.txt" '^LinuxGSM wrapper drift detected\.'

loop_out="${TMP_DIR}/loop-out"
OBELISK_SUPERVISOR_ALLOW_CHAT_REFLECTION=1 run_loop_once "${stable_root}" "${loop_out}" 4242 >/dev/null
assert_file_contains "${loop_out}/latest/summary.txt" '^posture_status=ok$'
assert_file_contains "${loop_out}/latest/summary.txt" '^quiet_posture_status=failed$'

unstable_root="${TMP_DIR}/unstable-root"
unstable_out="${TMP_DIR}/unstable-out"
write_obelisk_fixture "${unstable_root}" "arkserver2" "none"
write_proc_fixture 4343 "7f000000-7f001000 r-xp 00000000 00:00 0 ${unstable_root}/lib/libobelisk.so" \
    "OBELISK_ROOT=${unstable_root}" \
    "LD_PRELOAD=${unstable_root}/lib/libobelisk.so" \
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
assert_file_contains "${unstable_out}/latest/summary.txt" '^linuxgsm_wrapper_drift_status=ok$'
assert_file_contains "${unstable_out}/latest/summary.txt" '^stable_posture_summary=unstable;'
assert_file_contains "${unstable_out}/latest/chat-reflection.txt" '^skipped_unstable_posture=true$'
assert_file_contains "${unstable_out}/latest/inventory-reflection.txt" '^skipped_unstable_posture=true$'
assert_file_contains "${unstable_out}/latest/structure-reflection.txt" '^skipped_unstable_posture=true$'

invalid_root="${TMP_DIR}/invalid-root"
invalid_out="${TMP_DIR}/invalid-out"
write_obelisk_fixture "${invalid_root}" "arkserver2" "none"
mkdir -p "${invalid_root}/state/instances/arkserver2/enable-inventory-reflection"
: > "${TMP_DIR}/external-structure-marker"
ln -s "${TMP_DIR}/external-structure-marker" "${invalid_root}/state/instances/arkserver2/enable-structure-reflection"
write_proc_fixture 4444 "7f000000-7f001000 r-xp 00000000 00:00 0 ${invalid_root}/lib/libobelisk.so" \
    "OBELISK_ROOT=${invalid_root}" \
    "LD_PRELOAD=${invalid_root}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver2" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"

if run_snapshot "${invalid_root}" "${invalid_out}" 4444 >/dev/null 2>"${TMP_DIR}/invalid.err"; then
    echo "Expected invalid marker entries to fail stable posture" >&2
    exit 1
fi
assert_file_contains "${TMP_DIR}/invalid.err" 'unstable Obelisk posture'
assert_file_contains "${invalid_out}/latest/summary.txt" '^posture_status=failed$'
assert_file_contains "${invalid_out}/latest/posture.txt" 'Forbidden marker .*/enable-inventory-reflection exists\.'

if OBELISK_ROOT="${unstable_root}" \
    OBELISK_SUPERVISOR_OUT="${TMP_DIR}/loop-fail-out" \
    OBELISK_SUPERVISOR_PROC_ROOT="${TMP_DIR}/proc" \
    OBELISK_SUPERVISOR_INSTANCE=arkserver2 \
    OBELISK_SUPERVISOR_MAP=TheIsland \
    OBELISK_SUPERVISOR_PID=4343 \
    OBELISK_SUPERVISOR_WRAPPER_EXPECTED="${WRAPPER_EXPECTED_FIXTURE}" \
    OBELISK_SUPERVISOR_WRAPPER_INSTALLED="${WRAPPER_FIXTURE}" \
    "${LOOP}" --interval 1 --count 2 >/dev/null 2>"${TMP_DIR}/loop-fail.err"; then
    echo "Expected supervisor loop to stop on snapshot failure" >&2
    exit 1
fi
assert_file_contains "${TMP_DIR}/loop-fail.err" 'snapshot failed; stopping supervisor loop'

echo "obelisk_supervisor_snapshot offline tests passed"
