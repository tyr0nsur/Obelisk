#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d /tmp/obelisk-wrapper-markers.XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT
WRAPPER_DIR="${TMP_DIR}/wrapper"
WRAPPER="${WRAPPER_DIR}/ObeliskRun.sh"
DEBUG_WRAPPER="${WRAPPER_DIR}/ObeliskRunDebug.sh"
RUN_CWD="${TMP_DIR}/cwd"
LIBC_SO="$(ldconfig -p | awk '/libc\.so\.6/{print $NF; exit}')"
if [[ -z "${LIBC_SO}" ]]; then
    echo "Could not locate libc.so.6 for harmless LD_PRELOAD fixture" >&2
    exit 1
fi

assert_contains() {
    local file="$1"
    local pattern="$2"
    if ! grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

assert_not_contains() {
    local file="$1"
    local pattern="$2"
    if grep -Eq "${pattern}" "${file}"; then
        echo "Expected ${file} not to match ${pattern}" >&2
        cat "${file}" >&2
        exit 1
    fi
}

mkdir -p "${WRAPPER_DIR}" "${RUN_CWD}"
cp "${REPO_ROOT}/packaging/linuxgsm/ObeliskRun.sh" "${WRAPPER}"
cp "${REPO_ROOT}/packaging/linuxgsm/ObeliskRunDebug.sh" "${DEBUG_WRAPPER}"
chmod +x "${WRAPPER}" "${DEBUG_WRAPPER}"

cat > "${WRAPPER_DIR}/ShooterGameServer" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
{
    printf 'args=%s\n' "$*"
    printf 'server_path=%s\n' "$0"
    printf 'cwd=%s\n' "$(pwd)"
    env | sort
} > "${OBELISK_WRAPPER_CAPTURE}"
SH
chmod +x "${WRAPPER_DIR}/ShooterGameServer"

run_wrapper() {
    local root="$1"
    local capture="$2"
    shift 2

    (
        cd "${RUN_CWD}"
        OBELISK_ROOT="${root}" \
        OBELISK_WRAPPER_CAPTURE="${capture}" \
        "${WRAPPER}" "$@"
    )
}

run_wrapper_with_instance() {
    local root="$1"
    local capture="$2"
    local instance="$3"
    shift 3

    (
        cd "${RUN_CWD}"
        OBELISK_ROOT="${root}" \
        OBELISK_INSTANCE_ID="${instance}" \
        OBELISK_WRAPPER_CAPTURE="${capture}" \
        "${WRAPPER}" "$@"
    )
}

expect_wrapper_failure() {
    local label="$1"
    shift

    if "$@" > "${TMP_DIR}/${label}.stdout" 2> "${TMP_DIR}/${label}.stderr"; then
        echo "Expected wrapper failure for ${label}" >&2
        cat "${TMP_DIR}/${label}.stdout" >&2
        cat "${TMP_DIR}/${label}.stderr" >&2
        exit 1
    fi
}

prepare_root() {
    local root="$1"
    mkdir -p \
        "${root}/lib" \
        "${root}/plugins" \
        "${root}/config" \
        "${root}/logs" \
        "${root}/state/instances/arkserver2"
    cp "${LIBC_SO}" "${root}/lib/libobelisk.so"
}

root_no_marker="${TMP_DIR}/root-no-marker"
capture_no_marker="${TMP_DIR}/no-marker.env"
prepare_root "${root_no_marker}"
run_wrapper "${root_no_marker}" "${capture_no_marker}" TheIsland?listen

assert_contains "${capture_no_marker}" "^server_path=${WRAPPER_DIR}/ShooterGameServer$"
assert_contains "${capture_no_marker}" "^cwd=${RUN_CWD}$"
assert_contains "${capture_no_marker}" '^OBELISK_INSTANCE_ID=arkserver2$'
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='
assert_not_contains "${capture_no_marker}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_CHAT_ROUTE_OBSERVER='
assert_not_contains "${capture_no_marker}" '^OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_CHAT_ROUTE_OBSERVER_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_no_marker}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_ITEM_RETURN_EVENTS='
assert_not_contains "${capture_no_marker}" '^OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING='
assert_not_contains "${capture_no_marker}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT='

root_gen2_no_marker="${TMP_DIR}/root-gen2-no-marker"
capture_gen2_no_marker="${TMP_DIR}/gen2-no-marker.env"
prepare_root "${root_gen2_no_marker}"
mkdir -p "${root_gen2_no_marker}/state/instances/arkserver3"
run_wrapper "${root_gen2_no_marker}" "${capture_gen2_no_marker}" Gen2?listen

assert_contains "${capture_gen2_no_marker}" '^OBELISK_INSTANCE_ID=arkserver3$'
assert_not_contains "${capture_gen2_no_marker}" '^OBELISK_ENABLE_PROCESS_EVENT_HOOK='
assert_not_contains "${capture_gen2_no_marker}" '^OBELISK_DISABLE_PLUGINS='
assert_not_contains "${capture_gen2_no_marker}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER='

root_marker="${TMP_DIR}/root-marker"
capture_marker="${TMP_DIR}/marker.env"
prepare_root "${root_marker}"
: > "${root_marker}/state/instances/arkserver2/enable-structure-reflection"
: > "${root_marker}/state/instances/arkserver2/enable-inventory-reflection"
: > "${root_marker}/state/instances/arkserver2/enable-chat-reflection"
expect_wrapper_failure observer-marker-without-wrapper-approval env \
    OBELISK_ROOT="${root_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-marker-without-wrapper-approval.env" \
    "${WRAPPER}" TheIsland?listen

: > "${root_marker}/state/instances/arkserver2/allow-experimental-observers"
expect_wrapper_failure observer-allow-marker-without-wrapper-approval env \
    OBELISK_ROOT="${root_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-allow-marker-without-wrapper-approval.env" \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure observer-debug-profile-without-marker env \
    OBELISK_ROOT="${root_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-profile-without-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen

root_empty_observer_profile="${TMP_DIR}/root-empty-observer-profile"
prepare_root "${root_empty_observer_profile}"
: > "${root_empty_observer_profile}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_empty_observer_profile}/state/instances/arkserver2/allow-experimental-observers"
expect_wrapper_failure observer-debug-profile-without-scoped-marker env \
    OBELISK_ROOT="${root_empty_observer_profile}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-profile-without-scoped-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen

root_observer_profile_missing_experimental="${TMP_DIR}/root-observer-profile-missing-experimental"
prepare_root "${root_observer_profile_missing_experimental}"
: > "${root_observer_profile_missing_experimental}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_observer_profile_missing_experimental}/state/instances/arkserver2/enable-chat-events"
expect_wrapper_failure observer-debug-profile-without-experimental-approval env \
    OBELISK_ROOT="${root_observer_profile_missing_experimental}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-profile-without-experimental-approval.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen

root_observer_profile_escape_marker="${TMP_DIR}/root-observer-profile-escape-marker"
prepare_root "${root_observer_profile_escape_marker}"
: > "${root_observer_profile_escape_marker}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_observer_profile_escape_marker}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_observer_profile_escape_marker}/state/instances/arkserver2/enable-chat-events"
: > "${root_observer_profile_escape_marker}/state/instances/arkserver2/allow-ptrace"
expect_wrapper_failure observer-debug-profile-with-debug-marker env \
    OBELISK_ROOT="${root_observer_profile_escape_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-profile-with-debug-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen

root_symlink_scoped_observer_profile="${TMP_DIR}/root-symlink-scoped-observer-profile"
prepare_root "${root_symlink_scoped_observer_profile}"
: > "${root_symlink_scoped_observer_profile}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_symlink_scoped_observer_profile}/state/instances/arkserver2/allow-experimental-observers"
: > "${TMP_DIR}/external-chat-events-marker"
ln -s "${TMP_DIR}/external-chat-events-marker" \
    "${root_symlink_scoped_observer_profile}/state/instances/arkserver2/enable-chat-events"
expect_wrapper_failure observer-debug-profile-with-symlink-scoped-marker env \
    OBELISK_ROOT="${root_symlink_scoped_observer_profile}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-profile-with-symlink-scoped-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen

: > "${root_marker}/state/instances/arkserver2/allow-observer-debug-window"
expect_wrapper_failure observer-debug-reflection-markers-without-explicit-env env \
    OBELISK_ROOT="${root_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/observer-debug-reflection-markers-without-explicit-env.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_marker}" \
    OBELISK_WRAPPER_CAPTURE="${capture_marker}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_REFLECTION_LOG_LIMIT=0 \
    OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0 \
    OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=0 \
    OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0 \
    OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_marker}" '^OBELISK_ENABLE_CHAT_REFLECTION=1$'
assert_contains "${capture_marker}" '^OBELISK_CHAT_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_marker}" '^OBELISK_CHAT_REFLECTION_LOG_LIMIT=0$'
assert_not_contains "${capture_marker}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_contains "${capture_marker}" '^OBELISK_ENABLE_INVENTORY_REFLECTION=1$'
assert_contains "${capture_marker}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_marker}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0$'
assert_contains "${capture_marker}" '^OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=0$'
assert_contains "${capture_marker}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION=1$'
assert_contains "${capture_marker}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_marker}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0$'
assert_contains "${capture_marker}" '^OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=0$'
assert_not_contains "${capture_marker}" '^OBELISK_ENABLE_ITEM_RETURN_EVENTS='
assert_not_contains "${capture_marker}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER='

root_player_principal="${TMP_DIR}/root-player-principal"
capture_player_principal="${TMP_DIR}/player-principal.env"
prepare_root "${root_player_principal}"
: > "${root_player_principal}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_player_principal}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_player_principal}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
expect_wrapper_failure player-principal-marker-stable-profile env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-without-stable-markers env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-without-stable-markers.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
: > "${root_player_principal}/state/instances/arkserver2/enable-process-event-hook"
: > "${root_player_principal}/state/instances/arkserver2/disable-plugins"
expect_wrapper_failure player-principal-marker-without-explicit-budget env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-without-explicit-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-without-binary-sha env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-without-binary-sha.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-zero-log-budget env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-zero-log-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-small-log-budget env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-small-log-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=2 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-unsupported-sha env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-unsupported-sha.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=1111111111111111111111111111111111111111111111111111111111111111 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-dispatch-budget env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-dispatch-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-too-large-log-budget env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-too-large-log-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=11 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-invalid-diagnostic-candidates env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-invalid-diagnostic-candidates.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-near-miss-without-diagnostics env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-near-miss-without-diagnostics.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-invalid-near-miss-scan-limit env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-invalid-near-miss-scan-limit.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=10001 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-route-sampling-without-diagnostics env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-route-sampling-without-diagnostics.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-invalid-route-sampling-flag env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-invalid-route-sampling-flag.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-route-sample-limit-without-flag env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-route-sample-limit-without-flag.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure player-principal-marker-with-invalid-route-sample-limit env \
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-with-invalid-route-sample-limit.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=10001 \
    "${WRAPPER}" TheIsland?listen

root_player_principal_missing_experimental="${TMP_DIR}/root-player-principal-missing-experimental"
prepare_root "${root_player_principal_missing_experimental}"
: > "${root_player_principal_missing_experimental}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_player_principal_missing_experimental}/state/instances/arkserver2/enable-process-event-hook"
: > "${root_player_principal_missing_experimental}/state/instances/arkserver2/disable-plugins"
: > "${root_player_principal_missing_experimental}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
expect_wrapper_failure player-principal-marker-without-experimental-approval env \
    OBELISK_ROOT="${root_player_principal_missing_experimental}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-marker-without-experimental-approval.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen

root_player_principal_symlink_marker="${TMP_DIR}/root-player-principal-symlink-marker"
prepare_root "${root_player_principal_symlink_marker}"
: > "${root_player_principal_symlink_marker}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_player_principal_symlink_marker}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_player_principal_symlink_marker}/state/instances/arkserver2/enable-process-event-hook"
: > "${root_player_principal_symlink_marker}/state/instances/arkserver2/disable-plugins"
: > "${TMP_DIR}/external-player-principal-lifecycle-marker"
ln -s "${TMP_DIR}/external-player-principal-lifecycle-marker" \
    "${root_player_principal_symlink_marker}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
expect_wrapper_failure player-principal-symlink-observer-marker env \
    OBELISK_ROOT="${root_player_principal_symlink_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-symlink-observer-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen

root_player_principal_stale_env="${TMP_DIR}/root-player-principal-stale-env"
prepare_root "${root_player_principal_stale_env}"
: > "${root_player_principal_stale_env}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_player_principal_stale_env}/state/instances/arkserver2/allow-experimental-observers"
expect_wrapper_failure player-principal-env-without-marker env \
    OBELISK_ROOT="${root_player_principal_stale_env}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-env-without-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen

(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${capture_player_principal}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_player_principal}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1$'
assert_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10$'
assert_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0$'
assert_not_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES='
assert_not_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS='
assert_not_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT='
assert_not_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING='
assert_not_contains "${capture_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_CHAT_REFLECTION='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_CHAT_ROUTE_OBSERVER='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_ITEM_RETURN_EVENTS='
assert_not_contains "${capture_player_principal}" '^OBELISK_DEBUG_ALLOW_PTRACE='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_DEBUG_CONTROL='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_REFLECTION_SCANNER='
assert_not_contains "${capture_player_principal}" '^OBELISK_ENABLE_NATIVE_EXEC_PROBES='
assert_not_contains "${capture_player_principal}" '^OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS='
assert_not_contains "${capture_player_principal}" '^OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS='
assert_not_contains "${capture_player_principal}" '^OBELISK_ALLOW_CALL_PROCESS_EVENT='
assert_not_contains "${capture_player_principal}" '^OBELISK_ALLOW_PROCESS_EVENT_BLOCKING='

root_gen2_player_principal="${TMP_DIR}/root-gen2-player-principal"
capture_gen2_player_principal="${TMP_DIR}/gen2-player-principal.env"
prepare_root "${root_gen2_player_principal}"
mkdir -p "${root_gen2_player_principal}/state/instances/arkserver3"
: > "${root_gen2_player_principal}/state/instances/arkserver3/allow-observer-debug-window"
: > "${root_gen2_player_principal}/state/instances/arkserver3/allow-experimental-observers"
: > "${root_gen2_player_principal}/state/instances/arkserver3/enable-process-event-hook"
: > "${root_gen2_player_principal}/state/instances/arkserver3/disable-plugins"
: > "${root_gen2_player_principal}/state/instances/arkserver3/enable-player-principal-lifecycle-observer"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_gen2_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${capture_gen2_player_principal}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" Gen2?listen
)

