#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage:
  scripts/monitor_ark_player_presence_passive.sh [--interval seconds] [--once] [--no-details] [--linger-after-detect seconds] [--snapshot-output-root path] [--snapshot-monitor-log path] [--active-monitor-pid pid] [--replacement-requested] [--replacement-note text] INSTANCE:MAP[:QUERY_PORT] [...]

Passive ARK player/observer monitor. It does not edit markers, start, stop, or restart
servers. It prefers GameDig Steam query and treats query errors as unknown, never as zero.
It never calls LinuxGSM monitor/details/lifecycle commands.
--no-details is accepted for compatibility; LinuxGSM details are always disabled.
Use --linger-after-detect to keep tailing observer lines briefly after player presence is
first detected, so delayed lifecycle diagnostics are not missed.
Use --snapshot-output-root to copy/analyze one passive snapshot per target when player
presence is newly detected. A target can snapshot again after presence clears and is
newly detected later. The snapshot helper refuses protected server output paths and does
not edit markers or operate servers.
Use --snapshot-monitor-log to tee this monitor transcript to a path the snapshot helper
can copy into passive snapshots; launcher stdout capture remains unchanged.
Use --active-monitor-pid to record an existing passive monitor as metadata only. This
script never signals, stops, replaces, or detaches another monitor process.
--replacement-requested records an operator-requested handoff flag as metadata only; it
does not enable process control.

Test/offline path overrides:
  OBELISK_PASSIVE_MONITOR_ARK_ROOT    Default: /servidor/ark
  OBELISK_PASSIVE_MONITOR_GAMEDIG     Default: <ark-root>/lgsm/node_modules/gamedig/bin/gamedig.js
  OBELISK_PASSIVE_MONITOR_LOG_ROOT    Default: <ark-root>/obelisk/logs
  OBELISK_PASSIVE_MONITOR_RCON_ENABLED
                                      auto/off/on. Default: auto. Uses redacted
                                      ListPlayers only when available.
  OBELISK_PASSIVE_MONITOR_RCON_HELPER  Default: /home/flowcommunity-ark/dashboard/server/test_rcon.js
  OBELISK_PASSIVE_MONITOR_RCON_HOST    Default: 127.0.0.1
  OBELISK_PASSIVE_MONITOR_RCON_INI_PATH
                                      Default: <ark-root>/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
  OBELISK_PASSIVE_MONITOR_RCON_TIMEOUT_SECONDS
                                      Default: 5
  OBELISK_PASSIVE_MONITOR_SESSION_ID  Optional stable session label emitted in logs.
  OBELISK_PASSIVE_MONITOR_REPLACED_PID
                                      Legacy metadata-only active monitor PID.
  OBELISK_PASSIVE_MONITOR_ACTIVE_MONITOR_PID
                                      Metadata-only active monitor PID.
  OBELISK_PASSIVE_MONITOR_TMUX_SESSION
                                      Optional tmux session label when tmux cannot report it.
  OBELISK_PASSIVE_MONITOR_TMUX_SOCKET
                                      Optional tmux socket path when TMUX is unavailable.
  OBELISK_PASSIVE_MONITOR_TMUX_SOCKET_NAME
                                      Optional tmux socket name, for -L socket visibility.

Examples:
  scripts/monitor_ark_player_presence_passive.sh --once arkserver:Ragnarok arkserver2:TheIsland
  scripts/monitor_ark_player_presence_passive.sh --interval 60 arkserver:Ragnarok arkserver2:TheIsland
USAGE
}

interval=60
once=false
no_details=false
linger_after_detect=0
linger_until=0
linger_target_keys_csv="none"
linger_detected_instances_csv="none"
snapshot_output_root=""
snapshot_monitor_log=""
snapshot_sequence=0
active_monitor_pid=""
replacement_note=""
replacement_requested=false
declare -a targets=()
declare -A target_presence_active=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)
            if [[ $# -lt 2 || ! "$2" =~ ^[0-9]+$ || "$2" -lt 5 ]]; then
                echo "error: --interval requires an integer >= 5" >&2
                exit 2
            fi
            interval="$2"
            shift 2
            ;;
        --once)
            once=true
            shift
            ;;
        --no-details)
            no_details=true
            shift
            ;;
        --linger-after-detect)
            if [[ $# -lt 2 || ! "$2" =~ ^[0-9]+$ ]]; then
                echo "error: --linger-after-detect requires an integer >= 0" >&2
                exit 2
            fi
            linger_after_detect="$2"
            shift 2
            ;;
        --snapshot-output-root)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "error: --snapshot-output-root requires a path" >&2
                exit 2
            fi
            snapshot_output_root="$2"
            shift 2
            ;;
        --snapshot-monitor-log)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "error: --snapshot-monitor-log requires a path" >&2
                exit 2
            fi
            snapshot_monitor_log="$2"
            shift 2
            ;;
        --active-monitor-pid)
            if [[ $# -lt 2 || ! "$2" =~ ^[0-9]+$ ]]; then
                echo "error: --active-monitor-pid requires an integer PID" >&2
                exit 2
            fi
            active_monitor_pid="$2"
            shift 2
            ;;
        --replacement-note)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "error: --replacement-note requires text" >&2
                exit 2
            fi
            replacement_note="$2"
            shift 2
            ;;
        --replacement-requested)
            replacement_requested=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            while [[ $# -gt 0 ]]; do
                targets+=("$1")
                shift
            done
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            targets+=("$1")
            shift
            ;;
    esac
done

if [[ ${#targets[@]} -eq 0 ]]; then
    echo "error: at least one INSTANCE:MAP target is required" >&2
    usage >&2
    exit 2
fi

ark_root="${OBELISK_PASSIVE_MONITOR_ARK_ROOT:-/servidor/ark}"
gamedig_bin="${OBELISK_PASSIVE_MONITOR_GAMEDIG:-${ark_root}/lgsm/node_modules/gamedig/bin/gamedig.js}"
obelisk_log_root="${OBELISK_PASSIVE_MONITOR_LOG_ROOT:-${ark_root}/obelisk/logs}"
rcon_enabled="${OBELISK_PASSIVE_MONITOR_RCON_ENABLED:-auto}"
rcon_helper="${OBELISK_PASSIVE_MONITOR_RCON_HELPER:-/home/flowcommunity-ark/dashboard/server/test_rcon.js}"
rcon_host="${OBELISK_PASSIVE_MONITOR_RCON_HOST:-127.0.0.1}"
rcon_ini_path="${OBELISK_PASSIVE_MONITOR_RCON_INI_PATH:-${ark_root}/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini}"
rcon_timeout_seconds="${OBELISK_PASSIVE_MONITOR_RCON_TIMEOUT_SECONDS:-5}"
observer_tail_scan_lines=200
observer_tail_limit=10
observer_gate_line_pattern='PlayerPrincipalLifecycleObserver enabled'
observer_event_line_pattern='PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=(session_start|session_end|session_start_rejected)'
observer_session_start_candidate_pattern='PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_start target=ShooterGameMode\.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,1 redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=candidate_created apply_status=session_start_created correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none\.?'
observer_check_join_rejected_candidate_pattern='PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_start_rejected target=ShooterGameMode\.CheckJoinInProgress post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=1,0 redacted_count=1 redacted_fields=NewPlayer principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none\.?'
observer_session_end_candidate_pattern='PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_end target=ShooterGameMode\.OnLogout post_original=true copied_bool_fields= copied_bool_values= redacted_count=1 redacted_fields=Exiting principal_action=candidate_invalidated apply_status=session_end_invalidated correlation_status=matched principal_id_logged=false principal_generation_logged=false delivery_claim=none\.?'
observer_superseded_handle_rejected_pattern='PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_start_rejected target=ShooterGameMode\.HandleNewPlayer post_original=true copied_bool_fields=bIsFromLogin,ReturnValue copied_bool_values=(0,0|0,1|1,0) redacted_count=3 redacted_fields=NewPlayer,PlayerData,PlayerCharacter principal_action=none apply_status=session_start_rejected_noop correlation_status=not_applicable principal_id_logged=false principal_generation_logged=false delivery_claim=none\.?'
observer_diagnostic_line_pattern='PlayerPrincipalLifecycleDiagnostic (candidate|function-FName near-miss logging enabled|route-sampling enabled|route-sample)'
observer_route_sample_line_pattern='PlayerPrincipalLifecycleDiagnostic route-sample '
observer_line_pattern="${observer_gate_line_pattern}|${observer_event_line_pattern}|${observer_diagnostic_line_pattern}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$ark_root" ]]; then
    echo "error: ARK root not found: $ark_root" >&2
    exit 2
fi
case "$rcon_enabled" in
    auto|on|off) ;;
    *)
        echo "error: OBELISK_PASSIVE_MONITOR_RCON_ENABLED must be auto, on, or off" >&2
        exit 2
        ;;
esac
if [[ ! "$rcon_timeout_seconds" =~ ^[0-9]+$ || "$rcon_timeout_seconds" -lt 1 || "$rcon_timeout_seconds" -gt 60 ]]; then
    echo "error: OBELISK_PASSIVE_MONITOR_RCON_TIMEOUT_SECONDS must be an integer from 1 to 60" >&2
    exit 2
fi

monitor_session_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
monitor_started_at_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
monitor_session_id="${OBELISK_PASSIVE_MONITOR_SESSION_ID:-passive-${monitor_session_stamp}-$$}"
if [[ -z "$active_monitor_pid" ]]; then
    active_monitor_pid="${OBELISK_PASSIVE_MONITOR_ACTIVE_MONITOR_PID:-${OBELISK_PASSIVE_MONITOR_REPLACED_PID:-none}}"
fi
if [[ -z "$active_monitor_pid" ]]; then
    active_monitor_pid="none"
fi
if [[ -z "$replacement_note" ]]; then
    replacement_note="${OBELISK_PASSIVE_MONITOR_REPLACEMENT_NOTE:-none}"
fi
case "${OBELISK_PASSIVE_MONITOR_REPLACEMENT_REQUESTED:-}" in
    1|true|TRUE|yes|YES) replacement_requested=true ;;
    ""|0|false|FALSE|no|NO) ;;
    *)
        echo "error: OBELISK_PASSIVE_MONITOR_REPLACEMENT_REQUESTED must be boolean-like" >&2
        exit 2
        ;;
