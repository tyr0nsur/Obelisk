#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/install_obelisk_plugin.sh [options] <PluginName.so> [root]

Installs one Obelisk plugin into the shared plugin directory using a staged copy and
atomic rename inside the destination directory. The staged filename does not end in .so, so
runtime plugin discovery will not try to dlopen a partial copy.

Options:
  --dry-run              Print actions without changing files.
  --backup-existing      Back up a replaced plugin .so with a timestamp suffix.
  -h, --help             Show this help.

Default root:
  /servidor/ark/obelisk
EOF
}

ROOT="/servidor/ark/obelisk"
DRY_RUN=0
BACKUP_EXISTING=0
PLUGIN_SRC=""
ROOT_SET=0
STAMP="$(date +%Y%m%d-%H%M%S)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --backup-existing)
            BACKUP_EXISTING=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [[ -z "${PLUGIN_SRC}" ]]; then
                PLUGIN_SRC="$1"
            else
                if [[ "${ROOT_SET}" == "1" ]]; then
                    echo "Unexpected extra argument: $1" >&2
                    usage >&2
                    exit 2
                fi
                ROOT="$1"
                ROOT_SET=1
            fi
            shift
            ;;
    esac
done

if [[ -z "${PLUGIN_SRC}" ]]; then
    echo "Missing plugin .so path" >&2
    usage >&2
    exit 2
fi

if [[ ! -f "${PLUGIN_SRC}" || -L "${PLUGIN_SRC}" ]]; then
    echo "Plugin source must be a regular non-symlink file: ${PLUGIN_SRC}" >&2
    exit 1
fi

plugin_name="$(basename "${PLUGIN_SRC}")"
if [[ "${plugin_name}" != *.so || "${plugin_name}" == ".so" ]]; then
    echo "Plugin filename must end in .so: ${plugin_name}" >&2
    exit 1
fi

validate_root() {
    if [[ -z "${ROOT}" || "${ROOT}" != /* || "${ROOT}" == "/" ]]; then
        echo "Install root must be a non-root absolute path: ${ROOT:-<empty>}" >&2
        exit 2
    fi

    if [[ -L "${ROOT}" ]]; then
        echo "Install root must not be a symlink: ${ROOT}" >&2
        exit 2
    fi
}

validate_managed_subpaths() {
    local subpath
    for subpath in "$@"; do
        if [[ -L "${ROOT}/${subpath}" ]]; then
            echo "Managed install path must not be a symlink: ${ROOT}/${subpath}" >&2
            exit 2
        fi
    done
}

validate_root

PLUGIN_DIR="${ROOT}/plugins"
PLUGIN_DST="${PLUGIN_DIR}/${plugin_name}"
PLUGIN_TMP="${PLUGIN_DIR}/.${plugin_name}.incoming.$$"

run() {
    if [[ "${DRY_RUN}" == "1" ]]; then
        printf 'DRY-RUN:'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

cleanup() {
    if [[ "${DRY_RUN}" != "1" ]]; then
        rm -f "${PLUGIN_TMP}"
    fi
}
trap cleanup EXIT

validate_managed_subpaths "plugins"
run mkdir -p "${PLUGIN_DIR}"

if [[ "${BACKUP_EXISTING}" == "1" && -e "${PLUGIN_DST}" ]]; then
    run cp -a "${PLUGIN_DST}" "${PLUGIN_DST}.${STAMP}.bak"
fi

run install -m 755 "${PLUGIN_SRC}" "${PLUGIN_TMP}"
run mv -f "${PLUGIN_TMP}" "${PLUGIN_DST}"

echo "Obelisk plugin installed to ${PLUGIN_DST}"
