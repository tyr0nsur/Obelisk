#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/check_obelisk_server_posture.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

prepare_posture_root() {
    local root="$1"

    mkdir -p \
        "${root}/lib" \
        "${root}/plugins" \
        "${root}/config" \
        "${root}/logs" \
        "${root}/state/instances/arkserver"
    : > "${root}/lib/libobelisk.so"
    : > "${root}/state/instances/arkserver/enable-process-event-hook"
    : > "${root}/state/instances/arkserver/disable-plugins"
}

TEST_OBELISK_ROOT="${TMP_DIR}/obelisk-root"
prepare_posture_root "${TEST_OBELISK_ROOT}"

write_proc_fixture() {
    local pid="$1"
    local maps="$2"
    shift 2

    mkdir -p "${TMP_DIR}/proc/${pid}"
    printf '%s\0' "OBELISK_ROOT=${TEST_OBELISK_ROOT}" "$@" > "${TMP_DIR}/proc/${pid}/environ"
    printf '%s\n' "${maps}" > "${TMP_DIR}/proc/${pid}/maps"
}

write_cmdline_fixture() {
    local pid="$1"
    local map="$2"

    mkdir -p "${TMP_DIR}/proc/${pid}"
    printf '%s\0' \
        "/opt/ark/ShooterGameServer" \
        "${map}?SessionName=ObeliskPosture" \
        > "${TMP_DIR}/proc/${pid}/cmdline"
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

expect_failure live-procfs-read-requires-explicit-acknowledgement \
    "${SCRIPT}" --pid 101 --expect-stable --instance arkserver

live_proc_root_link="${TMP_DIR}/live-proc-root-link"
ln -s /proc "${live_proc_root_link}"
expect_failure live-procfs-symlink-root-requires-explicit-acknowledgement \
    "${SCRIPT}" --proc-root "${live_proc_root_link}" --pid 101 --expect-stable --instance arkserver

expect_failure protected-proc-root-for-offline-posture \
    "${SCRIPT}" --proc-root /servidor/ark/workspace-offline/proc --pid 101 --expect-stable --instance arkserver

protected_proc_root_link="${TMP_DIR}/protected-proc-root-link"
ln -s /servidor/ark "${protected_proc_root_link}"
expect_failure protected-proc-root-symlink-for-offline-posture \
    "${SCRIPT}" --proc-root "${protected_proc_root_link}/workspace-offline/proc" --pid 101 --expect-stable --instance arkserver

mkdir -p "${TMP_DIR}/proc-with-live-file-link/201"
ln -s /proc/self/environ "${TMP_DIR}/proc-with-live-file-link/201/environ"
printf '%s\n' "7f000000-7f001000 r-xp 00000000 00:00 0 /tmp/libobelisk.so" \
    > "${TMP_DIR}/proc-with-live-file-link/201/maps"
expect_failure live-procfs-environ-symlink-requires-explicit-acknowledgement \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc-with-live-file-link" --pid 201 --expect-stable --instance arkserver

expect_failure map-discovery-without-matching-proc-fixture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --map Ragnarok --expect-stable --instance arkserver

stable_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"

write_proc_fixture 101 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
write_cmdline_fixture 101 Ragnarok
expect_success stable-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
expect_success stable-posture-instance-id-alias \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance-id arkserver
expect_success stable-posture-legacy-chat-forbidden-flag-clean \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection --instance arkserver

"${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver --json \
    > "${TMP_DIR}/stable-posture.json"
python3 - "${TMP_DIR}/stable-posture.json" <<'PY'
import json
import sys
from datetime import datetime, timezone

payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert payload["schema"] == "obelisk.server-posture.v1"
assert payload["status"] == "posture_passed_no_runtime_approval_or_evidence"
assert payload["posture_check_passed"] is True
assert payload["ready"] is False
assert payload["ready_scope"] == "posture_observation_only"
assert payload["sdk_readiness_claim_allowed"] is False
assert payload["server_operations_authorized"] is False
assert payload["runtime_work_authorized"] is False
assert payload["runtime_capture_authorized"] is False
assert payload["current_turn_authorized"] is False
assert payload["current_turn_operator_approval_required"] is True
assert payload["posture_counts_as_current_turn_approval"] is False
assert payload["posture_counts_as_approved_runtime_evidence"] is False
assert payload["approved_runtime_evidence_present"] is False
assert payload["approved_runtime_evidence_ready"] is False
assert payload["public_sdk_ready"] is False
assert payload["stable_claim_allowed"] is False
assert payload["authorization_source"] == "none_posture_sidecar_only"
assert payload["approved_runtime_evidence_source"] == "none_posture_sidecar_only"
assert payload["mode"] == "stable"
assert payload["pid"] == "101"
assert payload["instance"] == "arkserver"
assert payload["map"] is None
assert payload["live_procfs_read_acknowledged"] is False
assert payload["protected_root_validation_acknowledged"] is False
assert payload["live_read_acknowledgement_counts_as_authorization"] is False
assert datetime.fromisoformat(payload["checked_at_utc"].removesuffix("Z") + "+00:00").tzinfo == timezone.utc
assert "not runtime approval" in payload["non_claim"]
PY

managed_env_override_pid=1200
for managed_env_name in OBELISK_PLUGIN_DIR OBELISK_CONFIG_DIR OBELISK_LOG_DIR; do
    write_proc_fixture "${managed_env_override_pid}" "${stable_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1" \
        "${managed_env_name}=${TMP_DIR}/unsafe-${managed_env_name}"
    expect_failure "stable-posture-rejects-${managed_env_name}-override" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${managed_env_override_pid}" --expect-stable --instance arkserver
    managed_env_override_pid=$((managed_env_override_pid + 1))

    write_proc_fixture "${managed_env_override_pid}" "${stable_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1" \
        "${managed_env_name}=relative-${managed_env_name}"
    expect_failure "stable-posture-rejects-relative-${managed_env_name}" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${managed_env_override_pid}" --expect-stable --instance arkserver
    managed_env_override_pid=$((managed_env_override_pid + 1))

    case "${managed_env_name}" in
        OBELISK_PLUGIN_DIR)
            managed_env_expected_path="${TEST_OBELISK_ROOT}/plugins"
            ;;
        OBELISK_CONFIG_DIR)
            managed_env_expected_path="${TEST_OBELISK_ROOT}/config"
            ;;
        OBELISK_LOG_DIR)
            managed_env_expected_path="${TEST_OBELISK_ROOT}/logs"
            ;;
    esac
    managed_env_symlink_path="${TMP_DIR}/symlink-${managed_env_name}"
    rm -f "${managed_env_symlink_path}"
    ln -s "${managed_env_expected_path}" "${managed_env_symlink_path}"
    write_proc_fixture "${managed_env_override_pid}" "${stable_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1" \
        "${managed_env_name}=${managed_env_symlink_path}"
    expect_failure "stable-posture-rejects-symlink-${managed_env_name}" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${managed_env_override_pid}" --expect-stable --instance arkserver
    managed_env_override_pid=$((managed_env_override_pid + 1))
