#include "core/ChatEventDispatcher.h"
#include "core/EventManager.h"
#include "core/PluginManager.h"
#include "runtime/Logger.h"

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;

namespace
{
    constexpr const char* kDefaultConfig =
        R"({"enabled":false,"allow_all_instances":false,"instance_allowlist":["arkserver"]})";

    struct FakePlugin {
        std::string filename;
        std::string pluginId = "fake_plugin";
        bool hasGetInfo = true;
        bool hasInit = true;
        bool hasShutdown = true;
        bool getInfoResult = true;
        bool initResult = true;
        bool validMetadata = true;
        bool registerCallback = false;
        bool registerNullCallback = false;
        bool registerFilteredCallback = false;
        bool registerInvalidFilteredCallback = false;
        bool registerNullFilteredCallback = false;
        bool registerOwnerTokenFromInitThread = false;
        bool registerChatCallback = false;
        bool throwOnGetInfoResolve = false;
        bool throwInInitAfterCallbacks = false;
        bool throwOnShutdown = false;
        bool throwOnClose = false;
        bool captureApi = false;
        int getInfoCalls = 0;
        int initCalls = 0;
        int shutdownCalls = 0;
        int closeCalls = 0;
        std::string initConfigDir;
        std::string initConfigPath;
        std::string initInstanceId;
        uint64_t initOwnerToken = 0;
        uint64_t initThreadRegistrationId = 0;
        void* owner = this;
        std::vector<std::string>* orderLog = nullptr;
        Obelisk::Core::ChatEventDispatcher* chatDispatcher = nullptr;
        ObeliskApi capturedApi{};
        bool eventCallbacksAtShutdown = false;
        size_t chatSubscriptionsAtShutdown = 0;
        size_t chatSubscriptionsAtClose = 0;
    };

    FakePlugin* g_CurrentFakePlugin = nullptr;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool FakeCallback(void*, void*, void*)
    {
        return true;
    }