assert_contains "${capture_gen2_player_principal}" '^OBELISK_INSTANCE_ID=arkserver3$'
assert_contains "${capture_gen2_player_principal}" '^OBELISK_ENABLE_PROCESS_EVENT_HOOK=1$'
assert_contains "${capture_gen2_player_principal}" '^OBELISK_DISABLE_PLUGINS=1$'
assert_contains "${capture_gen2_player_principal}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1$'
assert_contains "${capture_gen2_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10$'
assert_contains "${capture_gen2_player_principal}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0$'

capture_player_principal_diagnostic="${TMP_DIR}/player-principal-diagnostic.env"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${capture_player_principal_diagnostic}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_player_principal_diagnostic}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1$'
assert_contains "${capture_player_principal_diagnostic}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1$'

capture_player_principal_near_miss="${TMP_DIR}/player-principal-near-miss.env"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${capture_player_principal_near_miss}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_player_principal_near_miss}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1$'
assert_contains "${capture_player_principal_near_miss}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1$'
assert_contains "${capture_player_principal_near_miss}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS=1$'
assert_contains "${capture_player_principal_near_miss}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT=100$'

capture_player_principal_route_sampling="${TMP_DIR}/player-principal-route-sampling.env"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_player_principal}" \
    OBELISK_WRAPPER_CAPTURE="${capture_player_principal_route_sampling}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=100 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_player_principal_route_sampling}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1$'
