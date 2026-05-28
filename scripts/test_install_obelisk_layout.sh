#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${1:-}"
if [[ -z "${INSTALL_ROOT}" ]]; then
    INSTALL_ROOT="$(mktemp -d /tmp/obelisk-install-layout.XXXXXX)"
    CLEAN_INSTALL_ROOT=1
else
    CLEAN_INSTALL_ROOT=0
fi
WORK_DIR="$(mktemp -d /tmp/obelisk-sdk-consumer.XXXXXX)"
CXX_BIN="${CXX:-g++}"

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

fake_bin="${WORK_DIR}/fake-bin"
failure_root="${WORK_DIR}/failure-root"
mkdir -p "${fake_bin}"
cat > "${fake_bin}/mv" <<'SH'
#!/usr/bin/env bash
if [[ "$*" == *'.incoming.'* ]]; then
    exit 77
fi
exec /usr/bin/mv "$@"
SH
chmod +x "${fake_bin}/mv"
if PATH="${fake_bin}:${PATH}" "${REPO_DIR}/scripts/install_obelisk.sh" "${failure_root}" \
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

"${REPO_DIR}/scripts/install_obelisk.sh" "${INSTALL_ROOT}"

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

"${REPO_DIR}/scripts/install_obelisk.sh" --backup-existing "${INSTALL_ROOT}" >/tmp/obelisk-install-layout-reinstall.log
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

mkdir -p "${CONFIG_DIR}"
cat > "${CONFIG_PATH}" <<'JSON'
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
JSON

cat > "${WORK_DIR}/consumer_plugin.cpp" <<'CPP'
#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sys/stat.h>

static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected Obelisk API ABI version");
static_assert(OBELISK_PLUGIN_METADATA_ABI_VERSION == 1u, "unexpected plugin metadata ABI version");
static_assert(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION == 1u, "unexpected plugin init context ABI version");

namespace
{
    ObeliskApi* g_Api = nullptr;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ProcessEventHandle = 0;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    bool PathExists(const char* path)
    {
        struct stat st {};
        return path && stat(path, &st) == 0;
    }

    bool OnProcessEvent(void*, void*, void*)
    {
        return true;
    }

    bool HasProcessEventHandleApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
            api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
            api->UnregisterProcessEventCallbackWithOwnerToken;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "install_layout_consumer";
    out->name = "Install Layout Consumer";
    out->version = "0.1.0-dev";
    out->config_file = "config.json";
    out->default_config_json = kDefaultConfig;
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    if (!api || !context)
        return false;

    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
    {
        return false;
    }

    g_Api = api;
    g_OwnerToken = context->plugin_owner_token;

    const bool contextOk = context->config_dir &&
        context->config_path &&
        context->instance_id &&
        context->plugin_owner_token != 0 &&
        std::strcmp(context->instance_id, "install-layout-test") == 0 &&
        PathExists(context->config_dir) &&
        PathExists(context->config_path);
    if (!contextOk)
        return false;

    if (HasProcessEventHandleApi(api))
    {
        g_ProcessEventHandle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
            g_OwnerToken,
            42,
            OnProcessEvent);
        if (g_ProcessEventHandle == 0)
            return false;
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    if (g_Api && g_ProcessEventHandle != 0)
        g_Api->UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);
    g_Api = nullptr;
    g_OwnerToken = 0;
    g_ProcessEventHandle = 0;
}
CPP

cat > "${WORK_DIR}/consumer_fixture.cpp" <<'CPP'
#include <obelisk/ObeliskApi.h>

#include <dlfcn.h>

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
    using GetInfoFn = bool (*)(ObeliskPluginMetadata*);
    using InitFn = bool (*)(ObeliskApi*, const ObeliskPluginInitContext*);
    using ShutdownFn = void (*)();

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void NoOpLog(const char*)
    {
    }

    void RegisterProcessEvent(OnProcessEventCallback)
    {
    }

    void RegisterNamedProcessEvent(int32_t, OnProcessEventCallback)
    {
    }

    void CallProcessEvent(void*, void*, void*)
    {
    }

    uint64_t RegisterNamedProcessEventWithOwnerTokenHandle(uint64_t ownerToken,
                                                           int32_t nameIndex,
                                                           OnProcessEventCallback callback)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback registration");
        Require(nameIndex == 42, "unexpected callback FName index");
        Require(callback != nullptr, "callback registration received null callback");
        return 1001;
    }

    bool UnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback unregister");
        Require(registrationId == 1001, "unexpected callback registration id");
        return true;
    }

    template <typename T>
    T Resolve(void* handle, const char* symbol)
    {
        dlerror();
        void* pointer = dlsym(handle, symbol);
        const char* error = dlerror();
        if (error)
            throw std::runtime_error(std::string("missing symbol ") + symbol + ": " + error);
        return reinterpret_cast<T>(pointer);
    }
}

