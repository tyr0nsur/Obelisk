#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CHECK="${SCRIPT_DIR}/check_player_principal_lifecycle_preflight.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

assert_fail() {
    local name="$1"
    shift
    if "$@" >"${TMP_DIR}/${name}.out" 2>"${TMP_DIR}/${name}.err"; then
        echo "Expected failure for ${name}" >&2
        exit 1
    fi
}

prepare_root() {
    local root="$1"
    mkdir -p "${root}/"{lib,plugins,config,logs,state/instances/arkserver2}
    : > "${root}/lib/libobelisk.so"
    : > "${root}/state/instances/arkserver2/enable-process-event-hook"
    : > "${root}/state/instances/arkserver2/disable-plugins"
}

write_proc_fixture() {
    local proc_root="$1"
    local pid="$2"
    local root="$3"
    local map="$4"

    mkdir -p "${proc_root}/${pid}"
    printf '%s\0' \
        "${server_binary}" \
        "${map}?SessionName=ObeliskPreflight" \
        > "${proc_root}/${pid}/cmdline"
    printf '%s\0' \
        "OBELISK_ROOT=${root}" \
        "LD_PRELOAD=${root}/lib/libobelisk.so" \
        "OBELISK_INSTANCE_ID=arkserver2" \
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1" \
        "OBELISK_DISABLE_PLUGINS=1" \
        > "${proc_root}/${pid}/environ"
    printf '7f000000-7f001000 r-xp 00000000 00:00 0 %s/lib/libobelisk.so\n' "${root}" \
        > "${proc_root}/${pid}/maps"
}

make_server_binary() {
    local path="$1"
    printf 'ShooterGameServer fixture\n' > "${path}"
    sha256sum "${path}" | awk '{print $1}'
}

write_observer_env() {
    local path="$1"
    local sha="$2"
    cat > "${path}" <<EOF
OBELISK_INSTANCE_ID=arkserver2
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_WRAPPER_PROFILE=observer-debug
OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=${sha}
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10
OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0
OBELISK_PE_TRACE_LIMIT=0
EOF
}

write_diagnostic_observer_env() {
    local path="$1"
    local sha="$2"
    write_observer_env "${path}" "${sha}"
    printf 'OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1\n' >> "${path}"
}

make_fake_preflight_script_dir() {
    local script_dir="$1"

    mkdir -p "${script_dir}"
    cp "${CHECK}" "${script_dir}/check_player_principal_lifecycle_preflight.sh"
    chmod +x "${script_dir}/check_player_principal_lifecycle_preflight.sh"
    cat > "${script_dir}/check_linuxgsm_wrapper_drift.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exit 0
EOF
    cat > "${script_dir}/check_obelisk_server_posture.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${FAKE_POSTURE_ARGS_FILE:?missing FAKE_POSTURE_ARGS_FILE}"
for arg in "$@"; do
    printf '%s\n' "$arg"
done > "${FAKE_POSTURE_ARGS_FILE}"
EOF
    chmod +x \
        "${script_dir}/check_linuxgsm_wrapper_drift.sh" \
        "${script_dir}/check_obelisk_server_posture.sh"
}

wrapper="${TMP_DIR}/ObeliskRun.sh"
cp "${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh" "${wrapper}"
server_binary="${TMP_DIR}/ShooterGameServer"
server_sha="$(make_server_binary "${server_binary}")"
run_id="20260601T120000Z-player-principal-lifecycle"
evidence_dir="${TMP_DIR}/live-validation-logs/${run_id}"
copied_log="${evidence_dir}/Obelisk.log"
window_manifest="${evidence_dir}/window-manifest.env"
mkdir -p "${evidence_dir}"

root_stable="${TMP_DIR}/root-stable"
prepare_root "${root_stable}"
"${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=stable instance=arkserver2' >/dev/null

"${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "${run_id}" \
    --window-manifest "${window_manifest}" \
    --copied-log "${copied_log}" \
    --evidence-dir "${evidence_dir}" \
    --offline-only \
    --allow-stopped \
    --json > "${TMP_DIR}/stable-preflight.json"
python3 - "${TMP_DIR}/stable-preflight.json" "${server_sha}" "${run_id}" "${window_manifest}" "${copied_log}" "${evidence_dir}" <<'PY'
from datetime import datetime, timezone
import json
import sys