assert_contains "${capture_player_principal_route_sampling}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1$'
assert_contains "${capture_player_principal_route_sampling}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1$'
assert_contains "${capture_player_principal_route_sampling}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=100$'

for residual_observer_marker in \
    enable-chat-events \
    enable-chat-reflection \
    enable-chat-route-observer \
    enable-inventory-reflection \
    enable-structure-reflection \
    enable-item-return-events \
    enable-inventory-action-redacted-observer \
    allow-ptrace \
    enable-debug-control \
    enable-reflection-scanner \
    enable-native-exec-probes \
    allow-global-process-event-callbacks \
    allow-filtered-process-event-callbacks \
    allow-call-process-event \
    allow-process-event-blocking
do
    root_player_principal_residual="${TMP_DIR}/root-player-principal-residual-${residual_observer_marker}"
    prepare_root "${root_player_principal_residual}"
    : > "${root_player_principal_residual}/state/instances/arkserver2/allow-observer-debug-window"
    : > "${root_player_principal_residual}/state/instances/arkserver2/allow-experimental-observers"
    : > "${root_player_principal_residual}/state/instances/arkserver2/enable-process-event-hook"
    : > "${root_player_principal_residual}/state/instances/arkserver2/disable-plugins"
    : > "${root_player_principal_residual}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
    : > "${root_player_principal_residual}/state/instances/arkserver2/${residual_observer_marker}"
    expect_wrapper_failure "player-principal-window-with-residual-${residual_observer_marker}" env \
        OBELISK_ROOT="${root_player_principal_residual}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-window-with-residual-${residual_observer_marker}.env" \
        OBELISK_WRAPPER_PROFILE=observer-debug \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
        "${WRAPPER}" TheIsland?listen