    void FakeChatCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
    }

    bool FakeGetInfo(ObeliskPluginMetadata* out)
    {
        Require(g_CurrentFakePlugin != nullptr, "fake GetInfo called without current plugin");
        ++g_CurrentFakePlugin->getInfoCalls;
        if (!g_CurrentFakePlugin->getInfoResult)
            return false;

        const char* pluginId = g_CurrentFakePlugin->validMetadata
            ? g_CurrentFakePlugin->pluginId.c_str()
            : "../bad_plugin";

        *out = ObeliskPluginMetadata{
            OBELISK_PLUGIN_METADATA_ABI_VERSION,
            sizeof(ObeliskPluginMetadata),
            pluginId,
            "Fake Plugin",
            "1.0.0",
            "config.json",
            kDefaultConfig,
        };
        return true;
    }

    bool FakeInit(ObeliskApi* api, const ObeliskPluginInitContext* context)
    {
        Require(g_CurrentFakePlugin != nullptr, "fake Init called without current plugin");
        ++g_CurrentFakePlugin->initCalls;
        g_CurrentFakePlugin->initConfigDir = context->config_dir ? context->config_dir : "";
        g_CurrentFakePlugin->initConfigPath = context->config_path ? context->config_path : "";
        g_CurrentFakePlugin->initInstanceId = context->instance_id ? context->instance_id : "";
        g_CurrentFakePlugin->initOwnerToken = context->plugin_owner_token;

        Require(api != nullptr, "plugin init received null API");
        Require(api->abi_version == OBELISK_API_ABI_VERSION, "plugin init received wrong API ABI version");
        Require(api->struct_size >= sizeof(ObeliskApi), "plugin init received too-small API struct size");
        Require((api->capabilities & OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS) != 0,
                "plugin init received API without owned callback capability");
        Require((api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0,
                "plugin init received API without owner-token callback capability");
        Require((api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0,
                "plugin init received API without callback handle capability");
        Require(context->plugin_owner_token != 0, "plugin init received empty owner token");

        if (g_CurrentFakePlugin->captureApi)
            g_CurrentFakePlugin->capturedApi = *api;

        if (g_CurrentFakePlugin->registerCallback)
            api->RegisterPreProcessEvent(FakeCallback);

        if (g_CurrentFakePlugin->registerNullCallback)
            api->RegisterPreProcessEvent(nullptr);

        if (g_CurrentFakePlugin->registerFilteredCallback)
            api->RegisterPreProcessEventForNameIndex(42, FakeCallback);

        if (g_CurrentFakePlugin->registerInvalidFilteredCallback)
            api->RegisterPreProcessEventForNameIndex(-1, FakeCallback);

        if (g_CurrentFakePlugin->registerNullFilteredCallback)
            api->RegisterPreProcessEventForNameIndex(42, nullptr);

        if (g_CurrentFakePlugin->registerOwnerTokenFromInitThread)
        {
            std::thread worker([api, token = context->plugin_owner_token]() {
                g_CurrentFakePlugin->initThreadRegistrationId =
                    api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                        token,
                        42,
                        FakeCallback);
            });
            worker.join();
        }

        if (g_CurrentFakePlugin->registerChatCallback)
        {
            Require(g_CurrentFakePlugin->chatDispatcher != nullptr,
                    "fake plugin requested chat callback without dispatcher");
            const uint64_t registrationId = g_CurrentFakePlugin->chatDispatcher->Register(
                g_CurrentFakePlugin->owner,
                Obelisk::Core::ChatMessageSubscription{FakeChatCallback, g_CurrentFakePlugin});
            Require(registrationId != 0, "fake chat callback registration failed");
        }

        if (g_CurrentFakePlugin->orderLog)
            g_CurrentFakePlugin->orderLog->push_back("init:" + g_CurrentFakePlugin->filename);

        if (g_CurrentFakePlugin->throwInInitAfterCallbacks)
            throw std::runtime_error("fake init failure after callback registration");

        return g_CurrentFakePlugin->initResult;
    }

    void FakeShutdown()
    {
        Require(g_CurrentFakePlugin != nullptr, "fake Shutdown called without current plugin");
        g_CurrentFakePlugin->eventCallbacksAtShutdown =
            Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks();
        if (g_CurrentFakePlugin->chatDispatcher)
            g_CurrentFakePlugin->chatSubscriptionsAtShutdown =
                g_CurrentFakePlugin->chatDispatcher->SubscriptionCount();
        ++g_CurrentFakePlugin->shutdownCalls;
        if (g_CurrentFakePlugin->throwOnShutdown)
            throw std::runtime_error("fake shutdown failure");
    }

    class FakeLoader final : public Obelisk::Core::PluginManager::LibraryLoader
    {
    public:
        void Add(FakePlugin& plugin)
        {
            m_Plugins.emplace(plugin.filename, &plugin);
        }

        void* Open(const fs::path& path, std::string& error) override
        {
            const auto it = m_Plugins.find(path.filename().string());
            if (it == m_Plugins.end())
            {
                error = "fake plugin not registered";
                return nullptr;
            }
            return it->second;
        }

        void* Resolve(void* handle, const char* symbolName, std::string& error) override
        {
            auto* plugin = static_cast<FakePlugin*>(handle);
            g_CurrentFakePlugin = plugin;

            const std::string symbol = symbolName ? symbolName : "";
            if (symbol == "ObeliskPlugin_GetInfo" && plugin->throwOnGetInfoResolve)
                throw std::runtime_error("fake resolve failure");
            if (symbol == "ObeliskPlugin_GetInfo" && plugin->hasGetInfo)
                return reinterpret_cast<void*>(&FakeGetInfo);
            if (symbol == "ObeliskPlugin_Init" && plugin->hasInit)
                return reinterpret_cast<void*>(&FakeInit);
            if (symbol == "ObeliskPlugin_Shutdown" && plugin->hasShutdown)
                return reinterpret_cast<void*>(&FakeShutdown);

            error = "missing fake symbol " + symbol;
            return nullptr;
        }

        void* GetSymbolOwner(void* handle, void*) override
        {
            return static_cast<FakePlugin*>(handle)->owner;
        }

        void Close(void* handle) override
        {
            auto* plugin = static_cast<FakePlugin*>(handle);
            if (plugin->chatDispatcher)
                plugin->chatSubscriptionsAtClose = plugin->chatDispatcher->SubscriptionCount();
            ++plugin->closeCalls;
            if (plugin->orderLog)
                plugin->orderLog->push_back("close:" + plugin->filename);
            if (plugin->throwOnClose)
                throw std::runtime_error("fake close failure");
        }

    private:
        std::unordered_map<std::string, FakePlugin*> m_Plugins;
    };

    fs::path MakeTempRoot(const char* name)
    {
        const auto now = std::chrono::steady_clock::now().time_since_epoch().count();
        fs::path root = fs::temp_directory_path() / (std::string(name) + "_" + std::to_string(now));
        fs::create_directories(root / "plugins");
        fs::create_directories(root / "config");
        return root;
    }

    void TouchPlugin(const fs::path& root, const std::string& filename)
    {
        std::ofstream out(root / "plugins" / filename);
        Require(out.is_open(), "failed to create fake plugin candidate");
    }

    void WritePluginConfig(const fs::path& root, const std::string& pluginId, const std::string& contents)
    {
        fs::create_directories(root / "config" / pluginId);
        std::ofstream out(root / "config" / pluginId / "config.json");
        Require(out.is_open(), "failed to create fake plugin config");
        out << contents;
        out.close();
        Require(static_cast<bool>(out), "failed to write fake plugin config");
    }

    void ConfigureEnvironment(const fs::path& root)
    {
        setenv("OBELISK_CONFIG_DIR", (root / "config").string().c_str(), 1);
        setenv("OBELISK_LOG_DIR", (root / "logs").string().c_str(), 1);
        setenv("OBELISK_ROOT", root.string().c_str(), 1);
        setenv("OBELISK_INSTANCE_ID", "arkserver", 1);
        unsetenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
    }

    void CleanupPlugin(FakePlugin& plugin)
    {
        Obelisk::Core::EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
        if (plugin.chatDispatcher)
            plugin.chatDispatcher->UnregisterCallbacksForOwner(plugin.owner);
        g_CurrentFakePlugin = nullptr;
    }

    void TestUnsafeInstanceIdDisablesPluginLoading()
    {
        const char* unsafeInstanceIds[] = {nullptr, "", "../arkserver", "ark/server", "ark server"};

        for (const char* unsafeInstanceId : unsafeInstanceIds)
        {
            const fs::path root = MakeTempRoot("obelisk_plugin_manager_unsafe_instance_id");
            ConfigureEnvironment(root);
            if (unsafeInstanceId)
                setenv("OBELISK_INSTANCE_ID", unsafeInstanceId, 1);
            else
                unsetenv("OBELISK_INSTANCE_ID");

            FakePlugin plugin{.filename = "unsafe_instance.so", .pluginId = "unsafe_instance_plugin"};
            FakeLoader loader;
            loader.Add(plugin);
            TouchPlugin(root, plugin.filename);
            WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"allow_all_instances":true})");

            Obelisk::Core::PluginManager manager(loader);
            manager.LoadPlugins((root / "plugins").string());

            Require(plugin.getInfoCalls == 0, "plugin metadata was read with unsafe OBELISK_INSTANCE_ID");
            Require(plugin.initCalls == 0, "plugin initialized with unsafe OBELISK_INSTANCE_ID");
            Require(plugin.closeCalls == 0, "plugin handle was opened with unsafe OBELISK_INSTANCE_ID");

            CleanupPlugin(plugin);
            fs::remove_all(root);
        }
    }

    void TestValidPluginLoadsAndUnloadCleansCallbacks()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_valid");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "valid.so", .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "valid plugin GetInfo was not called once");
        Require(plugin.initCalls == 1, "valid plugin Init was not called once");
        Require(plugin.closeCalls == 0, "valid plugin was closed during load");
        Require(fs::exists(root / "config" / plugin.pluginId / "config.json"), "valid plugin config was not prepared");
        Require(plugin.initInstanceId == "arkserver", "instance id was not passed to plugin init");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback was not registered during plugin init");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "owned chat callback was not registered during plugin init");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "valid plugin shutdown was not called during unload");
        Require(plugin.eventCallbacksAtShutdown,
                "ProcessEvent callbacks were removed before plugin shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "chat callback was removed before plugin shutdown");
        Require(plugin.closeCalls == 1, "valid plugin was not closed during unload");
        Require(plugin.chatSubscriptionsAtClose == 0, "chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback survived plugin unload");
        Require(chatDispatcher.SubscriptionCount() == 0, "owned chat callback survived plugin unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGlobalProcessEventCallbackRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_denied");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "global_denied.so", .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) == 0,
                "global callback capability was enabled by default");

        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "global-denied plugin was not initialized");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global callback was registered without explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestFilteredProcessEventCallbackAllowedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_filtered_allowed");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "filtered_allowed.so", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "filtered callback was rejected by default");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestPostInitUnownedCallbackRegistrationIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_post_init_unowned");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "post_init_unowned.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "post-init plugin was not initialized");
        plugin.capturedApi.RegisterPreProcessEventForNameIndex(42, FakeCallback);
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "post-init unowned callback was registered");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestPostInitOwnerTokenCallbackRegistrationCleansOnUnload()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "owner_token.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token plugin was not initialized");
        Require(plugin.initOwnerToken != 0, "owner-token plugin did not receive a token");
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerToken != nullptr,
                "owner-token registration function was not exposed");
        plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerToken(plugin.initOwnerToken, 42, FakeCallback);
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token callback was not registered");

        manager.UnloadAll();

        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenCallbackRegistrationFromInitThread()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_init_thread");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_init_thread.so",
            .registerOwnerTokenFromInitThread = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token init-thread plugin was not initialized");
        Require(plugin.initThreadRegistrationId != 0,
                "owner-token callback from an init-time helper thread was rejected");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token callback from init-time helper thread was not registered");

        manager.UnloadAll();

        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token init-thread callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitFailureCleansInitThreadOwnerTokenCallbackAndToken()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_init_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_init_fail.so",
            .initResult = false,
            .registerOwnerTokenFromInitThread = true,
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token init-fail plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "owner-token init-fail plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "owner-token init-fail plugin was not closed");
        Require(plugin.initThreadRegistrationId != 0,
                "owner-token init-fail callback from helper thread was not registered before failure");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token callback from failed init survived load failure");
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    42,
                    FakeCallback) == 0,
                "owner token from failed init remained valid after cleanup");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitExceptionCleansInitThreadOwnerTokenCallbackAndToken()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_init_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_init_throw.so",
            .registerOwnerTokenFromInitThread = true,
            .throwInInitAfterCallbacks = true,
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token init-throw plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "owner-token init-throw plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "owner-token init-throw plugin was not closed");
        Require(plugin.initThreadRegistrationId != 0,
                "owner-token init-throw callback from helper thread was not registered before exception");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token callback from throwing init survived load failure");
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    42,
                    FakeCallback) == 0,
                "owner token from throwing init remained valid after cleanup");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenHandleRegistrationCanUnregister()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_handle");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "owner_token_handle.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token-handle plugin was not initialized");
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle != nullptr,
                "owner-token handle registration function was not exposed");
        Require(plugin.capturedApi.UnregisterProcessEventCallbackWithOwnerToken != nullptr,
                "ProcessEvent unregister function was not exposed");

        const uint64_t registrationId =
            plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                plugin.initOwnerToken,
                42,
                FakeCallback);
        Require(registrationId != 0, "owner-token handle registration returned zero");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token handle callback was not registered");

        Require(!plugin.capturedApi.UnregisterProcessEventCallbackWithOwnerToken(plugin.initOwnerToken + 1000, registrationId),
                "invalid owner token unregistered a ProcessEvent callback");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token handle callback was removed by invalid token");

        Require(plugin.capturedApi.UnregisterProcessEventCallbackWithOwnerToken(plugin.initOwnerToken, registrationId),
                "owner-token handle unregister failed");
        Require(!plugin.capturedApi.UnregisterProcessEventCallbackWithOwnerToken(plugin.initOwnerToken, registrationId),
                "owner-token handle unregister succeeded twice");
        Require(!plugin.capturedApi.UnregisterProcessEventCallbackWithOwnerToken(plugin.initOwnerToken, 0),
                "zero ProcessEvent callback handle unregistered a callback");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owner-token handle callback survived explicit unregister");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenGlobalHandleRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_global_handle_denied");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "owner_token_global_handle_denied.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token-global-handle plugin was not initialized");
        Require(plugin.capturedApi.RegisterPreProcessEventWithOwnerTokenHandle != nullptr,
                "global owner-token handle registration function was not exposed");
        const uint64_t registrationId =
            plugin.capturedApi.RegisterPreProcessEventWithOwnerTokenHandle(plugin.initOwnerToken, FakeCallback);
        Require(registrationId == 0, "global owner-token handle registered without explicit gate");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global owner-token handle callback was registered without explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInvalidOwnerTokenCallbackRegistrationIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_invalid_owner_token");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "invalid_owner_token.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "invalid-owner-token plugin was not initialized");
        plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerToken(plugin.initOwnerToken + 1000, 42, FakeCallback);
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle != nullptr,
                "owner-token handle registration function was not exposed");
        const uint64_t registrationId =
            plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                plugin.initOwnerToken + 1000,
                42,
                FakeCallback);
        Require(registrationId == 0, "invalid owner-token handle registration returned nonzero id");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "invalid owner-token callback was registered");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInvalidProcessEventCallbacksAreRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_invalid_callbacks");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "invalid_callbacks.so",
            .registerNullCallback = true,
            .registerInvalidFilteredCallback = true,
            .registerNullFilteredCallback = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "invalid-callback plugin was not initialized");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "invalid ProcessEvent callbacks were registered");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGlobalProcessEventCallbackAllowedWithGate()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_allowed");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-global-process-event-callbacks");
        Require(marker.is_open(), "failed to create global callback marker");
        marker.close();

        FakePlugin plugin{.filename = "global_allowed.so", .registerCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0,
                "global callback capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());

        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global callback was not registered with explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
        fs::remove_all(root);
    }

    void TestDisabledPluginPreparesConfigButDoesNotInit()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_disabled");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "disabled.so", .hasInit = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "disabled plugin metadata was not read");
        Require(plugin.initCalls == 0, "disabled plugin was initialized");
        Require(plugin.shutdownCalls == 0, "disabled plugin shutdown was called despite no init");
        Require(plugin.closeCalls == 1, "disabled plugin was not closed after skip");
        Require(fs::exists(root / "config" / plugin.pluginId / "config.json"),
                "disabled plugin default config was not prepared");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInstanceDisallowedPluginDoesNotInit()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_instance_disallowed");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "wrong_instance.so"};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver2"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "instance-disallowed plugin metadata was not read");
        Require(plugin.initCalls == 0, "instance-disallowed plugin was initialized");
        Require(plugin.closeCalls == 1, "instance-disallowed plugin was not closed after skip");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMissingGetInfoRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_no_getinfo");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "missing_getinfo.so", .hasGetInfo = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 0, "plugin without GetInfo was initialized");
        Require(plugin.closeCalls == 1, "plugin without GetInfo was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestResolveExceptionAfterOpenClosesHandle()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_resolve_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "resolve_throw.so", .throwOnGetInfoResolve = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 0, "resolve-throw plugin reported metadata");
        Require(plugin.initCalls == 0, "resolve-throw plugin was initialized");
        Require(plugin.closeCalls == 1, "resolve-throw plugin handle was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestPluginSymlinkCandidateIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_symlink");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "linked.so"};
        FakeLoader loader;
        loader.Add(plugin);

        const fs::path externalTarget = root / "external-plugin.so";
        {
            std::ofstream out(externalTarget);
            Require(out.is_open(), "failed to create external fake plugin target");
        }
        fs::create_symlink(externalTarget, root / "plugins" / plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 0, "symlink plugin candidate was opened");
        Require(plugin.initCalls == 0, "symlink plugin candidate was initialized");
        Require(plugin.closeCalls == 0, "symlink plugin candidate reached loader close path");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMissingInitRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_no_init");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "missing_init.so", .hasInit = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "plugin without Init did not report metadata before rejection");
        Require(plugin.closeCalls == 1, "plugin without Init was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInvalidMetadataRejectsAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_bad_metadata");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "bad_metadata.so", .validMetadata = false};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "bad metadata plugin did not report metadata");
        Require(plugin.initCalls == 0, "bad metadata plugin was initialized");
        Require(plugin.closeCalls == 1, "bad metadata plugin was not closed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitFailureCleansCallbacksAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_init_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "init_fail.so", .initResult = false, .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "init-failing plugin did not report metadata");
        Require(plugin.initCalls == 1, "init-failing plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-failing plugin shutdown was not called");
        Require(plugin.eventCallbacksAtShutdown,
                "init-failing plugin ProcessEvent callback was removed before shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "init-failing plugin chat callback was removed before shutdown");
        Require(plugin.closeCalls == 1, "init-failing plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "failed plugin chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback registered by failed plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by failed plugin survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitExceptionCleansCallbacksAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_init_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "init_throw.so",
            .registerFilteredCallback = true,
            .throwInInitAfterCallbacks = true,
        };
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 1, "init-throw plugin did not report metadata");
        Require(plugin.initCalls == 1, "init-throw plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-throw plugin shutdown was not called");
        Require(plugin.eventCallbacksAtShutdown,
                "init-throw plugin ProcessEvent callback was removed before shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "init-throw plugin chat callback was removed before shutdown");
        Require(plugin.closeCalls == 1, "init-throw plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "init-throw plugin chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "ProcessEvent callback registered by throwing plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by throwing plugin survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestMultiplePluginsLoadSortedAndUnloadReverse()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_multi");
        ConfigureEnvironment(root);

        std::vector<std::string> orderLog;
        FakePlugin pluginA{.filename = "a_first.so", .pluginId = "plugin_a", .hasShutdown = false, .orderLog = &orderLog};
        FakePlugin pluginB{.filename = "b_second.so", .pluginId = "plugin_b", .hasShutdown = false, .orderLog = &orderLog};
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginB.filename);
        TouchPlugin(root, pluginA.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.UnloadAll();

        const std::vector<std::string> expected{
            "init:a_first.so",
            "init:b_second.so",
            "close:b_second.so",
            "close:a_first.so",
        };
        Require(orderLog == expected, "plugins were not loaded sorted and unloaded in reverse load order");
        Require(pluginA.closeCalls == 1, "first plugin was not closed once");
        Require(pluginB.closeCalls == 1, "second plugin was not closed once");

        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
        fs::remove_all(root);
    }

    void TestUnloadAllContinuesAfterCloseException()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_close_throw");
        ConfigureEnvironment(root);

        FakePlugin pluginA{.filename = "a_first.so", .pluginId = "plugin_a", .hasShutdown = false};
        FakePlugin pluginB{.filename = "b_second.so", .pluginId = "plugin_b", .hasShutdown = false, .throwOnClose = true};
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginA.filename);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.UnloadAll();
        manager.UnloadAll();

        Require(pluginA.closeCalls == 1, "unload did not continue after later plugin close threw");
        Require(pluginB.closeCalls == 1, "throwing plugin close was repeated after unload");

        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
        fs::remove_all(root);
    }

    void TestUnloadAllCleansAfterShutdownException()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_shutdown_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "shutdown_throw.so",
            .registerFilteredCallback = true,
            .registerOwnerTokenFromInitThread = true,
            .registerChatCallback = true,
            .throwOnShutdown = true,
        };
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "shutdown-throw plugin was not initialized");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-throw plugin ProcessEvent callbacks were not registered");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "shutdown-throw plugin chat callback was not registered");

        manager.UnloadAll();
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "shutdown-throw plugin shutdown was not called once");
        Require(plugin.eventCallbacksAtShutdown,
                "shutdown-throw plugin ProcessEvent callbacks were removed before shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "shutdown-throw plugin chat callback was removed before shutdown");
        Require(plugin.closeCalls == 1, "shutdown-throw plugin was not closed once");
        Require(plugin.chatSubscriptionsAtClose == 0,
                "shutdown-throw plugin chat callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-throw plugin ProcessEvent callbacks survived unload");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "shutdown-throw plugin chat callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestDuplicatePluginIdRejectsSecondPlugin()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_duplicate_id");
        ConfigureEnvironment(root);

        FakePlugin pluginA{.filename = "a_first.so", .pluginId = "duplicate"};
        FakePlugin pluginB{.filename = "b_second.so", .pluginId = "duplicate"};
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginA.filename);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, "duplicate", R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(pluginA.initCalls == 1, "first duplicate-id plugin was not initialized");
        Require(pluginB.getInfoCalls == 1, "second duplicate-id plugin metadata was not read");
        Require(pluginB.initCalls == 0, "second duplicate-id plugin was initialized");
        Require(pluginB.closeCalls == 1, "second duplicate-id plugin was not closed");

        manager.UnloadAll();
        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
        fs::remove_all(root);
    }

    void TestLoadPluginsSkipsAlreadyLoadedPluginId()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_idempotent");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "idempotent.so", .pluginId = "idempotent_plugin", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 2, "already-loaded plugin metadata was not checked on reload");
        Require(plugin.initCalls == 1, "already-loaded plugin was initialized more than once");
        Require(plugin.closeCalls == 1, "already-loaded duplicate handle was not closed during reload");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback from first loaded plugin was removed during reload");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "idempotent plugin shutdown was not called once");
        Require(plugin.closeCalls == 2, "loaded plugin handle was not closed during unload");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback from idempotent plugin survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }
}