esac
replaced_monitor_pid="$active_monitor_pid"
if [[ "$active_monitor_pid" != "none" && ! "$active_monitor_pid" =~ ^[0-9]+$ ]]; then
    echo "error: active monitor PID metadata must be an integer PID or none" >&2
    exit 2
fi

setup_snapshot_monitor_log() {
    local log_dir

    if [[ -z "$snapshot_monitor_log" ]]; then
        return 0
    fi

    if [[ "$snapshot_monitor_log" == */* ]]; then
        log_dir="${snapshot_monitor_log%/*}"
        if [[ -z "$log_dir" ]]; then
            log_dir="/"
        fi
    else
        log_dir="."
    fi

    if ! mkdir -p "$log_dir"; then
        echo "error: failed to create --snapshot-monitor-log directory: $log_dir" >&2
        exit 2
    fi
    if [[ -d "$snapshot_monitor_log" ]]; then
        echo "error: --snapshot-monitor-log path is a directory: $snapshot_monitor_log" >&2
        exit 2
    fi
    if ! : >> "$snapshot_monitor_log"; then
        echo "error: failed to open --snapshot-monitor-log for append: $snapshot_monitor_log" >&2
        exit 2
    fi

    if ! [[ /proc/$$/fd/1 -ef "$snapshot_monitor_log" ]]; then
        exec > >(tee -a "$snapshot_monitor_log")
    fi
    if ! [[ /proc/$$/fd/2 -ef "$snapshot_monitor_log" ]]; then
        exec 2> >(tee -a "$snapshot_monitor_log" >&2)
    fi
}

join_comma() {
    local IFS=,
    printf '%s' "$*"
}

quote_kv_value() {
    local quoted
    printf -v quoted '%q' "$1"
    printf '%s' "$quoted"
}

print_kv() {
    printf ' %s=%s' "$1" "$(quote_kv_value "$2")"
}

print_passive_metadata() {
    print_kv process_control "none"
    print_kv evidence_classification "${1:-passive_monitor_metadata_non_evidence}"
    print_kv approved_runtime_evidence "false"
    print_kv ready "false"
    print_kv readiness_gate "none"
}

print_passive_snapshot_metadata() {
    print_kv snapshot_action "copy_analyze_only"
    print_kv snapshot_authorization_source "none_passive_monitor_only"
    print_kv snapshot_counts_as_approved_runtime_evidence "false"
    print_kv snapshot_counts_toward_sdk "false"
    print_kv snapshot_counts_toward_p0_dependency_chain "false"
    print_kv snapshot_authorizes_server_operations "false"
    print_kv snapshot_authorizes_runtime_capture "false"
    print_kv snapshot_authorizes_discord "false"
    print_passive_metadata "passive_snapshot_non_evidence"
}

print_tail_wait_metadata() {
    local linger_active="false"
    local linger_until_utc="none"
    local now_epoch
    if [[ "$linger_until" -gt 0 ]]; then
        now_epoch="$(date +%s)"
        linger_until_utc="$(date -u -d "@${linger_until}" +%Y-%m-%dT%H:%M:%SZ)"
        if [[ "$now_epoch" -lt "$linger_until" ]]; then
            linger_active="true"
        fi
    fi
    print_kv tail_scope "per_target"
    print_kv linger_after_detect "$linger_after_detect"
    print_kv linger_active "$linger_active"
    print_kv linger_until_utc "$linger_until_utc"
    print_passive_metadata "passive_tail_non_evidence"
}

print_player_presence_context_metadata() {
    print_passive_metadata "passive_player_presence_context_non_evidence"
}

query_rcon_discrepant_sources() {
    local query_signal="$1"
    local rcon_signal="$2"

    case "${query_signal}:${rcon_signal}" in
        zero:present)
            printf 'gamedig_ase_query_zero,rcon_listplayers_redacted_present'
            ;;
        present:zero)
            printf 'gamedig_ase_query_present,rcon_listplayers_redacted_zero'
            ;;
        *)
            printf 'none'
            ;;
    esac
}

query_rcon_discrepancy_classification() {
    local query_signal="$1"
    local rcon_signal="$2"

    case "${query_signal}:${rcon_signal}" in
        zero:present)
            printf 'rcon_present_query_zero_trusted_source_discrepancy_non_evidence'
            ;;
        present:zero)
            printf 'query_present_rcon_zero_trusted_source_discrepancy_non_evidence'
            ;;
        *)
            printf 'none'
            ;;
    esac
}

print_query_rcon_discrepancy_metadata() {
    local query_signal="$1"
    local rcon_signal="$2"
    local discrepant_sources discrepancy_classification source_discrepancy_detected

    discrepant_sources="$(query_rcon_discrepant_sources "$query_signal" "$rcon_signal")"
    discrepancy_classification="$(query_rcon_discrepancy_classification "$query_signal" "$rcon_signal")"
    source_discrepancy_detected=false
    if [[ "$discrepant_sources" != "none" ]]; then
        source_discrepancy_detected=true
    fi

    print_kv source_discrepancy_detected "$source_discrepancy_detected"
    print_kv discrepant_sources "$discrepant_sources"
    print_kv discrepancy_classification "$discrepancy_classification"
    print_kv discrepancy_counts_as_approved_runtime_evidence "false"
    print_kv discrepancy_counts_as_runtime_evidence "false"
    print_kv discrepancy_authorizes_server_operations "false"
}

count_text_matches() {
    local text="$1"
    local pattern="$2"
    local count
    count="$(printf '%s\n' "$text" | rg -c "$pattern" || true)"
    printf '%s' "${count:-0}"
}

text_has_match() {
    local text="$1"
    local pattern="$2"
    printf '%s\n' "$text" | rg -q "$pattern"
}

latest_match_position() {
    local text="$1"
    local pattern="$2"
    local position
    position="$(
        printf '%s\n' "$text" \
            | nl -ba \
            | rg "$pattern" \
            | tail -n 1 \
            | awk '{print $1}' || true
    )"
    printf '%s' "${position:-0}"
}

observer_event_classification() {
    local accepted_count="$1"
    local rejected_count="$2"
    local diagnostic_count="$3"
    local complete_triplet="$4"
    if [[ "$complete_triplet" == true ]]; then
        printf 'complete_accepted_observer_event_triplet_candidate_non_evidence'
    elif [[ "$accepted_count" -gt 0 ]]; then
        printf 'partial_accepted_observer_event_triplet_candidate_non_evidence'
    elif [[ "$rejected_count" -gt 0 ]]; then
        printf 'rejected_observer_event_lines_non_evidence'
    elif [[ "$diagnostic_count" -gt 0 ]]; then
        printf 'diagnostic_only_lines_non_evidence'
    else
        printf 'no_player_principal_observer_lines_non_evidence'
    fi
}

detect_tmux_session() {
    local session="${OBELISK_PASSIVE_MONITOR_TMUX_SESSION:-}"
    local rc
    if [[ -z "$session" && -n "${TMUX:-}" ]] && command -v tmux >/dev/null 2>&1; then
        set +e
        session="$(tmux display-message -p '#S' 2>/dev/null)"
        rc=$?
        set -e
        if [[ "$rc" -ne 0 ]]; then
            session=""
        fi
    fi
    printf '%s' "${session:-none}"
}

detect_tmux_session_source() {
    local session="${OBELISK_PASSIVE_MONITOR_TMUX_SESSION:-}"
    local detected rc
    if [[ -n "$session" ]]; then
        printf 'env_override'
        return 0
    fi
    if [[ -n "${TMUX:-}" ]] && command -v tmux >/dev/null 2>&1; then
        set +e
        detected="$(tmux display-message -p '#S' 2>/dev/null)"
        rc=$?
        set -e
        if [[ "$rc" -eq 0 && -n "$detected" ]]; then
            printf 'tmux_display_message'
            return 0
        fi
    fi
    printf 'none'
}

detect_tmux_socket() {
    local socket="${OBELISK_PASSIVE_MONITOR_TMUX_SOCKET:-}"
    if [[ -n "$socket" ]]; then
        printf '%s' "$socket"
        return 0
    fi
    if [[ -n "${TMUX:-}" ]]; then
        socket="${TMUX%%,*}"
        if [[ -n "$socket" ]]; then
            printf '%s' "$socket"
            return 0
        fi
    fi
    printf 'none'
}

detect_tmux_socket_source() {
    if [[ -n "${OBELISK_PASSIVE_MONITOR_TMUX_SOCKET:-}" ]]; then
        printf 'env_override'
    elif [[ -n "${TMUX:-}" ]]; then
        printf 'tmux_env'
    else
        printf 'none'
    fi
}

detect_tmux_socket_name() {
    local socket="$1"
    local socket_name="${OBELISK_PASSIVE_MONITOR_TMUX_SOCKET_NAME:-}"
    if [[ -n "$socket_name" ]]; then
        printf '%s' "$socket_name"
        return 0
    fi
    if [[ -z "$socket" || "$socket" == "none" ]]; then
        printf 'none'
        return 0
    fi
    socket_name="${socket##*/}"
    printf '%s' "${socket_name:-none}"
}

emit_monitor_session() {
    local targets_csv replacement_status old_monitor_action tmux_session tmux_session_source
    local tmux_socket tmux_socket_name tmux_socket_source tmux_pane details_request_mode
    targets_csv="$(join_comma "${targets[@]}")"
    tmux_session="$(detect_tmux_session)"
    tmux_session_source="$(detect_tmux_session_source)"
    tmux_socket="$(detect_tmux_socket)"
    tmux_socket_name="$(detect_tmux_socket_name "$tmux_socket")"
    tmux_socket_source="$(detect_tmux_socket_source)"
    tmux_pane="${TMUX_PANE:-none}"
    details_request_mode="default_passive_details_disabled"
    if [[ "$no_details" == true ]]; then
        details_request_mode="explicit_no_details"
    fi
    replacement_status="none_reported"
    old_monitor_action="not_performed_by_passive_monitor"
    if [[ "$active_monitor_pid" != "none" ]]; then
        replacement_status="active_monitor_reported_metadata_only"
        if [[ "$replacement_requested" == true ]]; then
            replacement_status="explicit_replacement_requested_metadata_only"
        fi
    fi

    printf 'passive_monitor_session'
    print_kv utc "$monitor_started_at_utc"
    print_kv pid "$$"
    print_kv ppid "$PPID"
    print_kv session_id "$monitor_session_id"
    print_kv tmux_session "$tmux_session"
    print_kv tmux_session_source "$tmux_session_source"
    print_kv tmux_socket "$tmux_socket"
    print_kv tmux_socket_name "$tmux_socket_name"
    print_kv tmux_socket_source "$tmux_socket_source"
    print_kv tmux_pane "$tmux_pane"
    print_kv targets "$targets_csv"
    print_kv target_count "${#targets[@]}"
    print_kv interval "$interval"
    print_kv once "$once"
    print_kv no_details "$no_details"
    print_kv details_mode "linuxgsm_details_disabled"
    print_kv details_request_mode "$details_request_mode"
    print_kv linuxgsm_details_policy "never_call_lgsm_details_or_monitor"
    print_kv linger_after_detect "$linger_after_detect"
    print_kv linger_window_seconds "$linger_after_detect"
    print_kv linger_window_state "idle_at_session_start"
    print_kv linger_window_policy "tail_observer_lines_after_detect"
    print_kv linger_active "false"
    print_kv snapshot_output_root "${snapshot_output_root:-none}"
    print_kv snapshot_monitor_log "${snapshot_monitor_log:-none}"
    print_kv snapshot_trigger_policy "per_target_new_detection"
    print_kv replacement_status "$replacement_status"
    print_kv replaced_monitor_pid "$replaced_monitor_pid"
    print_kv active_monitor_pid "$active_monitor_pid"
    print_kv replacement_requested "$replacement_requested"
    print_kv old_monitor_action "$old_monitor_action"
    print_kv replacement_note "$replacement_note"
    print_kv replacement_policy "never_signal_stop_or_replace_existing_monitor"
    print_kv active_monitor_policy "metadata_only_never_signal_stop_or_replace"
    print_kv process_control "none"
    print_kv evidence_classification "passive_monitor_metadata_non_evidence"
    print_kv evidence_policy "non_evidence_until_copied_sibling_set_checker_accepts_bundle"
    print_kv approved_runtime_evidence "false"
    print_kv ready "false"
    print_kv readiness_gate "none"
    printf '\n'
}

target_key_for() {
    local instance="$1"
    local game_map="$2"
    local query_port="${3:-}"
    if [[ -n "$query_port" ]]; then
        printf '%s:%s:%s' "$instance" "$game_map" "$query_port"
    else
        printf '%s:%s' "$instance" "$game_map"
    fi
}

query_port_for_instance() {
    local instance="$1"
    case "$instance" in
        arkserver) printf '27015' ;;
        arkserver2) printf '27016' ;;
        arkserver3) printf '27017' ;;
        *) printf '' ;;
    esac
}

