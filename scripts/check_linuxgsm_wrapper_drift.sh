#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh"
INSTALLED="/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh"

usage() {
    cat <<'EOF'
Usage: scripts/check_linuxgsm_wrapper_drift.sh [options]

Compares the versioned LinuxGSM production wrapper with an installed wrapper without
modifying server state. The check fails if either path is missing, is a symlink, is not a
regular file, or differs byte-for-byte.

Options:
  --expected <path>   Versioned wrapper path. Default: packaging/linuxgsm/ObeliskRun.sh.
  --installed <path>  Installed wrapper path. Default:
                      /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh.
  -h, --help          Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --expected)
            EXPECTED="${2:?--expected requires a path}"
            shift 2
            ;;
        --installed)
            INSTALLED="${2:?--installed requires a path}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

require_regular_file() {
    local label="$1"
    local path="$2"

    if [[ -L "${path}" ]]; then
        echo "${label} wrapper must not be a symlink: ${path}" >&2
        exit 1
    fi
    if [[ ! -f "${path}" ]]; then
        echo "${label} wrapper must be a regular file: ${path}" >&2
        exit 1
    fi
}

require_regular_file "Expected" "${EXPECTED}"
require_regular_file "Installed" "${INSTALLED}"

expected_hash="$(sha256sum "${EXPECTED}" | awk '{print $1}')"
installed_hash="$(sha256sum "${INSTALLED}" | awk '{print $1}')"

if ! cmp -s "${EXPECTED}" "${INSTALLED}"; then
    cat >&2 <<EOF
LinuxGSM wrapper drift detected.
expected:  ${EXPECTED}
installed: ${INSTALLED}
expected_sha256:  ${expected_hash}
installed_sha256: ${installed_hash}

Refresh the installed wrapper only during an approved maintenance window:
  install -m 755 ${EXPECTED} ${INSTALLED}
EOF
    exit 1
fi

printf 'LinuxGSM wrapper matches versioned template: %s\n' "${INSTALLED}"
printf 'sha256=%s\n' "${installed_hash}"
