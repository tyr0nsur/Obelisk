#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: obelisk_supervisor_loop.sh [--interval SECONDS] [--count N]

Runs read-only Obelisk supervisor snapshots on a timer.

Defaults:
  --interval 1800
  --count 0        Run until interrupted.

This script must stay observation-only. It delegates every capture to
scripts/obelisk_supervisor_snapshot.sh and never restarts servers, edits markers,
attaches debuggers, builds, installs, commits, or pushes.
EOF
}

INTERVAL=1800
COUNT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)
            [[ $# -ge 2 ]] || { echo "--interval requires a value" >&2; exit 2; }
            INTERVAL="$2"
            shift 2
            ;;
        --count)
            [[ $# -ge 2 ]] || { echo "--count requires a value" >&2; exit 2; }
            COUNT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! [[ "${INTERVAL}" =~ ^[0-9]+$ ]] || [[ "${INTERVAL}" -lt 1 ]]; then
    echo "--interval must be a positive integer" >&2
    exit 2
fi

if ! [[ "${COUNT}" =~ ^[0-9]+$ ]]; then
    echo "--count must be a non-negative integer" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOT="${SCRIPT_DIR}/obelisk_supervisor_snapshot.sh"

iteration=0
while true; do
    iteration=$((iteration + 1))
    printf '[%s] supervisor snapshot %d' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${iteration}"
    if [[ "${COUNT}" -gt 0 ]]; then
        printf '/%d' "${COUNT}"
    fi
    printf '\n'
    if ! "${SNAPSHOT}"; then
        echo "snapshot failed; stopping supervisor loop" >&2
        exit 1
    fi

    if [[ "${COUNT}" -gt 0 && "${iteration}" -ge "${COUNT}" ]]; then
        break
    fi

    sleep "${INTERVAL}"
done