path, server_sha, run_id, window_manifest, copied_log, evidence_dir = sys.argv[1:]
payload = json.loads(open(path, encoding="utf-8").read())
required_false_flags = (
    "server_operations_authorized",
    "runtime_work_authorized",
    "request_pack_counts_as_approved_runtime_evidence",
    "observer_env_counts_as_approved_runtime_evidence",
    "operator_request_counts_as_approved_runtime_evidence",
    "copied_log_metadata_counts_as_approved_runtime_evidence",
    "copied_log_presence_counts_as_approved_runtime_evidence",
    "bundle_output_counts_as_approved_runtime_evidence",
    "dry_run_success_counts_as_approved_runtime_evidence",
    "historical_target_names_authorize_runtime",
    "marker_env_readiness_counts_as_approved_runtime_evidence",
    "player_notice_counts_as_approved_runtime_evidence",
    "public_reachability_counts_as_approved_runtime_evidence",
    "preflight_counts_as_approved_runtime_evidence",
    "window_manifest_counts_as_approved_runtime_evidence",
    "completed_receipt_counts_as_approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "runtime_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "promotion_ready",
    "public_header_allowed",
    "v1_completion_ready",
    "stable_claim_allowed",
    "route_ready",
    "sdk_accounting_counts_as_completed_surface",
    "p0_accounting_counts_as_promoted_surface",
    "current_turn_authorized",
    "current_turn_approval_recorded",
)
assert payload["schema"] == "obelisk.player-principal-lifecycle-preflight.v1"
assert payload["status"] == "preflight_passed_no_runtime_approval_or_evidence"
assert payload["ready"] is True
assert payload["ready_scope"] == "offline_preflight_checks_only"
assert payload["preflight_passed"] is True
assert payload["current_turn_operator_approval_required"] is True
for flag in required_false_flags:
    assert payload[flag] is False, flag
assert payload["mode"] == "stable"
assert payload["instance"] == "arkserver2"
assert payload["map"] == "TheIsland"
assert payload["run_id"] == run_id
assert payload["target"] == {"instance": "arkserver2", "map": "TheIsland"}
assert payload["window_manifest_path"] == window_manifest
assert payload["copied_log_path"] == copied_log
assert payload["copied_evidence_dir"] == evidence_dir
assert payload["server_binary"]["sha256"] == server_sha
assert payload["env_file"] is None
assert payload["authorization_source"] == "none_preflight_sidecar_only"
assert payload["approved_runtime_evidence_source"] == "none_preflight_sidecar_only"
assert payload["preflight_records_current_turn_approval"] is False
assert payload["current_turn_approval_scope_status"] == "requires_exact_current_turn_operator_approval"
assert payload["current_turn_approval_required_fields"] == [
    "target",
    "marker_env_gates",
    "restart_window",
    "rollback",
    "evidence_paths",
    "final_posture",
]
assert payload["deployment_intent"]["intent_type"] == "lifecycle_anchor_drift_fix_deploy_request_only"
assert payload["deployment_intent"]["request_only"] is True
assert payload["deployment_intent"]["deployment_authorized"] is False
assert payload["deployment_intent"]["restart_authorized"] is False
assert payload["deployment_intent"]["runtime_capture_authorized"] is False
assert payload["deployment_intent"]["counts_as_approved_runtime_evidence"] is False
assert "does not authorize deployment" in payload["deployment_intent"]["non_authorization"]
assert datetime.fromisoformat(payload["checked_at_utc"].removesuffix("Z") + "+00:00").tzinfo == timezone.utc
assert "not runtime approval" in payload["non_claim"]
assert "not approved runtime evidence" in payload["non_claim"]
assert "preflight does not count as approved runtime evidence" in payload["non_claims"][2]
assert payload["live_procfs_read_acknowledged"] is False
assert payload["protected_root_validation_acknowledged"] is False
assert payload["live_read_acknowledgement_counts_as_authorization"] is False
PY

assert_fail protected-root-without-ack "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F -- 'Obelisk root must not read from protected server root /servidor/ark without --allow-protected-root' \
    "${TMP_DIR}/protected-root-without-ack.err" >/dev/null

assert_fail live-procfs-read-without-ack "${CHECK}" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F -- 'must not read the live /proc tree without --allow-live-procfs-read' \
    "${TMP_DIR}/live-procfs-read-without-ack.err" >/dev/null

