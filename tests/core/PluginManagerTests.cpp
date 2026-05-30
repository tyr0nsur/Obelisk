#include "core/ChatEventDispatcher.h"
#include "core/EventManager.h"
#include "core/InventoryPolicyEventDispatcher.h"
#include "core/ItemReturnEventDispatcher.h"
#include "core/PluginManager.h"
#include "core/StructureEventDispatcher.h"
#include "core/TimerManager.h"
#include "runtime/Logger.h"

// The plugin-manager test target compiles PluginManager.cpp directly instead of linking
// the full core object list, so keep the private item-return dispatcher implementation
// available here without changing build-system scope.
#include "core/ItemReturnEventDispatcher.cpp"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
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
    void SetProcessEventCallOriginalThrowForTesting(bool enabled);
}

namespace Obelisk::Core
{
    void SetPluginCallbackCleanupFailureForTesting(bool enabled);
}

namespace
{
    constexpr const char* kDefaultConfig =
        R"({"enabled":false,"allow_all_instances":false,"instance_allowlist":["arkserver"]})";

    struct TimerFenceState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        int Calls = 0;
        int Completed = 0;
        uint64_t LastTimerId = 0;
        bool Release = false;
        bool ShutdownEntered = false;
        bool CloseEntered = false;
        bool UnloadReturned = false;
    };

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
        bool registerItemReturnCallback = false;
        bool registerStructureCallback = false;
        bool registerGameplayPolicyCallback = false;
        bool registerTimerCallback = false;
        bool callProcessEventInInit = false;
        bool registerOwnerTokenCallbackInShutdown = false;
        bool unregisterOwnerTokenCallbackInShutdown = false;
        bool throwOnGetInfoResolve = false;
        bool throwInInitAfterCallbacks = false;
        bool throwOnShutdown = false;
        bool throwOnClose = false;
        bool captureApi = false;
        bool mutateApiInInit = false;
        std::atomic<bool>* closeObserved = nullptr;
        TimerFenceState* timerFence = nullptr;
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
        uint64_t timerRegistrationId = 0;
        int timerEventCalls = 0;
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
        size_t itemReturnSubscriptionsAtShutdown = 0;
        size_t itemReturnSubscriptionsAtClose = 0;
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
        uint32_t chatMessageReserved0 = 1;
        uint64_t chatMessageFlags = 0;
        uint64_t chatMessageSequence = 0;
        std::string chatMessageText;
        const char* chatMessageData = nullptr;
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

    void FakeTimerCallback(uint64_t, void* userData)
    {
        auto* plugin = static_cast<FakePlugin*>(userData);
        ++plugin->timerEventCalls;
    }

    void CountingTimerCallback(uint64_t timerId, void* userData)
    {
        auto* state = static_cast<TimerFenceState*>(userData);
        std::lock_guard<std::mutex> lock(state->Mutex);
        ++state->Calls;
        state->LastTimerId = timerId;
        state->Cv.notify_all();
    }

    void BlockingTimerCallback(uint64_t timerId, void* userData)
    {
        auto* state = static_cast<TimerFenceState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        ++state->Calls;
        state->LastTimerId = timerId;
        state->Cv.notify_all();
        state->Cv.wait(lock, [state]() { return state->Release; });
        ++state->Completed;
        state->Cv.notify_all();
    }

    void FakeInventoryPolicyCallback(const Obelisk::Core::InventoryPolicyEventView&, void*)
    {
    }

    void FakeItemReturnCallback(const Obelisk::Core::ItemReturnEventView&, void*)
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

    void ThrowingGameplayPolicyEventCallback(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        Require(event != nullptr, "throwing gameplay policy callback received null event");
        auto* callCount = static_cast<int*>(userData);
        ++(*callCount);
        throw std::runtime_error("injected gameplay policy callback failure");
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

    struct ConcurrentGameplayPolicyUnregisterState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        const ObeliskApi* Api = nullptr;
        uint64_t OwnerToken = 0;
        uint64_t RegistrationId = 0;
        int Entered = 0;
        int Completed = 0;
        int SuccessfulUnregisters = 0;
        bool SawStructure = false;
        bool SawInventory = false;
        bool Release = false;
    };

    void ConcurrentGameplayPolicyUnregisterCallback(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        Require(event != nullptr, "concurrent gameplay policy callback received null event");
        auto* state = static_cast<ConcurrentGameplayPolicyUnregisterState*>(userData);
        {
            std::unique_lock<std::mutex> lock(state->Mutex);
            state->SawStructure = state->SawStructure ||
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            state->SawInventory = state->SawInventory ||
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
            ++state->Entered;
            state->Cv.notify_all();
            state->Cv.wait(lock, [state]() { return state->Release; });
        }

        const bool unregistered =
            state->Api && state->Api->UnregisterGameplayPolicyEventWithOwnerToken &&
            state->Api->UnregisterGameplayPolicyEventWithOwnerToken(
                state->OwnerToken,
                state->RegistrationId);

        {
            std::lock_guard<std::mutex> lock(state->Mutex);
            if (unregistered)
                ++state->SuccessfulUnregisters;
            ++state->Completed;
            state->Cv.notify_all();
        }
    }

    struct CrossFamilyFenceState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        const ObeliskApi* Api = nullptr;
        uint64_t OwnerToken = 0;
        uint64_t RegistrationId = 0;
        int InventoryCalls = 0;
        int StructureCalls = 0;
        bool InventoryEntered = false;
        bool ReleaseInventory = false;
        bool StructureEntered = false;
        bool ReleaseStructure = false;
        bool StructureUnregisterReturned = false;
        bool StructureUnregisterResult = false;
        bool InventoryUnregisterReturned = false;
        bool InventoryUnregisterResult = false;
        bool BlockStructure = false;
    };

    void GameplayPolicyCrossFamilyFenceCallback(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        Require(event != nullptr, "cross-family fence callback received null event");
        auto* state = static_cast<CrossFamilyFenceState*>(userData);
        if (event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM)
        {
            {
                std::unique_lock<std::mutex> lock(state->Mutex);
                ++state->InventoryCalls;
                state->InventoryEntered = true;
                state->Cv.notify_all();
                if (!state->BlockStructure)
                {
                    state->Cv.wait(lock, [state]() { return state->ReleaseInventory; });
                    return;
                }
            }

            const bool unregistered =
                state->Api && state->Api->UnregisterGameplayPolicyEventWithOwnerToken &&
                state->Api->UnregisterGameplayPolicyEventWithOwnerToken(
                    state->OwnerToken,
                    state->RegistrationId);

            {
                std::lock_guard<std::mutex> lock(state->Mutex);
                state->InventoryUnregisterResult = unregistered;
                state->InventoryUnregisterReturned = true;
                state->Cv.notify_all();
            }
            return;
        }

        Require(event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                "cross-family fence callback received unexpected resource kind");
        {
            std::unique_lock<std::mutex> lock(state->Mutex);
            ++state->StructureCalls;
            state->StructureEntered = true;
            state->Cv.notify_all();
            if (state->BlockStructure)
            {
                state->Cv.wait(lock, [state]() { return state->ReleaseStructure; });
                return;
            }
        }

        const bool unregistered =
            state->Api && state->Api->UnregisterGameplayPolicyEventWithOwnerToken &&
            state->Api->UnregisterGameplayPolicyEventWithOwnerToken(
                state->OwnerToken,
                state->RegistrationId);

        {
            std::lock_guard<std::mutex> lock(state->Mutex);
            state->StructureUnregisterResult = unregistered;
            state->StructureUnregisterReturned = true;
            state->Cv.notify_all();
        }
    }

    struct ShutdownCrossFamilyFenceState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        int InventoryCalls = 0;
        int StructureCalls = 0;
        bool InventoryEntered = false;
        bool StructureEntered = false;
        bool ReleaseInventory = false;
        bool ReleaseStructure = false;
    };

    void GameplayPolicyShutdownCrossFamilyFenceCallback(
        const ObeliskGameplayPolicyEvent* event,
        void* userData)
    {
        Require(event != nullptr, "shutdown cross-family fence callback received null event");
        auto* state = static_cast<ShutdownCrossFamilyFenceState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        if (event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM)
        {
            ++state->InventoryCalls;
            state->InventoryEntered = true;
            state->Cv.notify_all();
            state->Cv.wait(lock, [state]() { return state->ReleaseInventory; });
            return;
        }

        Require(event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                "shutdown cross-family fence callback received unexpected resource kind");
        ++state->StructureCalls;
        state->StructureEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [state]() { return state->ReleaseStructure; });
    }

    void FakeChatMessageEventCallback(const ObeliskChatMessageEvent* event, void* userData)
    {
        Require(event != nullptr, "chat message callback received null event");
        auto* plugin = static_cast<FakePlugin*>(userData);
        ++plugin->chatMessageEventCalls;
        plugin->chatMessageSendMode = event->send_mode;
        plugin->chatMessageReserved0 = event->reserved0;
        plugin->chatMessageFlags = event->flags;
        plugin->chatMessageSequence = event->sequence;
        plugin->chatMessageText.assign(event->message.data, event->message.size);
        plugin->chatMessageData = event->message.data;
        plugin->chatMessageEventAbiVersion = event->abi_version;
        plugin->chatMessageEventStructSize = event->struct_size;
    }

    void ThrowingChatMessageEventCallback(const ObeliskChatMessageEvent* event, void* userData)
    {
        Require(event != nullptr, "throwing chat message callback received null event");
        auto* callCount = static_cast<int*>(userData);
        ++(*callCount);
        throw std::runtime_error("injected chat message callback failure");
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

    std::vector<Obelisk::Core::ItemReturnScalarValue> MakeItemReturnScalars(bool returnValue)
    {
        return {
            {
                .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
                .BoolValue = returnValue,
            },
        };
    }

    Obelisk::Core::ItemReturnEventView MakeItemReturnEvent(
        Obelisk::Core::ItemReturnEventKind kind,
        const std::vector<Obelisk::Core::ItemReturnScalarValue>& scalars)
    {
        return {
            .Kind = kind,
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
        Require((api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0,
                "plugin init received API without timer capability");
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

        if (g_CurrentFakePlugin->registerItemReturnCallback)
        {
            const uint64_t registrationId = Obelisk::Core::ItemReturnEventDispatcher::Get().Register(
                g_CurrentFakePlugin->owner,
                Obelisk::Core::ItemReturnEventSubscription{FakeItemReturnCallback, g_CurrentFakePlugin});
            Require(registrationId != 0, "fake item-return callback registration failed");
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

        if (g_CurrentFakePlugin->registerTimerCallback)
        {
            Require(api->RegisterTimerWithOwnerTokenHandle != nullptr,
                    "fake plugin requested timer callback without registration API");
            Require(api->UnregisterTimerWithOwnerToken != nullptr,
                    "fake plugin requested timer callback without unregister API");
            g_CurrentFakePlugin->timerRegistrationId =
                api->RegisterTimerWithOwnerTokenHandle(
                    context->plugin_owner_token,
                    1000,
                    0,
                    0,
                    FakeTimerCallback,
                    g_CurrentFakePlugin);
            Require(g_CurrentFakePlugin->timerRegistrationId != 0, "fake timer callback registration failed");
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
        g_CurrentFakePlugin->itemReturnSubscriptionsAtShutdown =
            Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount();
        g_CurrentFakePlugin->structureSubscriptionsAtShutdown =
            Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount();
        ++g_CurrentFakePlugin->shutdownCalls;
        if (g_CurrentFakePlugin->timerFence)
        {
            std::lock_guard<std::mutex> lock(g_CurrentFakePlugin->timerFence->Mutex);
            g_CurrentFakePlugin->timerFence->ShutdownEntered = true;
            g_CurrentFakePlugin->timerFence->Cv.notify_all();
        }
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
            plugin->itemReturnSubscriptionsAtClose =
                Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount();
            plugin->structureSubscriptionsAtClose =
                Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount();
            ++plugin->closeCalls;
            if (plugin->closeObserved)
                plugin->closeObserved->store(true, std::memory_order_release);
            if (plugin->timerFence)
            {
                std::lock_guard<std::mutex> lock(plugin->timerFence->Mutex);
                plugin->timerFence->CloseEntered = true;
                plugin->timerFence->Cv.notify_all();
            }
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
        unsetenv("OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS");
        unsetenv("OBELISK_ALLOW_CALL_PROCESS_EVENT");
        unsetenv("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING");
        unsetenv("OBELISK_ENABLE_CHAT_EVENTS");
        Obelisk::Core::EventManager::SetProcessEventBlockingCapabilityAdvertised(false);
    }

    void EnableFilteredProcessEventCallbacks(const fs::path& root)
    {
        setenv("OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-filtered-process-event-callbacks");
        Require(marker.is_open(), "failed to create filtered ProcessEvent callback marker");
    }

    void CleanupPlugin(FakePlugin& plugin)
    {
        Obelisk::Core::EventManager::Get().UnregisterCallbacksForOwner(plugin.owner);
        if (plugin.chatDispatcher)
            plugin.chatDispatcher->UnregisterCallbacksForOwner(plugin.owner);
        Obelisk::Core::InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(plugin.owner);
        Obelisk::Core::ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(plugin.owner);
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
        EnableFilteredProcessEventCallbacks(root);

        FakePlugin plugin{.filename = "valid.so", .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerItemReturnCallback = true;
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
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 1,
                "owned item-return callback was not registered during plugin init");
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
        Require(plugin.itemReturnSubscriptionsAtShutdown == 1,
                "item-return callback was removed before plugin shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "structure callback was removed before plugin shutdown");
        Require(plugin.closeCalls == 1, "valid plugin was not closed during unload");
        Require(plugin.chatSubscriptionsAtClose == 0, "chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "inventory policy callback was still registered at dlclose");
        Require(plugin.itemReturnSubscriptionsAtClose == 0,
                "item-return callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0, "structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "owned callback survived plugin unload");
        Require(chatDispatcher.SubscriptionCount() == 0, "owned chat callback survived plugin unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "owned inventory policy callback survived plugin unload");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "owned item-return callback survived plugin unload");
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

    void TestFilteredProcessEventCallbackRejectedByDefault()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_filtered_denied");
        ConfigureEnvironment(root);

        FakePlugin plugin{.filename = "filtered_denied.so", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) == 0,
                "filtered ProcessEvent callback capability was enabled by default");
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) == 0,
                "ProcessEvent callback handle capability was enabled by default");
        manager.LoadPlugins((root / "plugins").string());

        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "filtered callback was registered without explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestFilteredProcessEventCallbackAllowedWithGate()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_filtered_allowed");
        ConfigureEnvironment(root);
        EnableFilteredProcessEventCallbacks(root);

        FakePlugin plugin{.filename = "filtered_allowed.so", .registerFilteredCallback = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) != 0,
                "filtered ProcessEvent callback capability was not enabled with env and marker gate");
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0,
                "ProcessEvent callback handle capability was not enabled with filtered gate");
        manager.LoadPlugins((root / "plugins").string());

        Require(Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "filtered callback was rejected with explicit gate");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS");
        fs::remove_all(root);
    }

    void TestFilteredProcessEventCallbackRejectedAfterGateRevoked()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_filtered_revoked");
        ConfigureEnvironment(root);
        EnableFilteredProcessEventCallbacks(root);
        const fs::path markerPath =
            root / "state" / "instances" / "arkserver" / "allow-filtered-process-event-callbacks";

        FakePlugin plugin{.filename = "filtered_revoked.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) != 0,
                "filtered callback capability was not enabled with env and marker gate");
        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "filtered-revoked plugin was not initialized");
        fs::remove(markerPath);

        const uint64_t registrationId =
            plugin.capturedApi.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                plugin.initOwnerToken,
                42,
                FakeCallback);

        Require(registrationId == 0, "filtered callback registration succeeded after marker revocation");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "filtered callback was registered after marker revocation");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        unsetenv("OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS");
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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "invalid gameplay policy registrations left item-return subscriptions behind");

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
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "structure-only gameplay policy callback registered item-return dispatcher");

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
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy unregister left inventory dispatcher behind");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy unregister left item-return dispatcher behind");

        const uint64_t itemOnlyRegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                FakeGameplayPolicyEventCallback,
                &plugin);
        Require(itemOnlyRegistrationId != 0,
                "owner-token item-return gameplay policy registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "item-return-only gameplay policy callback registered structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "item-return-only gameplay policy callback registered inventory dispatcher");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 1,
                "item-return-only gameplay policy callback did not register item-return dispatcher");

        const std::vector<Obelisk::Core::ItemReturnScalarValue> itemOnlyScalars =
            MakeItemReturnScalars(true);
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().Dispatch(
                    MakeItemReturnEvent(
                        Obelisk::Core::ItemReturnEventKind::AllowEquipItem,
                        itemOnlyScalars)) == 1,
                "item-return-only gameplay policy callback did not receive item return dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                "item-return-only gameplay policy event kind was not mapped");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken(
                    plugin.initOwnerToken,
                    itemOnlyRegistrationId),
                "owner-token item-return gameplay policy unregister failed");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "item-return-only gameplay policy callback survived explicit unregister");
        plugin.gameplayPolicyEventCalls = 1;

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
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 1,
                "all gameplay policy callback did not register item-return dispatcher");

        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeSetVariantEvent(setVariantScalars)) == 1,
                "all-structures gameplay policy callback did not receive set variant dispatch");
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
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                "inventory use event kind was not mapped");
        Require((plugin.gameplayPolicyFieldMask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0,
                "inventory can-use did not expose copied ignore-cooldown flag");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) == 0,
                "inventory can-use copied wrong ignore-cooldown value");

        const std::vector<Obelisk::Core::ItemReturnScalarValue> allowEquipScalars =
            MakeItemReturnScalars(true);
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().Dispatch(
                    MakeItemReturnEvent(
                        Obelisk::Core::ItemReturnEventKind::AllowEquipItem,
                        allowEquipScalars)) == 1,
                "all gameplay policy callback did not receive allow-equip item return dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                "allow-equip item return event kind was not mapped");
        Require(plugin.gameplayPolicyResourceKind ==
                    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                "allow-equip item return resource kind was not inventory item");
        Require((plugin.gameplayPolicyFlags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0,
                "allow-equip item return event was not marked inventory-backed");
        Require(plugin.gameplayPolicyFieldMask == OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "allow-equip item return exposed fields beyond return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0,
                "allow-equip item return copied wrong return value");

        const std::vector<Obelisk::Core::ItemReturnScalarValue> canRepairScalars =
            MakeItemReturnScalars(false);
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().Dispatch(
                    MakeItemReturnEvent(
                        Obelisk::Core::ItemReturnEventKind::CanRepair,
                        canRepairScalars)) == 1,
                "all gameplay policy callback did not receive can-repair item return dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
                "can-repair item return event kind was not mapped");
        Require(plugin.gameplayPolicyFieldMask == OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "can-repair item return exposed fields beyond return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) == 0,
                "can-repair item return copied wrong return value");

        const std::vector<Obelisk::Core::ItemReturnScalarValue> useOntoScalars =
            MakeItemReturnScalars(true);
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().Dispatch(
                    MakeItemReturnEvent(
                        Obelisk::Core::ItemReturnEventKind::UseItemOntoItem,
                        useOntoScalars)) == 1,
                "all gameplay policy callback did not receive use-item-onto-item return dispatch");
        Require(plugin.gameplayPolicyEventKind ==
                    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                "use-item-onto-item return event kind was not mapped");
        Require(plugin.gameplayPolicyFieldMask == OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "use-item-onto-item return exposed fields beyond return value");
        Require((plugin.gameplayPolicyBoolValues &
                    (OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                     OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN)) == 0,
                "use-item-onto-item return leaked inventory policy-only boolean fields");

        manager.UnloadAll();

        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy callback survived plugin unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy inventory callback survived plugin unload");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "owner-token gameplay policy item-return callback survived plugin unload");
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

        const std::string sourceMessage = "!ping";
        const Obelisk::Core::ChatMessageView message{
            .Message = sourceMessage,
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
        Require(plugin.chatMessageReserved0 == 0,
                "chat message reserved0 was not zeroed");
        Require((plugin.chatMessageFlags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0,
                "chat message event was not marked copied-payload");
        Require(plugin.chatMessageSequence != 0,
                "chat message event sequence was zero");
        Require(plugin.chatMessageText == "!ping",
                "chat message event copied wrong text");
        Require(plugin.chatMessageData != sourceMessage.data(),
                "chat message event exposed the dispatcher input buffer");

        Obelisk::Core::PluginManager::SetNextChatMessageSequenceForTesting(
            std::numeric_limits<uint64_t>::max());
        Require(chatDispatcher.Dispatch(message) == 1,
                "chat message callback did not dispatch at sequence wrap boundary");
        Require(plugin.chatMessageSequence == std::numeric_limits<uint64_t>::max(),
                "chat message event did not expose max sequence before wrap");
        Require(chatDispatcher.Dispatch(message) == 1,
                "chat message callback did not dispatch after sequence wrap");
        Require(plugin.chatMessageSequence == 1,
                "chat message event sequence did not skip zero after wrap");

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

    void TestOwnerTokenTimerRegistrationCanUnregisterAndUnload()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_owner_token_timer");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "owner_token_timer_a.so",
            .pluginId = "owner_token_timer_a",
            .captureApi = true,
        };
        FakePlugin otherPlugin{
            .filename = "owner_token_timer_b.so",
            .pluginId = "owner_token_timer_b",
        };
        FakeLoader loader;
        loader.Add(plugin);
        loader.Add(otherPlugin);
        TouchPlugin(root, plugin.filename);
        TouchPlugin(root, otherPlugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");
        WritePluginConfig(root, otherPlugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_TIMERS) != 0,
                "timer capability was not advertised");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "owner-token timer plugin was not initialized");
        Require(otherPlugin.initCalls == 1, "second owner-token timer plugin was not initialized");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle != nullptr,
                "timer registration function was not exposed");
        Require(plugin.capturedApi.UnregisterTimerWithOwnerToken != nullptr,
                "timer unregister function was not exposed");

        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
                    plugin.initOwnerToken + 1000,
                    10,
                    0,
                    0,
                    FakeTimerCallback,
                    &plugin) == 0,
                "invalid owner token registered a timer");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    10,
                    0,
                    0,
                    nullptr,
                    &plugin) == 0,
                "null timer callback was registered");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    0,
                    0,
                    0,
                    FakeTimerCallback,
                    &plugin) == 0,
                "zero-delay timer was registered");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    10,
                    0,
                    OBELISK_TIMER_FLAG_REPEATING,
                    FakeTimerCallback,
                    &plugin) == 0,
                "repeating timer with zero interval was registered");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    10,
                    0,
                    OBELISK_TIMER_FLAG_REPEATING << 1,
                    FakeTimerCallback,
                    &plugin) == 0,
                "timer with reserved flags was registered");

        const uint64_t timerId = plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
            plugin.initOwnerToken,
            1000,
            0,
            0,
            FakeTimerCallback,
            &plugin);
        Require(timerId != 0, "owner-token timer registration returned zero");
        Require(!plugin.capturedApi.UnregisterTimerWithOwnerToken(otherPlugin.initOwnerToken, timerId),
                "wrong owner token unregistered timer");
        Require(plugin.capturedApi.UnregisterTimerWithOwnerToken(plugin.initOwnerToken, timerId),
                "timer unregister failed");
        Require(!plugin.capturedApi.UnregisterTimerWithOwnerToken(plugin.initOwnerToken, timerId),
                "timer unregister succeeded twice");
        Require(!plugin.capturedApi.UnregisterTimerWithOwnerToken(plugin.initOwnerToken, 0),
                "zero timer handle unregistered timer");

        const uint64_t unloadTimerId = plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
            plugin.initOwnerToken,
            1000,
            0,
            0,
            FakeTimerCallback,
            &plugin);
        Require(unloadTimerId != 0, "timer could not re-register before unload");
        manager.UnloadAll();
        Require(Obelisk::Core::TimerManager::Get().UnregisterCallbacksForOwner(plugin.owner) == 0,
                "timer survived plugin unload");
        Require(plugin.timerEventCalls == 0, "long-delay timer fired before unload cleanup");

        CleanupPlugin(plugin);
        CleanupPlugin(otherPlugin);
        fs::remove_all(root);
    }

    void TestPublicRepeatingTimerFiresAndStopsAfterUnregister()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_repeating_timer_unregister");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "repeating_timer_unregister.so",
            .pluginId = "repeating_timer_unregister",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "repeating timer plugin was not initialized");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle != nullptr,
                "timer registration function was not exposed");
        Require(plugin.capturedApi.UnregisterTimerWithOwnerToken != nullptr,
                "timer unregister function was not exposed");

        TimerFenceState state;
        const uint64_t timerId = plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
            plugin.initOwnerToken,
            1,
            1,
            OBELISK_TIMER_FLAG_REPEATING,
            CountingTimerCallback,
            &state);
        Require(timerId != 0, "public repeating timer registration returned zero");

        int callsAtUnregister = 0;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.Calls >= 2;
                    }),
                    "public repeating timer did not fire twice");
            Require(state.LastTimerId == timerId,
                    "public repeating timer callback received wrong timer handle");
            callsAtUnregister = state.Calls;
        }

        Require(plugin.capturedApi.UnregisterTimerWithOwnerToken(plugin.initOwnerToken, timerId),
                "public repeating timer unregister failed");

        bool firedAfterUnregister = false;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            firedAfterUnregister = state.Cv.wait_for(lock, std::chrono::milliseconds(100), [&state, callsAtUnregister]() {
                return state.Calls > callsAtUnregister;
            });
        }
        Require(!firedAfterUnregister, "public repeating timer fired after unregister returned");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestUnloadAllWaitsForInFlightPluginTimerBeforeClose()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_timer_unload_in_flight");
        ConfigureEnvironment(root);

        TimerFenceState state;
        FakePlugin plugin{
            .filename = "timer_unload_in_flight.so",
            .pluginId = "timer_unload_in_flight",
            .captureApi = true,
            .timerFence = &state,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "timer unload fence plugin was not initialized");
        Require(plugin.capturedApi.RegisterTimerWithOwnerTokenHandle != nullptr,
                "timer registration function was not exposed");

        const uint64_t timerId = plugin.capturedApi.RegisterTimerWithOwnerTokenHandle(
            plugin.initOwnerToken,
            1,
            0,
            0,
            BlockingTimerCallback,
            &state);
        Require(timerId != 0, "blocking plugin-owned timer registration returned zero");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.Calls == 1;
                    }),
                    "blocking plugin-owned timer callback did not enter");
            Require(state.LastTimerId == timerId,
                    "blocking plugin-owned timer callback received wrong timer handle");
        }

        std::thread unloadThread([&]() {
            manager.UnloadAll();
            {
                std::lock_guard<std::mutex> lock(state.Mutex);
                state.UnloadReturned = true;
            }
            state.Cv.notify_all();
        });

        bool shutdownEntered = false;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            shutdownEntered = state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                return state.ShutdownEntered;
            });
        }

        if (!shutdownEntered)
        {
            {
                std::lock_guard<std::mutex> lock(state.Mutex);
                state.Release = true;
            }
            state.Cv.notify_all();
            unloadThread.join();
            Require(false, "UnloadAll did not reach plugin shutdown while timer callback was in flight");
        }

        bool closedWhileCallbackInFlight = false;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            closedWhileCallbackInFlight =
                state.Cv.wait_for(lock, std::chrono::milliseconds(100), [&state]() {
                    return state.CloseEntered || state.UnloadReturned;
                });
            state.Release = true;
        }
        state.Cv.notify_all();

        bool callbackCompleted = false;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            callbackCompleted = state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                return state.Completed == 1;
            });
        }

        unloadThread.join();

        Require(!closedWhileCallbackInFlight,
                "UnloadAll closed plugin while plugin-owned timer callback was in flight");
        Require(callbackCompleted, "plugin-owned timer callback did not complete after release");
        Require(plugin.closeCalls == 1, "timer unload fence plugin was not closed once");
        Require(Obelisk::Core::TimerManager::Get().UnregisterCallbacksForOwner(plugin.owner) == 0,
                "plugin-owned timer survived unload after in-flight callback completed");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestTimerCallbackCleansOnInitFailure()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_timer_init_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "timer_init_fail.so",
            .initResult = false,
            .registerTimerCallback = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "timer init-fail plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "timer init-fail plugin shutdown was not called");
        Require(plugin.closeCalls == 1, "timer init-fail plugin was not closed");
        Require(plugin.timerRegistrationId != 0, "timer was not registered before init failure");
        Require(Obelisk::Core::TimerManager::Get().UnregisterCallbacksForOwner(plugin.owner) == 0,
                "timer survived plugin init failure");
        Require(plugin.timerEventCalls == 0, "long-delay timer fired before init-failure cleanup");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestChatMessageRegistrationRejectedWhenCapabilityWasNotAdvertised()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_chat_message_capability_snapshot");
        ConfigureEnvironment(root);
        fs::create_directories(root / "state" / "instances" / "arkserver");

        FakePlugin plugin{
            .filename = "chat_capability_snapshot.so",
            .pluginId = "chat_capability_snapshot",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CHAT_EVENTS) == 0,
                "chat message capability was advertised before the gate was enabled");
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "chat capability snapshot plugin was not initialized");
        Require((plugin.capturedApi.capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) == 0,
                "plugin captured chat capability despite disabled constructor-time gate");

        setenv("OBELISK_ENABLE_CHAT_EVENTS", "1", 1);
        {
            std::ofstream marker(root / "state" / "instances" / "arkserver" / "enable-chat-events");
            Require(marker.is_open(), "failed to create chat events marker");
        }

        Require(plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    FakeChatMessageEventCallback,
                    &plugin) == 0,
                "chat message callback registered after dynamic gate enabled without advertised capability");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback subscription was created without advertised capability");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestChatMessageCallbackExceptionDoesNotEscapeDispatch()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_chat_message_callback_throw");
        ConfigureEnvironment(root);
        setenv("OBELISK_ENABLE_CHAT_EVENTS", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        {
            std::ofstream marker(root / "state" / "instances" / "arkserver" / "enable-chat-events");
            Require(marker.is_open(), "failed to create chat events marker");
        }

        FakePlugin plugin{
            .filename = "chat_message_callback_throw.so",
            .pluginId = "chat_message_callback_throw",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "throwing chat message plugin was not initialized");

        int throwingCallCount = 0;
        const uint64_t registrationId =
            plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                ThrowingChatMessageEventCallback,
                &throwingCallCount);
        Require(registrationId != 0, "throwing chat message callback could not register");

        const Obelisk::Core::ChatMessageView message{
            .Message = "!throw",
            .SenderName = "ignored",
            .SenderPlatformId = "ignored",
            .SendMode = Obelisk::Core::ChatSendMode::Global,
            .SenderNameIndex = 777,
        };
        Require(chatDispatcher.Dispatch(message) == 1,
                "throwing chat message callback was not counted as handled");
        Require(throwingCallCount == 1, "throwing chat message callback was not invoked once");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "throwing chat message callback was removed during dispatch");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestChatMessageRegistrationUsesOwnerCapabilitySnapshotAcrossManagers()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_chat_message_cross_manager_capability_snapshot");
        ConfigureEnvironment(root);
        fs::create_directories(root / "state" / "instances" / "arkserver");

        FakePlugin pluginA{
            .filename = "chat_cross_manager_a.so",
            .pluginId = "chat_cross_manager_a",
            .captureApi = true,
        };
        FakeLoader loaderA;
        loaderA.Add(pluginA);
        TouchPlugin(root, pluginA.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::ChatEventDispatcher dispatcherA;
        Obelisk::Core::PluginManager managerA(loaderA, dispatcherA);
        Require((managerA.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CHAT_EVENTS) == 0,
                "first manager advertised chat events before the gate was enabled");
        managerA.LoadPlugins((root / "plugins").string());
        Require(pluginA.initCalls == 1, "cross-manager plugin A was not initialized");
        Require((pluginA.capturedApi.capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) == 0,
                "plugin A captured chat capability despite disabled gate");

        setenv("OBELISK_ENABLE_CHAT_EVENTS", "1", 1);
        {
            std::ofstream marker(root / "state" / "instances" / "arkserver" / "enable-chat-events");
            Require(marker.is_open(), "failed to create chat events marker");
        }

        FakePlugin pluginB{
            .filename = "chat_cross_manager_b.so",
            .pluginId = "chat_cross_manager_b",
            .captureApi = true,
        };
        FakeLoader loaderB;
        loaderB.Add(pluginB);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::ChatEventDispatcher dispatcherB;
        Obelisk::Core::PluginManager managerB(loaderB, dispatcherB);
        Require((managerB.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0,
                "second manager did not advertise chat events after the gate was enabled");
        managerB.LoadPlugins((root / "plugins").string());
        Require(pluginB.initCalls == 1, "cross-manager plugin B was not initialized");
        Require((pluginB.capturedApi.capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0,
                "plugin B did not capture chat capability after gate enable");

        Require(pluginA.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                    pluginA.initOwnerToken,
                    FakeChatMessageEventCallback,
                    &pluginA) == 0,
                "plugin A registered chat after a later manager widened global capability");
        Require(dispatcherA.SubscriptionCount() == 0,
                "plugin A registration created a subscription in its original dispatcher");
        Require(dispatcherB.SubscriptionCount() == 0,
                "plugin A registration leaked into a later manager dispatcher");

        managerB.UnloadAll();
        managerA.UnloadAll();
        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
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

    void TestGameplayPolicyCallbackExceptionDoesNotEscapeDispatch()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_callback_throw");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_callback_throw.so",
            .pluginId = "gameplay_policy_callback_throw",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "throwing gameplay policy plugin was not initialized");

        int throwingCallCount = 0;
        const uint64_t registrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                ThrowingGameplayPolicyEventCallback,
                &throwingCallCount);
        Require(registrationId != 0, "throwing gameplay policy callback could not register");

        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeStructureScalars();
        Require(Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeStructureEvent(scalars)) == 1,
                "throwing gameplay policy callback was not counted as handled");
        Require(throwingCallCount == 1, "throwing gameplay policy callback was not invoked once");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "throwing gameplay policy callback was removed during dispatch");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestGameplayPolicyCrossDispatcherSelfUnregisterDoesNotDeadlock()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_cross_dispatcher_unregister");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_cross_dispatcher_unregister.so",
            .pluginId = "gameplay_policy_cross_dispatcher_unregister",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "cross-dispatcher plugin was not initialized");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy registration function was not exposed");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken != nullptr,
                "gameplay policy unregister function was not exposed");

        ConcurrentGameplayPolicyUnregisterState state;
        state.Api = &plugin.capturedApi;
        state.OwnerToken = plugin.initOwnerToken;
        state.RegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                ConcurrentGameplayPolicyUnregisterCallback,
                &state);
        Require(state.RegistrationId != 0, "cross-dispatcher gameplay policy registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-dispatcher callback was not bridged into structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-dispatcher callback was not bridged into inventory dispatcher");

        const std::vector<Obelisk::Core::StructureScalarValue> structureScalars = MakeStructureScalars();
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryScalars =
            MakeInventoryCanUseScalars();
        std::atomic<size_t> structureDispatches{0};
        std::atomic<size_t> inventoryDispatches{0};

        std::thread structureThread([&]() {
            structureDispatches.store(
                Obelisk::Core::StructureEventDispatcher::Get().Dispatch(MakeStructureEvent(structureScalars)),
                std::memory_order_release);
        });
        std::thread inventoryThread([&]() {
            inventoryDispatches.store(
                Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.Entered == 2;
                    }),
                    "both gameplay policy dispatcher callbacks did not enter");
            state.Release = true;
        }
        state.Cv.notify_all();

        bool completed = false;
        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            completed = state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                return state.Completed == 2;
            });
        }

        if (!completed)
        {
            structureThread.detach();
            inventoryThread.detach();
            Require(false, "cross-dispatcher gameplay policy unregister deadlocked");
        }

        structureThread.join();
        inventoryThread.join();

        Require(structureDispatches.load(std::memory_order_acquire) == 1,
                "structure dispatch did not complete exactly one callback");
        Require(inventoryDispatches.load(std::memory_order_acquire) == 1,
                "inventory dispatch did not complete exactly one callback");
        Require(state.SawStructure, "cross-dispatcher test did not observe structure event");
        Require(state.SawInventory, "cross-dispatcher test did not observe inventory event");
        Require(state.SuccessfulUnregisters == 1,
                "cross-dispatcher self-unregister should succeed exactly once");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "cross-dispatcher structure callback survived unregister");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "cross-dispatcher inventory callback survived unregister");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestCrossFamilyUnregisterSuppressesWaitForOtherFamilyDispatch()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_cross_family_fence");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_cross_family_fence.so",
            .pluginId = "gameplay_policy_cross_family_fence",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "cross-family fence plugin was not initialized");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy registration function was not exposed");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken != nullptr,
                "gameplay policy unregister function was not exposed");

        CrossFamilyFenceState state;
        state.Api = &plugin.capturedApi;
        state.OwnerToken = plugin.initOwnerToken;
        state.RegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                GameplayPolicyCrossFamilyFenceCallback,
                &state);
        Require(state.RegistrationId != 0, "cross-family fence registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-family fence callback was not bridged into structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-family fence callback was not bridged into inventory dispatcher");

        const std::vector<Obelisk::Core::StructureScalarValue> structureScalars = MakeStructureScalars();
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryScalars =
            MakeInventoryCanUseScalars();
        std::atomic<size_t> structureDispatches{0};
        std::atomic<size_t> inventoryDispatches{0};

        std::thread inventoryThread([&]() {
            inventoryDispatches.store(
                Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.InventoryEntered;
                    }),
                    "inventory fence callback did not enter");
        }

        std::thread structureThread([&]() {
            structureDispatches.store(
                Obelisk::Core::StructureEventDispatcher::Get().Dispatch(
                    MakeStructureEvent(structureScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.StructureEntered;
                    }),
                    "structure fence callback did not enter");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.StructureUnregisterReturned,
                    "cross-family unregister waited for the other family dispatch from a gameplay callback");
        }

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseInventory = true;
        }
        state.Cv.notify_all();

        inventoryThread.join();
        structureThread.join();

        Require(inventoryDispatches.load(std::memory_order_acquire) == 1,
                "inventory fence dispatch did not complete exactly one callback");
        Require(structureDispatches.load(std::memory_order_acquire) == 1,
                "structure fence dispatch did not complete exactly one callback");
        Require(state.InventoryCalls == 1, "inventory fence callback call count mismatch");
        Require(state.StructureCalls == 1, "structure fence callback call count mismatch");
        Require(state.StructureUnregisterResult,
                "cross-family unregister did not remove inventory callback");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory fence callback survived cross-family unregister");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure fence callback survived cross-family unregister");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestCrossFamilyUnregisterSuppressesWaitForStructureDispatch()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_cross_family_structure_fence");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "gameplay_policy_cross_family_structure_fence.so",
            .pluginId = "gameplay_policy_cross_family_structure_fence",
            .captureApi = true,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "cross-family structure fence plugin was not initialized");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy registration function was not exposed");
        Require(plugin.capturedApi.UnregisterGameplayPolicyEventWithOwnerToken != nullptr,
                "gameplay policy unregister function was not exposed");

        CrossFamilyFenceState state;
        state.Api = &plugin.capturedApi;
        state.OwnerToken = plugin.initOwnerToken;
        state.BlockStructure = true;
        state.RegistrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                GameplayPolicyCrossFamilyFenceCallback,
                &state);
        Require(state.RegistrationId != 0, "cross-family structure fence registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-family structure fence callback was not bridged into structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "cross-family structure fence callback was not bridged into inventory dispatcher");

        const std::vector<Obelisk::Core::StructureScalarValue> structureScalars = MakeStructureScalars();
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryScalars =
            MakeInventoryCanUseScalars();
        std::atomic<size_t> structureDispatches{0};
        std::atomic<size_t> inventoryDispatches{0};

        std::thread structureThread([&]() {
            structureDispatches.store(
                Obelisk::Core::StructureEventDispatcher::Get().Dispatch(
                    MakeStructureEvent(structureScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.StructureEntered;
                    }),
                    "structure fence callback did not enter");
        }

        std::thread inventoryThread([&]() {
            inventoryDispatches.store(
                Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.InventoryEntered;
                    }),
                    "inventory fence callback did not enter");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.InventoryUnregisterReturned,
                    "cross-family unregister waited for the structure dispatch from a gameplay callback");
        }

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseStructure = true;
        }
        state.Cv.notify_all();

        structureThread.join();
        inventoryThread.join();

        Require(structureDispatches.load(std::memory_order_acquire) == 1,
                "structure fence dispatch did not complete exactly one callback");
        Require(inventoryDispatches.load(std::memory_order_acquire) == 1,
                "inventory fence dispatch did not complete exactly one callback");
        Require(state.StructureCalls == 1, "structure fence callback call count mismatch");
        Require(state.InventoryCalls == 1, "inventory fence callback call count mismatch");
        Require(state.InventoryUnregisterResult,
                "cross-family unregister did not remove structure callback");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure fence callback survived cross-family unregister");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory fence callback survived cross-family unregister");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestUnloadAllWaitsForCrossFamilyGameplayPolicyDispatchBeforeClose()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_gameplay_policy_shutdown_cross_family_fence");
        ConfigureEnvironment(root);

        std::atomic<bool> closeObserved{false};
        FakePlugin plugin{
            .filename = "gameplay_policy_shutdown_cross_family_fence.so",
            .pluginId = "gameplay_policy_shutdown_cross_family_fence",
            .captureApi = true,
            .closeObserved = &closeObserved,
        };
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "shutdown cross-family plugin was not initialized");
        Require(plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle != nullptr,
                "gameplay policy registration function was not exposed");

        ShutdownCrossFamilyFenceState state;
        const uint64_t registrationId =
            plugin.capturedApi.RegisterGameplayPolicyEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                GameplayPolicyShutdownCrossFamilyFenceCallback,
                &state);
        Require(registrationId != 0, "shutdown cross-family registration returned zero");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 1,
                "shutdown cross-family callback was not bridged into structure dispatcher");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 1,
                "shutdown cross-family callback was not bridged into inventory dispatcher");

        const std::vector<Obelisk::Core::StructureScalarValue> structureScalars = MakeStructureScalars();
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> inventoryScalars =
            MakeInventoryCanUseScalars();
        std::atomic<size_t> structureDispatches{0};
        std::atomic<size_t> inventoryDispatches{0};
        std::atomic<bool> unloadReturned{false};

        std::thread structureThread([&]() {
            structureDispatches.store(
                Obelisk::Core::StructureEventDispatcher::Get().Dispatch(
                    MakeStructureEvent(structureScalars)),
                std::memory_order_release);
        });
        std::thread inventoryThread([&]() {
            inventoryDispatches.store(
                Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(
                    MakeInventoryCanUseEvent(inventoryScalars)),
                std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.StructureEntered && state.InventoryEntered;
                    }),
                    "shutdown cross-family callbacks did not both enter");
        }

        std::thread unloadThread([&]() {
            manager.UnloadAll();
            unloadReturned.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!closeObserved.load(std::memory_order_acquire),
                "plugin was closed while cross-family gameplay policy callbacks were in flight");
        Require(!unloadReturned.load(std::memory_order_acquire),
                "UnloadAll returned while cross-family gameplay policy callbacks were in flight");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseStructure = true;
        }
        state.Cv.notify_all();
        structureThread.join();

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!closeObserved.load(std::memory_order_acquire),
                "plugin was closed while the inventory gameplay policy callback was still in flight");
        Require(!unloadReturned.load(std::memory_order_acquire),
                "UnloadAll returned while the inventory gameplay policy callback was still in flight");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseInventory = true;
        }
        state.Cv.notify_all();

        inventoryThread.join();
        unloadThread.join();

        Require(structureDispatches.load(std::memory_order_acquire) == 1,
                "shutdown cross-family structure dispatch did not complete exactly one callback");
        Require(inventoryDispatches.load(std::memory_order_acquire) == 1,
                "shutdown cross-family inventory dispatch did not complete exactly one callback");
        Require(state.StructureCalls == 1, "shutdown cross-family structure callback call count mismatch");
        Require(state.InventoryCalls == 1, "shutdown cross-family inventory callback call count mismatch");
        Require(closeObserved.load(std::memory_order_acquire),
                "plugin was not closed after cross-family callbacks completed");
        Require(plugin.closeCalls == 1, "shutdown cross-family plugin was not closed once");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown cross-family structure callback survived unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown cross-family inventory callback survived unload");

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
        Require(descriptor.reserved0 == 0,
                "resource descriptor reserved0 was not zeroed");
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
        Require(descriptor.reserved0 == 0,
                "inventory resource descriptor reserved0 was not zeroed");
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
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.allow_equip_check",
                "Inventory Item Allow Equip Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.can_repair_check",
                "Inventory Item Can Repair Check",
            },
            {
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.use_onto_item_check",
                "Inventory Item Use Onto Item Check",
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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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
        EnableFilteredProcessEventCallbacks(root);

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

    void TestGlobalProcessEventRegistrationUsesOwnerCapabilitySnapshotAcrossManagers()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_global_cross_manager_capability_snapshot");
        ConfigureEnvironment(root);
        fs::create_directories(root / "state" / "instances" / "arkserver");

        FakePlugin pluginA{
            .filename = "global_cross_manager_a.so",
            .pluginId = "global_cross_manager_a",
            .captureApi = true,
        };
        FakeLoader loaderA;
        loaderA.Add(pluginA);
        TouchPlugin(root, pluginA.filename);
        WritePluginConfig(root, pluginA.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager managerA(loaderA);
        Require((managerA.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) == 0,
                "first manager advertised global callbacks before the gate was enabled");
        managerA.LoadPlugins((root / "plugins").string());
        Require(pluginA.initCalls == 1, "global cross-manager plugin A was not initialized");
        Require((pluginA.capturedApi.capabilities & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) == 0,
                "plugin A captured global callback capability despite disabled gate");

        setenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS", "1", 1);
        const fs::path markerPath =
            root / "state" / "instances" / "arkserver" / "allow-global-process-event-callbacks";
        std::ofstream marker(markerPath);
        Require(marker.is_open(), "failed to create global callback marker");
        marker.close();

        FakePlugin pluginB{
            .filename = "global_cross_manager_b.so",
            .pluginId = "global_cross_manager_b",
            .captureApi = true,
        };
        FakeLoader loaderB;
        loaderB.Add(pluginB);
        TouchPlugin(root, pluginB.filename);
        WritePluginConfig(root, pluginB.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager managerB(loaderB);
        Require((managerB.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0,
                "second manager did not advertise global callbacks after the gate was enabled");
        managerB.LoadPlugins((root / "plugins").string());
        Require(pluginB.initCalls == 1, "global cross-manager plugin B was not initialized");
        Require((pluginB.capturedApi.capabilities & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0,
                "plugin B did not capture global callback capability after gate enable");

        const uint64_t registrationId =
            pluginA.capturedApi.RegisterPreProcessEventWithOwnerTokenHandle(
                pluginA.initOwnerToken,
                FakeCallback);
        Require(registrationId == 0,
                "plugin A registered a global callback after a later manager widened global capability");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "plugin A global callback registered after a later manager widened capability");

        managerB.UnloadAll();
        managerA.UnloadAll();
        CleanupPlugin(pluginA);
        CleanupPlugin(pluginB);
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

    void TestCallProcessEventSuppressesOriginalException()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_call_process_event_exception");
        ConfigureEnvironment(root);
        setenv("OBELISK_ALLOW_CALL_PROCESS_EVENT", "1", 1);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        std::ofstream marker(root / "state" / "instances" / "arkserver" / "allow-call-process-event");
        Require(marker.is_open(), "failed to create CallProcessEvent marker");
        marker.close();
        Obelisk::Hooks::ResetProcessEventCallOriginalCountForTesting();
        Obelisk::Hooks::SetProcessEventCallOriginalThrowForTesting(true);

        FakePlugin plugin{.filename = "call_process_event_exception.so", .captureApi = true};
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader);
        Require((manager.ApiCapabilitiesForTesting() & OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) != 0,
                "CallProcessEvent capability was not enabled with env and marker gate");

        manager.LoadPlugins((root / "plugins").string());
        Require(plugin.initCalls == 1, "CallProcessEvent-exception plugin was not initialized");

        try
        {
            plugin.capturedApi.CallProcessEvent(
                reinterpret_cast<void*>(0x1),
                reinterpret_cast<void*>(0x2),
                reinterpret_cast<void*>(0x3));
        }
        catch (...)
        {
            Require(false, "CallProcessEvent let a trampoline exception escape the C ABI boundary");
        }

        Require(Obelisk::Hooks::ProcessEventCallOriginalCountForTesting() == 1,
                "CallProcessEvent did not attempt original trampoline before suppressing exception");

        manager.UnloadAll();
        CleanupPlugin(plugin);
        Obelisk::Hooks::SetProcessEventCallOriginalThrowForTesting(false);
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
        EnableFilteredProcessEventCallbacks(root);

        FakePlugin plugin{.filename = "init_fail.so", .initResult = false, .registerFilteredCallback = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerItemReturnCallback = true;
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
        Require(plugin.itemReturnSubscriptionsAtShutdown == 1,
                "init-failing plugin item-return callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "init-failing plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "init-failing plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "failed plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "failed plugin inventory policy callback was still registered at dlclose");
        Require(plugin.itemReturnSubscriptionsAtClose == 0,
                "failed plugin item-return callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "failed plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "callback registered by failed plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by failed plugin survived load failure");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory policy callback registered by failed plugin survived load failure");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "item-return callback registered by failed plugin survived load failure");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "structure callback registered by failed plugin survived load failure");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitExceptionCleansCallbacksAndCloses()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_init_throw");
        ConfigureEnvironment(root);
        EnableFilteredProcessEventCallbacks(root);

        FakePlugin plugin{
            .filename = "init_throw.so",
            .registerFilteredCallback = true,
            .throwInInitAfterCallbacks = true,
        };
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.registerChatCallback = true;
        plugin.registerInventoryPolicyCallback = true;
        plugin.registerItemReturnCallback = true;
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
        Require(plugin.itemReturnSubscriptionsAtShutdown == 1,
                "init-throw plugin item-return callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "init-throw plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "init-throw plugin was not closed");
        Require(plugin.chatSubscriptionsAtClose == 0, "init-throw plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "init-throw plugin inventory policy callback was still registered at dlclose");
        Require(plugin.itemReturnSubscriptionsAtClose == 0,
                "init-throw plugin item-return callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "init-throw plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "ProcessEvent callback registered by throwing plugin survived load failure");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "chat callback registered by throwing plugin survived load failure");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "inventory policy callback registered by throwing plugin survived load failure");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "item-return callback registered by throwing plugin survived load failure");
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
        EnableFilteredProcessEventCallbacks(root);

        FakePlugin plugin{
            .filename = "shutdown_throw.so",
            .registerFilteredCallback = true,
            .registerOwnerTokenFromInitThread = true,
            .registerChatCallback = true,
            .registerInventoryPolicyCallback = true,
            .registerItemReturnCallback = true,
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
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 1,
                "shutdown-throw plugin item-return callback was not registered");
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
        Require(plugin.itemReturnSubscriptionsAtShutdown == 1,
                "shutdown-throw plugin item-return callback was not present during shutdown");
        Require(plugin.structureSubscriptionsAtShutdown == 1,
                "shutdown-throw plugin structure callback was not present during shutdown");
        Require(plugin.closeCalls == 1, "shutdown-throw plugin was not closed once");
        Require(plugin.chatSubscriptionsAtClose == 0,
                "shutdown-throw plugin chat callback was still registered at dlclose");
        Require(plugin.inventoryPolicySubscriptionsAtClose == 0,
                "shutdown-throw plugin inventory policy callback was still registered at dlclose");
        Require(plugin.itemReturnSubscriptionsAtClose == 0,
                "shutdown-throw plugin item-return callback was still registered at dlclose");
        Require(plugin.structureSubscriptionsAtClose == 0,
                "shutdown-throw plugin structure callback was still registered at dlclose");
        Require(!Obelisk::Core::EventManager::Get().HasPreProcessEventCallbacks(),
                "shutdown-throw plugin ProcessEvent callbacks survived unload");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "shutdown-throw plugin chat callback survived unload");
        Require(Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown-throw plugin inventory policy callback survived unload");
        Require(Obelisk::Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown-throw plugin item-return callback survived unload");
        Require(Obelisk::Core::StructureEventDispatcher::Get().SubscriptionCount() == 0,
                "shutdown-throw plugin structure callback survived unload");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestUnloadAllRetainsPluginWhenCallbackCleanupFails()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_cleanup_fail");
        ConfigureEnvironment(root);
        fs::create_directories(root / "state" / "instances" / "arkserver");
        setenv("OBELISK_ENABLE_CHAT_EVENTS", "1", 1);
        {
            std::ofstream marker(root / "state" / "instances" / "arkserver" / "enable-chat-events");
            Require(marker.is_open(), "failed to create chat events marker");
        }

        FakePlugin plugin{.filename = "cleanup_fail.so", .registerChatCallback = true, .captureApi = true};
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "cleanup-fail plugin was not initialized");
        Require(chatDispatcher.SubscriptionCount() == 1, "cleanup-fail plugin chat callback was not registered");
        const uint64_t ownerTokenRegistrationId =
            plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                plugin.initOwnerToken,
                FakeChatMessageEventCallback,
                &plugin);
        Require(ownerTokenRegistrationId != 0, "cleanup-fail plugin owner-token chat callback was not registered");
        Require(chatDispatcher.SubscriptionCount() == 2,
                "cleanup-fail plugin owner-token chat callback was not bridged");

        Obelisk::Core::SetPluginCallbackCleanupFailureForTesting(true);
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "cleanup-fail plugin shutdown was not called");
        Require(plugin.closeCalls == 0, "cleanup-fail plugin was closed despite failed callback cleanup");
        Require(chatDispatcher.SubscriptionCount() == 2,
                "cleanup-fail plugin callback was removed despite injected cleanup failure");
        Require(plugin.capturedApi.RegisterChatMessageEventWithOwnerTokenHandle(
                    plugin.initOwnerToken,
                    FakeChatMessageEventCallback,
                    &plugin) == 0,
                "cleanup-fail retained plugin accepted a new owner-token callback while unloading");

        Obelisk::Core::SetPluginCallbackCleanupFailureForTesting(false);
        Require(plugin.capturedApi.UnregisterChatMessageEventWithOwnerToken(
                    plugin.initOwnerToken,
                    ownerTokenRegistrationId),
                "cleanup-fail retained plugin owner-token unregister failed");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "cleanup-fail retained plugin owner-token unregister did not remove its callback");
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "cleanup-fail plugin shutdown was repeated after retained unload retry");
        Require(plugin.closeCalls == 1, "cleanup-fail plugin was not closed after cleanup retry");
        Require(plugin.chatSubscriptionsAtClose == 0, "cleanup-fail plugin chat callback was still registered at dlclose");
        Require(chatDispatcher.SubscriptionCount() == 0, "cleanup-fail plugin callback survived cleanup retry");

        CleanupPlugin(plugin);
        fs::remove_all(root);
    }

    void TestInitFailureRetainsPluginWhenCallbackCleanupFailsAndRetries()
    {
        const fs::path root = MakeTempRoot("obelisk_plugin_manager_init_cleanup_fail");
        ConfigureEnvironment(root);

        FakePlugin plugin{
            .filename = "init_cleanup_fail.so",
            .initResult = false,
            .registerChatCallback = true,
        };
        Obelisk::Core::ChatEventDispatcher chatDispatcher;
        plugin.chatDispatcher = &chatDispatcher;
        FakeLoader loader;
        loader.Add(plugin);
        TouchPlugin(root, plugin.filename);
        WritePluginConfig(root, plugin.pluginId, R"({"enabled":true,"instance_allowlist":["arkserver"]})");

        Obelisk::Core::PluginManager manager(loader, chatDispatcher);
        Obelisk::Core::SetPluginCallbackCleanupFailureForTesting(true);
        manager.LoadPlugins((root / "plugins").string());

        Require(plugin.initCalls == 1, "init-cleanup-fail plugin was not initialized");
        Require(plugin.shutdownCalls == 1, "init-cleanup-fail plugin shutdown was not called after init failure");
        Require(plugin.closeCalls == 0, "init-cleanup-fail plugin was closed despite failed callback cleanup");
        Require(chatDispatcher.SubscriptionCount() == 1,
                "init-cleanup-fail plugin callback was removed despite injected cleanup failure");

        Obelisk::Core::SetPluginCallbackCleanupFailureForTesting(false);
        manager.UnloadAll();

        Require(plugin.shutdownCalls == 1, "init-cleanup-fail plugin shutdown was repeated after cleanup retry");
        Require(plugin.closeCalls == 1, "init-cleanup-fail plugin was not closed after cleanup retry");
        Require(plugin.chatSubscriptionsAtClose == 0,
                "init-cleanup-fail plugin chat callback was still registered at dlclose");
        Require(chatDispatcher.SubscriptionCount() == 0,
                "init-cleanup-fail plugin callback survived cleanup retry");

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
        EnableFilteredProcessEventCallbacks(root);

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
    TestFilteredProcessEventCallbackRejectedByDefault();
    TestFilteredProcessEventCallbackAllowedWithGate();
    TestFilteredProcessEventCallbackRejectedAfterGateRevoked();
    TestPostInitUnownedCallbackRegistrationIsRejected();
    TestPostInitOwnerTokenCallbackRegistrationCleansOnUnload();
    TestOwnerTokenCallbackRegistrationFromInitThread();
    TestInitFailureCleansInitThreadOwnerTokenCallbackAndToken();
    TestInitExceptionCleansInitThreadOwnerTokenCallbackAndToken();
    TestOwnerTokenHandleRegistrationCanUnregister();
    TestOwnerTokenGameplayPolicyEventRegistrationCanUnregister();
    TestOwnerTokenChatMessageEventRegistrationCanUnregister();
    TestOwnerTokenTimerRegistrationCanUnregisterAndUnload();
    TestPublicRepeatingTimerFiresAndStopsAfterUnregister();
    TestUnloadAllWaitsForInFlightPluginTimerBeforeClose();
    TestTimerCallbackCleansOnInitFailure();
    TestChatMessageRegistrationRejectedWhenCapabilityWasNotAdvertised();
    TestChatMessageCallbackExceptionDoesNotEscapeDispatch();
    TestChatMessageRegistrationUsesOwnerCapabilitySnapshotAcrossManagers();
    TestGameplayPolicyCallbackCanSelfUnregisterDuringDispatch();
    TestGameplayPolicyCallbackExceptionDoesNotEscapeDispatch();
    TestGameplayPolicyCrossDispatcherSelfUnregisterDoesNotDeadlock();
    TestCrossFamilyUnregisterSuppressesWaitForOtherFamilyDispatch();
    TestCrossFamilyUnregisterSuppressesWaitForStructureDispatch();
    TestUnloadAllWaitsForCrossFamilyGameplayPolicyDispatchBeforeClose();
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
    TestGlobalProcessEventRegistrationUsesOwnerCapabilitySnapshotAcrossManagers();
    TestCallProcessEventRejectedByDefault();
    TestCallProcessEventAllowedWithGate();
    TestCallProcessEventRejectedAfterGateRevoked();
    TestCallProcessEventSuppressesOriginalException();
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
    TestUnloadAllRetainsPluginWhenCallbackCleanupFails();
    TestInitFailureRetainsPluginWhenCallbackCleanupFailsAndRetries();
    TestDuplicatePluginIdRejectsSecondPlugin();
    TestLoadPluginsSkipsAlreadyLoadedPluginId();

    Obelisk::Logger::Shutdown();
    fs::remove_all(logRoot);

    std::cout << "PluginManagerTests passed\n";
    return 0;
}
