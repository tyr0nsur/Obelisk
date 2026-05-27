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

require_cmd "${CXX_BIN}"

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

CONFIG_DIR="${INSTALL_ROOT}/config/install_layout_consumer"
CONFIG_PATH="${CONFIG_DIR}/config.json"
PLUGIN_PATH="${INSTALL_ROOT}/plugins/install_layout_consumer.so"

mkdir -p "${CONFIG_DIR}"
cat > "${CONFIG_PATH}" <<'JSON'
{
  "enabled": false,
  "instance_allowlist": []
}
JSON

cat > "${WORK_DIR}/consumer_plugin.cpp" <<'CPP'
#include <obelisk/ObeliskApi.h>

#include <cstring>
#include <sys/stat.h>

namespace
{
    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "instance_allowlist": []
})json";

    bool PathExists(const char* path)
    {
        struct stat st {};
        return path && stat(path, &st) == 0;
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

    return context->config_dir &&
        context->config_path &&
        context->instance_id &&
        std::strcmp(context->instance_id, "install-layout-test") == 0 &&
        PathExists(context->config_dir) &&
        PathExists(context->config_path);
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
}
CPP

cat > "${WORK_DIR}/consumer_fixture.cpp" <<'CPP'
#include <obelisk/ObeliskApi.h>

#include <dlfcn.h>

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
        api.capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;

        ObeliskPluginInitContext context{};
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = sizeof(ObeliskPluginInitContext);
        context.config_dir = argv[2];
        context.config_path = argv[3];
        context.instance_id = argv[4];

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

find_package(Obelisk CONFIG REQUIRED)

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