assert_fail protected-proc-root-rejected "${CHECK}" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --proc-root /servidor/ark/workspace-offline/proc \
    --allow-live-procfs-read \
    --allow-stopped
grep -F -- '--proc-root must not read from protected server root /servidor/ark' \
    "${TMP_DIR}/protected-proc-root-rejected.err" >/dev/null

proc_root="${TMP_DIR}/proc"
write_proc_fixture "${proc_root}" 4242 "${root_stable}" "TheIsland"
"${CHECK}" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --proc-root "${proc_root}" \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=stable instance=arkserver2' >/dev/null

fake_script_dir="${TMP_DIR}/fake-preflight-script-dir"
make_fake_preflight_script_dir "${fake_script_dir}"
stable_posture_args="${TMP_DIR}/stable-posture-args.txt"
env FAKE_POSTURE_ARGS_FILE="${stable_posture_args}" \
    "${fake_script_dir}/check_player_principal_lifecycle_preflight.sh" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --proc-root "${proc_root}" \
    --allow-live-procfs-read \
    --allow-protected-root \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=stable instance=arkserver2' >/dev/null
python3 - "${stable_posture_args}" "${proc_root}" <<'PY'
import sys

path, proc_root = sys.argv[1:]
args = open(path, encoding="utf-8").read().splitlines()
assert args == [
    "--expect-stable",
    "--pid",
    "4242",
    "--instance",
    "arkserver2",
    "--proc-root",
    proc_root,
    "--allow-live-procfs-read",
    "--allow-protected-root",
]
PY

root_window="${TMP_DIR}/root-window"
observer_env="${TMP_DIR}/observer-window.env"
prepare_root "${root_window}"
: > "${root_window}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_window}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_window}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
write_observer_env "${observer_env}" "${server_sha}"
"${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${observer_env}" \
    --allow-stopped \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2' >/dev/null

"${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${observer_env}" \
    --run-id "${run_id}" \
    --window-manifest "${window_manifest}" \
    --copied-log "${copied_log}" \
    --evidence-dir "${evidence_dir}" \
    --allow-stopped \
    --json > "${TMP_DIR}/observer-preflight.json"
python3 - "${TMP_DIR}/observer-preflight.json" "${observer_env}" "${run_id}" <<'PY'
import hashlib
import json
import sys

path, env_path, run_id = sys.argv[1:]
payload = json.loads(open(path, encoding="utf-8").read())
required_false_flags = (
    "server_operations_authorized",
    "runtime_work_authorized",
    "request_pack_counts_as_approved_runtime_evidence",
    "observer_env_counts_as_approved_runtime_evidence",
    "operator_request_counts_as_approved_runtime_evidence",
    "copied_log_metadata_counts_as_approved_runtime_evidence",
    "copied_log_presence_counts_as_approved_runtime_evidence",
    "bundle_output_counts_as_approved_runtime_evidence",
    "dry_run_success_counts_as_approved_runtime_evidence",
    "historical_target_names_authorize_runtime",
    "marker_env_readiness_counts_as_approved_runtime_evidence",
    "player_notice_counts_as_approved_runtime_evidence",
    "public_reachability_counts_as_approved_runtime_evidence",
    "preflight_counts_as_approved_runtime_evidence",
    "window_manifest_counts_as_approved_runtime_evidence",
    "completed_receipt_counts_as_approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "runtime_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "promotion_ready",
    "public_header_allowed",
    "v1_completion_ready",
    "stable_claim_allowed",
    "route_ready",
    "sdk_accounting_counts_as_completed_surface",
    "p0_accounting_counts_as_promoted_surface",
    "current_turn_authorized",
    "current_turn_approval_recorded",
)
assert payload["ready"] is True
assert payload["ready_scope"] == "offline_preflight_checks_only"
assert payload["preflight_passed"] is True
assert payload["current_turn_operator_approval_required"] is True
for flag in required_false_flags:
    assert payload[flag] is False, flag