int main(int argc, char** argv)
{
    try
    {
        Require(argc == 5, "usage: consumer_fixture <plugin-so> <config-dir> <config-path> <instance-id>");

        void* handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(std::string("dlopen failed: ") + dlerror());

        GetInfoFn getInfo = Resolve<GetInfoFn>(handle, "ObeliskPlugin_GetInfo");
        InitFn init = Resolve<InitFn>(handle, "ObeliskPlugin_Init");
        ShutdownFn shutdown = Resolve<ShutdownFn>(handle, "ObeliskPlugin_Shutdown");

        ObeliskPluginMetadata metadata{};
        Require(getInfo(&metadata), "ObeliskPlugin_GetInfo failed");
        Require(metadata.abi_version == OBELISK_PLUGIN_METADATA_ABI_VERSION, "metadata ABI mismatch");
        Require(metadata.struct_size >= sizeof(ObeliskPluginMetadata), "metadata size mismatch");
        Require(std::strcmp(metadata.plugin_id, "install_layout_consumer") == 0, "plugin_id mismatch");
        Require(std::strcmp(metadata.config_file, "config.json") == 0, "config file mismatch");

        ObeliskApi api{};
        api.LogInfo = NoOpLog;
        api.LogWarn = NoOpLog;
        api.LogError = NoOpLog;
        api.RegisterPreProcessEvent = RegisterProcessEvent;
        api.RegisterPostProcessEvent = RegisterProcessEvent;
        api.RegisterPreProcessEventForNameIndex = RegisterNamedProcessEvent;
        api.RegisterPostProcessEventForNameIndex = RegisterNamedProcessEvent;
        api.CallProcessEvent = CallProcessEvent;
        api.abi_version = OBELISK_API_ABI_VERSION;
        api.struct_size = sizeof(ObeliskApi);
        api.capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS |
            OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS |
            OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES;
        api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle =
            RegisterNamedProcessEventWithOwnerTokenHandle;
        api.UnregisterProcessEventCallbackWithOwnerToken =
            UnregisterProcessEventCallbackWithOwnerToken;

        ObeliskPluginInitContext context{};
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = sizeof(ObeliskPluginInitContext);
        context.config_dir = argv[2];
        context.config_path = argv[3];
        context.instance_id = argv[4];
        context.plugin_owner_token = 0xC0FFEE;

        Require(init(&api, &context), "ObeliskPlugin_Init failed");
        shutdown();
        dlclose(handle);
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
CPP

cat > "${WORK_DIR}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.22)
project(ObeliskInstallLayoutConsumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Obelisk 0.1.0 CONFIG REQUIRED)

if(NOT Obelisk_DEVELOPMENT_LINE STREQUAL "0.1.0-dev")
    message(FATAL_ERROR "Unexpected Obelisk development line: ${Obelisk_DEVELOPMENT_LINE}")
endif()
if(NOT Obelisk_RELEASE_CHANNEL STREQUAL "dev")
    message(FATAL_ERROR "Unexpected Obelisk release channel: ${Obelisk_RELEASE_CHANNEL}")
endif()
if(NOT Obelisk_API_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk API ABI version: ${Obelisk_API_ABI_VERSION}")
endif()
if(NOT Obelisk_PLUGIN_METADATA_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk plugin metadata ABI version: ${Obelisk_PLUGIN_METADATA_ABI_VERSION}")
endif()
if(NOT Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION EQUAL 1)
    message(FATAL_ERROR "Unexpected Obelisk plugin init context ABI version: ${Obelisk_PLUGIN_INIT_CONTEXT_ABI_VERSION}")
endif()

add_library(install_layout_consumer SHARED consumer_plugin.cpp)
target_link_libraries(install_layout_consumer PRIVATE Obelisk::obelisk_sdk)
set_target_properties(install_layout_consumer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "install_layout_consumer"
    LIBRARY_OUTPUT_DIRECTORY "${OBELISK_INSTALL_ROOT}/plugins"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN 1
)

add_executable(consumer_fixture consumer_fixture.cpp)
target_link_libraries(consumer_fixture PRIVATE Obelisk::obelisk_sdk dl)
CMAKE

cmake -S "${WORK_DIR}" -B "${WORK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_PREFIX_PATH="${INSTALL_ROOT}" \
    -DOBELISK_INSTALL_ROOT="${INSTALL_ROOT}" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${WORK_DIR}/build" --parallel

require_path "${PLUGIN_PATH}"

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

"${WORK_DIR}/build/consumer_fixture" "${PLUGIN_PATH}" "${CONFIG_DIR}" "${CONFIG_PATH}" "install-layout-test"

echo "Install layout and public SDK consumer validation passed for ${INSTALL_ROOT}"