done
unset managed_env_name managed_env_override_pid managed_env_expected_path managed_env_symlink_path

expect_success stable-posture-map-detects-absolute-shootergameserver \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --map Ragnarok --expect-stable --instance arkserver
expect_failure stable-posture-map-rejects-literal-prefix-mismatch \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --map Ragnar --expect-stable --instance arkserver

write_cmdline_fixture 910 TheIsland
expect_success two-shooter-processes-allowed-for-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
write_cmdline_fixture 911 Genesis2
expect_failure three-shooter-processes-forbidden-for-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -rf "${TMP_DIR}/proc/910" "${TMP_DIR}/proc/911"

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

write_proc_fixture 1191 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=legacy-debug"
expect_failure non-stable-wrapper-profile-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1191 --expect-stable --instance arkserver

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-experimental-observers"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
write_proc_fixture 130 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_success approved-observer-debug-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver

write_proc_fixture 1302 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=10000"
expect_success approved-observer-debug-posture-with-player-principal-near-miss \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1302 --expect-observer-debug --instance arkserver

write_proc_fixture 1303 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=500"
expect_success approved-observer-debug-posture-with-player-principal-route-sampling \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1303 --expect-observer-debug --instance arkserver

"${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver --json \
    > "${TMP_DIR}/observer-posture.json"