done

root_player_principal_symlink_residual="${TMP_DIR}/root-player-principal-symlink-residual"
prepare_root "${root_player_principal_symlink_residual}"
: > "${root_player_principal_symlink_residual}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_player_principal_symlink_residual}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_player_principal_symlink_residual}/state/instances/arkserver2/enable-process-event-hook"
: > "${root_player_principal_symlink_residual}/state/instances/arkserver2/disable-plugins"
: > "${root_player_principal_symlink_residual}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
: > "${TMP_DIR}/external-player-principal-chat-reflection-marker"
ln -s "${TMP_DIR}/external-player-principal-chat-reflection-marker" \
    "${root_player_principal_symlink_residual}/state/instances/arkserver2/enable-chat-reflection"
expect_wrapper_failure player-principal-window-with-symlink-residual-marker env \
    OBELISK_ROOT="${root_player_principal_symlink_residual}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-window-with-symlink-residual-marker.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen

root_chat_events="${TMP_DIR}/root-chat-events"
capture_chat_events="${TMP_DIR}/chat-events.env"
prepare_root "${root_chat_events}"
: > "${root_chat_events}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_chat_events}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_chat_events}/state/instances/arkserver2/enable-chat-events"
expect_wrapper_failure chat-events-marker-stable-profile env \
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-events-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-events-marker-without-explicit-budget env \
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-events-marker-without-explicit-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-events-marker-with-zero-budget env \
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-events-marker-with-zero-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-events-marker-with-padded-zero-budget env \
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-events-marker-with-padded-zero-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=00 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-events-marker-with-invalid-sha env \
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-events-marker-with-invalid-sha.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=bad-chat-events-sha \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_chat_events}" \
    OBELISK_WRAPPER_CAPTURE="${capture_chat_events}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_chat_events}" '^OBELISK_ENABLE_CHAT_EVENTS=1$'
assert_contains "${capture_chat_events}" '^OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_chat_events}" '^OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1$'
assert_not_contains "${capture_chat_events}" '^OBELISK_ENABLE_CHAT_REFLECTION='
assert_not_contains "${capture_chat_events}" '^OBELISK_CHAT_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_chat_events}" '^OBELISK_CHAT_REFLECTION_LOG_LIMIT='

root_item_return="${TMP_DIR}/root-item-return"
capture_item_return="${TMP_DIR}/item-return.env"
prepare_root "${root_item_return}"
: > "${root_item_return}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_item_return}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_item_return}/state/instances/arkserver2/enable-item-return-events"
expect_wrapper_failure item-return-marker-stable-profile env \
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/item-return-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure item-return-marker-without-explicit-budget env \
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/item-return-marker-without-explicit-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure item-return-marker-with-zero-budget env \
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/item-return-marker-with-zero-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure item-return-marker-with-invalid-sha env \
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/item-return-marker-with-invalid-sha.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=bad-item-return-sha \
    OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure item-return-marker-with-invalid-log-limit env \
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/item-return-marker-with-invalid-log-limit.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=1 \
    OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT=bad-log-limit \
    "${WRAPPER}" TheIsland?listen
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_item_return}" \
    OBELISK_WRAPPER_CAPTURE="${capture_item_return}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=2 \
    OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_item_return}" '^OBELISK_ENABLE_ITEM_RETURN_EVENTS=1$'
assert_contains "${capture_item_return}" '^OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_item_return}" '^OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT=2$'
assert_contains "${capture_item_return}" '^OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT=1$'
assert_not_contains "${capture_item_return}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_item_return}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='

root_chat_route="${TMP_DIR}/root-chat-route"
capture_chat_route="${TMP_DIR}/chat-route.env"
prepare_root "${root_chat_route}"
: > "${root_chat_route}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_chat_route}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_chat_route}/state/instances/arkserver2/enable-chat-route-observer"
expect_wrapper_failure chat-route-marker-stable-profile env \
    OBELISK_ROOT="${root_chat_route}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-route-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-route-marker-without-explicit-budget env \
    OBELISK_ROOT="${root_chat_route}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-route-marker-without-explicit-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-route-marker-with-zero-budget env \
    OBELISK_ROOT="${root_chat_route}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-route-marker-with-zero-budget.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=0 \
    "${WRAPPER}" TheIsland?listen
expect_wrapper_failure chat-route-marker-with-unsupported-sha env \
    OBELISK_ROOT="${root_chat_route}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/chat-route-marker-with-unsupported-sha.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=1111111111111111111111111111111111111111111111111111111111111111 \
    OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=1 \
    "${WRAPPER}" TheIsland?listen
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_chat_route}" \
    OBELISK_WRAPPER_CAPTURE="${capture_chat_route}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=2 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_chat_route}" '^OBELISK_ENABLE_CHAT_ROUTE_OBSERVER=1$'
assert_contains "${capture_chat_route}" '^OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_chat_route}" '^OBELISK_CHAT_ROUTE_OBSERVER_LIMIT=2$'
assert_not_contains "${capture_chat_route}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_chat_route}" '^OBELISK_ENABLE_CHAT_REFLECTION='