assert payload["mode"] == "observer-window"
assert payload["run_id"] == run_id
assert payload["target"] == {"instance": "arkserver2", "map": "TheIsland"}
assert payload["env_file"]["path"] == env_path
assert payload["env_file"]["sha256"] == hashlib.sha256(open(env_path, "rb").read()).hexdigest()
assert payload["posture_check"] == "accepted"
assert payload["authorization_source"] == "none_preflight_sidecar_only"
assert payload["approved_runtime_evidence_source"] == "none_preflight_sidecar_only"
assert payload["preflight_records_current_turn_approval"] is False
assert payload["diagnostic_candidates_enabled"] is False
assert payload["current_turn_approval_scope_status"] == "requires_exact_current_turn_operator_approval"
assert payload["deployment_intent"]["intent_type"] == "lifecycle_anchor_drift_fix_deploy_request_only"
assert payload["deployment_intent"]["request_only"] is True
assert payload["deployment_intent"]["deployment_authorized"] is False
assert payload["deployment_intent"]["counts_as_approved_runtime_evidence"] is False
assert "preflight does not authorize deployment" in payload["non_claims"][1]
assert payload["live_procfs_read_acknowledged"] is False
assert payload["protected_root_validation_acknowledged"] is False
assert payload["live_read_acknowledgement_counts_as_authorization"] is False
PY

observer_posture_args="${TMP_DIR}/observer-posture-args.txt"
env FAKE_POSTURE_ARGS_FILE="${observer_posture_args}" \
    "${fake_script_dir}/check_player_principal_lifecycle_preflight.sh" \
    --instance arkserver2 \
    --map TheIsland \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${observer_env}" \
    --proc-root "${proc_root}" \
    --allow-live-procfs-read \
    --allow-protected-root \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2' >/dev/null
python3 - "${observer_posture_args}" "${proc_root}" <<'PY'
import sys

path, proc_root = sys.argv[1:]
args = open(path, encoding="utf-8").read().splitlines()
assert args == [
    "--expect-observer-debug",
    "--pid",
    "4242",
    "--instance",
    "arkserver2",
    "--proc-root",
    proc_root,
    "--allow-live-procfs-read",
    "--allow-protected-root",
]
PY

diagnostic_observer_env="${TMP_DIR}/observer-window-diagnostic.env"
write_diagnostic_observer_env "${diagnostic_observer_env}" "${server_sha}"
"${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${diagnostic_observer_env}" \
    --run-id "${run_id}" \
    --window-manifest "${window_manifest}" \
    --copied-log "${copied_log}" \
    --evidence-dir "${evidence_dir}" \
    --allow-stopped \
    --allow-diagnostic-candidates \
    --json > "${TMP_DIR}/diagnostic-observer-preflight.json"
python3 - "${TMP_DIR}/diagnostic-observer-preflight.json" <<'PY'
import json
import sys

payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert payload["ready"] is True
assert payload["ready_scope"] == "offline_preflight_checks_only"
assert payload["preflight_passed"] is True
assert payload["mode"] == "observer-window"
assert payload["diagnostic_candidates_enabled"] is True
assert payload["approved_runtime_evidence_present"] is False
assert payload["runtime_ready"] is False
assert payload["public_sdk_ready"] is False
assert payload["deployment_intent"]["request_only"] is True
assert payload["deployment_intent"]["deployment_authorized"] is False
assert payload["deployment_intent"]["counts_as_approved_runtime_evidence"] is False
assert payload["live_read_acknowledgement_counts_as_authorization"] is False
PY

assert_fail observer-window-diagnostic-env-without-allow "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${diagnostic_observer_env}" \
    --allow-stopped
grep -F 'Forbidden env exists for player-principal preflight: OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES' \
    "${TMP_DIR}/observer-window-diagnostic-env-without-allow.err" >/dev/null

assert_fail observer-window-missing-diagnostic-env-with-allow "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${observer_env}" \
    --allow-stopped \
    --allow-diagnostic-candidates
grep -F 'Required env is missing from' \
    "${TMP_DIR}/observer-window-missing-diagnostic-env-with-allow.err" >/dev/null

assert_fail stable-diagnostic-allow-invalid "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped \
    --allow-diagnostic-candidates
grep -F -- '--allow-diagnostic-candidates is only valid with --mode observer-window' \
    "${TMP_DIR}/stable-diagnostic-allow-invalid.err" >/dev/null

assert_fail observer-window-missing-env "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F -- '--mode observer-window requires --env-file' "${TMP_DIR}/observer-window-missing-env.err" >/dev/null

