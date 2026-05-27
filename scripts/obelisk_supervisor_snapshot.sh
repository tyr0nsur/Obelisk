#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBELISK_ROOT="${OBELISK_ROOT:-/servidor/ark/obelisk}"
OUT_ROOT="${OBELISK_SUPERVISOR_OUT:-${OBELISK_ROOT}/dumps/supervisor}"
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

run_capture git-status git -C "${REPO_ROOT}" status -sb
run_capture git-log git -C "${REPO_ROOT}" log --oneline -10
run_capture disk df -h / /servidor/ark "${OBELISK_ROOT}"
run_capture processes pgrep -af 'ShooterGameServer|arkserver'
run_capture markers find "${OBELISK_ROOT}/state/instances" -maxdepth 3 -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n'
run_capture posture "${REPO_ROOT}/scripts/check_obelisk_server_posture.sh" --expect-stable

CHAT_LOG="${OBELISK_ROOT}/logs/arkserver/Obelisk.log"
CHAT_MARKER="${OBELISK_ROOT}/state/instances/arkserver/enable-chat-reflection"

{
    printf 'chat_reflection_marker=%s\n' "$([[ -f "${CHAT_MARKER}" ]] && printf enabled || printf disabled)"
    printf 'log_path=%s\n' "${CHAT_LOG}"
    if [[ -f "${CHAT_LOG}" ]]; then
        printf 'experimental_gate_lines=%s\n' "$(grep -c 'Experimental chat reflection enabled' "${CHAT_LOG}" || true)"
        printf 'reflected_chat_lines=%s\n' "$(grep -c 'Reflected chat ProcessEvent' "${CHAT_LOG}" || true)"
        printf 'rejected_chat_lines=%s\n' "$(grep -Ec 'Chat reflection rejected|Reflected chat rejected' "${CHAT_LOG}" || true)"
        printf '\nrecent_chat_reflection_lines:\n'
        grep -E 'Experimental chat reflection|Reflected chat|Chat reflection rejected' "${CHAT_LOG}" | tail -n 80 || true
    else
        printf 'missing_log=true\n'
    fi
} > "${OUT_DIR}/chat-reflection.txt" 2>&1

if [[ -f "${OBELISK_ROOT}/logs/arkserver/Obelisk.log" ]]; then
    run_capture obelisk-log-tail tail -n 200 "${OBELISK_ROOT}/logs/arkserver/Obelisk.log"
fi

if [[ -f "${OBELISK_ROOT}/logs/arkserver/Obelisk-Ragnarok.log" ]]; then
    run_capture obelisk-map-log-tail tail -n 200 "${OBELISK_ROOT}/logs/arkserver/Obelisk-Ragnarok.log"
fi

cat > "${OUT_DIR}/summary.txt" <<EOF
timestamp_utc=${STAMP}
repo=${REPO_ROOT}
obelisk_root=${OBELISK_ROOT}
snapshot_dir=${OUT_DIR}

This snapshot is read-only. It must not be used as proof of an accepted offset,
signature, or runtime behavior without a follow-up active review.
EOF

ln -sfn "${OUT_DIR}" "${OUT_ROOT}/latest"
printf '%s\n' "${OUT_DIR}"
