#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${OBELISK_BUILD_DIR:-${REPO_DIR}/build}"
if [[ "${BUILD_DIR}" != /* ]]; then
    BUILD_DIR="${REPO_DIR}/${BUILD_DIR}"
fi
INSTALL_ROOT="${1:-}"
if [[ -z "${INSTALL_ROOT}" ]]; then
    INSTALL_ROOT="$(mktemp -d /tmp/obelisk-install-layout.XXXXXX)"
    CLEAN_INSTALL_ROOT=1
else
    CLEAN_INSTALL_ROOT=0
fi
WORK_DIR="$(mktemp -d /tmp/obelisk-sdk-consumer.XXXXXX)"
CXX_BIN="${CXX:-g++}"
SDK_CONSUMER_FIXTURE="${BUILD_DIR}/tests/sdk_consumer/sdk_consumer_fixture"

cleanup() {
    rm -rf "${WORK_DIR}"
    if [[ "${CLEAN_INSTALL_ROOT}" == "1" ]]; then
        rm -rf "${INSTALL_ROOT}"
    fi
}
trap cleanup EXIT

require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Missing required command: ${cmd}" >&2
        exit 1
    fi
}

require_path() {
    local path="$1"
    if [[ ! -e "${path}" ]]; then
        echo "Missing expected install path: ${path}" >&2
        exit 1
    fi
}

require_not_contains() {
    local pattern="$1"
    local path="$2"
    if grep -F "${pattern}" "${path}" >/dev/null; then
        echo "Unexpected local path leak in ${path}: ${pattern}" >&2
        cat "${path}" >&2
        exit 1
    fi
}

require_cmd "${CXX_BIN}"
require_cmd readelf

if env -u OBELISK_ROOT "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run \
    >"${WORK_DIR}/missing-root.out" 2>"${WORK_DIR}/missing-root.err"; then
    echo "install_obelisk.sh accepted a missing install root" >&2
    exit 1
fi
if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/missing-root.err" >/dev/null; then
    echo "missing root error was unclear" >&2
    cat "${WORK_DIR}/missing-root.err" >&2
    exit 1
fi

if OBELISK_ROOT="${WORK_DIR}/env-root" "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run \
    >"${WORK_DIR}/env-root.out" 2>"${WORK_DIR}/env-root.err"; then
    echo "install_obelisk.sh accepted OBELISK_ROOT without a positional root" >&2
    exit 1
fi
if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/env-root.err" >/dev/null; then
    echo "OBELISK_ROOT fallback rejection was unclear" >&2
    cat "${WORK_DIR}/env-root.err" >&2
    exit 1
fi

for invalid_root in "" "/" "." "relative/root"; do
    if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${invalid_root}" \
        >"${WORK_DIR}/invalid-root.out" 2>"${WORK_DIR}/invalid-root.err"; then
        echo "install_obelisk.sh accepted invalid root '${invalid_root}'" >&2
        exit 1
    fi
    if ! grep -F 'Install root must be a non-root absolute path' "${WORK_DIR}/invalid-root.err" >/dev/null; then
        echo "invalid root error was unclear for '${invalid_root}'" >&2
        cat "${WORK_DIR}/invalid-root.err" >&2
        exit 1
    fi
done

if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run /tmp/obelisk-extra-root /tmp/obelisk-other-root \
    >"${WORK_DIR}/extra-root.out" 2>"${WORK_DIR}/extra-root.err"; then
    echo "install_obelisk.sh accepted an extra positional root" >&2
    exit 1
fi
if ! grep -F 'Unexpected extra argument' "${WORK_DIR}/extra-root.err" >/dev/null; then
    echo "extra root error was unclear" >&2
    cat "${WORK_DIR}/extra-root.err" >&2
    exit 1
fi

symlink_target="${WORK_DIR}/root-target"
symlink_root="${WORK_DIR}/root-symlink"
mkdir -p "${symlink_target}"
ln -s "${symlink_target}" "${symlink_root}"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${symlink_root}" \
    >"${WORK_DIR}/symlink-root.out" 2>"${WORK_DIR}/symlink-root.err"; then
    echo "install_obelisk.sh accepted symlink root" >&2
    exit 1
fi
if ! grep -F 'Install root must not be a symlink' "${WORK_DIR}/symlink-root.err" >/dev/null; then
    echo "symlink root error was unclear" >&2
    cat "${WORK_DIR}/symlink-root.err" >&2
    exit 1
fi

symlink_subpath_root="${WORK_DIR}/symlink-subpath-root"
symlink_subpath_target="${WORK_DIR}/symlink-subpath-target"
mkdir -p "${symlink_subpath_root}" "${symlink_subpath_target}"
ln -s "${symlink_subpath_target}" "${symlink_subpath_root}/lib"
if "${REPO_DIR}/scripts/install_obelisk.sh" --dry-run "${symlink_subpath_root}" \
    >"${WORK_DIR}/symlink-subpath.out" 2>"${WORK_DIR}/symlink-subpath.err"; then
    echo "install_obelisk.sh accepted symlink managed subpath" >&2
    exit 1
fi
if ! grep -F 'Managed install path must not be a symlink' "${WORK_DIR}/symlink-subpath.err" >/dev/null; then
    echo "symlink subpath error was unclear" >&2
    cat "${WORK_DIR}/symlink-subpath.err" >&2
    exit 1
fi

fake_bin="${WORK_DIR}/fake-bin"
failure_root="${WORK_DIR}/failure-root"
mkdir -p "${fake_bin}"
cat > "${fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *.incoming.* ]]; then
        exit 77
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${fake_bin}/mv"
if PATH="${fake_bin}:${PATH}" "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${failure_root}" \
    >"${WORK_DIR}/fail-mv.out" 2>"${WORK_DIR}/fail-mv.err"; then
    echo "install_obelisk.sh succeeded despite failing runtime rename" >&2
    exit 1
fi
if find "${failure_root}" -name '*.incoming.*' | grep -q .; then
    echo "failed runtime install left incoming temporary files" >&2
    find "${failure_root}" -print >&2
    exit 1
fi
if find "${failure_root}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "failed runtime install left staging directories" >&2
    find "${failure_root}" -maxdepth 1 -print >&2
    exit 1
fi

pair_failure_root="${WORK_DIR}/pair-failure-root"
mkdir -p "${pair_failure_root}/lib"
printf 'old-subhook\n' > "${pair_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${pair_failure_root}/lib/libobelisk.so"
cat > "${fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *.incoming.* ]]; then
        count=0
        if [[ -n "${OBELISK_FAKE_MV_COUNT:-}" && -f "${OBELISK_FAKE_MV_COUNT}" ]]; then
            count="$(cat "${OBELISK_FAKE_MV_COUNT}")"
        fi
        count=$((count + 1))
        if [[ -n "${OBELISK_FAKE_MV_COUNT:-}" ]]; then
            printf '%s\n' "${count}" > "${OBELISK_FAKE_MV_COUNT}"
        fi
        if [[ "${count}" == "2" ]]; then
            exit 77
        fi
        break
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${fake_bin}/mv"
fake_mv_count="${WORK_DIR}/fake-mv-count"
if OBELISK_FAKE_MV_COUNT="${fake_mv_count}" PATH="${fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${pair_failure_root}" \
    >"${WORK_DIR}/pair-fail-mv.out" 2>"${WORK_DIR}/pair-fail-mv.err"; then
    echo "install_obelisk.sh succeeded despite failing second runtime rename" >&2
    exit 1
fi
if [[ "$(cat "${pair_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed runtime pair install did not restore original libsubhook.so" >&2
    ls -la "${pair_failure_root}/lib" >&2
    exit 1
fi
if [[ "$(cat "${pair_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed runtime pair install changed original libobelisk.so" >&2
    ls -la "${pair_failure_root}/lib" >&2
    exit 1
fi
if find "${pair_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed runtime pair install left temporary files" >&2
    find "${pair_failure_root}" -print >&2
    exit 1
fi

sdk_failure_root="${WORK_DIR}/sdk-failure-root"
sdk_fake_bin="${WORK_DIR}/sdk-fake-bin"
mkdir -p "${sdk_failure_root}/lib" "${sdk_fake_bin}"
printf 'old-subhook\n' > "${sdk_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${sdk_failure_root}/lib/libobelisk.so"
real_cmake="$(command -v cmake)"
cat > "${sdk_fake_bin}/cmake" <<'SH'
#!/usr/bin/env bash
previous=""
for arg in "$@"; do
    if [[ "${previous}" == "--component" && "${arg}" == "SDK" ]]; then
        exit 78
    fi
    previous="${arg}"
done
exec "${OBELISK_REAL_CMAKE}" "$@"
SH
chmod +x "${sdk_fake_bin}/cmake"
if OBELISK_REAL_CMAKE="${real_cmake}" PATH="${sdk_fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${sdk_failure_root}" \
    >"${WORK_DIR}/sdk-fail.out" 2>"${WORK_DIR}/sdk-fail.err"; then
    echo "install_obelisk.sh succeeded despite failing SDK install" >&2
    exit 1
fi
if [[ "$(cat "${sdk_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed SDK install did not restore original libsubhook.so" >&2
    ls -la "${sdk_failure_root}/lib" >&2
    exit 1
fi
if [[ "$(cat "${sdk_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed SDK install did not restore original libobelisk.so" >&2
    ls -la "${sdk_failure_root}/lib" >&2
    exit 1
fi
if find "${sdk_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed SDK install left temporary files" >&2
    find "${sdk_failure_root}" -print >&2
    exit 1
fi

sdk_publish_failure_root="${WORK_DIR}/sdk-publish-failure-root"
sdk_publish_fake_bin="${WORK_DIR}/sdk-publish-fake-bin"
mkdir -p "${sdk_publish_failure_root}/lib" \
    "${sdk_publish_failure_root}/include/obelisk" \
    "${sdk_publish_failure_root}/lib/cmake/Obelisk" \
    "${sdk_publish_fake_bin}"
printf 'old-subhook\n' > "${sdk_publish_failure_root}/lib/libsubhook.so"
printf 'old-obelisk\n' > "${sdk_publish_failure_root}/lib/libobelisk.so"
printf 'old-header\n' > "${sdk_publish_failure_root}/include/obelisk/ObeliskApi.h"
printf 'old-config\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskConfig.cmake"
printf 'old-version\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskConfigVersion.cmake"
printf 'old-targets\n' > "${sdk_publish_failure_root}/lib/cmake/Obelisk/ObeliskTargets.cmake"
cat > "${sdk_publish_fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "${arg}" == *ObeliskConfig.cmake.incoming.* ]]; then
        exit 79
    fi
done
exec /usr/bin/mv "$@"
SH
chmod +x "${sdk_publish_fake_bin}/mv"
if PATH="${sdk_publish_fake_bin}:${PATH}" \
    "${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${sdk_publish_failure_root}" \
    >"${WORK_DIR}/sdk-publish-fail.out" 2>"${WORK_DIR}/sdk-publish-fail.err"; then
    echo "install_obelisk.sh succeeded despite failing SDK publish" >&2
    exit 1
fi
if [[ "$(cat "${sdk_publish_failure_root}/lib/libsubhook.so")" != "old-subhook" ]]; then
    echo "failed SDK publish did not restore original libsubhook.so" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi
if [[ "$(cat "${sdk_publish_failure_root}/lib/libobelisk.so")" != "old-obelisk" ]]; then
    echo "failed SDK publish did not restore original libobelisk.so" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi
for sdk_file in \
    "include/obelisk/ObeliskApi.h:old-header" \
    "lib/cmake/Obelisk/ObeliskConfig.cmake:old-config" \
    "lib/cmake/Obelisk/ObeliskConfigVersion.cmake:old-version" \
    "lib/cmake/Obelisk/ObeliskTargets.cmake:old-targets"; do
    sdk_path="${sdk_file%%:*}"
    expected="${sdk_file#*:}"
    if [[ "$(cat "${sdk_publish_failure_root}/${sdk_path}")" != "${expected}" ]]; then
        echo "failed SDK publish did not restore ${sdk_path}" >&2
        find "${sdk_publish_failure_root}" -print >&2
        exit 1
    fi
done
if find "${sdk_publish_failure_root}" \( -name '*.incoming.*' -o -name '.install-runtime.*' -o -name '.install-sdk.*' -o -name '.install-rollback.*' \) | grep -q .; then
    echo "failed SDK publish left temporary files" >&2
    find "${sdk_publish_failure_root}" -print >&2
    exit 1
fi

"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" "${INSTALL_ROOT}"

require_path "${INSTALL_ROOT}/lib/libobelisk.so"
require_path "${INSTALL_ROOT}/lib/libsubhook.so"
require_path "${INSTALL_ROOT}/plugins"
require_path "${INSTALL_ROOT}/config"
require_path "${INSTALL_ROOT}/logs"
require_path "${INSTALL_ROOT}/state/instances"
require_path "${INSTALL_ROOT}/include/obelisk/ObeliskApi.h"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskConfig.cmake"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskConfigVersion.cmake"
require_path "${INSTALL_ROOT}/lib/cmake/Obelisk/ObeliskTargets.cmake"
require_path "${SDK_CONSUMER_FIXTURE}"

installed_headers="$(find "${INSTALL_ROOT}/include" -type f -printf '%P\n' | sort)"
if [[ "${installed_headers}" != "obelisk/ObeliskApi.h" ]]; then
    echo "SDK install published unexpected public headers" >&2
    printf '%s\n' "${installed_headers}" >&2
    exit 1
fi

if find "${INSTALL_ROOT}/lib" -maxdepth 1 -name '*.incoming.*' | grep -q .; then
    echo "Runtime install left incoming temporary files in ${INSTALL_ROOT}/lib" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "Runtime install left staging directories in ${INSTALL_ROOT}" >&2
    find "${INSTALL_ROOT}" -maxdepth 1 -print >&2
    exit 1
fi

for cmake_package_file in "${INSTALL_ROOT}"/lib/cmake/Obelisk/*.cmake; do
    require_not_contains "${REPO_DIR}" "${cmake_package_file}"
    require_not_contains "${REPO_DIR}/build" "${cmake_package_file}"
done

if readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" | grep -F "${REPO_DIR}" >/dev/null; then
    echo "Installed libobelisk.so contains a source/build-tree dynamic path leak" >&2
    readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" >&2
    exit 1
fi

if ! readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" | grep -F 'Library runpath: [$ORIGIN]' >/dev/null; then
    echo "Installed libobelisk.so must resolve bundled runtime dependencies through RUNPATH=\$ORIGIN" >&2
    readelf -d "${INSTALL_ROOT}/lib/libobelisk.so" >&2
    exit 1
fi

SDK_VERSIONLESS_CHECK_DIR="${WORK_DIR}/sdk_versionless_package_check"
mkdir -p "${SDK_VERSIONLESS_CHECK_DIR}"
cat > "${SDK_VERSIONLESS_CHECK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskSdkVersionlessPackageCheck LANGUAGES C)

find_package(Obelisk CONFIG REQUIRED COMPONENTS SDK)

if(NOT TARGET Obelisk::obelisk_sdk)
    message(FATAL_ERROR "Installed Obelisk package did not define Obelisk::obelisk_sdk")
endif()
if(NOT Obelisk_SDK_FOUND)
    message(FATAL_ERROR "Installed Obelisk package did not report SDK component found")
endif()
if(NOT Obelisk_VERSION STREQUAL "0.1.0")
    message(FATAL_ERROR "Unexpected Obelisk package version: ${Obelisk_VERSION}")
endif()
if(NOT Obelisk_VERSION_MAJOR EQUAL 0)
    message(FATAL_ERROR "Unexpected Obelisk package version major: ${Obelisk_VERSION_MAJOR}")
endif()
if(NOT Obelisk_VERSION_MINOR EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk package version minor: ${Obelisk_VERSION_MINOR}")
endif()
if(NOT Obelisk_VERSION_PATCH EQUAL 0)
    message(FATAL_ERROR "Unexpected Obelisk package version patch: ${Obelisk_VERSION_PATCH}")
endif()

add_library(versionless_sdk_check SHARED versionless_sdk_check.c)
target_link_libraries(versionless_sdk_check PRIVATE Obelisk::obelisk_sdk)
CMAKE
cat > "${SDK_VERSIONLESS_CHECK_DIR}/versionless_sdk_check.c" <<'C'
#include <obelisk/ObeliskApi.h>

_Static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected Obelisk API ABI version");

unsigned obelisk_sdk_versionless_package_check(void) {
    return OBELISK_API_ABI_VERSION;
}
C
cmake -S "${SDK_VERSIONLESS_CHECK_DIR}" -B "${SDK_VERSIONLESS_CHECK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}"
cmake --build "${SDK_VERSIONLESS_CHECK_DIR}/build" --parallel

"${REPO_DIR}/scripts/install_obelisk.sh" --build-dir "${BUILD_DIR}" --backup-existing "${INSTALL_ROOT}" >/tmp/obelisk-install-layout-reinstall.log
obelisk_backup_count="$(find "${INSTALL_ROOT}/lib" -maxdepth 1 -name 'libobelisk.so.*.bak' | wc -l)"
subhook_backup_count="$(find "${INSTALL_ROOT}/lib" -maxdepth 1 -name 'libsubhook.so.*.bak' | wc -l)"
if [[ "${obelisk_backup_count}" != "1" || "${subhook_backup_count}" != "1" ]]; then
    echo "Expected one backup each for libobelisk.so and libsubhook.so after backup reinstall" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}/lib" -maxdepth 1 -name '*.incoming.*' | grep -q .; then
    echo "Runtime reinstall left incoming temporary files in ${INSTALL_ROOT}/lib" >&2
    find "${INSTALL_ROOT}/lib" -maxdepth 1 -print >&2
    exit 1
fi

if find "${INSTALL_ROOT}" -maxdepth 1 -name '.install-runtime.*' | grep -q .; then
    echo "Runtime reinstall left staging directories in ${INSTALL_ROOT}" >&2
    find "${INSTALL_ROOT}" -maxdepth 1 -print >&2
    exit 1
fi

CONFIG_DIR="${INSTALL_ROOT}/config/install_layout_consumer"
CONFIG_PATH="${CONFIG_DIR}/config.json"
PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_consumer.so"
C_ABI_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_c_abi_consumer.so"
NO_SHUTDOWN_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_no_shutdown_consumer.so"
DESCRIPTOR_CATALOG_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_descriptor_catalog_consumer.so"
DESCRIPTOR_TIMER_PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_descriptor_timer_consumer.so"
RELEASE_BASE_EVENTS_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oBaseEvents.so"
RELEASE_TIMER_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oProcessTimer.so"
RELEASE_DESCRIPTOR_PLUGIN_PATH="${INSTALL_ROOT}/plugins/oDescriptorCatalog.so"

mkdir -p "${CONFIG_DIR}"
cat > "${CONFIG_PATH}" <<'JSON'
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
JSON

cp -R "${REPO_DIR}/tests/sdk_installed_consumer/." "${WORK_DIR}/"

cmake -S "${WORK_DIR}" -B "${WORK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_INSTALL_ROOT="${INSTALL_ROOT}" \
    -DOBELISK_RELEASE_SCOPE_PLUGIN_SOURCE_ROOT="${REPO_DIR}/plugins" \
    -DOBELISK_RELEASE_SCOPE_EXTERN_ROOT="${REPO_DIR}/extern" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${WORK_DIR}/build" --parallel

require_path "${PLUGIN_PATH}"
require_path "${C_ABI_PLUGIN_PATH}"
require_path "${NO_SHUTDOWN_PLUGIN_PATH}"
require_path "${DESCRIPTOR_CATALOG_PLUGIN_PATH}"
require_path "${DESCRIPTOR_TIMER_PLUGIN_PATH}"
require_path "${RELEASE_BASE_EVENTS_PLUGIN_PATH}"
require_path "${RELEASE_TIMER_PLUGIN_PATH}"
require_path "${RELEASE_DESCRIPTOR_PLUGIN_PATH}"

if ! grep -F "${INSTALL_ROOT}/include" "${WORK_DIR}/build/compile_commands.json" >/dev/null; then
    echo "SDK consumer did not include headers from the installed SDK layout" >&2
    cat "${WORK_DIR}/build/compile_commands.json" >&2
    exit 1
fi

if grep -F "${REPO_DIR}/include" "${WORK_DIR}/build/compile_commands.json" >/dev/null; then
    echo "SDK consumer accidentally included headers from the source tree" >&2
    cat "${WORK_DIR}/build/compile_commands.json" >&2
    exit 1
fi

"${WORK_DIR}/build/consumer_fixture" \
    "${PLUGIN_PATH}" \
    "install_layout_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${C_ABI_PLUGIN_PATH}" \
    "install_layout_c_abi_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${NO_SHUTDOWN_PLUGIN_PATH}" \
    "install_layout_no_shutdown_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${DESCRIPTOR_CATALOG_PLUGIN_PATH}" \
    "install_layout_descriptor_catalog_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"
"${WORK_DIR}/build/consumer_fixture" \
    "${DESCRIPTOR_TIMER_PLUGIN_PATH}" \
    "install_layout_descriptor_timer_consumer" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

"${SDK_CONSUMER_FIXTURE}" "${RELEASE_BASE_EVENTS_PLUGIN_PATH}" oBaseEvents
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_BASE_EVENTS_PLUGIN_PATH}" oBaseEvents active-chat-command-helper
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_TIMER_PLUGIN_PATH}" oProcessTimer
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_TIMER_PLUGIN_PATH}" oProcessTimer active-timer
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_DESCRIPTOR_PLUGIN_PATH}" oDescriptorCatalog
"${SDK_CONSUMER_FIXTURE}" "${RELEASE_DESCRIPTOR_PLUGIN_PATH}" oDescriptorCatalog active-descriptor-catalog

SDK_MINIMAL_EXAMPLE_DIR="${WORK_DIR}/sdk_minimal_plugin"
mkdir -p "${SDK_MINIMAL_EXAMPLE_DIR}"
cp -R "${REPO_DIR}/examples/sdk_minimal_plugin/." "${SDK_MINIMAL_EXAMPLE_DIR}/"
cmake -S "${SDK_MINIMAL_EXAMPLE_DIR}" -B "${SDK_MINIMAL_EXAMPLE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${SDK_MINIMAL_EXAMPLE_DIR}/build" --parallel
SDK_MINIMAL_EXAMPLE_PLUGIN_PATH="${SDK_MINIMAL_EXAMPLE_DIR}/build/obelisk_sdk_minimal_plugin.so"
require_path "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}"

if ! grep -F "${INSTALL_ROOT}/include" "${SDK_MINIMAL_EXAMPLE_DIR}/build/compile_commands.json" >/dev/null; then
    echo "Minimal SDK example did not include headers from the installed SDK layout" >&2
    cat "${SDK_MINIMAL_EXAMPLE_DIR}/build/compile_commands.json" >&2
    exit 1
fi

if grep -F "${REPO_DIR}/include" "${SDK_MINIMAL_EXAMPLE_DIR}/build/compile_commands.json" >/dev/null; then
    echo "Minimal SDK example accidentally included headers from the source tree" >&2
    cat "${SDK_MINIMAL_EXAMPLE_DIR}/build/compile_commands.json" >&2
    exit 1
fi

"${WORK_DIR}/build/consumer_fixture" \
    "${SDK_MINIMAL_EXAMPLE_PLUGIN_PATH}" \
    "obelisk_sdk_minimal_plugin" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

SDK_TIMER_EXAMPLE_DIR="${WORK_DIR}/sdk_timer_plugin"
mkdir -p "${SDK_TIMER_EXAMPLE_DIR}"
cp -R "${REPO_DIR}/examples/sdk_timer_plugin/." "${SDK_TIMER_EXAMPLE_DIR}/"
cmake -S "${SDK_TIMER_EXAMPLE_DIR}" -B "${SDK_TIMER_EXAMPLE_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_SDK_TIMER_PLUGIN_TEST_PROBES=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${SDK_TIMER_EXAMPLE_DIR}/build" --parallel
SDK_TIMER_EXAMPLE_PLUGIN_PATH="${SDK_TIMER_EXAMPLE_DIR}/build/obelisk_sdk_timer_plugin.so"
require_path "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}"

if ! grep -F "${INSTALL_ROOT}/include" "${SDK_TIMER_EXAMPLE_DIR}/build/compile_commands.json" >/dev/null; then
    echo "Timer SDK example did not include headers from the installed SDK layout" >&2
    cat "${SDK_TIMER_EXAMPLE_DIR}/build/compile_commands.json" >&2
    exit 1
fi

if grep -F "${REPO_DIR}/include" "${SDK_TIMER_EXAMPLE_DIR}/build/compile_commands.json" >/dev/null; then
    echo "Timer SDK example accidentally included headers from the source tree" >&2
    cat "${SDK_TIMER_EXAMPLE_DIR}/build/compile_commands.json" >&2
    exit 1
fi

"${WORK_DIR}/build/consumer_fixture" \
    "${SDK_TIMER_EXAMPLE_PLUGIN_PATH}" \
    "obelisk_sdk_timer_plugin" \
    "${CONFIG_DIR}" \
    "${CONFIG_PATH}" \
    "install-layout-test"

echo "Install layout and public SDK consumer validation passed for ${INSTALL_ROOT}"