rcon_port_for_instance() {
    local instance="$1"
    case "$instance" in
        arkserver) printf '27020' ;;
        arkserver2) printf '27021' ;;
        arkserver3) printf '27022' ;;
        *) printf '' ;;
    esac
}

normalize_targets() {
    local target instance rest game_map query_port normalized
    local -a normalized_targets=()

    for target in "${targets[@]}"; do
        if [[ "$target" != *:* ]]; then
            echo "error: target must be INSTANCE:MAP[:QUERY_PORT]: $target" >&2
            exit 2
        fi

        instance="${target%%:*}"
        rest="${target#*:}"
        game_map="${rest%%:*}"
        if [[ "$rest" == *:* ]]; then
            query_port="${rest#*:}"
        else
            query_port="$(query_port_for_instance "$instance")"
        fi
        if [[ ! "$instance" =~ ^[A-Za-z0-9_.-]+$ || ! "$game_map" =~ ^[A-Za-z0-9_.-]+$ || ( -n "$query_port" && ! "$query_port" =~ ^[0-9]+$ ) ]]; then
            echo "error: unsafe target: $target" >&2
            exit 2
        fi

        normalized="${instance}:${game_map}"
        if [[ -n "$query_port" ]]; then
            normalized="${normalized}:${query_port}"
        fi
        normalized_targets+=("$normalized")
    done

    targets=("${normalized_targets[@]}")
}

