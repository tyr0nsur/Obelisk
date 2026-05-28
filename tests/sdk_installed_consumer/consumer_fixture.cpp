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

    int g_RegisterCount = 0;
    int g_UnregisterCount = 0;

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
        ++g_RegisterCount;
        return 1001;
    }

    bool UnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback unregister");
        Require(registrationId == 1001, "unexpected callback registration id");
        ++g_UnregisterCount;
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
        Require(argc == 6, "usage: consumer_fixture <plugin-so> <expected-plugin-id> <config-dir> <config-path> <instance-id>");

        void* handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(std::string("dlopen failed: ") + dlerror());

        GetInfoFn getInfo = Resolve<GetInfoFn>(handle, "ObeliskPlugin_GetInfo");
        InitFn init = Resolve<InitFn>(handle, "ObeliskPlugin_Init");
        ShutdownFn shutdown = ResolveOptional<ShutdownFn>(handle, "ObeliskPlugin_Shutdown");

        ObeliskPluginMetadata metadata{};
        Require(getInfo(&metadata), "ObeliskPlugin_GetInfo failed");
        Require(metadata.abi_version == OBELISK_PLUGIN_METADATA_ABI_VERSION, "metadata ABI mismatch");
        Require(metadata.struct_size >= sizeof(ObeliskPluginMetadata), "metadata size mismatch");
        Require(std::strcmp(metadata.plugin_id, argv[2]) == 0, "plugin_id mismatch");
        Require(std::strcmp(metadata.config_file, "config.json") == 0, "config file mismatch");
        Require(metadata.default_config_json != nullptr, "missing default config");

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
        context.config_dir = argv[3];
        context.config_path = argv[4];
        context.instance_id = argv[5];
        context.plugin_owner_token = 0xC0FFEE;

        g_RegisterCount = 0;
        g_UnregisterCount = 0;
        Require(init(&api, &context), "ObeliskPlugin_Init failed");
        if (shutdown)
        {
            Require(g_RegisterCount == 1, "expected one owner-token callback registration");
            api = {};
            shutdown();
            Require(g_UnregisterCount == 1, "expected one owner-token callback unregister");
        }
        else
        {
            Require(g_RegisterCount == 0, "no-shutdown fixture should not register callbacks");
            Require(g_UnregisterCount == 0, "no-shutdown fixture should not unregister callbacks");
        }
        dlclose(handle);
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