python3 - "${TMP_DIR}/observer-posture.json" <<'PY'
import json
import sys

payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert payload["schema"] == "obelisk.server-posture.v1"
assert payload["mode"] == "player-principal-lifecycle-observer-debug"
assert payload["posture_check_passed"] is True
assert payload["ready"] is False
assert payload["sdk_readiness_claim_allowed"] is False
assert payload["server_operations_authorized"] is False
assert payload["runtime_capture_authorized"] is False
assert payload["posture_counts_as_approved_runtime_evidence"] is False
assert payload["approved_runtime_evidence_ready"] is False
assert payload["stable_claim_allowed"] is False
assert payload["authorization_source"] == "none_posture_sidecar_only"
assert payload["live_read_acknowledgement_counts_as_authorization"] is False
PY
write_proc_fixture 1301 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_LOG_DIR=${TMP_DIR}/unsafe-observer-debug-logs" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure observer-debug-managed-log-env-override \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1301 --expect-observer-debug --instance arkserver
expect_failure approved-observer-debug-still-not-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-stable --instance arkserver
expect_failure stable-posture-not-observer-debug \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-observer-debug --instance arkserver
expect_failure mutually-exclusive-observer-and-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-stable --expect-observer-debug --instance arkserver

write_proc_fixture 133 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure observer-debug-player-principal-missing-binary-sha \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 133 --expect-observer-debug --instance arkserver

write_proc_fixture 134 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=1111111111111111111111111111111111111111111111111111111111111111" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure observer-debug-player-principal-unsupported-binary-sha \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 134 --expect-observer-debug --instance arkserver

write_proc_fixture 135 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure observer-debug-player-principal-missing-log-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 135 --expect-observer-debug --instance arkserver

write_proc_fixture 136 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=2" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure observer-debug-player-principal-wrong-log-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 136 --expect-observer-debug --instance arkserver

write_proc_fixture 137 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10"
expect_failure observer-debug-player-principal-missing-dispatch-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 137 --expect-observer-debug --instance arkserver

write_proc_fixture 138 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1"
expect_failure observer-debug-player-principal-wrong-dispatch-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 138 --expect-observer-debug --instance arkserver

write_proc_fixture 1381 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1"
expect_failure observer-debug-player-principal-near-miss-missing-scan-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1381 --expect-observer-debug --instance arkserver

write_proc_fixture 1382 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=10000"
expect_failure observer-debug-player-principal-near-miss-scan-limit-without-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1382 --expect-observer-debug --instance arkserver

write_proc_fixture 1383 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=10001"
expect_failure observer-debug-player-principal-near-miss-scan-limit-too-large \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1383 --expect-observer-debug --instance arkserver

write_proc_fixture 1384 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1"
expect_failure observer-debug-player-principal-route-sampling-missing-limit \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1384 --expect-observer-debug --instance arkserver

write_proc_fixture 1385 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=500"
expect_failure observer-debug-player-principal-route-sample-limit-without-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1385 --expect-observer-debug --instance arkserver

write_proc_fixture 1386 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=500"
expect_failure observer-debug-player-principal-route-sampling-requires-diagnostics \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1386 --expect-observer-debug --instance arkserver

write_proc_fixture 1387 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=10001"
expect_failure observer-debug-player-principal-route-sample-limit-too-large \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1387 --expect-observer-debug --instance arkserver

rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window"
expect_failure observer-debug-missing-approval-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window"

rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_failure observer-debug-env-without-observer-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"

write_proc_fixture 131 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug"
expect_failure observer-debug-marker-without-observer-env \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 131 --expect-observer-debug --instance arkserver

rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_failure observer-debug-without-observer-pair \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 131 --expect-observer-debug --instance arkserver

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"
write_proc_fixture 139 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_CHAT_EVENTS=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10"
expect_failure observer-debug-stale-player-principal-budget-env \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 139 --expect-observer-debug --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
ln -s "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-reflection"
expect_failure observer-debug-player-principal-symlink-forbidden-observer-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-reflection"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"
write_proc_fixture 140 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_ENABLE_CHAT_EVENTS=1"
expect_failure observer-debug-player-principal-mixed-observer-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 140 --expect-observer-debug --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-inventory-action-redacted-observer"
expect_failure observer-debug-player-principal-redacted-inventory-action-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-inventory-action-redacted-observer"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"
expect_failure observer-debug-player-principal-unknown-observer-marker \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 130 --expect-observer-debug --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"

write_proc_fixture 1322 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_ENABLE_FUTURE_OBSERVER=1"
expect_failure observer-debug-player-principal-unknown-observer-env \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1322 --expect-observer-debug --instance arkserver

write_proc_fixture 132 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0" \
    "OBELISK_ENABLE_DEBUG_CONTROL=1"
expect_failure observer-debug-runtime-debug-control-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 132 --expect-observer-debug --instance arkserver

rm -f \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-experimental-observers" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-experimental-observers"
: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events"
write_proc_fixture 141 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_CHAT_EVENTS=1" \
    "OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1"
expect_success observer-debug-chat-events-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 141 --expect-observer-debug --instance arkserver

write_proc_fixture 142 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_CHAT_EVENTS=1" \
    "OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
expect_failure observer-debug-chat-events-missing-dispatch-budget \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 142 --expect-observer-debug --instance arkserver

write_proc_fixture 143 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_WRAPPER_PROFILE=observer-debug" \
    "OBELISK_ENABLE_CHAT_EVENTS=1" \
    "OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1" \
    "OBELISK_ENABLE_FUTURE_OBSERVER=1"
expect_failure observer-debug-future-observer-env-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 143 --expect-observer-debug --instance arkserver

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"
expect_failure observer-debug-future-observer-marker-forbidden \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 141 --expect-observer-debug --instance arkserver
rm -f \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-observer-debug-window" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/allow-experimental-observers" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-events" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"

expect_failure missing-explicit-instance \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable
expect_failure missing-map-without-pid \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --expect-stable --instance arkserver
expect_failure unsafe-map-name-for-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --map 'Ragnarok.*' --expect-stable --instance arkserver

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

TEST_OBELISK_ROOT_ORIGINAL="${TEST_OBELISK_ROOT}"
TEST_OBELISK_ROOT_SYMLINK="${TMP_DIR}/obelisk-root-link"
ln -s "${TEST_OBELISK_ROOT_ORIGINAL}" "${TEST_OBELISK_ROOT_SYMLINK}"
TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_SYMLINK}"
symlink_root_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
write_proc_fixture 181 "${symlink_root_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure symlink-obelisk-root-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 181 --expect-stable --instance arkserver
TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_ORIGINAL}"

TEST_OBELISK_ROOT_PROTECTED_ORIGINAL="${TEST_OBELISK_ROOT}"
TEST_OBELISK_ROOT="/servidor/ark/obelisk"
protected_root_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
write_proc_fixture 182 "${protected_root_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure protected-obelisk-root-for-offline-posture \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 182 --expect-stable --instance arkserver
TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_PROTECTED_ORIGINAL}"

TEST_OBELISK_ROOT_PROTECTED_ORIGINAL="${TEST_OBELISK_ROOT}"
TEST_OBELISK_ROOT="/servidor/ark/workspace-offline/obelisk"
protected_noncentral_root_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
write_proc_fixture 184 "${protected_noncentral_root_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure protected-root-ack-only-allows-central-obelisk-root \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 184 --expect-stable --allow-protected-root --instance arkserver
TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_PROTECTED_ORIGINAL}"

path_component_real_parent="${TMP_DIR}/path-component-real-parent"
path_component_link_parent="${TMP_DIR}/path-component-link-parent"
mkdir -p "${path_component_real_parent}"
ln -s "${path_component_real_parent}" "${path_component_link_parent}"
TEST_OBELISK_ROOT_PATH_COMPONENT_ORIGINAL="${TEST_OBELISK_ROOT}"
TEST_OBELISK_ROOT="${path_component_link_parent}/obelisk-root"
prepare_posture_root "${TEST_OBELISK_ROOT}"
path_component_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
write_proc_fixture 183 "${path_component_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure symlink-path-component-obelisk-root-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 183 --expect-stable --instance arkserver
TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_PATH_COMPONENT_ORIGINAL}"

