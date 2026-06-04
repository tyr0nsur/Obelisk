#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage:
  scripts/monitor_ark_player_presence_passive.sh [--interval seconds] [--once] INSTANCE:MAP[:QUERY_PORT] [...]

Passive ARK player/observer monitor. It does not edit markers, start, stop, or restart
servers. It prefers GameDig Steam query and treats query errors as unknown, never as zero.
LinuxGSM details output is filtered before printing when used as a fallback.

Examples:
  scripts/monitor_ark_player_presence_passive.sh --once arkserver:Ragnarok arkserver2:TheIsland
  scripts/monitor_ark_player_presence_passive.sh --interval 60 arkserver:Ragnarok arkserver2:TheIsland
USAGE
}

interval=60
once=false
declare -a targets=()

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

if [[ ! -d /servidor/ark ]]; then
    echo "error: /servidor/ark not found" >&2
    exit 2
fi

strip_ansi() {
    sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g'
}

query_port_for_instance() {
    local instance="$1"
    case "$instance" in
        arkserver) printf '27015' ;;
        arkserver2) printf '27016' ;;
        *) printf '' ;;
    esac
}

gamedig_presence() {
    local instance="$1"
    local map="$2"
    local query_port="$3"
    local gamedig="/servidor/ark/lgsm/node_modules/gamedig/bin/gamedig.js"
    local output name current_map numplayers maxplayers error

    [[ -x "$gamedig" && -n "$query_port" && -x "$(command -v jq)" ]] || return 20

    set +e
    output="$("$gamedig" --type ase --host 127.0.0.1 --port "$query_port" --maxAttempts 1 --socketTimeout 2000 2>&1)"
    local rc=$?
    set -e

    if [[ "$rc" -ne 0 ]]; then
        printf 'query instance=%s map=%s query_port=%s rc=%s status=unknown error=command_failed\n' \
            "$instance" "$map" "$query_port" "$rc"
        return 20
    fi

    if ! printf '%s\n' "$output" | jq -e . >/dev/null 2>&1; then
        printf 'query instance=%s map=%s query_port=%s rc=0 status=unknown error=invalid_json\n' \
            "$instance" "$map" "$query_port"
        return 20
    fi

    error="$(printf '%s\n' "$output" | jq -r '.error // empty')"
    if [[ -n "$error" ]]; then
        printf 'query instance=%s map=%s query_port=%s rc=0 status=unknown error=%q\n' \
            "$instance" "$map" "$query_port" "$error"
        return 20
    fi

    name="$(printf '%s\n' "$output" | jq -r '.name // "unknown"')"
    current_map="$(printf '%s\n' "$output" | jq -r '.map // "unknown"')"
    numplayers="$(printf '%s\n' "$output" | jq -r 'if .numplayers != null then .numplayers elif .players != null then (.players | length) else "unknown" end')"
    maxplayers="$(printf '%s\n' "$output" | jq -r '.maxplayers // "unknown"')"

    printf 'query instance=%s map=%s query_port=%s status=ok current_map=%s players=%s/%s name=%q\n' \
        "$instance" "$map" "$query_port" "$current_map" "$numplayers" "$maxplayers" "$name"

    [[ "$numplayers" =~ ^[1-9][0-9]*$ ]] && return 10
    return 0
}

safe_details() {
    local instance="$1"
    local output clean players status current_map master

    set +e
    output="$(cd /servidor/ark && env -u TMUX "./${instance}" details 2>&1)"
    local rc=$?
    set -e

    clean="$(printf '%s\n' "$output" | strip_ansi | tr -d '\r')"
    players="$(printf '%s\n' "$clean" | awk -F: '/^[[:space:]]*Players[[:space:]]*:/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
    status="$(printf '%s\n' "$clean" | awk -F: '/^[[:space:]]*Status[[:space:]]*:/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
    current_map="$(printf '%s\n' "$clean" | awk -F: '/^[[:space:]]*Current map[[:space:]]*:/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
    master="$(printf '%s\n' "$clean" | awk -F: '/^[[:space:]]*Master server[[:space:]]*:/{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"

    printf 'details instance=%s rc=%s status=%s map=%s players=%s master=%s\n' \
        "$instance" "$rc" "${status:-unknown}" "${current_map:-unknown}" \
        "${players:-unknown}" "${master:-unknown}"

    [[ "$players" =~ ^[1-9][0-9]*/ ]] && return 10
    return 0
}

observer_delta() {
    local instance="$1"
    local log="/servidor/ark/obelisk/logs/${instance}/Obelisk.log"

    [[ -f "$log" ]] || return 0
    tail -n 200 "$log" \
        | rg 'PlayerPrincipalLifecycleObserver (enabled|event)|session_start|session_end|session_start_rejected' \
        | tail -n 10 \
        | sed "s|^|observer instance=${instance} |" || true
}

while true; do
    detected=false
    printf 'tick utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

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
        if [[ ! "$instance" =~ ^[A-Za-z0-9_.-]+$ || -z "$map" || ( -n "$query_port" && ! "$query_port" =~ ^[0-9]+$ ) ]]; then
            echo "error: unsafe target: $target" >&2
            exit 2
        fi

        if gamedig_presence "$instance" "$map" "$query_port"; then
            :
        else
            query_rc=$?
            if [[ "$query_rc" -eq 10 ]]; then
                detected=true
                printf 'player_presence_detected instance=%s map=%s\n' "$instance" "$map"
            else
                printf 'query_warning instance=%s rc=%s; trying_filtered_lgsm_details\n' "$instance" "$query_rc"
                if safe_details "$instance"; then
                    :
                else
                    details_rc=$?
                    if [[ "$details_rc" -eq 10 ]]; then
                        detected=true
                        printf 'player_presence_detected instance=%s map=%s source=details\n' "$instance" "$map"
                    else
                        printf 'details_warning instance=%s rc=%s\n' "$instance" "$details_rc"
                    fi
                fi
            fi
        fi
        observer_delta "$instance"
    done

    if [[ "$detected" == true || "$once" == true ]]; then
        exit 0
    fi
    sleep "$interval"
done