gamedig_presence() {
    local instance="$1"
    local map="$2"
    local query_port="$3"
    local gamedig="$gamedig_bin"
    local output name current_map numplayers maxplayers error target_key presence_detected

    target_key="$(target_key_for "$instance" "$map" "$query_port")"

    [[ -x "$gamedig" && -n "$query_port" ]] || return 20
    command -v jq >/dev/null 2>&1 || return 20

    set +e
    output="$("$gamedig" --type ase --host 127.0.0.1 --port "$query_port" --maxAttempts 1 --socketTimeout 2000 2>&1)"
    local rc=$?
    set -e

    if [[ "$rc" -ne 0 ]]; then
        printf 'query instance=%s map=%s query_port=%s rc=%s status=unknown error=command_failed target_key=%s presence_detected=false detection_source=gamedig_ase_query' \
            "$instance" "$map" "$query_port" "$rc" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi

    if ! printf '%s\n' "$output" | jq -e . >/dev/null 2>&1; then
        printf 'query instance=%s map=%s query_port=%s rc=0 status=unknown error=invalid_json target_key=%s presence_detected=false detection_source=gamedig_ase_query' \
            "$instance" "$map" "$query_port" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi

    error="$(printf '%s\n' "$output" | jq -r '.error // empty')"
    if [[ -n "$error" ]]; then
        printf 'query instance=%s map=%s query_port=%s rc=0 status=unknown error=%q target_key=%s presence_detected=false detection_source=gamedig_ase_query' \
            "$instance" "$map" "$query_port" "$error" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi

    name="$(printf '%s\n' "$output" | jq -r '.name // "unknown"')"
    current_map="$(printf '%s\n' "$output" | jq -r '.map // "unknown"')"
    numplayers="$(printf '%s\n' "$output" | jq -r 'if .numplayers != null then .numplayers elif .players != null then (.players | length) else "unknown" end')"
    maxplayers="$(printf '%s\n' "$output" | jq -r '.maxplayers // "unknown"')"
    if [[ ! "$numplayers" =~ ^[0-9]+$ ]]; then
        printf 'query instance=%s map=%s query_port=%s rc=0 status=unknown error=missing_player_count current_map=%s name=%q target_key=%s players_current=unknown players_max=%s presence_detected=false detection_source=gamedig_ase_query' \
            "$instance" "$map" "$query_port" "$current_map" "$name" "$target_key" "$maxplayers"
        print_passive_metadata
        printf '\n'
        return 20
    fi
    presence_detected=false
    if [[ "$numplayers" =~ ^[1-9][0-9]*$ ]]; then
        presence_detected=true
    fi

    printf 'query instance=%s map=%s query_port=%s status=ok current_map=%s players=%s/%s name=%q target_key=%s players_current=%s players_max=%s presence_detected=%s detection_source=gamedig_ase_query' \
        "$instance" "$map" "$query_port" "$current_map" "$numplayers" "$maxplayers" "$name" "$target_key" "$numplayers" "$maxplayers" "$presence_detected"
    print_passive_metadata
    printf '\n'

    [[ "$numplayers" =~ ^[1-9][0-9]*$ ]] && return 10
    return 0
}

rcon_player_count_from_response() {
    local response="$1"
    local count

    response="${response//$'\r'/}"
    if [[ -z "${response//[[:space:]]/}" ]]; then
        printf 'unknown'
        return 0
    fi
    if printf '%s\n' "$response" | rg -qi 'no players connected|no players'; then
        printf '0'
        return 0
    fi

    count="$(printf '%s\n' "$response" | awk '/^[[:space:]]*[0-9]+[.)][[:space:]]/ { count += 1 } END { print count + 0 }')"
    if [[ "$count" =~ ^[1-9][0-9]*$ ]]; then
        printf '%s' "$count"
        return 0
    fi

    printf 'unknown'
}