root_residual="${TMP_DIR}/root-residual"
prepare_root "${root_residual}"
: > "${root_residual}/state/instances/arkserver2/enable-reflection-scanner"
assert_fail residual-marker "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_residual}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Forbidden marker exists' "${TMP_DIR}/residual-marker.err" >/dev/null

root_debug_request="${TMP_DIR}/root-debug-request"
prepare_root "${root_debug_request}"
: > "${root_debug_request}/state/instances/arkserver2/request-static-fname-probe"
assert_fail debug-request-marker "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_debug_request}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Forbidden marker exists' "${TMP_DIR}/debug-request-marker.err" >/dev/null

root_unexpected_marker="${TMP_DIR}/root-unexpected-marker"
prepare_root "${root_unexpected_marker}"
: > "${root_unexpected_marker}/state/instances/arkserver2/local-test-marker"
assert_fail unexpected-marker "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_unexpected_marker}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Unexpected marker exists' "${TMP_DIR}/unexpected-marker.err" >/dev/null

root_suffix_marker="${TMP_DIR}/root-suffix-marker"
prepare_root "${root_suffix_marker}"
: > "${root_suffix_marker}/state/instances/arkserver2/process-event-hook"
assert_fail suffix-marker "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_suffix_marker}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Unexpected marker exists' "${TMP_DIR}/suffix-marker.err" >/dev/null

root_unexpected_dir="${TMP_DIR}/root-unexpected-dir"
prepare_root "${root_unexpected_dir}"
mkdir -p "${root_unexpected_dir}/state/instances/arkserver2/enable-process-event-hook-dir"
assert_fail unexpected-marker-dir "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_unexpected_dir}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Unexpected marker exists' "${TMP_DIR}/unexpected-marker-dir.err" >/dev/null

root_symlink="${TMP_DIR}/root-symlink"
prepare_root "${root_symlink}"
: > "${TMP_DIR}/external-marker"
ln -s "${TMP_DIR}/external-marker" "${root_symlink}/state/instances/arkserver2/allow-call-process-event"
assert_fail symlink-marker "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_symlink}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Forbidden marker exists' "${TMP_DIR}/symlink-marker.err" >/dev/null

bad_observer_env="${TMP_DIR}/observer-window-bad-log.env"
write_observer_env "${bad_observer_env}" "${server_sha}"
sed -i 's/^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=.*/OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=2/' \
    "${bad_observer_env}"
assert_fail observer-window-bad-log-env "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${bad_observer_env}" \
    --allow-stopped
grep -F "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT must be '10'" \
    "${TMP_DIR}/observer-window-bad-log-env.err" >/dev/null

forbidden_observer_env="${TMP_DIR}/observer-window-forbidden.env"
write_observer_env "${forbidden_observer_env}" "${server_sha}"
printf 'OBELISK_ENABLE_CHAT_EVENTS=1\n' >> "${forbidden_observer_env}"
assert_fail observer-window-forbidden-env "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${forbidden_observer_env}" \
    --allow-stopped
grep -F 'Forbidden env exists for player-principal preflight: OBELISK_ENABLE_CHAT_EVENTS' \
    "${TMP_DIR}/observer-window-forbidden-env.err" >/dev/null

for forbidden_launch_key in \
    LD_PRELOAD \
    LD_LIBRARY_PATH \
    OBELISK_ROOT \
    OBELISK_PLUGIN_DIR \
    OBELISK_CONFIG_DIR \
    OBELISK_LOG_DIR
do
    launch_env="${TMP_DIR}/observer-window-forbidden-${forbidden_launch_key}.env"
    write_observer_env "${launch_env}" "${server_sha}"
    printf '%s=%s\n' "${forbidden_launch_key}" "${root_window}" >> "${launch_env}"
    assert_fail "observer-window-forbidden-${forbidden_launch_key}" "${CHECK}" \
        --instance arkserver2 \
        --mode observer-window \
        --obelisk-root "${root_window}" \
        --installed-wrapper "${wrapper}" \
        --server-binary "${server_binary}" \
        --expected-binary-sha256 "${server_sha}" \
        --env-file "${launch_env}" \
        --allow-stopped
    grep -F "Forbidden env exists for player-principal preflight: ${forbidden_launch_key}" \
        "${TMP_DIR}/observer-window-forbidden-${forbidden_launch_key}.err" >/dev/null
done

