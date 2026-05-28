#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALLER="${REPO_ROOT}/scripts/install_obelisk_plugin.sh"
TMP_DIR="$(mktemp -d /tmp/obelisk-plugin-install.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT

assert_exists() {
    local path="$1"
    if [[ ! -e "${path}" ]]; then
        echo "Expected path to exist: ${path}" >&2
        exit 1
    fi
}

assert_not_exists() {
    local path="$1"
    if [[ -e "${path}" ]]; then
        echo "Expected path not to exist: ${path}" >&2
        find "${TMP_DIR}" -maxdepth 4 -print >&2
        exit 1
    fi
}

assert_contains() {
    local file="$1"
    local pattern="$2"
    if ! grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

plugin_src="${TMP_DIR}/ExamplePlugin.so"
root="${TMP_DIR}/root"
printf 'first\n' > "${plugin_src}"

"${INSTALLER}" "${plugin_src}" "${root}" > "${TMP_DIR}/install.out"
assert_exists "${root}/plugins/ExamplePlugin.so"
assert_not_exists "${root}/plugins/.ExamplePlugin.so.incoming.$$"
assert_contains "${root}/plugins/ExamplePlugin.so" '^first$'
assert_contains "${TMP_DIR}/install.out" 'Obelisk plugin installed to'

printf 'second\n' > "${plugin_src}"
"${INSTALLER}" --backup-existing "${plugin_src}" "${root}" > "${TMP_DIR}/replace.out"
assert_contains "${root}/plugins/ExamplePlugin.so" '^second$'
backup_count="$(find "${root}/plugins" -maxdepth 1 -name 'ExamplePlugin.so.*.bak' | wc -l)"
if [[ "${backup_count}" != "1" ]]; then
    echo "Expected one plugin backup, found ${backup_count}" >&2
    find "${root}/plugins" -maxdepth 1 -print >&2
    exit 1
fi

dry_root="${TMP_DIR}/dry-root"
"${INSTALLER}" --dry-run "${plugin_src}" "${dry_root}" > "${TMP_DIR}/dry-run.out"
assert_not_exists "${dry_root}"
assert_contains "${TMP_DIR}/dry-run.out" 'DRY-RUN:'

if "${INSTALLER}" --dry-run "${plugin_src}" "${dry_root}" "${TMP_DIR}/other-root" \
    >"${TMP_DIR}/extra-root.out" 2>"${TMP_DIR}/extra-root.err"; then
    echo "Installer accepted an extra positional root" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/extra-root.err" 'Unexpected extra argument'

bad_ext="${TMP_DIR}/BadPlugin.txt"
printf 'bad\n' > "${bad_ext}"
if "${INSTALLER}" "${bad_ext}" "${root}" >"${TMP_DIR}/bad-ext.out" 2>"${TMP_DIR}/bad-ext.err"; then
    echo "Installer accepted non-.so plugin" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/bad-ext.err" 'must end in .so'

symlink_src="${TMP_DIR}/SymlinkPlugin.so"
ln -s "${plugin_src}" "${symlink_src}"
if "${INSTALLER}" "${symlink_src}" "${root}" >"${TMP_DIR}/symlink.out" 2>"${TMP_DIR}/symlink.err"; then
    echo "Installer accepted symlink plugin source" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/symlink.err" 'regular non-symlink'

for invalid_root in "" "/" "." "relative/root"; do
    if "${INSTALLER}" --dry-run "${plugin_src}" "${invalid_root}" \
        >"${TMP_DIR}/invalid-root.out" 2>"${TMP_DIR}/invalid-root.err"; then
        echo "Installer accepted invalid root '${invalid_root}'" >&2
        exit 1
    fi
    assert_contains "${TMP_DIR}/invalid-root.err" 'Install root must be a non-root absolute path'
done

symlink_root="${TMP_DIR}/root-symlink"
ln -s "${root}" "${symlink_root}"
if "${INSTALLER}" --dry-run "${plugin_src}" "${symlink_root}" \
    >"${TMP_DIR}/symlink-root.out" 2>"${TMP_DIR}/symlink-root.err"; then
    echo "Installer accepted symlink root" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/symlink-root.err" 'Install root must not be a symlink'

symlink_plugins_root="${TMP_DIR}/root-symlink-plugins"
symlink_plugins_target="${TMP_DIR}/external-plugins"
mkdir -p "${symlink_plugins_root}" "${symlink_plugins_target}"
ln -s "${symlink_plugins_target}" "${symlink_plugins_root}/plugins"
if "${INSTALLER}" --dry-run "${plugin_src}" "${symlink_plugins_root}" \
    >"${TMP_DIR}/symlink-plugins.out" 2>"${TMP_DIR}/symlink-plugins.err"; then
    echo "Installer accepted symlink plugins directory" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/symlink-plugins.err" 'Managed install path must not be a symlink'

directory_destination_root="${TMP_DIR}/root-directory-destination"
mkdir -p "${directory_destination_root}/plugins/ExamplePlugin.so"
if "${INSTALLER}" "${plugin_src}" "${directory_destination_root}" \
    >"${TMP_DIR}/directory-destination.out" 2>"${TMP_DIR}/directory-destination.err"; then
    echo "Installer accepted a plugin destination directory" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/directory-destination.err" 'Plugin destination must be a regular non-symlink file'
assert_not_exists "${directory_destination_root}/plugins/.ExamplePlugin.so.incoming.$$"

symlink_destination_root="${TMP_DIR}/root-symlink-destination"
mkdir -p "${symlink_destination_root}/plugins"
ln -s "${TMP_DIR}/external-plugin-target.so" "${symlink_destination_root}/plugins/ExamplePlugin.so"
if "${INSTALLER}" "${plugin_src}" "${symlink_destination_root}" \
    >"${TMP_DIR}/symlink-destination.out" 2>"${TMP_DIR}/symlink-destination.err"; then
    echo "Installer accepted a plugin destination symlink" >&2
    exit 1
fi
assert_contains "${TMP_DIR}/symlink-destination.err" 'Plugin destination must be a regular non-symlink file'

echo "test_install_obelisk_plugin passed"