mv "${TEST_OBELISK_ROOT}/plugins" "${TEST_OBELISK_ROOT}/plugins.real"
ln -s "${TEST_OBELISK_ROOT}/plugins.real" "${TEST_OBELISK_ROOT}/plugins"
expect_failure symlink-managed-plugin-dir-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/plugins"
mv "${TEST_OBELISK_ROOT}/plugins.real" "${TEST_OBELISK_ROOT}/plugins"

rm -f "${TEST_OBELISK_ROOT}/lib/libobelisk.so"
: > "${TMP_DIR}/external-libobelisk.so"
ln -s "${TMP_DIR}/external-libobelisk.so" "${TEST_OBELISK_ROOT}/lib/libobelisk.so"
expect_failure symlink-runtime-lib-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/lib/libobelisk.so"
: > "${TEST_OBELISK_ROOT}/lib/libobelisk.so"

managed_dir_pid=190
for managed_dir in lib plugins config logs state state/instances; do
    managed_dir_label="${managed_dir//\//-}"
    managed_root="${TMP_DIR}/root-missing-managed-${managed_dir_label}"
    TEST_OBELISK_ROOT_MANAGED_ORIGINAL="${TEST_OBELISK_ROOT}"
    TEST_OBELISK_ROOT="${managed_root}"
    prepare_posture_root "${TEST_OBELISK_ROOT}"
    rm -rf "${TEST_OBELISK_ROOT}/${managed_dir}"
    managed_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
    write_proc_fixture "${managed_dir_pid}" "${managed_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1"
    expect_failure "missing-managed-dir-${managed_dir_label}-for-stable" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${managed_dir_pid}" --expect-stable --instance arkserver
    TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_MANAGED_ORIGINAL}"
    managed_dir_pid=$((managed_dir_pid + 1))

    managed_root="${TMP_DIR}/root-symlink-managed-${managed_dir_label}"
    TEST_OBELISK_ROOT="${managed_root}"
    prepare_posture_root "${TEST_OBELISK_ROOT}"
    rm -rf "${TEST_OBELISK_ROOT}/${managed_dir}"
    mkdir -p "$(dirname "${TEST_OBELISK_ROOT}/${managed_dir}")" \
        "${TMP_DIR}/external-managed-${managed_dir_label}"
    ln -s "${TMP_DIR}/external-managed-${managed_dir_label}" \
        "${TEST_OBELISK_ROOT}/${managed_dir}"
    managed_maps="7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so"
    write_proc_fixture "${managed_dir_pid}" "${managed_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1"
    expect_failure "symlink-managed-dir-${managed_dir_label}-for-stable" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${managed_dir_pid}" --expect-stable --instance arkserver
    TEST_OBELISK_ROOT="${TEST_OBELISK_ROOT_MANAGED_ORIGINAL}"
    managed_dir_pid=$((managed_dir_pid + 1))
done
unset managed_dir managed_dir_label managed_root managed_maps managed_dir_pid TEST_OBELISK_ROOT_MANAGED_ORIGINAL

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

write_proc_fixture 116 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_ITEM_RETURN_EVENTS=1" \
    "OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=abc123" \
    "OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=25" \
    "OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT=5"
expect_failure item-return-events-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 116 --expect-stable --instance arkserver

write_proc_fixture 117 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0"
expect_failure player-principal-lifecycle-observer-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 117 --expect-stable --instance arkserver

residual_player_principal_env_pid=170
for residual_player_principal_env_name in \
    OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT
do
    case "${residual_player_principal_env_name}" in
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256)
            residual_player_principal_env_value="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
            ;;
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT)
            residual_player_principal_env_value="10"
            ;;
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT)
            residual_player_principal_env_value="0"
            ;;
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT)
            residual_player_principal_env_value="10000"
            ;;
        *)
            residual_player_principal_env_value="1"
            ;;
    esac
    write_proc_fixture "${residual_player_principal_env_pid}" "${stable_maps}" \
        "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1" \
        "${residual_player_principal_env_name}=${residual_player_principal_env_value}"
    expect_failure "player-principal-lifecycle-residual-env-${residual_player_principal_env_name}-forbidden-for-stable" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid "${residual_player_principal_env_pid}" --expect-stable --instance arkserver
    residual_player_principal_env_pid=$((residual_player_principal_env_pid + 1))
done
unset residual_player_principal_env_name residual_player_principal_env_value residual_player_principal_env_pid

write_proc_fixture 123 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1"
expect_failure player-principal-lifecycle-diagnostic-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 123 --expect-stable --instance arkserver

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

write_proc_fixture 122 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_CHAT_ROUTE_OBSERVER=1" \
    "OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=2"
expect_failure chat-route-observer-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 122 --expect-stable --instance arkserver
expect_failure chat-route-observer-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 122 --expect-stable --forbid-chat-reflection --instance arkserver

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

write_proc_fixture 1131 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1"
expect_failure filtered-process-event-callbacks-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1131 --expect-stable --instance arkserver

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

write_proc_fixture 1031 "7f000000-7f001000 r-xp 00000000 00:00 0 ${TEST_OBELISK_ROOT}/lib/libobelisk.so.backup" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1"
expect_failure runtime-mapping-requires-exact-path \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 1031 --expect-stable --instance arkserver

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
    allow-filtered-process-event-callbacks \
    allow-call-process-event \
    allow-process-event-blocking \
    enable-chat-events \
    enable-chat-reflection \
    enable-chat-route-observer \
    enable-inventory-reflection \
    enable-structure-reflection \
    enable-item-return-events \
    enable-player-principal-lifecycle-observer \
    enable-inventory-action-redacted-observer \
    enable-reflection-scanner
do
    : > "${TEST_OBELISK_ROOT}/state/instances/arkserver/${marker}"
    expect_failure "forbidden-marker-${marker}" \
        "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
    rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/${marker}"
done

write_proc_fixture 242 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER=1" \
    "OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520" \
    "OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT=1" \
    "OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT=0"
expect_failure inventory-action-redacted-observer-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 242 --expect-stable --instance arkserver

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe"
expect_failure active-debug-request-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
mv "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe.done.1234"
expect_success completed-debug-request-marker-allowed-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/request-static-fname-probe.done.1234"

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"
expect_failure unknown-observer-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-future-observer"

write_proc_fixture 124 "${stable_maps}" \
    "LD_PRELOAD=${TEST_OBELISK_ROOT}/lib/libobelisk.so" \
    "OBELISK_INSTANCE_ID=arkserver" \
    "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
    "OBELISK_DISABLE_PLUGINS=1" \
    "OBELISK_ENABLE_FUTURE_OBSERVER=1"
expect_failure unknown-observer-env-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 124 --expect-stable --instance arkserver

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

: > "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-item-return-events"
expect_failure item-return-events-marker-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-item-return-events"

: > "${TMP_DIR}/external-player-principal-lifecycle-marker"
ln -s "${TMP_DIR}/external-player-principal-lifecycle-marker" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_failure player-principal-lifecycle-marker-symlink-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"

mkdir -p "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_failure player-principal-lifecycle-marker-directory-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -rf "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"

ln -s "${TMP_DIR}/missing-player-principal-lifecycle-marker" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_failure player-principal-lifecycle-marker-broken-symlink-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-player-principal-lifecycle-observer"

: > "${TMP_DIR}/external-chat-route-marker"
ln -s "${TMP_DIR}/external-chat-route-marker" \
    "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-route-observer"
expect_failure chat-route-marker-symlink-forbidden-for-stable \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --instance arkserver
expect_failure chat-route-marker-symlink-forbidden-for-stable-legacy-flag \
    "${SCRIPT}" --proc-root "${TMP_DIR}/proc" --pid 101 --expect-stable --forbid-chat-reflection --instance arkserver
rm -f "${TEST_OBELISK_ROOT}/state/instances/arkserver/enable-chat-route-observer"

echo "check_obelisk_server_posture offline tests passed"