duplicate_observer_env="${TMP_DIR}/observer-window-duplicate.env"
write_observer_env "${duplicate_observer_env}" "${server_sha}"
printf 'OBELISK_PE_TRACE_LIMIT=0\n' >> "${duplicate_observer_env}"
assert_fail observer-window-duplicate-env "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${duplicate_observer_env}" \
    --allow-stopped
grep -F 'Env file contains duplicate key: OBELISK_PE_TRACE_LIMIT' \
    "${TMP_DIR}/observer-window-duplicate-env.err" >/dev/null

future_observer_env="${TMP_DIR}/observer-window-future-observer.env"
write_observer_env "${future_observer_env}" "${server_sha}"
printf 'OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER=1\n' >> "${future_observer_env}"
assert_fail observer-window-future-observer-env "${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --env-file "${future_observer_env}" \
    --allow-stopped
grep -F 'Unexpected env key for exact player-principal preflight: OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER' \
    "${TMP_DIR}/observer-window-future-observer-env.err" >/dev/null

assert_fail bad-sha "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 0000000000000000000000000000000000000000000000000000000000000000 \
    --allow-stopped
grep -F 'SHA256 mismatch' "${TMP_DIR}/bad-sha.err" >/dev/null

assert_fail stopped-without-allow "${CHECK}" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --proc-root "${TMP_DIR}/empty-proc"
grep -F 'pass --allow-stopped' "${TMP_DIR}/stopped-without-allow.err" >/dev/null

assert_fail unsafe-map "${CHECK}" \
    --instance arkserver2 \
    --map 'TheIsland.*' \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Invalid map name' "${TMP_DIR}/unsafe-map.err" >/dev/null

assert_fail unsafe-target-map "${CHECK}" \
    --instance arkserver2 \
    --target-map 'TheIsland.*' \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped
grep -F 'Invalid target map name' "${TMP_DIR}/unsafe-target-map.err" >/dev/null

assert_fail partial-binding "${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "${run_id}" \
    --allow-stopped
grep -F 'Evidence binding requires' "${TMP_DIR}/partial-binding.err" >/dev/null

assert_fail bad-run-id "${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "bad-run" \
    --window-manifest "${window_manifest}" \
    --copied-log "${copied_log}" \
    --evidence-dir "${evidence_dir}" \
    --allow-stopped
grep -F 'Invalid run id' "${TMP_DIR}/bad-run-id.err" >/dev/null

assert_fail bad-evidence-dir-shape "${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "${run_id}" \
    --window-manifest "${window_manifest}" \
    --copied-log "${copied_log}" \
    --evidence-dir "${TMP_DIR}/wrong/${run_id}" \
    --allow-stopped
grep -F -- '--evidence-dir must end with live-validation-logs' "${TMP_DIR}/bad-evidence-dir-shape.err" >/dev/null

assert_fail copied-log-mismatch "${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "${run_id}" \
    --window-manifest "${window_manifest}" \
    --copied-log "${evidence_dir}/Other.log" \
    --evidence-dir "${evidence_dir}" \
    --allow-stopped
grep -F -- '--copied-log must equal --evidence-dir/Obelisk.log' "${TMP_DIR}/copied-log-mismatch.err" >/dev/null

assert_fail window-manifest-mismatch "${CHECK}" \
    --instance arkserver2 \
    --target-map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --run-id "${run_id}" \
    --window-manifest "${evidence_dir}/other.env" \
    --copied-log "${copied_log}" \
    --evidence-dir "${evidence_dir}" \
    --allow-stopped
grep -F -- '--window-manifest must equal --evidence-dir/window-manifest.env' "${TMP_DIR}/window-manifest-mismatch.err" >/dev/null

assert_fail offline-only-live-path "${CHECK}" \
    --instance arkserver2 \
    --mode stable \
    --expected-binary-sha256 0000000000000000000000000000000000000000000000000000000000000000 \
    --offline-only \
    --allow-stopped
grep -F 'Obelisk root must be an offline copy, not a live server path' "${TMP_DIR}/offline-only-live-path.err" >/dev/null

assert_fail offline-only-map "${CHECK}" \
    --instance arkserver2 \
    --map TheIsland \
    --mode stable \
    --obelisk-root "${root_stable}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --offline-only
grep -F -- '--offline-only rejects --map' "${TMP_DIR}/offline-only-map.err" >/dev/null

echo "test_check_player_principal_lifecycle_preflight passed"
