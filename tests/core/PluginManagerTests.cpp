#include "core/ChatEventDispatcher.h"
#include "core/EventManager.h"
#include "core/InventoryPolicyEventDispatcher.h"
#include "core/PluginManager.h"
#include "core/StructureEventDispatcher.h"
#include "runtime/Logger.h"

#include <chrono>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;

namespace Obelisk::Hooks
{
    int ProcessEventCallOriginalCountForTesting();
    void ResetProcessEventCallOriginalCountForTesting();
}

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
        bool registerInventoryPolicyCallback = false;
        bool registerStructureCallback = false;
        bool registerGameplayPolicyCallback = false;
        bool callProcessEventInInit = false;
        bool registerOwnerTokenCallbackInShutdown = false;
        bool unregisterOwnerTokenCallbackInShutdown = false;
        bool throwOnGetInfoResolve = false;
        bool throwInInitAfterCallbacks = false;
        bool throwOnShutdown = false;
        bool throwOnClose = false;
        bool captureApi = false;
        bool mutateApiInInit = false;
        int getInfoCalls = 0;
        int initCalls = 0;
        int shutdownCalls = 0;
        int closeCalls = 0;
        std::string initConfigDir;
        std::string initConfigPath;
        std::string initInstanceId;
        uint64_t initOwnerToken = 0;
        uint64_t initThreadRegistrationId = 0;
        uint64_t gameplayPolicyRegistrationId = 0;
        bool gameplayPolicySelfUnregisterResult = false;
        uint64_t chatMessageRegistrationId = 0;
        bool chatMessageSelfUnregisterResult = false;
        uint64_t shutdownRegistrationId = 0;
        bool shutdownUnregisterResult = false;
        void* owner = this;
        std::vector<std::string>* orderLog = nullptr;
        Obelisk::Core::ChatEventDispatcher* chatDispatcher = nullptr;
        ObeliskApi capturedApi{};
        bool eventCallbacksAtShutdown = false;
        size_t chatSubscriptionsAtShutdown = 0;
        size_t chatSubscriptionsAtClose = 0;
        size_t inventoryPolicySubscriptionsAtShutdown = 0;
        size_t inventoryPolicySubscriptionsAtClose = 0;
        int gameplayPolicyEventCalls = 0;
        uint32_t gameplayPolicyEventKind = 0;
        uint32_t gameplayPolicyResourceKind = 0;
        uint64_t gameplayPolicyFlags = 0;
        uint64_t gameplayPolicyFieldMask = 0;
        uint64_t gameplayPolicyBoolValues = 0;
        int32_t gameplayPolicyInt32Values[OBELISK_GAMEPLAY_POLICY_FIELD_COUNT]{};
        uint32_t gameplayPolicyEventAbiVersion = 0;
        uint32_t gameplayPolicyEventStructSize = 0;
        int chatMessageEventCalls = 0;
        uint32_t chatMessageSendMode = 0;
        uint64_t chatMessageFlags = 0;
        uint64_t chatMessageSequence = 0;
        std::string chatMessageText;
        uint32_t chatMessageEventAbiVersion = 0;
        uint32_t chatMessageEventStructSize = 0;
        size_t structureSubscriptionsAtShutdown = 0;
        size_t structureSubscriptionsAtClose = 0;
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

    void FakeInventoryPolicyCallback(const Obelisk::Core::InventoryPolicyEventView&, void*)
    {
    }

    void FakeStructureCallback(const Obelisk::Core::StructureEventView&, void*)
    {
    }

    void FakeGameplayPolicyEventCallback(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        Require(event != nullptr, "gameplay policy callback received null event");
        auto* plugin = static_cast<FakePlugin*>(userData);
        ++plugin->gameplayPolicyEventCalls;
        plugin->gameplayPolicyEventKind = event->event_kind;
        plugin->gameplayPolicyResourceKind = event->resource_kind;
        plugin->gameplayPolicyFlags = event->flags;
        plugin->gameplayPolicyFieldMask = event->field_mask;
        plugin->gameplayPolicyBoolValues = event->bool_values;
        for (uint32_t i = 0; i < OBELISK_GAMEPLAY_POLICY_FIELD_COUNT; ++i)
            plugin->gameplayPolicyInt32Values[i] = event->int32_values[i];
        plugin->gameplayPolicyEventAbiVersion = event->abi_version;
        plugin->gameplayPolicyEventStructSize = event->struct_size;
    }

    void FakeGameplayPolicySelfUnregisterCallback(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        FakeGameplayPolicyEventCallback(event, userData);
        auto* plugin = static_cast<FakePlugin*>(userData);
        plugin->gameplayPolicySelfUnregisterResult =
            plugin->capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                plugin->initOwnerToken,
                plugin->gameplayPolicyRegistrationId);
    }

    void FakeChatMessageEventCallback(const ObeliskChatMessageEvent* event, void* userData)
    {
        Require(event != nullptr, "chat message callback received null event");
        auto* plugin = static_cast<FakePlugin*>(userData);
        ++plugin->chatMessageEventCalls;
        plugin->chatMessageSendMode = event->send_mode;
        plugin->chatMessageFlags = event->flags;
        plugin->chatMessageSequence = event->sequence;
        plugin->chatMessageText.assign(event->message.data, event->message.size);
        plugin->chatMessageEventAbiVersion = event->abi_version;
        plugin->chatMessageEventStructSize = event->struct_size;
    }

    void FakeChatMessageSelfUnregisterCallback(const ObeliskChatMessageEvent* event, void* userData)
    {
        FakeChatMessageEventCallback(event, userData);
        auto* plugin = static_cast<FakePlugin*>(userData);
        plugin->chatMessageSelfUnregisterResult =
            plugin->capturedApi.UnregisterChatMessageEventWithOwnerToken(
                plugin->initOwnerToken,
                plugin->chatMessageRegistrationId);
    }

    std::vector<Obelisk::Core::StructureScalarValue> MakeStructureScalars()
    {
        return {
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
        };
    }

    Obelisk::Core::StructureEventView MakeStructureEvent(
        const std::vector<Obelisk::Core::StructureScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::StructureEventKind::AllowStructureAccess,
            .FunctionNameIndex = 7605,
            .OuterNameIndex = 7539,
            .Scalars = scalars,
        };
    }

    std::vector<Obelisk::Core::StructureScalarValue> MakeSetVariantScalars()
    {
        return {
            {
                .Field = Obelisk::Core::StructureScalarField::VariantIndex,
                .Type = Obelisk::Core::StructureScalarType::Int32,
                .BoolValue = false,
                .Int32Value = 3,
            },
            {
                .Field = Obelisk::Core::StructureScalarField::BForceSet,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = false,
                .Int32Value = 0,
            },
        };
    }

    Obelisk::Core::StructureEventView MakeSetVariantEvent(
        const std::vector<Obelisk::Core::StructureScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::StructureEventKind::SetVariant,
            .FunctionNameIndex = 7606,
            .OuterNameIndex = 7539,
            .Scalars = scalars,
        };
    }

    std::vector<Obelisk::Core::StructureScalarValue> MakeActivationToggleScalars()
    {
        return {
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
        };
    }

    Obelisk::Core::StructureEventView MakeActivationToggleEvent(
        const std::vector<Obelisk::Core::StructureScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::StructureEventKind::AllowToggleActivation,
            .FunctionNameIndex = 12039,
            .OuterNameIndex = 18998,
            .Scalars = scalars,
        };
    }

    std::vector<Obelisk::Core::StructureScalarValue> MakeCanSeatScalars()
    {
        return {
            {
                .Field = Obelisk::Core::StructureScalarField::BForce,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = false,
                .Int32Value = 0,
            },
        };
    }

    Obelisk::Core::StructureEventView MakeCanSeatEvent(
        const std::vector<Obelisk::Core::StructureScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::StructureEventKind::CanSeat,
            .FunctionNameIndex = 18999,
            .OuterNameIndex = 7539,
            .Scalars = scalars,
        };
    }

    std::vector<Obelisk::Core::InventoryPolicyScalarValue> MakeInventoryRemoteAddScalars()
    {
        return {
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                .BoolValue = true,
            },
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                .BoolValue = true,
            },
        };
    }

    Obelisk::Core::InventoryPolicyEventView MakeInventoryRemoteAddEvent(
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::InventoryPolicyEventKind::AllowRemoteAddToInventory,
            .Scalars = scalars,
        };
    }

    std::vector<Obelisk::Core::InventoryPolicyScalarValue> MakeInventoryCanUseScalars()
    {
        return {
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::BIgnoreCooldown,
                .BoolValue = false,
            },
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                .BoolValue = true,
            },
        };
    }

    Obelisk::Core::InventoryPolicyEventView MakeInventoryCanUseEvent(
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::InventoryPolicyEventKind::CanUse,
            .Scalars = scalars,
        };
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

        if (g_CurrentFakePlugin->registerOwnerTokenCallbackInShutdown ||
            g_CurrentFakePlugin->unregisterOwnerTokenCallbackInShutdown)
        {
            g_CurrentFakePlugin->capturedApi = *api;
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

        if (g_CurrentFakePlugin->registerInventoryPolicyCallback)
        {
            const uint64_t registrationId = Obelisk::Core::InventoryPolicyEventDispatcher::Get().Register(
                g_CurrentFakePlugin->owner,
                Obelisk::Core::InventoryPolicyEventSubscription{FakeInventoryPolicyCallback, g_CurrentFakePlugin});
            Require(registrationId != 0, "fake inventory policy callback registration failed");
        }

        if (g_CurrentFakePlugin->registerStructureCallback)
        {
            const uint64_t registrationId = Obelisk::Core::StructureEventDispatcher::Get().Register(
                g_CurrentFakePlugin->owner,
                Obelisk::Core::StructureEventSubscription{FakeStructureCallback, g_CurrentFakePlugin});
            Require(registrationId != 0, "fake structure callback registration failed");
        }

        if (g_CurrentFakePlugin->registerGameplayPolicyCallback)
        {
            Require(api->RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                    "fake plugin requested gameplay policy callback without registration API");
            g_CurrentFakePlugin->gameplayPolicyRegistrationId =
                api->RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    context->plugin_owner_token,
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                    FakeGameplayPolicyEventCallback,
                    g_CurrentFakePlugin);
            Require(g_CurrentFakePlugin->gameplayPolicyRegistrationId != 0,
                    "fake gameplay policy callback registration failed");
        }

        if (g_CurrentFakePlugin->callProcessEventInInit)
            api->CallProcessEvent(reinterpret_cast<void*>(0x1), reinterpret_cast<void*>(0x2), reinterpret_cast<void*>(0x3));

        if (g_CurrentFakePlugin->orderLog)
            g_CurrentFakePlugin->orderLog->push_back("init:" + g_CurrentFakePlugin->filename);

        if (g_CurrentFakePlugin->mutateApiInInit)
        {
            api->LogInfo = nullptr;
            api->capabilities = 0;
            api->abi_version = 0;
        }

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
        g_CurrentFakePlugin->inventoryPolicySubscriptionsAtShutdown =
            Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount();
        g_CurrentFakePlugin->structureSubscriptionsAtShutdown =
            Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount();
        ++g_CurrentFakePlugin->shutdownCalls;
        if (g_CurrentFakePlugin->registerOwnerTokenCallbackInShutdown)
        {
            g_CurrentFakePlugin->shutdownRegistrationId =
                g_CurrentFakePlugin->capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                    g_CurrentFakePlugin->initOwnerToken,
                    42,
                    FakeCallback);
        }
        if (g_CurrentFakePlugin->unregisterOwnerTokenCallbackInShutdown)
        {
            g_CurrentFakePlugin->shutdownUnregisterResult =
                g_CurrentFakePlugin->capturedApi.UnregisterProcessEventCallbackWithOwnerToken(
                    g_CurrentFakePlugin->initOwnerToken,
                    g_CurrentFakePlugin->initThreadRegistrationId);
        }
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
            plugin->inventoryPolicySubscriptionsAtClose =
                Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount();
            plugin->structureSubscriptionsAtClose =
                Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount();
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
        unsetenv("OBELISK_ALLOW_CALL_PROCESS_EVENT");
        unsetenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING");
        unsetenv("OBELISK_ENABLE_CHAT_EVENTS");
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(false);
    }

    void CleanupPlugin(FakePlugin& plugin)
    {
        Obelisk::Core::EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
        if (plugin.chatDispatcher)
            plugin.chatDispatcher->UnregisterCallbacksForOwner(plugin.owner);
        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(plugin.owner);
        Obelisk::Core::StructureEventDispatcher::Get().UnregisterCallbacksForOwner(plugin.owner);
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

    void TestUnsafeConfigRootDisablesPluginLoading()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_unsafe_config_root");
        ConfigureEnvironment(root);

        const fs::path externalConfigRoot = root / "external-config-root";
        fs::create_directories(externalConfigRoot);
        const fs::path symlinkConfigRoot = root / "config-root-symlink";
        fs::remove_all(root / "config");
        fs::create_symlink(externalConfigRoot, symlinkConfigRoot);
        setenv("OBELISK_CONFIG_DIR", symlinkConfigRoot.string().c_str(), 1);

        FakePlugin plugin{.filename = "unsafe_config_root.so", .pluginId = "unsafe_config_root_plugin"};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 0, "plugin metadata was read with unsafe OBELISK_CONFIG_DIR");
        Require(plugin.initCalls == 0, "plugin initialized with unsafe OBELISK_CONFIG_DIR");
        Require(plugin.closeCalls == 0, "plugin handle was opened with unsafe OBELISK_CONFIG_DIR");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestEmptyPluginDirectoryIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_empty_plugin_dir");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "empty_plugin_dir.so"};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins("");

        Require(plugin.getInfoCalls == 0, "empty plugin directory still scanned plugin metadata");
        Require(plugin.initCalls == 0, "empty plugin directory initialized plugin");
        Require(plugin.closeCalls == 0, "empty plugin directory opened plugin handle");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestRelativePluginDirectoryIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_relative_plugin_dir");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "relative_plugin_dir.so"};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins("plugins");

        Require(plugin.getInfoCalls == 0, "relative plugin directory still scanned plugin metadata");
        Require(plugin.initCalls == 0, "relative plugin directory initialized plugin");
        Require(plugin.closeCalls == 0, "relative plugin directory opened plugin handle");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestValidPluginLoadsAndUnloadCleansCallbacks()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_valid");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "valid.so", .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerStructureCallback = true;
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
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "owned inventory policy callback was not registered during plugin init");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "owned structure callback was not registered during plugin init");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "valid plugin shutdown was not called during unload");
        Require(plugin.eventCallbacksAtShutdown,
                "ProcessEvent callbacks were removed before plugin shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "chat callback was removed before plugin shutdown");
        Require(plugin.inventoryPolicySubscriptionsAtShutdown == 1,
                "inventory policy callback was removed before plugin shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "structure callback was removed before plugin shutdown");
        Require(plugin.closeCalls == 1, "valid plugin was not closed during unload");
        Require(plugin.chatSubscriptionsAtClose == 0, "chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "inventory policy callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0, "structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback survived plugin unload");
        Require(chatDispatcher.SubscriptionCount() == 0, "owned chat callback survived plugin unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "owned inventory policy callback survived plugin unload");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "owned structure callback survived plugin unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestPluginOwnerTokensSkipZeroAndLiveTokensAfterWrap()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_wrap");
        ConfigureEnvironment(root);

        FakePlugin first{
            .filename = "owner_token_a.so",
            .pluginId = "owner_token_a",
        };
        FakePlugin second{
            .filename = "owner_token_b.so",
            .pluginId = "owner_token_b",
        };
        FakePlugin third{
            .filename = "owner_token_c.so",
            .pluginId = "owner_token_c",
        };
        FakeLoader loader;
        loader.Add(first);
        loader.Add(second);
        loader.Add(third);
        TouchPlugin(root, first.filename);
        WritePluginConfig(root, first.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Obelisk::Core::PluginManager::SetNextPluginOwnerTokenForTesting(1);
        manager.LoadPlugins((root / "plugins").string());
        Require(first.initOwnerToken == 1, "first plugin owner token was not one");

        TouchPlugin(root, second.filename);
        TouchPlugin(root, third.filename);
        WritePluginConfig(root, second.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, third.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager::SetNextPluginOwnerTokenForTesting(std::numeric_limits<uint64_t>::max());
        manager.LoadPlugins((root / "plugins").string());

        const std::vector<uint64_t> wrappedTokens{second.initOwnerToken, third.initOwnerToken};
        Require(second.initOwnerToken != 0, "second plugin owner token was zero after wrap");
        Require(third.initOwnerToken != 0, "third plugin owner token was zero after wrap");
        Require(second.initOwnerToken != third.initOwnerToken, "wrapped owner tokens were duplicated");
        Require(second.initOwnerToken != first.initOwnerToken, "second plugin reused a live owner token");
        Require(third.initOwnerToken != first.initOwnerToken, "third plugin reused a live owner token");
        Require(
            (wrappedTokens[0] == std::numeric_limits<uint64_t>::max() && wrappedTokens[1] == 2) ||
                (wrappedTokens[1] == std::numeric_limits<uint64_t>::max() && wrappedTokens[0] == 2),
            "wrapped owner tokens did not preserve max token and skip live token one");

        manager.UnloadAll();
        CleanupPlugin(first);
        CleanupPlugin(second);
        CleanupPlugin(third);
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

    void TestCallbackHandleCapabilityImpliesOwnerTokenCapability()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_capability_invariant");
        ConfigureEnvironment(root);

        FakeLoader loader;
        Obelisk::Core::PluginManager manager(loader);
        const uint64_t capabilities = manager.ApiCapabilitiesForTesting();

        Require((capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) == 0 ||
                    (capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0,
                "callback handle capability was advertised without owner-token capability");

        fs::remove_all(root);
    }

    void TestProcessEventBlockingCapabilityRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_process_event_blocking_denied");
        ConfigureEnvironment(root);

        FakeLoader loader;
        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING) == 0,
                "ProcessEvent blocking capability was enabled by default");

        fs::remove_all(root);
    }

    void TestProcessEventBlockingCapabilityAllowedWithGate()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_process_event_blocking_allowed");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-process-event-blocking");
        Require(marker.is_open(), "failed to create ProcessEvent blocking marker");
        marker.close();

        FakeLoader loader;
        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING) != 0,
                "ProcessEvent blocking capability was not enabled with env and marker gate");

        unsetenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING");
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
        Require(plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    42,
                    FakeCallback) == 0,
                "owner token remained valid after plugin unload");

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

    void TestOwnerTokenGameplayPolicyEventRegistrationCanUnregister()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_gameplay_policy_handle");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_gameplay_policy_a.so",
            .pluginId = "owner_token_gameplay_policy_a",
            .captureApi = true,
        };
        FakePlugin otherPlugin{
            .filename = "owner_token_gameplay_policy_b.so",
            .pluginId = "owner_token_gameplay_policy_b",
        };
        FakeLoader loader;
        loader.Add(plugin);
        loader.Add(otherPlugin);
        TouchPlugin(root, plugin.filename);
        TouchPlugin(root, otherPlugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, otherPlugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0,
                "gameplay policy event capability was not advertised");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token gameplay-policy plugin was not initialized");
        Require(otherPlugin.initCalls == 1, "second owner-token gameplay-policy plugin was not initialized");
        Require(plugin.initOwnerToken != 0, "owner-token gameplay-policy plugin did not receive a token");
        Require(otherPlugin.initOwnerToken != 0, "second owner-token gameplay-policy plugin did not receive a token");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy event registration function was not exposed");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken != nullptr,
                "gameplay policy event unregister function was not exposed");

        const uint64_t invalidRegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken + 1000,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                FakeGameplayPolicyEventCallback,
                &plugin);
        Require(invalidRegistrationId == 0, "invalid owner token registered a gameplay policy callback");

        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
                    nullptr,
                    &plugin) == 0,
                "null gameplay policy callback was registered");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    0,
                    FakeGameplayPolicyEventCallback,
                    &plugin) == 0,
                "empty gameplay policy event mask was registered");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK | (1ull << 63),
                    FakeGameplayPolicyEventCallback,
                    &plugin) == 0,
                "reserved gameplay policy event mask bits were registered");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "invalid gameplay policy registrations left structure subscriptions behind");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "invalid gameplay policy registrations left inventory subscriptions behind");

        const uint64_t registrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                FakeGameplayPolicyEventCallback,
                &plugin);
        Require(registrationId != 0, "owner-token gameplay policy registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "owner-token gameplay policy callback was not bridged into structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "structure-only gameplay policy callback registered inventory dispatcher");

        Require(!plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                    otherPlugin.initOwnerToken,
                    registrationId),
                "wrong owner token unregistered a gameplay policy callback");

        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeStructureScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeStructureEvent(scalars)) == 1,
                "wrong-token unregister removed the gameplay policy callback");
        Require(plugin.gameplayPolicyEventCalls == 1,
                "owner-token gameplay policy callback did not dispatch");
        Require(plugin.gameplayPolicyEventAbiVersion == OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
                "gameplay policy event ABI version mismatch");
        Require(plugin.gameplayPolicyEventStructSize == sizeof(ObeliskGameplayPolicyEvent),
                "gameplay policy event struct size mismatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
                "structure event kind was not mapped to gameplay policy event kind");
        Require(plugin.gameplayPolicyResourceKind ==
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                "gameplay policy event resource kind was not structure");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0,
                "gameplay policy event was not marked copied-payload");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) != 0,
                "gameplay policy event was not marked structure-backed");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "gameplay policy event did not expose copied return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0,
                "gameplay policy event copied wrong return value");
        Require((plugin.gameplayPolicyFieldMask &
                    (OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                     OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                     OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE)) == 0,
                "gameplay policy event exposed unrelated scalar fields");

        const std::vector<Obelisk::Core::StructureScalarValue> setVariantScalars = MakeSetVariantScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeSetVariantEvent(setVariantScalars)) == 1,
                "masked gameplay policy callback did not receive structure dispatcher call");
        Require(plugin.gameplayPolicyEventCalls == 1,
                "gameplay policy callback ignored event kind mask");

        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                    plugin.initOwnerToken,
                    registrationId),
                "owner-token gameplay policy unregister failed");
        Require(!plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                    plugin.initOwnerToken,
                    registrationId),
                "owner-token gameplay policy unregister succeeded twice");
        Require(!plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                    plugin.initOwnerToken,
                    0),
                "zero gameplay policy callback handle unregistered a callback");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy callback survived explicit unregister");

        const uint64_t unloadRegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                FakeGameplayPolicyEventCallback,
                &plugin);
        Require(unloadRegistrationId != 0, "owner-token gameplay policy callback could not re-register before unload");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "all gameplay policy callback did not register structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "all gameplay policy callback did not register inventory dispatcher");

        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeSetVariantEvent(setVariantScalars)) == 1,
                "all-structures gameplay policy callback did not receive set variant dispatch");
        Require(plugin.gameplayPolicyEventCalls == 2,
                "all-structures gameplay policy callback did not dispatch set variant event");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                "set variant event kind was not mapped");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX) != 0,
                "set variant event did not expose copied variant index");
        Require(plugin.gameplayPolicyInt32Values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] == 3,
                "set variant event copied wrong variant index");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET) != 0,
                "set variant event did not expose copied force-set flag");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET)) != 0,
                "set variant event copied wrong force-set flag");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "set variant event did not expose copied return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) == 0,
                "set variant event copied wrong false return value");

        const std::vector<Obelisk::Core::StructureScalarValue> activationToggleScalars =
            MakeActivationToggleScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(
                    MakeActivationToggleEvent(activationToggleScalars)) == 1,
                "all gameplay policy callback did not receive activation toggle dispatch");
        Require(plugin.gameplayPolicyEventCalls == 3,
                "activation toggle gameplay policy callback did not dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE,
                "activation toggle event kind was not mapped");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "activation toggle did not expose copied return value");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE) == 0,
                "activation toggle exposed force field that current producer does not copy");

        const std::vector<Obelisk::Core::StructureScalarValue> canSeatScalars = MakeCanSeatScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeCanSeatEvent(canSeatScalars)) == 1,
                "all gameplay policy callback did not receive can-seat dispatch");
        Require(plugin.gameplayPolicyEventCalls == 4,
                "can-seat gameplay policy callback did not dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK,
                "can-seat event kind was not mapped");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE) != 0,
                "can-seat did not expose copied force flag");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE)) != 0,
                "can-seat copied wrong force flag");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "can-seat did not expose copied return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) == 0,
                "can-seat copied wrong false return value");

        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryRemoteAddScalars =
            MakeInventoryRemoteAddScalars();
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryRemoteAddEvent(inventoryRemoteAddScalars)) == 1,
                "all gameplay policy callback did not receive inventory remote-add dispatch");
        Require(plugin.gameplayPolicyEventCalls == 5,
                "inventory gameplay policy callback did not dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
                "inventory remote-add event kind was not mapped");
        Require(plugin.gameplayPolicyResourceKind ==
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                "inventory gameplay policy resource kind was not inventory item");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0,
                "inventory gameplay policy event was not marked copied-payload");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0,
                "inventory gameplay policy event was not marked inventory-backed");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) == 0,
                "inventory gameplay policy event was incorrectly marked structure-backed");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER) != 0,
                "inventory remote-add did not expose copied requested-by-player flag");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER)) != 0,
                "inventory remote-add copied wrong requested-by-player value");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "inventory remote-add did not expose copied return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0,
                "inventory remote-add copied wrong return value");

        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryCanUseScalars =
            MakeInventoryCanUseScalars();
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryCanUseScalars)) == 1,
                "all gameplay policy callback did not receive inventory can-use dispatch");
        Require(plugin.gameplayPolicyEventCalls == 6,
                "inventory can-use gameplay policy callback did not dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                "inventory use event kind was not mapped");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0,
                "inventory can-use did not expose copied ignore-cooldown flag");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) == 0,
                "inventory can-use copied wrong ignore-cooldown value");

        manager.UnloadAll();

        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy callback survived plugin unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy inventory callback survived plugin unload");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                    FakeGameplayPolicyEventCallback,
                    &plugin) == 0,
                "owner token remained valid for gameplay policy callbacks after plugin unload");

        CleanupPlugin(plugin);
        CleanupPlugin(otherPlugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenChatMessageEventRegistrationCanUnregister()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_chat_message_handle");
        ConfigureEnvironment(root);
        fs::create_directories(root / "state" / "instances" / "arkserver");

        {
            Obelisk::Core::ChatEventDispatcher disabledDispatcher;
            FakeLoader disabledLoader;
            Obelisk::Core::PluginManager disabledManager(disabledLoader, disabledDispatcher);
            Require((disabledManager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CHAT_EVENTS) == 0,
                    "chat message capability was advertised without the chat events gate");
        }

        setenv("OBELISK_ENABLE_CHAT_EVENTS", "1", 1);
        {
            std::ofstream marker(root / "state" / "instances" / "arkserver" / "enable-chat-events");
            Require(marker.is_open(), "failed to create chat events marker");
        }

        FakePlugin plugin{
            .filename = "owner_token_chat_message_a.so",
            .pluginId = "owner_token_chat_message_a",
            .captureApi = true,
        };
        FakePlugin otherPlugin{
            .filename = "owner_token_chat_message_b.so",
            .pluginId = "owner_token_chat_message_b",
        };
        FakeLoader loader;
        loader.Add(plugin);
        loader.Add(otherPlugin);
        TouchPlugin(root, plugin.filename);
        TouchPlugin(root, otherPlugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, otherPlugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0,
                "chat message event capability was not advertised");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token chat plugin was not initialized");
        Require(otherPlugin.initCalls == 1, "second owner-token chat plugin was not initialized");
        Require(plugin.initOwnerToken != 0, "owner-token chat plugin did not receive a token");
        Require(otherPlugin.initOwnerToken != 0, "second owner-token chat plugin did not receive a token");
        Require(plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle != nullptr,
                "chat message event registration function was not exposed");
        Require(plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken != nullptr,
                "chat message event unregister function was not exposed");

        Require(plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                    plugin.initOwnerToken + 1000,
                    FakeChatMessageEventCallback,
                    &plugin) == 0,
                "invalid owner token registered a chat message callback");
        Require(plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    nullptr,
                    &plugin) == 0,
                "null chat message callback was registered");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "invalid chat registrations left subscriptions behind");

        const uint64_t registrationId =
            plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                FakeChatMessageEventCallback,
                &plugin);
        Require(registrationId != 0, "owner-token chat message registration returned zero");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "owner-token chat callback was not bridged into chat dispatcher");

        Require(!plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken(
                    otherPlugin.initOwnerToken,
                    registrationId),
                "wrong owner token unregistered a chat message callback");

        const Obelisk::Core::ChatMessageView message{
            .Message = "!ping",
            .SenderName = "ignored",
            .SenderPlatformId = "ignored",
            .SendMode = Obelisk::Core::ChatSendMode::Global,
            .SenderNameIndex = 777,
        };
        Require(chatDispatcher.Dispatch(message) == 1,
                "wrong-token unregister removed the chat message callback");
        Require(plugin.chatMessageEventCalls == 1,
                "owner-token chat message callback did not dispatch");
        Require(plugin.chatMessageEventAbiVersion == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION,
                "chat message event ABI version mismatch");
        Require(plugin.chatMessageEventStructSize == sizeof(ObeliskChatMessageEvent),
                "chat message event struct size mismatch");
        Require(plugin.chatMessageSendMode == OBELISK_CHAT_SEND_MODE_GLOBAL,
                "chat message send mode mismatch");
        Require((plugin.chatMessageFlags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0,
                "chat message event was not marked copied-payload");
        Require(plugin.chatMessageSequence != 0,
                "chat message event sequence was zero");
        Require(plugin.chatMessageText == "!ping",
                "chat message event copied wrong text");

        Require(plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken(
                    plugin.initOwnerToken,
                    registrationId),
                "owner-token chat message unregister failed");
        Require(!plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken(
                    plugin.initOwnerToken,
                    registrationId),
                "owner-token chat message unregister succeeded twice");
        Require(!plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken(
                    plugin.initOwnerToken,
                    0),
                "zero chat message callback handle unregistered a callback");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "owner-token chat message callback survived explicit unregister");

        plugin.chatMessageRegistrationId =
            plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                FakeChatMessageSelfUnregisterCallback,
                &plugin);
        Require(plugin.chatMessageRegistrationId != 0,
                "owner-token chat message self-unregister callback could not register");
        Require(chatDispatcher.Dispatch(message) == 1,
                "chat message self-unregister callback did not dispatch");
        Require(plugin.chatMessageSelfUnregisterResult,
                "chat message self-unregister callback failed to unregister itself");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat message self-unregister callback survived dispatch");

        const uint64_t unloadRegistrationId =
            plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                FakeChatMessageEventCallback,
                &plugin);
        Require(unloadRegistrationId != 0, "owner-token chat message callback could not re-register before unload");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "chat message callback did not register before unload");
        manager.UnloadAll();
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat message callback survived plugin unload");

        CleanupPlugin(plugin);
        CleanupPlugin(otherPlugin);
        fs::remove_all(root);
    }

    void TestGameplayPolicyCallbackCanSelfUnregisterDuringDispatch()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_self_unregister");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_self_unregister.so",
            .pluginId = "gameplay_policy_self_unregister",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "self-unregister plugin was not initialized");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy registration function was not exposed");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken != nullptr,
                "gameplay policy unregister function was not exposed");

        plugin.gameplayPolicyRegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                FakeGameplayPolicySelfUnregisterCallback,
                &plugin);
        Require(plugin.gameplayPolicyRegistrationId != 0,
                "structure self-unregister gameplay policy registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "structure self-unregister callback was not bridged into structure dispatcher");

        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeStructureScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeStructureEvent(scalars)) == 1,
                "structure self-unregister callback did not dispatch");
        Require(plugin.gameplayPolicyEventCalls == 1,
                "structure self-unregister callback call count mismatch");
        Require(plugin.gameplayPolicySelfUnregisterResult,
                "structure self-unregister callback could not unregister itself");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure self-unregister callback remained registered after dispatch");
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeStructureEvent(scalars)) == 0,
                "structure self-unregister callback dispatched after removal");

        plugin.gameplayPolicyEventCalls = 0;
        plugin.gameplayPolicySelfUnregisterResult = false;
        plugin.gameplayPolicyRegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                FakeGameplayPolicySelfUnregisterCallback,
                &plugin);
        Require(plugin.gameplayPolicyRegistrationId != 0,
                "inventory self-unregister gameplay policy registration returned zero");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "inventory self-unregister callback was not bridged into inventory dispatcher");

        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryScalars =
            MakeInventoryCanUseScalars();
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)) == 1,
                "inventory self-unregister callback did not dispatch");
        Require(plugin.gameplayPolicyEventCalls == 1,
                "inventory self-unregister callback call count mismatch");
        Require(plugin.gameplayPolicySelfUnregisterResult,
                "inventory self-unregister callback could not unregister itself");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory self-unregister callback remained registered after dispatch");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)) == 0,
                "inventory self-unregister callback dispatched after removal");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "self-unregister plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "self-unregister plugin was not closed");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "structure self-unregister callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "inventory self-unregister callback was still registered at dlclose");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                    FakeGameplayPolicyEventCallback,
                    &plugin) == 0,
                "owner token remained valid after self-unregister plugin unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestDescribeResourceKind()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_describe_resource_kind");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "describe_resource_kind.so",
            .pluginId = "describe_resource_kind",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) != 0,
                "resource kind descriptor capability was not advertised");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "resource descriptor plugin was not initialized");
        Require(plugin.capturedApi.DescribeResourceKind != nullptr,
                "DescribeResourceKind function was not exposed");

        ObeliskResourceKindDescriptor descriptor{};
        Require(!plugin.capturedApi.DescribeResourceKind(
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                    &descriptor),
                "DescribeResourceKind accepted a zero-size descriptor");

        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        Require(plugin.capturedApi.DescribeResourceKind(
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                    &descriptor),
                "DescribeResourceKind rejected structure resource kind");
        Require(descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION,
                "resource descriptor ABI version mismatch");
        Require(descriptor.struct_size == sizeof(ObeliskResourceKindDescriptor),
                "resource descriptor struct size mismatch");
        Require(descriptor.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                "resource descriptor kind mismatch");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY) != 0,
                "resource descriptor did not mark category-only");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY) != 0,
                "resource descriptor did not mark no-identity");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP) != 0,
                "resource descriptor did not mark no-lookup");
        Require(descriptor.supported_gameplay_policy_event_mask ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
                "resource descriptor event mask mismatch");
        Require((descriptor.supported_gameplay_policy_field_mask &
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0,
                "resource descriptor field mask did not include return value");
        Require(std::strcmp(descriptor.stable_name, "structure") == 0,
                "resource descriptor stable name mismatch");
        Require(std::strcmp(descriptor.display_name, "Structure") == 0,
                "resource descriptor display name mismatch");

        descriptor = {};
        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        Require(plugin.capturedApi.DescribeResourceKind(
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                    &descriptor),
                "DescribeResourceKind rejected inventory item resource kind");
        Require(descriptor.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                "inventory resource descriptor kind mismatch");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY) != 0,
                "inventory resource descriptor did not mark category-only");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY) != 0,
                "inventory resource descriptor did not mark no-identity");
        Require((descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP) != 0,
                "inventory resource descriptor did not mark no-lookup");
        Require(descriptor.supported_gameplay_policy_event_mask ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY,
                "inventory resource descriptor event mask mismatch");
        Require((descriptor.supported_gameplay_policy_field_mask &
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER) != 0,
                "inventory resource descriptor field mask did not include requested-by-player");
        Require((descriptor.supported_gameplay_policy_field_mask &
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0,
                "inventory resource descriptor field mask did not include ignore-cooldown");
        Require(std::strcmp(descriptor.stable_name, "inventory_item") == 0,
                "inventory resource descriptor stable name mismatch");
        Require(std::strcmp(descriptor.display_name, "Inventory Item") == 0,
                "inventory resource descriptor display name mismatch");

        descriptor = {};
        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        Require(!plugin.capturedApi.DescribeResourceKind(
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN,
                    &descriptor),
                "DescribeResourceKind accepted unknown resource kind");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestDescribeGameplayPolicyEventKind()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_describe_gameplay_policy_event_kind");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "describe_gameplay_policy_event_kind.so",
            .pluginId = "describe_gameplay_policy_event_kind",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() &
                    OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) != 0,
                "gameplay policy event descriptor capability was not advertised");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "event descriptor plugin was not initialized");
        Require(plugin.capturedApi.DescribeGameplayPolicyEventKind != nullptr,
                "DescribeGameplayPolicyEventKind function was not exposed");

        ObeliskGameplayPolicyEventDescriptor descriptor{};
        Require(!plugin.capturedApi.DescribeGameplayPolicyEventKind(
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                    &descriptor),
                "DescribeGameplayPolicyEventKind accepted a zero-size descriptor");

        struct ExpectedEventDescriptor
        {
            uint32_t eventKind;
            uint32_t resourceKind;
            uint64_t flags;
            uint64_t eventMask;
            uint64_t fieldMask;
            const char* stableName;
            const char* displayName;
        };

        const ExpectedEventDescriptor expectedDescriptors[] = {
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "structure.access_check",
                "Structure Access Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "structure.demolish_check",
                "Structure Demolish Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET,
                "structure.variant_change",
                "Structure Variant Change",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "structure.activation_toggle",
                "Structure Activation Toggle",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "structure.pin_code_check",
                "Structure Pin Code Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                "structure.seat_check",
                "Structure Seat Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
                "inventory.remote_add_check",
                "Inventory Remote Add Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                "inventory.use_check",
                "Inventory Use Check",
            },
        };

        Require(sizeof(expectedDescriptors) / sizeof(expectedDescriptors[0]) ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT,
                "event descriptor test matrix is out of sync with public event count");

        ObeliskResourceKindDescriptor resourceDescriptor{};
        for (const ExpectedEventDescriptor& expected : expectedDescriptors)
        {
            descriptor = {};
            descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
            Require(plugin.capturedApi.DescribeGameplayPolicyEventKind(expected.eventKind, &descriptor),
                    "DescribeGameplayPolicyEventKind rejected a promoted event kind");
            Require(descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION,
                    "event descriptor ABI version mismatch");
            Require(descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor),
                    "event descriptor struct size mismatch");
            Require(descriptor.event_kind == expected.eventKind,
                    "event descriptor kind mismatch");
            Require(descriptor.resource_kind == expected.resourceKind,
                    "event descriptor resource kind mismatch");
            Require(descriptor.flags == expected.flags,
                    "event descriptor flags mismatch");
            Require(descriptor.event_kind_mask == expected.eventMask,
                    "event descriptor event mask mismatch");
            Require(descriptor.field_mask == expected.fieldMask,
                    "event descriptor field mask mismatch");
            Require(std::strcmp(descriptor.stable_name, expected.stableName) == 0,
                    "event descriptor stable name mismatch");
            Require(std::strcmp(descriptor.display_name, expected.displayName) == 0,
                    "event descriptor display name mismatch");

            resourceDescriptor = {};
            resourceDescriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
            Require(plugin.capturedApi.DescribeResourceKind(expected.resourceKind, &resourceDescriptor),
                    "DescribeResourceKind rejected descriptor resource kind");
            Require((resourceDescriptor.supported_gameplay_policy_event_mask & descriptor.event_kind_mask) != 0,
                    "event descriptor mask is not supported by its resource descriptor");
            Require((descriptor.field_mask & ~resourceDescriptor.supported_gameplay_policy_field_mask) == 0,
                    "event descriptor exposes fields outside resource descriptor support");
        }

        descriptor = {};
        descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        Require(!plugin.capturedApi.DescribeGameplayPolicyEventKind(
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN,
                    &descriptor),
                "DescribeGameplayPolicyEventKind accepted unknown event kind");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGameplayPolicyCallbackCleansOnInitFailure()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_init_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_init_fail.so",
            .initResult = false,
            .registerGameplayPolicyCallback = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "gameplay-policy init-fail plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "gameplay-policy init-fail plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "gameplay-policy init-fail plugin was not closed");
        Require(plugin.gameplayPolicyRegistrationId != 0,
                "gameplay-policy callback was not registered before init failure");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "gameplay-policy structure callback survived init failure");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "gameplay-policy inventory callback survived init failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGameplayPolicyCallbackCleansOnInitException()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_init_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_init_throw.so",
            .registerGameplayPolicyCallback = true,
            .throwInInitAfterCallbacks = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "gameplay-policy init-throw plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "gameplay-policy init-throw plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "gameplay-policy init-throw plugin was not closed");
        Require(plugin.gameplayPolicyRegistrationId != 0,
                "gameplay-policy callback was not registered before init exception");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "gameplay-policy structure callback survived init exception");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "gameplay-policy inventory callback survived init exception");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenRegistrationRejectedDuringShutdown()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_shutdown_register");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_shutdown_register.so",
            .registerOwnerTokenCallbackInShutdown = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "shutdown-register plugin shutdown was not called");
        Require(plugin.shutdownRegistrationId == 0,
                "owner-token callback registration succeeded while plugin was unloading");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-time owner-token callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenRegistrationRejectedDuringInitFailureShutdown()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_init_fail_shutdown_register");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_init_fail_shutdown_register.so",
            .initResult = false,
            .registerOwnerTokenCallbackInShutdown = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "init-failure shutdown-register plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-failure shutdown-register plugin shutdown was not called");
        Require(plugin.shutdownRegistrationId == 0,
                "owner-token callback registration succeeded during init-failure shutdown");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "init-failure shutdown-time owner-token callback survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenUnregisterAllowedDuringShutdown()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_shutdown_unregister");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_shutdown_unregister.so",
            .registerOwnerTokenFromInitThread = true,
            .unregisterOwnerTokenCallbackInShutdown = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initThreadRegistrationId != 0,
                "shutdown-unregister plugin did not register a callback before unload");
        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-unregister plugin callback was not registered before unload");

        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "shutdown-unregister plugin shutdown was not called");
        Require(plugin.shutdownUnregisterResult,
                "owner-token callback unregister was rejected while plugin was unloading");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-unregistered owner-token callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestOwnerTokenUnregisterAllowedDuringInitFailureShutdown()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_init_fail_shutdown_unregister");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_init_fail_shutdown_unregister.so",
            .initResult = false,
            .registerOwnerTokenFromInitThread = true,
            .unregisterOwnerTokenCallbackInShutdown = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "init-failure shutdown-unregister plugin Init was not called");
        Require(plugin.shutdownCalls == 1, "init-failure shutdown-unregister plugin shutdown was not called");
        Require(plugin.initThreadRegistrationId != 0,
                "init-failure shutdown-unregister plugin did not register a callback before failing");
        Require(plugin.shutdownUnregisterResult,
                "owner-token callback unregister was rejected during init-failure shutdown");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "init-failure shutdown-unregistered owner-token callback survived load failure");

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

    void TestGlobalProcessEventCallbackRejectedAfterGateRevoked()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_revoked");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        const fs::path markerPath =
            root / "state" / "instances" / "arkserver" / "allow-global-process-event-callbacks";
        std::ofstream marker(markerPath);
        Require(marker.is_open(), "failed to create global callback marker");
        marker.close();

        FakePlugin plugin{.filename = "global_revoked.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0,
                "global callback capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "global-revoked plugin was not initialized");
        fs::remove(markerPath);

        const uint64_t registrationId =
            plugin.capturedApi.RegisterPreProcessEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                FakeCallback);

        Require(registrationId == 0, "global callback registration succeeded after marker revocation");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "global callback was registered after marker revocation");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
        fs::remove_all(root);
    }

    void TestCallProcessEventRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_call_process_event_denied");
        ConfigureEnvironment(root);
        Obelisk::Hooks::ResetProcessEventCallOriginalCountForTesting();

        FakePlugin plugin{.filename = "call_process_event_denied.so", .callProcessEventInInit = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) == 0,
                "CallProcessEvent capability was enabled by default");

        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "CallProcessEvent-denied plugin was not initialized");
        Require(Obelisk::Hooks::ProcessEventCallOriginalCountForTesting() == 0,
                "CallProcessEvent reached original trampoline without explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestCallProcessEventAllowedWithGate()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_call_process_event_allowed");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_CALL_PROCESS_EVENT", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-call-process-event");
        Require(marker.is_open(), "failed to create CallProcessEvent marker");
        marker.close();
        Obelisk::Hooks::ResetProcessEventCallOriginalCountForTesting();

        FakePlugin plugin{.filename = "call_process_event_allowed.so", .callProcessEventInInit = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) != 0,
                "CallProcessEvent capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "CallProcessEvent-allowed plugin was not initialized");
        Require(Obelisk::Hooks::ProcessEventCallOriginalCountForTesting() == 1,
                "CallProcessEvent did not reach original trampoline with explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_CALL_PROCESS_EVENT");
        fs::remove_all(root);
    }

    void TestCallProcessEventRejectedAfterGateRevoked()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_call_process_event_revoked");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_CALL_PROCESS_EVENT", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        const fs::path markerPath =
            root / "state" / "instances" / "arkserver" / "allow-call-process-event";
        std::ofstream marker(markerPath);
        Require(marker.is_open(), "failed to create CallProcessEvent marker");
        marker.close();
        Obelisk::Hooks::ResetProcessEventCallOriginalCountForTesting();

        FakePlugin plugin{.filename = "call_process_event_revoked.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) != 0,
                "CallProcessEvent capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "CallProcessEvent-revoked plugin was not initialized");
        fs::remove(markerPath);

        plugin.capturedApi.CallProcessEvent(
            reinterpret_cast<void*>(0x1),
            reinterpret_cast<void*>(0x2),
            reinterpret_cast<void*>(0x3));

        Require(Obelisk::Hooks::ProcessEventCallOriginalCountForTesting() == 0,
                "CallProcessEvent reached original trampoline after marker revocation");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_CALL_PROCESS_EVENT");
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

    void TestPluginSymlinkDirectoryIsRejected()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_plugin_dir_symlink");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "escaped.so"};
        FakeLoader loader;
        loader.Add(plugin);

        const fs::path externalPlugins = root / "external-plugins";
        fs::create_directories(externalPlugins);
        fs::remove_all(root / "plugins");
        fs::create_directory_symlink(externalPlugins, root / "plugins");
        {
            std::ofstream out(root / "plugins" / plugin.filename);
            Require(out.is_open(), "failed to create fake plugin in symlinked plugin directory");
        }
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.getInfoCalls == 0, "plugin in symlinked plugin directory was opened");
        Require(plugin.initCalls == 0, "plugin in symlinked plugin directory was initialized");
        Require(plugin.closeCalls == 0, "plugin in symlinked plugin directory reached loader close path");

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
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerStructureCallback = true;
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
                "init-failing plugin ProcessEvent callback was not present during shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "init-failing plugin chat callback was not present during shutdown");
        Require(plugin.inventoryPolicySubscriptionsAtShutdown == 1,
                "init-failing plugin inventory policy callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "init-failing plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "init-failing plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "failed plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "failed plugin inventory policy callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "failed plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback registered by failed plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by failed plugin survived load failure");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory policy callback registered by failed plugin survived load failure");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure callback registered by failed plugin survived load failure");

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
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerStructureCallback = true;
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
                "init-throw plugin ProcessEvent callback was not present during shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "init-throw plugin chat callback was not present during shutdown");
        Require(plugin.inventoryPolicySubscriptionsAtShutdown == 1,
                "init-throw plugin inventory policy callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "init-throw plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "init-throw plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "init-throw plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "init-throw plugin inventory policy callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "init-throw plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "ProcessEvent callback registered by throwing plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by throwing plugin survived load failure");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory policy callback registered by throwing plugin survived load failure");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure callback registered by throwing plugin survived load failure");

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

    void TestPluginApiMutationDoesNotPoisonLaterPlugins()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_api_mutation");
        ConfigureEnvironment(root);

        FakePlugin pluginA{
            .filename = "a_mutates_api.so",
            .pluginId = "plugin_a",
            .mutateApiInInit = true,
        };
        FakePlugin pluginB{
            .filename = "b_requires_clean_api.so",
            .pluginId = "plugin_b",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(pluginA);
        loader.Add(pluginB);
        TouchPlugin(root, pluginA.filename);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        const uint64_t expectedCapabilities = manager.ApiCapabilitiesForTesting();
        manager.LoadPlugins((root / "plugins").string());

        Require(pluginA.initCalls == 1, "API-mutating plugin was not initialized");
        Require(pluginB.initCalls == 1, "later plugin did not initialize after API mutation");
        Require(pluginB.capturedApi.LogInfo != nullptr, "later plugin received corrupted LogInfo pointer");
        Require(pluginB.capturedApi.abi_version == OBELISK_API_ABI_VERSION,
                "later plugin received corrupted API ABI version");
        Require(pluginB.capturedApi.capabilities == expectedCapabilities,
                "later plugin received corrupted API capabilities");
        Require(manager.ApiCapabilitiesForTesting() == expectedCapabilities,
                "manager API template was corrupted by plugin mutation");

        manager.UnloadAll();
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
            .registerInventoryPolicyCallback = true,
            .registerStructureCallback = true,
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
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "shutdown-throw plugin inventory policy callback was not registered");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "shutdown-throw plugin structure callback was not registered");

        manager.UnloadAll();
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "shutdown-throw plugin shutdown was not called once");
        Require(plugin.eventCallbacksAtShutdown,
                "shutdown-throw plugin ProcessEvent callbacks were not present during shutdown");
        Require(plugin.chatSubscriptionsAtShutdown == 1,
                "shutdown-throw plugin chat callback was not present during shutdown");
        Require(plugin.inventoryPolicySubscriptionsAtShutdown == 1,
                "shutdown-throw plugin inventory policy callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "shutdown-throw plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "shutdown-throw plugin was not closed once");
        Require(plugin.chatSubscriptionsAtClose == 0,
                "shutdown-throw plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "shutdown-throw plugin inventory policy callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "shutdown-throw plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-throw plugin ProcessEvent callbacks survived unload");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "shutdown-throw plugin chat callback survived unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown-throw plugin inventory policy callback survived unload");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown-throw plugin structure callback survived unload");

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

    TestEmptyPluginDirectoryIsRejected();
    TestRelativePluginDirectoryIsRejected();
    TestValidPluginLoadsAndUnloadCleansCallbacks();
    TestPluginOwnerTokensSkipZeroAndLiveTokensAfterWrap();
    TestGlobalProcessEventCallbackRejectedByDefault();
    TestCallbackHandleCapabilityImpliesOwnerTokenCapability();
    TestProcessEventBlockingCapabilityRejectedByDefault();
    TestProcessEventBlockingCapabilityAllowedWithGate();
    TestFilteredProcessEventCallbackAllowedByDefault();
    TestPostInitUnownedCallbackRegistrationIsRejected();
    TestPostInitOwnerTokenCallbackRegistrationCleansOnUnload();
    TestOwnerTokenCallbackRegistrationFromInitThread();
    TestInitFailureCleansInitThreadOwnerTokenCallbackAndToken();
    TestInitExceptionCleansInitThreadOwnerTokenCallbackAndToken();
    TestOwnerTokenHandleRegistrationCanUnregister();
    TestOwnerTokenGameplayPolicyEventRegistrationCanUnregister();
    TestOwnerTokenChatMessageEventRegistrationCanUnregister();
    TestGameplayPolicyCallbackCanSelfUnregisterDuringDispatch();
    TestDescribeResourceKind();
    TestDescribeGameplayPolicyEventKind();
    TestGameplayPolicyCallbackCleansOnInitFailure();
    TestGameplayPolicyCallbackCleansOnInitException();
    TestOwnerTokenGlobalHandleRejectedByDefault();
    TestInvalidOwnerTokenCallbackRegistrationIsRejected();
    TestInvalidProcessEventCallbacksAreRejected();
    TestOwnerTokenRegistrationRejectedDuringShutdown();
    TestOwnerTokenRegistrationRejectedDuringInitFailureShutdown();
    TestOwnerTokenUnregisterAllowedDuringShutdown();
    TestOwnerTokenUnregisterAllowedDuringInitFailureShutdown();
    TestUnsafeInstanceIdDisablesPluginLoading();
    TestUnsafeConfigRootDisablesPluginLoading();
    TestGlobalProcessEventCallbackAllowedWithGate();
    TestGlobalProcessEventCallbackRejectedAfterGateRevoked();
    TestCallProcessEventRejectedByDefault();
    TestCallProcessEventAllowedWithGate();
    TestCallProcessEventRejectedAfterGateRevoked();
    TestDisabledPluginPreparesConfigButDoesNotInit();
    TestInstanceDisallowedPluginDoesNotInit();
    TestMissingGetInfoRejectsAndCloses();
    TestResolveExceptionAfterOpenClosesHandle();
    TestPluginSymlinkCandidateIsRejected();
    TestPluginSymlinkDirectoryIsRejected();
    TestMissingInitRejectsAndCloses();
    TestInvalidMetadataRejectsAndCloses();
    TestInitFailureCleansCallbacksAndCloses();
    TestInitExceptionCleansCallbacksAndCloses();
    TestMultiplePluginsLoadSortedAndUnloadReverse();
    TestPluginApiMutationDoesNotPoisonLaterPlugins();
    TestUnloadAllContinuesAfterCloseException();
    TestUnloadAllCleansAfterShutdownException();
    TestDuplicatePluginIdRejectsSecondPlugin();
    TestLoadPluginsSkipsAlreadyLoadedPluginId();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "PluginManagerTests passed\n";
    return 0;
}
