#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
OUT_ROOT="${OBELISK_SUPERVISOR_OUT:-${OBELISK_ROOT}/dumps/supervisor}"
INSTANCE="${OBELISK_SUPERVISOR_INSTANCE:-arkserver}"
MAP="${OBELISK_SUPERVISOR_MAP:-Ragnarok}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OUT_ROOT}/${STAMP}"

mkdir -p "${OUT_DIR}"

run_capture() {
    local name="$1"
    shift
    {
        printf '$'
        printf ' %q' "$@"
        printf '\n\n'
        "$@"
    } > "${OUT_DIR}/${name}.txt" 2>&1 || true
}

capture_command() {
    local name="$1"
    shift
    {
        printf '$'
        printf ' %q' "$@"
        printf '\n\n'
        "$@"
    } > "${OUT_DIR}/${name}.txt" 2>&1
}

safe_grep_count() {
    local pattern="$1"
    local file="$2"
    grep -Ec "${pattern}" "${file}" || true
}

posture_value() {
    local name="$1"
    sed -n "s/^${name}=//p" "${OUT_DIR}/posture.txt" | tail -n1
}

write_unstable_summary() {
    local posture_status="$1"
    local pid
    pid="$(posture_value pid)"
    {
        printf 'timestamp_utc=%s\n' "${STAMP}"
        printf 'repo=%s\n' "${REPO_ROOT}"
        printf 'obelisk_root=%s\n' "${OBELISK_ROOT}"
        printf 'instance=%s\n' "${INSTANCE}"
        printf 'map=%s\n' "${MAP}"
        printf 'snapshot_dir=%s\n' "${OUT_DIR}"
        printf 'pid=%s\n' "${pid:-unknown}"
        printf 'posture_status=%s\n' "${posture_status}"
        printf 'stable_posture_summary=unstable; see posture.txt before trusting chat/reflection evidence\n'
        printf '\n'
        printf 'This snapshot is read-only and stopped early because stable posture was not confirmed.\n'
    } > "${OUT_DIR}/summary.txt"

    {
        printf 'skipped_unstable_posture=true\n'
        printf 'posture_status=%s\n' "${posture_status}"
        printf 'reason=stable posture was not confirmed; see posture.txt\n'
    } > "${OUT_DIR}/chat-reflection.txt"
}

run_capture git-status git -C "${REPO_ROOT}" status -sb
run_capture git-log git -C "${REPO_ROOT}" log --oneline -10
run_capture disk df -h / "${OBELISK_ROOT}"
run_capture processes pgrep -af 'ShooterGameServer|arkserver'
run_capture markers find "${OBELISK_ROOT}/state/instances" -maxdepth 3 -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n'

POSTURE_CMD=("${REPO_ROOT}/scripts/check_obelisk_server_posture.sh" --expect-stable --map "${MAP}" --instance "${INSTANCE}")
if [[ -n "${OBELISK_SUPERVISOR_PROC_ROOT:-}" ]]; then
    POSTURE_CMD+=(--proc-root "${OBELISK_SUPERVISOR_PROC_ROOT}")
fi
if [[ -n "${OBELISK_SUPERVISOR_PID:-}" ]]; then
    POSTURE_CMD+=(--pid "${OBELISK_SUPERVISOR_PID}")
fi

posture_status=ok
if ! capture_command posture "${POSTURE_CMD[@]}"; then
    posture_status=failed
    write_unstable_summary "${posture_status}"
    ln -sfn "${OUT_DIR}" "${OUT_ROOT}/latest"
    printf '%s\n' "${OUT_DIR}"
    printf 'unstable Obelisk posture; snapshot stopped after %s\n' "${OUT_DIR}" >&2
    exit 1
fi

CHAT_LOG="${OBELISK_ROOT}/logs/${INSTANCE}/Obelisk.log"
CHAT_MARKER="${OBELISK_ROOT}/state/instances/${INSTANCE}/enable-chat-reflection"
PID="$(posture_value pid)"
CHAT_REFLECTION_ENV="$(posture_value OBELISK_ENABLE_CHAT_REFLECTION)"
CHAT_REFLECTION_SHA="$(posture_value OBELISK_CHAT_REFLECTION_BINARY_SHA256)"