rcon_player_count_from_helper_json() {
    local output="$1"
    local count response

    count="$(
        printf '%s\n' "$output" | jq -r '
            if
                (.ok == true)
                and (((.responseKind // "") | ascii_downcase) == "listplayers")
                and ((.playerCount | type) == "number")
                and (.playerCount >= 0)
                and (.playerCount == (.playerCount | floor))
            then
                (.playerCount | tostring)
            else
                empty
            end
        '
    )"
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        printf '%s' "$count"
        return 0
    fi

    response="$(printf '%s\n' "$output" | jq -r '.response // empty')"
    rcon_player_count_from_response "$response"
}

rcon_presence() {
    local instance="$1"
    local map="$2"
    local query_port="$3"
    local target_key rcon_port output rc player_count presence_detected

    target_key="$(target_key_for "$instance" "$map" "$query_port")"
    rcon_port="$(rcon_port_for_instance "$instance")"

    if [[ "$rcon_enabled" == "off" ]]; then
        return 20
    fi
    if [[ -z "$rcon_port" ]]; then
        printf 'rcon_listplayers instance=%s map=%s query_port=%s status=unknown reason=no_default_rcon_port target_key=%s presence_detected=false detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
            "$instance" "$map" "$query_port" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi
    if [[ ! -f "$rcon_helper" || ! -f "$rcon_ini_path" || ! -x "$(command -v node 2>/dev/null || true)" ]]; then
        if [[ "$rcon_enabled" == "on" ]]; then
            printf 'rcon_listplayers instance=%s map=%s query_port=%s rcon_port=%s status=unknown reason=rcon_helper_or_ini_unavailable target_key=%s presence_detected=false detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
                "$instance" "$map" "$query_port" "$rcon_port" "$target_key"
            print_passive_metadata
            printf '\n'
        fi
        return 20
    fi

    set +e
    output="$(
        timeout "$rcon_timeout_seconds" env \
        RUN_RCON_INTEGRATION=1 \
        RCON_TEST_INI_PATH="$rcon_ini_path" \
        RCON_TEST_HOST="$rcon_host" \
        RCON_TEST_PORT="$rcon_port" \
        RCON_TEST_COMMAND="ListPlayers" \
        node "$rcon_helper" 2>&1
    )"
    rc=$?
    set -e

    if [[ "$rc" -ne 0 ]]; then
        rcon_error="command_failed"
        if [[ "$rc" -eq 124 ]]; then
            rcon_error="timeout"
        fi
        printf 'rcon_listplayers instance=%s map=%s query_port=%s rcon_port=%s rc=%s status=unknown error=%s timeout_seconds=%s target_key=%s presence_detected=false detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
            "$instance" "$map" "$query_port" "$rcon_port" "$rc" "$rcon_error" "$rcon_timeout_seconds" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi
    if ! printf '%s\n' "$output" | jq -e . >/dev/null 2>&1; then
        printf 'rcon_listplayers instance=%s map=%s query_port=%s rcon_port=%s rc=0 status=unknown error=invalid_json target_key=%s presence_detected=false detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
            "$instance" "$map" "$query_port" "$rcon_port" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi

    player_count="$(rcon_player_count_from_helper_json "$output")"
    if [[ "$player_count" == "unknown" ]]; then
        printf 'rcon_listplayers instance=%s map=%s query_port=%s rcon_port=%s status=unknown players_current=unknown target_key=%s presence_detected=false detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
            "$instance" "$map" "$query_port" "$rcon_port" "$target_key"
        print_passive_metadata
        printf '\n'
        return 20
    fi

    presence_detected=false
    if [[ "$player_count" =~ ^[1-9][0-9]*$ ]]; then
        presence_detected=true
    fi
    printf 'rcon_listplayers instance=%s map=%s query_port=%s rcon_port=%s status=ok players_current=%s target_key=%s presence_detected=%s detection_source=rcon_listplayers_redacted rcon_output_redacted=true' \
        "$instance" "$map" "$query_port" "$rcon_port" "$player_count" "$target_key" "$presence_detected"
    print_passive_metadata
    printf '\n'

    [[ "$presence_detected" == true ]] && return 10
    return 0
}

observer_delta() {
    local instance="$1"
    local game_map="${2:-unknown}"
    local query_port="${3:-}"
    local log="${obelisk_log_root}/${instance}/Obelisk.log"
    local matches line_count target_key gate_count raw_event_count diagnostic_count route_sample_count rejected_count
    local accepted_event_count start_count check_join_rejected_count end_count superseded_handle_rejected_count
    local has_session_start has_session_start_rejected has_session_end complete_triplet
    local event_roles raw_event_roles event_classification latest_event_role latest_raw_event_role
    local latest_start_position latest_end_position lifecycle_active_candidate
    local session_end_without_session_start_candidate

    target_key="$(target_key_for "$instance" "$game_map" "$query_port")"
    OBELISK_PASSIVE_OBSERVER_SIGNAL="unknown"

    if [[ ! -f "$log" ]]; then
        OBELISK_PASSIVE_OBSERVER_SIGNAL="unavailable_no_log"
        printf 'observer_tail instance=%s status=no_log scan_lines=%s limit=%s map=%s query_port=%s target_key=%s observer_gate_lines=0 raw_observer_event_lines=0 accepted_observer_event_triplet_candidate_lines=0 rejected_observer_event_line_count=0 check_join_rejected_start_candidate_lines=0 superseded_handle_new_player_rejected_start_lines=0 diagnostic_only_lines=0 route_sample_lines=0 raw_event_roles=none event_roles=none latest_raw_observer_event_role=none latest_observer_event_role=none lifecycle_active_candidate=false complete_triplet_candidate=false session_end_without_session_start_candidate=false classification=no_player_principal_observer_lines_non_evidence observer_event_role_policy=accepted_safe_observer_events_only' \
            "$instance" "$observer_tail_scan_lines" "$observer_tail_limit" "$game_map" "$query_port" "$target_key"
        print_tail_wait_metadata
        printf '\n'
        return 0
    fi

    matches="$(
        tail -n "$observer_tail_scan_lines" "$log" \
            | rg "$observer_line_pattern" \
            | tail -n "$observer_tail_limit" || true
    )"
    if [[ -z "$matches" ]]; then
        OBELISK_PASSIVE_OBSERVER_SIGNAL="unavailable_no_observer_lines"
        printf 'observer_tail instance=%s status=no_matching_lines scan_lines=%s limit=%s map=%s query_port=%s target_key=%s observer_gate_lines=0 raw_observer_event_lines=0 accepted_observer_event_triplet_candidate_lines=0 rejected_observer_event_line_count=0 check_join_rejected_start_candidate_lines=0 superseded_handle_new_player_rejected_start_lines=0 diagnostic_only_lines=0 route_sample_lines=0 raw_event_roles=none event_roles=none latest_raw_observer_event_role=none latest_observer_event_role=none lifecycle_active_candidate=false complete_triplet_candidate=false session_end_without_session_start_candidate=false classification=no_player_principal_observer_lines_non_evidence observer_event_role_policy=accepted_safe_observer_events_only' \
            "$instance" "$observer_tail_scan_lines" "$observer_tail_limit" "$game_map" "$query_port" "$target_key"
        print_tail_wait_metadata
        printf '\n'
        return 0
    fi

    line_count="$(printf '%s\n' "$matches" | wc -l | tr -d ' ')"
    gate_count="$(count_text_matches "$matches" "$observer_gate_line_pattern")"
    raw_event_count="$(count_text_matches "$matches" "$observer_event_line_pattern")"
    diagnostic_count="$(count_text_matches "$matches" "$observer_diagnostic_line_pattern")"
    route_sample_count="$(count_text_matches "$matches" "$observer_route_sample_line_pattern")"
    start_count="$(count_text_matches "$matches" "$observer_session_start_candidate_pattern")"
    check_join_rejected_count="$(count_text_matches "$matches" "$observer_check_join_rejected_candidate_pattern")"
    end_count="$(count_text_matches "$matches" "$observer_session_end_candidate_pattern")"
    superseded_handle_rejected_count="$(count_text_matches "$matches" "$observer_superseded_handle_rejected_pattern")"
    accepted_event_count=$((start_count + check_join_rejected_count + end_count))
    rejected_count="$superseded_handle_rejected_count"
    has_session_start=false
    has_session_start_rejected=false
    has_session_end=false
    if [[ "$start_count" -gt 0 ]]; then
        has_session_start=true
    fi
    if [[ "$check_join_rejected_count" -gt 0 ]]; then
        has_session_start_rejected=true
    fi
    if [[ "$end_count" -gt 0 ]]; then
        has_session_end=true
    fi
    raw_event_roles="none"
    if text_has_match "$matches" 'PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_start '; then
        raw_event_roles="session_start"
    fi
    if text_has_match "$matches" 'PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_start_rejected '; then
        if [[ "$raw_event_roles" == "none" ]]; then
            raw_event_roles="session_start_rejected"
        else
            raw_event_roles="${raw_event_roles},session_start_rejected"
        fi
    fi
    if text_has_match "$matches" 'PlayerPrincipalLifecycleObserver event sequence=[0-9]+ role=session_end '; then
        if [[ "$raw_event_roles" == "none" ]]; then
            raw_event_roles="session_end"
        else
            raw_event_roles="${raw_event_roles},session_end"
        fi
    fi
    event_roles="none"
    if [[ "$has_session_start" == true ]]; then
        event_roles="session_start"
    fi
    if [[ "$has_session_start_rejected" == true ]]; then
        if [[ "$event_roles" == "none" ]]; then
            event_roles="session_start_rejected"
        else
            event_roles="${event_roles},session_start_rejected"
        fi
    fi
    if [[ "$has_session_end" == true ]]; then
        if [[ "$event_roles" == "none" ]]; then
            event_roles="session_end"
        else
            event_roles="${event_roles},session_end"
        fi
    fi
    complete_triplet=false
    if [[ "$has_session_start" == true && "$has_session_start_rejected" == true && "$has_session_end" == true ]]; then
        complete_triplet=true
    fi
    event_classification="$(observer_event_classification "$accepted_event_count" "$rejected_count" "$diagnostic_count" "$complete_triplet")"
    session_end_without_session_start_candidate=false
    if [[ "$has_session_end" == true && "$has_session_start" == false ]]; then
        session_end_without_session_start_candidate=true
        event_classification="session_end_without_session_start_candidate_non_evidence"
    fi
    latest_event_role="$(
        printf '%s\n' "$matches" \
            | rg "$observer_session_start_candidate_pattern|$observer_check_join_rejected_candidate_pattern|$observer_session_end_candidate_pattern" \
            | tail -n 1 \
            | sed -E 's/.* role=([^ ]+) .*/\1/' || true
    )"
    latest_event_role="${latest_event_role:-none}"
    latest_raw_event_role="$(
        printf '%s\n' "$matches" \
            | rg "$observer_event_line_pattern" \
            | tail -n 1 \
            | sed -E 's/.* role=([^ ]+) .*/\1/' || true
    )"
    latest_raw_event_role="${latest_raw_event_role:-none}"
    lifecycle_active_candidate=false
    latest_start_position="$(latest_match_position "$matches" "$observer_session_start_candidate_pattern")"
    latest_end_position="$(latest_match_position "$matches" "$observer_session_end_candidate_pattern")"
    if [[ "$latest_start_position" -gt 0 && ( "$latest_end_position" -eq 0 || "$latest_start_position" -gt "$latest_end_position" ) ]]; then
        lifecycle_active_candidate=true
    fi
    if [[ "$lifecycle_active_candidate" == true ]]; then
        OBELISK_PASSIVE_OBSERVER_SIGNAL="active_candidate"
    else
        case "$latest_event_role" in
            session_end)
                OBELISK_PASSIVE_OBSERVER_SIGNAL="inactive_latest_session_end"
                ;;
            session_start_rejected)
                OBELISK_PASSIVE_OBSERVER_SIGNAL="inactive_latest_session_start_rejected"
                ;;
            *)
                OBELISK_PASSIVE_OBSERVER_SIGNAL="matched_no_accepted_observer_event"
                ;;
        esac
    fi
    printf 'observer_tail instance=%s status=matched lines=%s scan_lines=%s limit=%s map=%s query_port=%s target_key=%s observer_gate_lines=%s raw_observer_event_lines=%s accepted_observer_event_triplet_candidate_lines=%s rejected_observer_event_line_count=%s check_join_rejected_start_candidate_lines=%s superseded_handle_new_player_rejected_start_lines=%s diagnostic_only_lines=%s route_sample_lines=%s raw_event_roles=%s event_roles=%s latest_raw_observer_event_role=%s latest_observer_event_role=%s lifecycle_active_candidate=%s complete_triplet_candidate=%s session_end_without_session_start_candidate=%s classification=%s observer_event_role_policy=accepted_safe_observer_events_only' \
        "$instance" "$line_count" "$observer_tail_scan_lines" "$observer_tail_limit" "$game_map" "$query_port" "$target_key" "$gate_count" "$raw_event_count" "$accepted_event_count" "$rejected_count" "$check_join_rejected_count" "$superseded_handle_rejected_count" "$diagnostic_count" "$route_sample_count" "$raw_event_roles" "$event_roles" "$latest_raw_event_role" "$latest_event_role" "$lifecycle_active_candidate" "$complete_triplet" "$session_end_without_session_start_candidate" "$event_classification"
    print_tail_wait_metadata
    printf '\n'
    printf '%s\n' "$matches" | sed "s|^|observer instance=${instance} map=${game_map} query_port=${query_port} target_key=${target_key} process_control=none evidence_classification=passive_tail_non_evidence approved_runtime_evidence=false ready=false readiness_gate=none |"
    [[ "$lifecycle_active_candidate" == true ]] && return 10
    return 0
}