root_chat_events_ragnarok="${TMP_DIR}/root-chat-events-ragnarok"
capture_chat_events_ragnarok="${TMP_DIR}/chat-events-ragnarok.env"
prepare_root "${root_chat_events_ragnarok}"
mkdir -p "${root_chat_events_ragnarok}/state/instances/arkserver"
: > "${root_chat_events_ragnarok}/state/instances/arkserver/allow-observer-debug-window"
: > "${root_chat_events_ragnarok}/state/instances/arkserver/allow-experimental-observers"
: > "${root_chat_events_ragnarok}/state/instances/arkserver/enable-chat-events"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_chat_events_ragnarok}" \
    OBELISK_WRAPPER_CAPTURE="${capture_chat_events_ragnarok}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1 \
    "${WRAPPER}" Ragnarok?listen
)

assert_contains "${capture_chat_events_ragnarok}" '^OBELISK_INSTANCE_ID=arkserver$'
assert_contains "${capture_chat_events_ragnarok}" '^OBELISK_ENABLE_CHAT_EVENTS=1$'
assert_contains "${capture_chat_events_ragnarok}" '^OBELISK_CHAT_EVENTS_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_chat_events_ragnarok}" '^OBELISK_CHAT_EVENTS_DISPATCH_LIMIT=1$'
assert_not_contains "${capture_chat_events_ragnarok}" '^OBELISK_ENABLE_CHAT_REFLECTION='

root_ragnarok_stale="${TMP_DIR}/root-ragnarok-stale"
capture_ragnarok_stale="${TMP_DIR}/ragnarok-stale.env"
prepare_root "${root_ragnarok_stale}"
mkdir -p "${root_ragnarok_stale}/state/instances/arkserver"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-chat-events"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-chat-reflection"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-inventory-reflection"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-structure-reflection"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-item-return-events"
: > "${root_ragnarok_stale}/state/instances/arkserver/enable-player-principal-lifecycle-observer"
expect_wrapper_failure ragnarok-stale-observer-markers env \
    OBELISK_ROOT="${root_ragnarok_stale}" \
    OBELISK_WRAPPER_CAPTURE="${capture_ragnarok_stale}" \
    "${WRAPPER}" Ragnarok?listen
: > "${root_ragnarok_stale}/state/instances/arkserver/allow-experimental-observers"
: > "${root_ragnarok_stale}/state/instances/arkserver/allow-observer-debug-window"
expect_wrapper_failure ragnarok-observer-markers-stable-profile env \
    OBELISK_ROOT="${root_ragnarok_stale}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/ragnarok-observer-markers-stable-profile.env" \
    "${WRAPPER}" Ragnarok?listen

root_override="${TMP_DIR}/root-override"
capture_override="${TMP_DIR}/override.env"
prepare_root "${root_override}"
: > "${root_override}/state/instances/arkserver2/allow-observer-debug-window"
: > "${root_override}/state/instances/arkserver2/allow-experimental-observers"
: > "${root_override}/state/instances/arkserver2/enable-structure-reflection"
: > "${root_override}/state/instances/arkserver2/enable-inventory-reflection"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_override}" \
    OBELISK_WRAPPER_CAPTURE="${capture_override}" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5 \
    OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=8 \
    OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
    OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=7 \
    OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=9 \
    "${WRAPPER}" TheIsland?listen
)

assert_contains "${capture_override}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_override}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=5$'
assert_contains "${capture_override}" '^OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT=8$'
assert_contains "${capture_override}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520$'
assert_contains "${capture_override}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=7$'
assert_contains "${capture_override}" '^OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=9$'

root_invalid="${TMP_DIR}/root-invalid"
capture_wrong_instance="${TMP_DIR}/wrong-instance.env"
prepare_root "${root_invalid}"
mkdir -p "${root_invalid}/state/instances/not-arkserver2"
: > "${root_invalid}/state/instances/not-arkserver2/enable-chat-events"
: > "${root_invalid}/state/instances/not-arkserver2/enable-inventory-reflection"
: > "${root_invalid}/state/instances/not-arkserver2/enable-structure-reflection"
run_wrapper "${root_invalid}" "${capture_wrong_instance}" TheIsland?listen

assert_not_contains "${capture_wrong_instance}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_wrong_instance}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_wrong_instance}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='

capture_directory_marker="${TMP_DIR}/directory-marker.env"
mkdir -p "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
expect_wrapper_failure directory-observer-marker env \
    OBELISK_ROOT="${root_invalid}" \
    OBELISK_WRAPPER_CAPTURE="${capture_directory_marker}" \
    "${WRAPPER}" TheIsland?listen

capture_symlink_marker="${TMP_DIR}/symlink-marker.env"
rm -rf "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
: > "${TMP_DIR}/external-inventory-marker"
ln -s "${TMP_DIR}/external-inventory-marker" "${root_invalid}/state/instances/arkserver2/enable-inventory-reflection"
expect_wrapper_failure symlink-observer-marker env \
    OBELISK_ROOT="${root_invalid}" \
    OBELISK_WRAPPER_CAPTURE="${capture_symlink_marker}" \
    "${WRAPPER}" TheIsland?listen

root_malformed_player_principal_marker="${TMP_DIR}/root-malformed-player-principal-marker"
prepare_root "${root_malformed_player_principal_marker}"
mkdir -p "${root_malformed_player_principal_marker}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
expect_wrapper_failure player-principal-directory-observer-marker-stable-profile env \
    OBELISK_ROOT="${root_malformed_player_principal_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-directory-observer-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
rm -rf "${root_malformed_player_principal_marker}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
ln -s "${TMP_DIR}/missing-player-principal-lifecycle-marker" \
    "${root_malformed_player_principal_marker}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"
expect_wrapper_failure player-principal-broken-symlink-observer-marker-stable-profile env \
    OBELISK_ROOT="${root_malformed_player_principal_marker}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/player-principal-broken-symlink-observer-marker-stable-profile.env" \
    "${WRAPPER}" TheIsland?listen
