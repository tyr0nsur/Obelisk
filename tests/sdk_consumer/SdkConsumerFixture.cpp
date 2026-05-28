#include <obelisk/ObeliskApi.h>

#include <dlfcn.h>

#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
    using GetInfoFn = bool (*)(ObeliskPluginMetadata*);
    using InitFn = bool (*)(ObeliskApi*, const ObeliskPluginInitContext*);
    using ShutdownFn = void (*)();

    int g_RegisterCount = 0;
    int g_UnregisterCount = 0;
    bool g_ThrowLog = false;
    OnProcessEventCallback g_RegisteredCallback = nullptr;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void NoOpLog(const char*)
    {
        if (g_ThrowLog)
            throw std::runtime_error("injected log callback failure");
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
        g_RegisteredCallback = callback;
        ++g_RegisterCount;
        return 1001;
    }

    bool UnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback unregister");
        Require(registrationId == 1001, "unexpected callback registration id");
        g_RegisteredCallback = nullptr;
        ++g_UnregisterCount;
        return true;
    }

    constexpr const char* kActiveOBaseEventsConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": 42,
        "log_limit": 1
    }
})json";

    constexpr const char* kUnsupportedMapAllowlistConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "map_allowlist": ["Ragnarok"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": 42,
        "log_limit": 1
    }
})json";

    std::filesystem::path CreateConfigDir(const char* defaultConfigJson)
    {
        char templatePath[] = "/tmp/obelisk-sdk-consumer.XXXXXX";
        char* directory = mkdtemp(templatePath);
        Require(directory != nullptr, "mkdtemp failed");

        const std::filesystem::path configDir = directory;
        std::ofstream config(configDir / "config.json");
        Require(config.is_open(), "failed to create plugin config");
        config << defaultConfigJson;
        config.close();
        return configDir;
    }

    template <typename T>
    T ResolveRequired(void* handle, const char* symbol)
    {
        dlerror();
        void* pointer = dlsym(handle, symbol);
        const char* error = dlerror();
        if (error)
            throw std::runtime_error(std::string("missing symbol ") + symbol + ": " + error);
        return reinterpret_cast<T>(pointer);
    }

    template <typename T>
    T ResolveOptional(void* handle, const char* symbol)
    {
        dlerror();
        void* pointer = dlsym(handle, symbol);
        const char* error = dlerror();
        if (error)
            return nullptr;
        return reinterpret_cast<T>(pointer);
    }
}

int main(int argc, char** argv)
{
    try
    {
        Require(argc >= 2 && argc <= 4, "usage: sdk_consumer_fixture <plugin-so> [expected-plugin-id] [mode]");
        const char* expectedPluginId = argc == 3 ? argv[2] : "sdk_consumer_minimal";
        if (argc == 4)
            expectedPluginId = argv[2];
        const std::string mode = argc == 4 ? argv[3] : "";

        void* handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(std::string("dlopen failed: ") + dlerror());

        const auto closeHandle = [&handle]() {
            if (handle)
            {
                dlclose(handle);
                handle = nullptr;
            }
        };

        GetInfoFn getInfo = ResolveRequired<GetInfoFn>(handle, "ObeliskPlugin_GetInfo");
        InitFn init = ResolveRequired<InitFn>(handle, "ObeliskPlugin_Init");
        ShutdownFn shutdown = ResolveOptional<ShutdownFn>(handle, "ObeliskPlugin_Shutdown");

        ObeliskPluginMetadata metadata{};
        Require(getInfo(&metadata), "ObeliskPlugin_GetInfo failed");
        Require(metadata.abi_version == OBELISK_PLUGIN_METADATA_ABI_VERSION, "metadata ABI mismatch");
        Require(metadata.struct_size >= sizeof(ObeliskPluginMetadata), "metadata size mismatch");
        Require(std::strcmp(metadata.plugin_id, expectedPluginId) == 0, "plugin_id mismatch");
        Require(std::strcmp(metadata.config_file, "config.json") == 0, "config file mismatch");
        Require(metadata.default_config_json != nullptr, "missing default config");
        const char* configJson = metadata.default_config_json;
        if (mode == "active-process-event" || mode == "callback-throw-log")
            configJson = kActiveOBaseEventsConfig;
        else if (mode == "unsupported-map-allowlist")
            configJson = kUnsupportedMapAllowlistConfig;
        std::filesystem::path configDir = CreateConfigDir(configJson);
        const auto cleanupConfigDir = [&configDir]() {
            if (!configDir.empty())
                std::filesystem::remove_all(configDir);
        };

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
        const std::string configDirString = configDir.string();
        const std::string configPathString = (configDir / "config.json").string();
        context.config_dir = configDirString.c_str();
        context.config_path = configPathString.c_str();
        context.instance_id = "sdk-consumer-test";
        context.plugin_owner_token = 0xC0FFEE;

        if (mode == "throw-log-init")
            g_ThrowLog = true;

        if (mode == "invalid-context")
        {
            Require(!init(&api, nullptr), "plugin accepted null init context");
            ObeliskPluginInitContext shortContext = context;
            shortContext.struct_size = offsetof(ObeliskPluginInitContext, plugin_owner_token);
            Require(!init(&api, &shortContext), "plugin accepted too-small init context");
            Require(g_RegisterCount == 0, "invalid context unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "invalid context unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }

        const bool initSucceeded = init(&api, &context);
        if (mode == "throw-log-init")
        {
            Require(!initSucceeded, "plugin allowed log exception to cross or reported init success");
            Require(g_RegisterCount == 0, "failed init unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "failed init unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "unsupported-map-allowlist")
        {
            Require(!initSucceeded, "oBaseEvents accepted unsupported map_allowlist");
            Require(g_RegisterCount == 0, "rejected oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "rejected oBaseEvents unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }

        Require(initSucceeded, "ObeliskPlugin_Init failed");
        if (mode == "callback-throw-log")
        {
            Require(g_RegisterCount == 1, "active plugin did not register one callback");
            Require(g_RegisteredCallback != nullptr, "active plugin did not expose callback to fixture");
            g_ThrowLog = true;
            Require(g_RegisteredCallback(nullptr, nullptr, nullptr), "callback returned false");
            g_ThrowLog = false;
        }
        api = {};
        if (shutdown)
            shutdown();
        if (mode == "active-process-event" || mode == "callback-throw-log")
        {
            Require(g_RegisterCount == 1, "active plugin did not register one callback");
            Require(g_UnregisterCount == 1, "active plugin did not unregister one callback");
            Require(g_RegisteredCallback == nullptr, "active plugin callback survived shutdown unregister");
        }
        else if (std::strcmp(expectedPluginId, "oBaseEvents") == 0)
        {
            Require(g_RegisterCount == 0, "disabled oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "disabled oBaseEvents unexpectedly unregistered a callback");
        }
        cleanupConfigDir();
        closeHandle();
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