emit_player_presence_context() {
    local instance="$1"
    local game_map="$2"
    local query_port="$3"
    local target_key="$4"
    local query_signal="$5"
    local rcon_signal="$6"
    local observer_signal="$7"
    local detection_source="$8"
    local presence_detected="false"
    local unknown_player_context="false"
    local no_users_confirmed="false"
    local no_users_confirmation_sources="none"
    local unknown_sources="none"
    local presence_without_lifecycle_start_after_observer_gate="false"
    local diagnostic_condition="none"
    local -a unknown_source_parts=()

    if [[ "$query_signal" == "present" || "$rcon_signal" == "present" || ( "$observer_signal" == "active_candidate" && "$rcon_signal" != "zero" ) ]]; then
        presence_detected="true"
    fi

    if [[ "$presence_detected" == "true" && "$observer_signal" == "matched_no_accepted_observer_event" ]]; then
        presence_without_lifecycle_start_after_observer_gate="true"
        diagnostic_condition="presence_without_lifecycle_start_after_observer_gate_non_evidence"
    fi

    if [[ "$query_signal" == "unknown" ]]; then
        unknown_source_parts+=("gamedig_ase_query")
    fi
    case "$rcon_signal" in
        unknown|disabled)
            unknown_source_parts+=("rcon_listplayers_redacted:${rcon_signal}")
            ;;
    esac
    case "$observer_signal" in
        unknown|unavailable_no_log|unavailable_no_observer_lines)
            unknown_source_parts+=("observer_lifecycle:${observer_signal}")
            ;;
    esac

    if ((${#unknown_source_parts[@]} > 0)); then
        unknown_player_context="true"
        unknown_sources="$(join_comma "${unknown_source_parts[@]}")"
    fi

    if [[ "$presence_detected" == "false" && "$query_signal" == "zero" && "$rcon_signal" == "zero" ]]; then
        case "$observer_signal" in
            inactive_latest_session_end|inactive_latest_session_start_rejected|matched_no_observer_event)
                no_users_confirmed="true"
                no_users_confirmation_sources="gamedig_ase_query,rcon_listplayers_redacted,observer_lifecycle_latest_non_start"
                ;;
        esac
    fi

    printf 'player_presence_context'
    print_kv instance "$instance"
    print_kv map "$game_map"
    print_kv query_port "$query_port"
    print_kv target_key "$target_key"
    print_kv presence_detected "$presence_detected"
    print_kv no_users_confirmed "$no_users_confirmed"
    print_kv unknown_player_context "$unknown_player_context"
    print_kv query_signal "$query_signal"
    print_kv rcon_signal "$rcon_signal"
    print_kv observer_signal "$observer_signal"
    print_kv detection_source "$detection_source"
    print_kv presence_without_lifecycle_start_after_observer_gate "$presence_without_lifecycle_start_after_observer_gate"
    print_kv diagnostic_condition "$diagnostic_condition"
    print_kv no_users_confirmation_sources "$no_users_confirmation_sources"
    print_kv unknown_sources "$unknown_sources"
    print_query_rcon_discrepancy_metadata "$query_signal" "$rcon_signal"
    print_player_presence_context_metadata
    printf '\n'
}

capture_detection_snapshot() {
    local detected_instances_csv="$1"
    local detected_target_keys_csv="$2"
    shift 2
    local stamp safe_target_keys output_dir output rc snapshot_target_count
    local -a snapshot_command
    local -a snapshot_targets=("$@")

    if [[ -z "$snapshot_output_root" || ${#snapshot_targets[@]} -eq 0 ]]; then
        return 0
    fi

    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    safe_target_keys="${detected_target_keys_csv//:/-}"
    safe_target_keys="${safe_target_keys//,/+}"
    safe_target_keys="${safe_target_keys:-unknown}"
    snapshot_sequence=$((snapshot_sequence + 1))
    snapshot_target_count="${#snapshot_targets[@]}"
    output_dir="${snapshot_output_root%/}/passive-detect-${stamp}-${safe_target_keys}-seq${snapshot_sequence}-$$"

    snapshot_command=(
        python3
        "${script_dir}/capture_player_principal_passive_snapshot.py"
        --allow-server-path
        --log-root
        "$obelisk_log_root"
        --output-dir
        "$output_dir"
    )
    if [[ -n "$snapshot_monitor_log" ]]; then
        snapshot_command+=(--monitor-log "$snapshot_monitor_log")
    fi
    for target in "${snapshot_targets[@]}"; do
        snapshot_command+=(--target "$target")
    done

    set +e
    output="$("${snapshot_command[@]}" 2>&1)"
    rc=$?
    set -e

    if [[ "$rc" -eq 0 ]]; then
        printf 'passive_snapshot_captured output_dir=%s detected_instances=%s detected_target_keys=%s snapshot_sequence=%s snapshot_target_count=%s snapshot_trigger_policy=per_target_new_detection summary=%q' \
            "$output_dir" "$detected_instances_csv" "$detected_target_keys_csv" "$snapshot_sequence" "$snapshot_target_count" "$output"
        print_passive_snapshot_metadata
        printf '\n'
    else
        printf 'passive_snapshot_failed output_dir=%s detected_instances=%s detected_target_keys=%s snapshot_sequence=%s snapshot_target_count=%s snapshot_trigger_policy=per_target_new_detection rc=%s error=%q' \
            "$output_dir" "$detected_instances_csv" "$detected_target_keys_csv" "$snapshot_sequence" "$snapshot_target_count" "$rc" "$output"
        print_passive_snapshot_metadata
        printf '\n'
    fi
}

capture_new_detection_snapshots() {
    local target instance rest map query_port target_key

    for target in "$@"; do
        instance="${target%%:*}"
        rest="${target#*:}"
        map="${rest%%:*}"
        if [[ "$rest" == *:* ]]; then
            query_port="${rest#*:}"
        else
            query_port="$(query_port_for_instance "$instance")"
        fi
        target_key="$(target_key_for "$instance" "$map" "$query_port")"
        capture_detection_snapshot "$instance" "$target_key" "$target"
    done
}

setup_snapshot_monitor_log
normalize_targets
emit_monitor_session

while true; do
    detected=false
    detected_instances=()
    detected_target_keys=()
    newly_detected_targets=()
    declare -A current_detected_target_keys=()
    printf 'tick utc=%s' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    print_passive_metadata
    printf '\n'

    for target in "${targets[@]}"; do
        if [[ "$target" != *:* ]]; then
            echo "error: target must be INSTANCE:MAP[:QUERY_PORT]: $target" >&2
            exit 2
        fi

        instance="${target%%:*}"
        rest="${target#*:}"
        map="${rest%%:*}"
        if [[ "$rest" == *:* ]]; then
            query_port="${rest#*:}"
        else
            query_port="$(query_port_for_instance "$instance")"
        fi
        target_key="$(target_key_for "$instance" "$map" "$query_port")"
        query_detected=false
        rcon_detected=false
        observer_detected=false
        detection_source="none"
        query_signal="unknown"
        rcon_signal="unknown"
        observer_signal="unknown"

        if gamedig_presence "$instance" "$map" "$query_port"; then
            query_signal="zero"
            :
        else
            query_rc=$?
            if [[ "$query_rc" -eq 10 ]]; then
                query_signal="present"
                query_detected=true
                detection_source="gamedig_ase_query"
            else
                query_signal="unknown"
                printf 'query_warning instance=%s rc=%s details_fallback=disabled map=%s query_port=%s target_key=%s detection_source=gamedig_ase_query' "$instance" "$query_rc" "$map" "$query_port" "$target_key"
                print_passive_metadata
                printf '\n'
                printf 'linuxgsm_skipped instance=%s commands=monitor,details reason=passive_path linuxgsm_invoked=false map=%s query_port=%s target_key=%s' "$instance" "$map" "$query_port" "$target_key"
                print_passive_metadata
                printf '\n'
            fi
        fi
        if [[ "$rcon_enabled" == "off" ]]; then
            rcon_signal="disabled"
        fi
        if rcon_presence "$instance" "$map" "$query_port"; then
            rcon_signal="zero"
            :
        else
            rcon_rc=$?
            if [[ "$rcon_rc" -eq 10 ]]; then
                rcon_signal="present"
                rcon_detected=true
                if [[ "$detection_source" == "none" ]]; then
                    detection_source="rcon_listplayers_redacted"
                elif [[ "$detection_source" != *rcon_listplayers_redacted* ]]; then
                    detection_source="${detection_source},rcon_listplayers_redacted"
                fi
            else
                if [[ "$rcon_signal" != "disabled" ]]; then
                    rcon_signal="unknown"
                fi
            fi
        fi
        OBELISK_PASSIVE_OBSERVER_SIGNAL="unknown"
        if observer_delta "$instance" "$map" "$query_port"; then
            observer_signal="${OBELISK_PASSIVE_OBSERVER_SIGNAL:-unknown}"
            :
        else
            observer_rc=$?
            observer_signal="${OBELISK_PASSIVE_OBSERVER_SIGNAL:-unknown}"
            if [[ "$observer_rc" -eq 10 ]]; then
                observer_signal="active_candidate"
                if [[ "$rcon_signal" != "zero" ]]; then
                    observer_detected=true
                    if [[ "$detection_source" == "none" ]]; then
                        detection_source="observer_lifecycle_active_candidate"
                    elif [[ "$detection_source" != *observer_lifecycle_active_candidate* ]]; then
                        detection_source="${detection_source},observer_lifecycle_active_candidate"
                    fi
                fi
            fi
        fi
        emit_player_presence_context "$instance" "$map" "$query_port" "$target_key" "$query_signal" "$rcon_signal" "$observer_signal" "$detection_source"
        if [[ "$query_detected" == true || "$rcon_detected" == true || "$observer_detected" == true ]]; then
            detected=true
            detected_instances+=("$instance")
            detected_target_keys+=("$target_key")
            current_detected_target_keys["$target_key"]=true
            if [[ "${target_presence_active[$target_key]:-false}" != true ]]; then
                newly_detected_targets+=("$target")
            fi
            printf 'player_presence_detected instance=%s map=%s query_port=%s target_key=%s detection_source=%s' "$instance" "$map" "$query_port" "$target_key" "$detection_source"
            print_query_rcon_discrepancy_metadata "$query_signal" "$rcon_signal"
            print_passive_metadata
            printf '\n'
        fi
    done

    for target in "${targets[@]}"; do
        instance="${target%%:*}"
        rest="${target#*:}"
        map="${rest%%:*}"
        if [[ "$rest" == *:* ]]; then
            query_port="${rest#*:}"
        else
            query_port="$(query_port_for_instance "$instance")"
        fi
        target_key="$(target_key_for "$instance" "$map" "$query_port")"
        if [[ "${current_detected_target_keys[$target_key]:-false}" == true ]]; then
            target_presence_active["$target_key"]=true
        else
            target_presence_active["$target_key"]=false
        fi
    done

    now_epoch="$(date +%s)"
    if [[ "$detected" == true ]]; then
        detected_instances_csv="$(join_comma "${detected_instances[@]}")"
        detected_target_keys_csv="$(join_comma "${detected_target_keys[@]}")"
        linger_target_keys_csv="$detected_target_keys_csv"
        linger_detected_instances_csv="$detected_instances_csv"
        if [[ "$once" == true ]]; then
            if ((${#newly_detected_targets[@]} > 0)); then
                capture_new_detection_snapshots "${newly_detected_targets[@]}"
            fi
            exit 0
        fi
        if [[ "$linger_after_detect" -eq 0 ]]; then
            if ((${#newly_detected_targets[@]} > 0)); then
                capture_new_detection_snapshots "${newly_detected_targets[@]}"
            fi
            sleep "$interval"
            continue
        fi
        previous_linger_until="$linger_until"
        candidate_linger_until=$((now_epoch + linger_after_detect))
        if [[ "$candidate_linger_until" -gt "$linger_until" ]]; then
            linger_until="$candidate_linger_until"
        fi
        if [[ "$previous_linger_until" -eq 0 ]]; then
            printf 'player_presence_linger_start seconds=%s until_utc=%s detected_instances=%s observer_tail=per_target target_keys=%s' \
                "$linger_after_detect" "$(date -u -d "@${linger_until}" +%Y-%m-%dT%H:%M:%SZ)" "$detected_instances_csv" "$detected_target_keys_csv"
            print_passive_metadata "passive_linger_metadata_non_evidence"
            printf '\n'
        elif [[ "$linger_until" -gt "$previous_linger_until" ]]; then
            printf 'player_presence_linger_extend seconds=%s until_utc=%s detected_instances=%s observer_tail=per_target target_keys=%s' \
                "$linger_after_detect" "$(date -u -d "@${linger_until}" +%Y-%m-%dT%H:%M:%SZ)" "$detected_instances_csv" "$detected_target_keys_csv"
            print_passive_metadata "passive_linger_metadata_non_evidence"
            printf '\n'
        fi
        if ((${#newly_detected_targets[@]} > 0)); then
            capture_new_detection_snapshots "${newly_detected_targets[@]}"
        fi
    fi

    if [[ "$once" == true ]]; then
        exit 0
    fi
    if [[ "$linger_until" -gt 0 && "$now_epoch" -ge "$linger_until" ]]; then
        printf 'player_presence_linger_complete seconds=%s until_utc=%s observer_tail=per_target target_keys=%s detected_instances=%s' \
            "$linger_after_detect" "$(date -u -d "@${linger_until}" +%Y-%m-%dT%H:%M:%SZ)" "$linger_target_keys_csv" "$linger_detected_instances_csv"
        print_passive_metadata "passive_linger_metadata_non_evidence"
        printf '\n'
        exit 0
    fi

    sleep_seconds="$interval"
    if [[ "$linger_until" -gt 0 ]]; then
        remaining_linger=$((linger_until - now_epoch))
        if [[ "$remaining_linger" -gt 0 && "$remaining_linger" -lt "$sleep_seconds" ]]; then
            sleep_seconds="$remaining_linger"
        fi
    fi
    sleep "$sleep_seconds"
done