rm -f "${root_malformed_player_principal_marker}/state/instances/arkserver2/enable-player-principal-lifecycle-observer"

expect_wrapper_failure unsafe-instance-id-marker-scope env \
    OBELISK_ROOT="${root_marker}" \
    OBELISK_INSTANCE_ID='../arkserver2' \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/traversal.env" \
    "${WRAPPER}" TheIsland?listen

for stable_debug_marker in \
    allow-ptrace \
    enable-debug-control \
    enable-reflection-scanner \
    enable-native-exec-probes \
    allow-global-process-event-callbacks \
    allow-filtered-process-event-callbacks \
    allow-call-process-event \
    allow-process-event-blocking \
    request-static-fname-probe
do
    root_stable_debug_marker="${TMP_DIR}/root-stable-debug-marker-${stable_debug_marker}"
    prepare_root "${root_stable_debug_marker}"
    : > "${root_stable_debug_marker}/state/instances/arkserver2/${stable_debug_marker}"
    expect_wrapper_failure "stable-debug-marker-${stable_debug_marker}" env \
        OBELISK_ROOT="${root_stable_debug_marker}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/stable-debug-marker-${stable_debug_marker}.env" \
        "${WRAPPER}" TheIsland?listen
done

root_inherited="${TMP_DIR}/root-inherited"
capture_inherited="${TMP_DIR}/inherited.env"
prepare_root "${root_inherited}"
for inherited_player_principal_env_name in \
    OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256 \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT
do
    case "${inherited_player_principal_env_name}" in
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256)
            inherited_player_principal_env_value="7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
            ;;
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT)
            inherited_player_principal_env_value="10"
            ;;
        OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT)
            inherited_player_principal_env_value="0"
            ;;
        *)
            inherited_player_principal_env_value="1"
            ;;
    esac
    expect_wrapper_failure "inherited-${inherited_player_principal_env_name}-stable-profile" env \
        OBELISK_ROOT="${root_inherited}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inherited-${inherited_player_principal_env_name}-stable-profile.env" \
        "${inherited_player_principal_env_name}=${inherited_player_principal_env_value}" \
        "${WRAPPER}" Ragnarok?listen
done
unset inherited_player_principal_env_name inherited_player_principal_env_value
expect_wrapper_failure inherited-observer-env-stable-profile env \
    OBELISK_ROOT="${root_inherited}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inherited-observer-env-stable-profile.env" \
    OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10 \
    "${WRAPPER}" Ragnarok?listen
expect_wrapper_failure inherited-scanner-root-env-stable-profile env \
    OBELISK_ROOT="${root_inherited}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inherited-scanner-root-env-stable-profile.env" \
    OBELISK_REFLECTION_STATIC_FNAME_ROOTS=0x5956f30 \
    "${WRAPPER}" Ragnarok?listen
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_inherited}" \
    OBELISK_WRAPPER_CAPTURE="${capture_inherited}" \
    OBELISK_PLUGIN_DIR=/tmp/unsafe-obelisk-plugins \
    OBELISK_CONFIG_DIR=/tmp/unsafe-obelisk-config \
    OBELISK_LOG_DIR=/tmp/unsafe-obelisk-logs \
    OBELISK_ENABLE_PROCESS_EVENT_HOOK=1 \
    OBELISK_DISABLE_PLUGINS=1 \
    "${WRAPPER}" Ragnarok?listen
)

assert_contains "${capture_inherited}" '^OBELISK_INSTANCE_ID=arkserver$'
assert_contains "${capture_inherited}" "^OBELISK_PLUGIN_DIR=${root_inherited}/plugins$"
assert_contains "${capture_inherited}" "^OBELISK_CONFIG_DIR=${root_inherited}/config$"
assert_contains "${capture_inherited}" "^OBELISK_LOG_DIR=${root_inherited}/logs$"
assert_not_contains "${capture_inherited}" '^OBELISK_PLUGIN_DIR=/tmp/unsafe-obelisk-plugins$'
assert_not_contains "${capture_inherited}" '^OBELISK_CONFIG_DIR=/tmp/unsafe-obelisk-config$'
assert_not_contains "${capture_inherited}" '^OBELISK_LOG_DIR=/tmp/unsafe-obelisk-logs$'
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_PROCESS_EVENT_HOOK='
assert_not_contains "${capture_inherited}" '^OBELISK_DISABLE_PLUGINS='
assert_not_contains "${capture_inherited}" '^OBELISK_DEBUG_ALLOW_PTRACE='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_DEBUG_CONTROL='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_REFLECTION_SCANNER='
assert_not_contains "${capture_inherited}" '^OBELISK_REFLECTION_STATIC_FNAME_ROOTS='
assert_not_contains "${capture_inherited}" '^OBELISK_REFLECTION_SAMPLE_STATIC_FNAME_ROOTS='
assert_not_contains "${capture_inherited}" '^OBELISK_REFLECTION_LOG_FNAME_REJECTS='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_NATIVE_EXEC_PROBES='
assert_not_contains "${capture_inherited}" '^OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS='
assert_not_contains "${capture_inherited}" '^OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS='
assert_not_contains "${capture_inherited}" '^OBELISK_ALLOW_CALL_PROCESS_EVENT='
assert_not_contains "${capture_inherited}" '^OBELISK_ALLOW_PROCESS_EVENT_BLOCKING='
assert_not_contains "${capture_inherited}" '^OBELISK_PE_TRACE_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_CHAT_EVENTS='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_EVENTS_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_EVENTS_DISPATCH_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_CHAT_REFLECTION='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_REFLECTION_LOG_TEXT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_CHAT_ROUTE_OBSERVER='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_CHAT_ROUTE_OBSERVER_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_INVENTORY_REFLECTION='
assert_not_contains "${capture_inherited}" '^OBELISK_INVENTORY_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_INVENTORY_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_STRUCTURE_REFLECTION='
assert_not_contains "${capture_inherited}" '^OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_ITEM_RETURN_EVENTS='
assert_not_contains "${capture_inherited}" '^OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING='
assert_not_contains "${capture_inherited}" '^OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT='