{
    printf 'chat_reflection_marker=%s\n' "$([[ -f "${CHAT_MARKER}" ]] && printf enabled || printf disabled)"
    printf 'chat_reflection_env=%s\n' "${CHAT_REFLECTION_ENV:-<unset>}"
    printf 'chat_reflection_binary_sha256=%s\n' "$([[ -n "${CHAT_REFLECTION_SHA}" ]] && printf present || printf missing)"
    printf 'log_path=%s\n' "${CHAT_LOG}"
    if [[ -f "${CHAT_LOG}" ]]; then
        experimental_gate_lines="$(safe_grep_count 'Experimental chat reflection enabled' "${CHAT_LOG}")"
        reflected_chat_process_event_lines="$(safe_grep_count 'Reflected chat ProcessEvent' "${CHAT_LOG}")"
        server_send_chat_message_lines="$(safe_grep_count 'ServerSendChatMessage' "${CHAT_LOG}")"
        client_chat_message_lines="$(safe_grep_count 'ClientChatMessage' "${CHAT_LOG}")"
        client_server_chat_message_lines="$(safe_grep_count 'ClientServerChatMessage' "${CHAT_LOG}")"
        client_server_chat_direct_message_lines="$(safe_grep_count 'ClientServerChatDirectMessage' "${CHAT_LOG}")"
        metadata_only_lines="$(safe_grep_count 'metadata_only=true' "${CHAT_LOG}")"
        chat_candidate_lines="$(safe_grep_count 'ServerSendChatMessage|ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage' "${CHAT_LOG}")"
        rejected_chat_lines="$(safe_grep_count 'Chat reflection rejected|Reflected chat rejected' "${CHAT_LOG}")"
        rejected_or_unknown_send_mode_lines="$(safe_grep_count 'rejected|send_mode_known=false' "${CHAT_LOG}")"
        send_mode_unknown_lines="$(safe_grep_count 'send_mode_known=false' "${CHAT_LOG}")"
        last_relevant_line="$(grep -E 'Experimental chat reflection|Reflected chat|Chat reflection rejected|ServerSendChatMessage|ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage|metadata_only=true|send_mode_known=false' "${CHAT_LOG}" | tail -n1 || true)"

        printf 'experimental_gate_lines=%s\n' "${experimental_gate_lines}"
        printf 'reflected_chat_lines=%s\n' "${reflected_chat_process_event_lines}"
        printf 'reflected_chat_process_event_lines=%s\n' "${reflected_chat_process_event_lines}"
        printf 'server_send_chat_message_lines=%s\n' "${server_send_chat_message_lines}"
        printf 'client_chat_message_lines=%s\n' "${client_chat_message_lines}"
        printf 'client_server_chat_message_lines=%s\n' "${client_server_chat_message_lines}"
        printf 'client_server_chat_direct_message_lines=%s\n' "${client_server_chat_direct_message_lines}"
        printf 'metadata_only_lines=%s\n' "${metadata_only_lines}"
        printf 'chat_candidate_lines=%s\n' "${chat_candidate_lines}"
        printf 'rejected_chat_lines=%s\n' "${rejected_chat_lines}"
        printf 'rejected_or_unknown_send_mode_lines=%s\n' "${rejected_or_unknown_send_mode_lines}"
        printf 'send_mode_unknown_lines=%s\n' "${send_mode_unknown_lines}"
        printf 'last_relevant_line=%s\n' "${last_relevant_line:-<none>}"
        printf '\nrecent_chat_reflection_lines:\n'
        grep -E 'Experimental chat reflection|Reflected chat|Chat reflection rejected|ServerSendChatMessage|ClientChatMessage|ClientServerChatMessage|ClientServerChatDirectMessage|metadata_only=true|send_mode_known=false' "${CHAT_LOG}" | tail -n 80 || true
    else
        printf 'missing_log=true\n'
        printf 'experimental_gate_lines=0\n'
        printf 'reflected_chat_lines=0\n'
        printf 'reflected_chat_process_event_lines=0\n'
        printf 'server_send_chat_message_lines=0\n'
        printf 'client_chat_message_lines=0\n'
        printf 'client_server_chat_message_lines=0\n'
        printf 'client_server_chat_direct_message_lines=0\n'
        printf 'metadata_only_lines=0\n'
        printf 'chat_candidate_lines=0\n'
        printf 'rejected_chat_lines=0\n'
        printf 'rejected_or_unknown_send_mode_lines=0\n'
        printf 'send_mode_unknown_lines=0\n'
        printf 'last_relevant_line=<none>\n'
    fi
} > "${OUT_DIR}/chat-reflection.txt" 2>&1

if [[ -f "${OBELISK_ROOT}/logs/${INSTANCE}/Obelisk.log" ]]; then
    run_capture obelisk-log-tail tail -n 200 "${OBELISK_ROOT}/logs/${INSTANCE}/Obelisk.log"
fi

if [[ -f "${OBELISK_ROOT}/logs/${INSTANCE}/Obelisk-${MAP}.log" ]]; then
    run_capture obelisk-map-log-tail tail -n 200 "${OBELISK_ROOT}/logs/${INSTANCE}/Obelisk-${MAP}.log"
fi

cat > "${OUT_DIR}/summary.txt" <<EOF
timestamp_utc=${STAMP}
repo=${REPO_ROOT}
obelisk_root=${OBELISK_ROOT}
instance=${INSTANCE}
map=${MAP}
snapshot_dir=${OUT_DIR}
pid=${PID:-unknown}
posture_status=${posture_status}
stable_posture_summary=stable; instance=${INSTANCE}; process_event_hook=1; plugins_disabled=1; libobelisk_mapped=1; scanner_debug_native_exec_absent=1
chat_reflection_gate_env=${CHAT_REFLECTION_ENV:-<unset>}
chat_reflection_binary_sha256=$([[ -n "${CHAT_REFLECTION_SHA}" ]] && printf present || printf missing)

This snapshot is read-only. It must not be used as proof of an accepted offset,
signature, or runtime behavior without a follow-up active review.
EOF

ln -sfn "${OUT_DIR}" "${OUT_ROOT}/latest"
printf '%s\n' "${OUT_DIR}"
