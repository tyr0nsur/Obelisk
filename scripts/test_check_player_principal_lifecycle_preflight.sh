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

make_server_binary() {
    local path="$1"
    printf 'ShooterGameServer fixture\n' > "${path}"
    sha256sum "${path}" | awk '{print $1}'
}

wrapper="${TMP_DIR}/ObeliskRun.sh"
cp "${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh" "${wrapper}"
server_binary="${TMP_DIR}/ShooterGameServer"
server_sha="$(make_server_binary "${server_binary}")"

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

root_window="${TMP_DIR}/root-window"
prepare_root "${root_window}"
: > "${root_window}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_window}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_window}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
"${CHECK}" \
    --instance arkserver2 \
    --mode observer-window \
    --obelisk-root "${root_window}" \
    --installed-wrapper "${wrapper}" \
    --server-binary "${server_binary}" \
    --expected-binary-sha256 "${server_sha}" \
    --allow-stopped \
    | grep -F 'player_principal_lifecycle_preflight=ok mode=observer-window instance=arkserver2' >/dev/null

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
    --expected-binary-sha256 "${server_sha}"
grep -F 'pass --allow-stopped' "${TMP_DIR}/stopped-without-allow.err" >/dev/null

echo "test_check_player_principal_lifecycle_preflight passed"