root_symlink_instance="${TMP_DIR}/root-symlink-instance"
prepare_root "${root_symlink_instance}"
mkdir -p "${root_symlink_instance}/real-instance"
rm -rf "${root_symlink_instance}/state/instances/arkserver2"
: > "${root_symlink_instance}/real-instance/enable-inventory-reflection"
ln -s "${root_symlink_instance}/real-instance" "${root_symlink_instance}/state/instances/arkserver2"
expect_wrapper_failure symlink-instance-marker-dir env \
    OBELISK_ROOT="${root_symlink_instance}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-instance.env" \
    "${WRAPPER}" TheIsland?listen

expect_wrapper_failure relative-root env \
    OBELISK_ROOT=relative/root \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/relative-root.env" \
    "${WRAPPER}" TheIsland?listen

root_symlink_real="${TMP_DIR}/root-symlink-real"
root_symlink_link="${TMP_DIR}/root-symlink-link"
prepare_root "${root_symlink_real}"
ln -s "${root_symlink_real}" "${root_symlink_link}"
expect_wrapper_failure symlink-root env \
    OBELISK_ROOT="${root_symlink_link}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-root.env" \
    "${WRAPPER}" TheIsland?listen

root_path_component_real_parent="${TMP_DIR}/root-path-component-real-parent"
root_path_component_link_parent="${TMP_DIR}/root-path-component-link-parent"
mkdir -p "${root_path_component_real_parent}"
ln -s "${root_path_component_real_parent}" "${root_path_component_link_parent}"
root_path_component_escape="${root_path_component_link_parent}/obelisk-root"
prepare_root "${root_path_component_escape}"
expect_wrapper_failure symlink-root-path-component env \
    OBELISK_ROOT="${root_path_component_escape}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-root-path-component.env" \
    "${WRAPPER}" TheIsland?listen

for missing_managed_dir in lib plugins config logs state state/instances; do
    missing_managed_label="${missing_managed_dir//\//-}"
    root_missing_managed="${TMP_DIR}/root-missing-managed-${missing_managed_label}"
    prepare_root "${root_missing_managed}"
    rm -rf "${root_missing_managed}/${missing_managed_dir}"
    expect_wrapper_failure "missing-managed-dir-${missing_managed_label}" env \
        OBELISK_ROOT="${root_missing_managed}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/missing-managed-dir-${missing_managed_label}.env" \
        "${WRAPPER}" TheIsland?listen
done
unset missing_managed_dir missing_managed_label root_missing_managed

for symlink_managed_dir in lib plugins config logs state state/instances; do
    symlink_managed_label="${symlink_managed_dir//\//-}"
    root_symlink_managed="${TMP_DIR}/root-symlink-managed-${symlink_managed_label}"
    prepare_root "${root_symlink_managed}"
    rm -rf "${root_symlink_managed}/${symlink_managed_dir}"
    mkdir -p "$(dirname "${root_symlink_managed}/${symlink_managed_dir}")" \
        "${TMP_DIR}/external-managed-${symlink_managed_label}"
    ln -s "${TMP_DIR}/external-managed-${symlink_managed_label}" \
        "${root_symlink_managed}/${symlink_managed_dir}"
    expect_wrapper_failure "symlink-managed-dir-${symlink_managed_label}" env \
        OBELISK_ROOT="${root_symlink_managed}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-managed-dir-${symlink_managed_label}.env" \
        "${WRAPPER}" TheIsland?listen
done
unset symlink_managed_dir symlink_managed_label root_symlink_managed

root_plugins_symlink="${TMP_DIR}/root-plugins-symlink"
prepare_root "${root_plugins_symlink}"
rm -rf "${root_plugins_symlink}/plugins"
mkdir -p "${TMP_DIR}/external-plugins"
ln -s "${TMP_DIR}/external-plugins" "${root_plugins_symlink}/plugins"
expect_wrapper_failure symlink-plugins env \
    OBELISK_ROOT="${root_plugins_symlink}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-plugins.env" \
    "${WRAPPER}" TheIsland?listen

root_lib_symlink="${TMP_DIR}/root-lib-symlink"
prepare_root "${root_lib_symlink}"
rm -f "${root_lib_symlink}/lib/libobelisk.so"
ln -s "${LIBC_SO}" "${root_lib_symlink}/lib/libobelisk.so"
expect_wrapper_failure symlink-runtime-lib env \
    OBELISK_ROOT="${root_lib_symlink}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/symlink-runtime-lib.env" \
    "${WRAPPER}" TheIsland?listen

root_unknown_observer_profile="${TMP_DIR}/root-unknown-observer-profile"
prepare_root "${root_unknown_observer_profile}"
expect_wrapper_failure unknown-map-observer-debug-profile env \
    OBELISK_ROOT="${root_unknown_observer_profile}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/unknown-map-observer-debug-profile.env" \
    OBELISK_WRAPPER_PROFILE=observer-debug \
    "${WRAPPER}" Extinction?listen

root_unknown_stale_env="${TMP_DIR}/root-unknown-stale-env"
prepare_root "${root_unknown_stale_env}"
expect_wrapper_failure unknown-map-stale-observer-env env \
    OBELISK_ROOT="${root_unknown_stale_env}" \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/unknown-map-stale-observer-env.env" \
    OBELISK_ENABLE_CHAT_EVENTS=1 \
    "${WRAPPER}" Extinction?listen