int main()
{
    const fs::path logRoot = MakeTempRoot("obelisk_plugin_manager_logs");
    setenv("OBELISK_LOG_DIR", logRoot.string().c_str(), 1);
    Obelisk::Logger::Init();

    TestValidPluginLoadsAndUnloadCleansCallbacks();
    TestGlobalProcessEventCallbackRejectedByDefault();
    TestFilteredProcessEventCallbackAllowedByDefault();
    TestPostInitUnownedCallbackRegistrationIsRejected();
    TestPostInitOwnerTokenCallbackRegistrationCleansOnUnload();
    TestOwnerTokenCallbackRegistrationFromInitThread();
    TestInitFailureCleansInitThreadOwnerTokenCallbackAndToken();
    TestInitExceptionCleansInitThreadOwnerTokenCallbackAndToken();
    TestOwnerTokenHandleRegistrationCanUnregister();
    TestOwnerTokenGlobalHandleRejectedByDefault();
    TestInvalidOwnerTokenCallbackRegistrationIsRejected();
    TestInvalidProcessEventCallbacksAreRejected();
    TestUnsafeInstanceIdDisablesPluginLoading();
    TestGlobalProcessEventCallbackAllowedWithGate();
    TestDisabledPluginPreparesConfigButDoesNotInit();
    TestInstanceDisallowedPluginDoesNotInit();
    TestMissingGetInfoRejectsAndCloses();
    TestResolveExceptionAfterOpenClosesHandle();
    TestPluginSymlinkCandidateIsRejected();
    TestMissingInitRejectsAndCloses();
    TestInvalidMetadataRejectsAndCloses();
    TestInitFailureCleansCallbacksAndCloses();
    TestInitExceptionCleansCallbacksAndCloses();
    TestMultiplePluginsLoadSortedAndUnloadReverse();
    TestUnloadAllContinuesAfterCloseException();
    TestUnloadAllCleansAfterShutdownException();
    TestDuplicatePluginIdRejectsSecondPlugin();
    TestLoadPluginsSkipsAlreadyLoadedPluginId();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "PluginManagerTests passed\n";
    return 0;
}