root_unknown_stale_marker="${TMP_DIR}/root-unknown-stale-marker"
prepare_root "${root_unknown_stale_marker}"
: > "${root_unknown_stale_marker}/state/instances/arkserver2/enable-chat-events"
expect_wrapper_failure unknown-map-stale-observer-marker env \
    OBELISK_ROOT="${root_unknown_stale_marker}" \
    OBELISK_INSTANCE_ID=arkserver2 \
    OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/unknown-map-stale-observer-marker.env" \
    "${WRAPPER}" Extinction?listen

capture_debug_default="${TMP_DIR}/debug-default.env"
root_debug_default="${TMP_DIR}/root-debug-default"
prepare_root "${root_debug_default}"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_debug_default}" \
    OBELISK_WRAPPER_CAPTURE="${capture_debug_default}" \
    OBELISK_PLUGIN_DIR=/tmp/unsafe-debug-plugins \
    OBELISK_CONFIG_DIR=/tmp/unsafe-debug-config \
    OBELISK_LOG_DIR=/tmp/unsafe-debug-logs \
    "${DEBUG_WRAPPER}" TheIsland?listen
)

assert_contains "${capture_debug_default}" '^OBELISK_INSTANCE_ID=arkserver-obelisk-debug$'
assert_contains "${capture_debug_default}" "^OBELISK_PLUGIN_DIR=${root_debug_default}/plugins$"
assert_contains "${capture_debug_default}" "^OBELISK_CONFIG_DIR=${root_debug_default}/config$"
assert_contains "${capture_debug_default}" "^OBELISK_LOG_DIR=${root_debug_default}/logs/isolated-debug$"
assert_not_contains "${capture_debug_default}" '^OBELISK_PLUGIN_DIR=/tmp/unsafe-debug-plugins$'
assert_not_contains "${capture_debug_default}" '^OBELISK_CONFIG_DIR=/tmp/unsafe-debug-config$'
assert_not_contains "${capture_debug_default}" '^OBELISK_LOG_DIR=/tmp/unsafe-debug-logs$'
assert_contains "${capture_debug_default}" '^OBELISK_ENABLE_PROCESS_EVENT_HOOK=1$'
assert_contains "${capture_debug_default}" '^OBELISK_DISABLE_PLUGINS=1$'
assert_contains "${capture_debug_default}" '^OBELISK_PE_TRACE_LIMIT=0$'
assert_not_contains "${capture_debug_default}" '^OBELISK_DEBUG_ALLOW_PTRACE='
assert_not_contains "${capture_debug_default}" '^OBELISK_ENABLE_NATIVE_EXEC_PROBES='

capture_debug_ptrace="${TMP_DIR}/debug-ptrace.env"
(
    cd "${RUN_CWD}"
    OBELISK_ROOT="${root_debug_default}" \
    OBELISK_WRAPPER_CAPTURE="${capture_debug_ptrace}" \
    OBELISK_DEBUG_ALLOW_PTRACE=1 \
    "${DEBUG_WRAPPER}" TheIsland?listen
)

assert_contains "${capture_debug_ptrace}" '^OBELISK_DEBUG_ALLOW_PTRACE=1$'

run_pending_inventory_action_redacted_observer_tests() {
    local root_future="${TMP_DIR}/root-inventory-action-redacted-observer"
    local capture_future="${TMP_DIR}/inventory-action-redacted-observer.env"
    prepare_root "${root_future}"

    : > "${root_future}/state/instances/arkserver2/enable-inventory-action-redacted-observer"
    expect_wrapper_failure inventory-action-redacted-marker-stable-profile env \
        OBELISK_ROOT="${root_future}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inventory-action-redacted-marker-stable-profile.env" \
        "${WRAPPER}" TheIsland?listen

    : > "${root_future}/state/instances/arkserver2/allow-observer-debug-window"
    : > "${root_future}/state/instances/arkserver2/allow-experimental-observers"
    : > "${root_future}/state/instances/arkserver2/enable-inventory-action-redacted-observer"
    expect_wrapper_failure inventory-action-redacted-marker-without-explicit-budget env \
        OBELISK_ROOT="${root_future}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inventory-action-redacted-marker-without-explicit-budget.env" \
        OBELISK_WRAPPER_PROFILE=observer-debug \
        "${WRAPPER}" TheIsland?listen
    expect_wrapper_failure inventory-action-redacted-marker-with-dispatch-budget env \
        OBELISK_ROOT="${root_future}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inventory-action-redacted-marker-with-dispatch-budget.env" \
        OBELISK_WRAPPER_PROFILE=observer-debug \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT=1 \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT=1 \
        "${WRAPPER}" TheIsland?listen
    mkdir -p "${root_future}/state/instances/arkserver"
    ln -s "${TMP_DIR}/external-inventory-action-redacted-marker" \
        "${root_future}/state/instances/arkserver/enable-inventory-action-redacted-observer"
    expect_wrapper_failure inventory-action-redacted-symlink-marker env \
        OBELISK_ROOT="${root_future}" \
        OBELISK_WRAPPER_CAPTURE="${TMP_DIR}/inventory-action-redacted-symlink-marker.env" \
        "${WRAPPER}" Ragnarok?listen

    local root_future_stale_env="${TMP_DIR}/root-inventory-action-redacted-observer-stale-env"
    prepare_root "${root_future_stale_env}"
    expect_wrapper_failure inventory-action-redacted-stale-env-stable-profile env \
        OBELISK_ROOT="${root_future_stale_env}" \
        OBELISK_WRAPPER_CAPTURE="${capture_future}" \
        OBELISK_ENABLE_INVENTORY_ACTION_REDACTED_OBSERVER=1 \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_BINARY_SHA256=bad-inventory-action-sha \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_LOG_LIMIT=99 \
        OBELISK_INVENTORY_ACTION_REDACTED_OBSERVER_DISPATCH_LIMIT=1 \
        "${WRAPPER}" TheIsland?listen
}

run_pending_inventory_action_redacted_observer_tests

echo "test_linuxgsm_wrapper_markers passed"
