#include "PluginManager.h"
#include "EventManager.h"
#include "InventoryPolicyEventDispatcher.h"
#include "PluginConfig.h"
#include "StructureEventDispatcher.h"
#include "hooks/ProcessEventHook.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include <dlfcn.h>
#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cstddef>
#include <cstdlib>
#include <exception>
#include <memory>
#include <mutex>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace fs = std::filesystem;

namespace Obelisk::Core
{
    namespace
    {
        thread_local void* g_CurrentPluginOwner = nullptr;
        std::atomic<uint64_t> g_ApiCapabilities{OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS};

        struct GameplayPolicyRegistration
        {
            void* Owner = nullptr;
            uint64_t StructureRegistrationId = 0;
            uint64_t InventoryRegistrationId = 0;
        };

        struct ChatMessageRegistration
        {
            void* Owner = nullptr;
            ChatEventDispatcher* Dispatcher = nullptr;
            uint64_t InternalRegistrationId = 0;
        };

        struct PluginOwnerApiState
        {
            uint64_t Capabilities = 0;
            ChatEventDispatcher* ChatDispatcher = nullptr;
        };

        std::mutex& PluginOwnerLifecycleMutex()
        {
            static auto* mutex = new std::mutex();
            return *mutex;
        }

        std::unordered_set<void*>& LoadedPluginOwners()
        {
            static auto* owners = new std::unordered_set<void*>();
            return *owners;
        }

        std::unordered_set<void*>& InitializingPluginOwners()
        {
            static auto* owners = new std::unordered_set<void*>();
            return *owners;
        }

        std::unordered_set<void*>& UnloadingPluginOwners()
        {
            static auto* owners = new std::unordered_set<void*>();
            return *owners;
        }

        std::atomic<uint64_t>& NextPluginOwnerToken()
        {
            static auto* token = new std::atomic<uint64_t>(1);
            return *token;
        }

        std::unordered_map<uint64_t, void*>& PluginOwnerTokens()
        {
            static auto* tokens = new std::unordered_map<uint64_t, void*>();
            return *tokens;
        }

        std::unordered_map<void*, PluginOwnerApiState>& PluginOwnerApiStates()
        {
            static auto* states = new std::unordered_map<void*, PluginOwnerApiState>();
            return *states;
        }

        std::mutex& GameplayPolicyRegistrationMutex()
        {
            static auto* mutex = new std::mutex();
            return *mutex;
        }

        uint64_t& NextGameplayPolicyRegistrationId()
        {
            static auto* id = new uint64_t(1);
            return *id;
        }

        std::unordered_map<uint64_t, GameplayPolicyRegistration>& GameplayPolicyRegistrations()
        {
            static auto* registrations = new std::unordered_map<uint64_t, GameplayPolicyRegistration>();
            return *registrations;
        }

        std::mutex& ChatMessageRegistrationMutex()
        {
            static auto* mutex = new std::mutex();
            return *mutex;
        }

        uint64_t& NextChatMessageRegistrationId()
        {
            static auto* id = new uint64_t(1);
            return *id;
        }

        std::atomic<uint64_t>& NextChatMessageSequence()
        {
            static auto* sequence = new std::atomic<uint64_t>(1);
            return *sequence;
        }

        uint64_t AllocateChatMessageSequence()
        {
            for (;;)
            {
                const uint64_t sequence = NextChatMessageSequence().fetch_add(1, std::memory_order_relaxed);
                if (sequence != 0)
                    return sequence;
            }
        }

        std::unordered_map<uint64_t, ChatMessageRegistration>& ChatMessageRegistrations()
        {
            static auto* registrations = new std::unordered_map<uint64_t, ChatMessageRegistration>();
            return *registrations;
        }

        using GetInfoFunc = bool(*)(ObeliskPluginMetadata*);
        using InitFunc = bool(*)(ObeliskApi*, const ObeliskPluginInitContext*);
        using ShutdownFunc = void(*)();

        class DlopenLibraryLoader final : public PluginManager::LibraryLoader
        {
        public:
            void* Open(const fs::path& path, std::string& error) override
            {
                dlerror();
                void* handle = dlopen(path.string().c_str(), RTLD_NOW | RTLD_LOCAL);
                if (!handle)
                    error = dlerror();
                return handle;
            }

            void* Resolve(void* handle, const char* symbolName, std::string& error) override
            {
                dlerror();
                void* symbol = dlsym(handle, symbolName);
                const char* symbolError = dlerror();
                if (symbolError || !symbol)
                    error = symbolError ? symbolError : "unknown dlsym error";
                return symbol;
            }

            void* GetSymbolOwner(void* handle, void* symbol) override
            {
                Dl_info symbolInfo{};
                if (dladdr(symbol, &symbolInfo) != 0 && symbolInfo.dli_fbase)
                    return symbolInfo.dli_fbase;
                return handle;
            }

            void Close(void* handle) override
            {
                dlclose(handle);
            }
        };

        DlopenLibraryLoader& DefaultLoader()
        {
            static DlopenLibraryLoader loader;
            return loader;
        }

        bool IsLoadedPluginOwnerLocked(void* owner)
        {
            if (!owner)
                return false;

            return LoadedPluginOwners().find(owner) != LoadedPluginOwners().end();
        }

        void AddLoadedPluginOwner(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            LoadedPluginOwners().insert(owner);
        }

        void RemoveLoadedPluginOwner(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            LoadedPluginOwners().erase(owner);
        }

        bool IsInitializingPluginOwnerLocked(void* owner)
        {
            if (!owner)
                return false;

            return InitializingPluginOwners().find(owner) != InitializingPluginOwners().end();
        }

        void AddInitializingPluginOwner(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            InitializingPluginOwners().insert(owner);
        }

        void RemoveInitializingPluginOwner(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            InitializingPluginOwners().erase(owner);
        }

        void MarkPluginOwnerUnloading(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            UnloadingPluginOwners().insert(owner);
        }

        void ClearPluginOwnerUnloading(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            UnloadingPluginOwners().erase(owner);
        }

        bool IsUnloadingPluginOwnerLocked(void* owner)
        {
            return owner && UnloadingPluginOwners().find(owner) != UnloadingPluginOwners().end();
        }

        uint64_t AddPluginOwnerToken(void* owner, uint64_t capabilities, ChatEventDispatcher* chatDispatcher)
        {
            if (!owner)
                return 0;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            uint64_t token = 0;
            do
            {
                token = NextPluginOwnerToken().load(std::memory_order_relaxed);
                uint64_t nextToken = token + 1;
                if (nextToken == 0)
                    nextToken = 1;
                NextPluginOwnerToken().store(nextToken, std::memory_order_relaxed);
            } while (token == 0 || PluginOwnerTokens().find(token) != PluginOwnerTokens().end());

            PluginOwnerTokens()[token] = owner;
            PluginOwnerApiStates()[owner] = PluginOwnerApiState{
                .Capabilities = capabilities,
                .ChatDispatcher = chatDispatcher,
            };
            return token;
        }

        void RemovePluginOwnerToken(uint64_t token)
        {
            if (token == 0)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            const auto it = PluginOwnerTokens().find(token);
            if (it != PluginOwnerTokens().end())
            {
                PluginOwnerApiStates().erase(it->second);
                PluginOwnerTokens().erase(it);
            }
        }

        bool PluginOwnerHasCapabilityLocked(void* owner, uint64_t capability)
        {
            const auto it = PluginOwnerApiStates().find(owner);
            return it != PluginOwnerApiStates().end() && (it->second.Capabilities & capability) != 0;
        }

        ChatEventDispatcher* PluginOwnerChatDispatcherLocked(void* owner)
        {
            const auto it = PluginOwnerApiStates().find(owner);
            if (it == PluginOwnerApiStates().end())
                return nullptr;
            return it->second.ChatDispatcher;
        }

        void* ResolvePluginOwnerTokenLocked(uint64_t token)
        {
            if (token == 0)
                return nullptr;

            const auto it = PluginOwnerTokens().find(token);
            if (it == PluginOwnerTokens().end())
                return nullptr;
            return it->second;
        }

        void* ResolveOwnerTokenForRegistrationLocked(const char* apiName, uint64_t token)
        {
            void* owner = ResolvePluginOwnerTokenLocked(token);
            if (!owner)
            {
                OBELISK_WARN("{} rejected callback because the owner token is invalid.", apiName);
                return nullptr;
            }

            if (IsUnloadingPluginOwnerLocked(owner))
            {
                OBELISK_WARN("{} rejected callback because the plugin owner is unloading.", apiName);
                return nullptr;
            }

            if (owner == g_CurrentPluginOwner || IsInitializingPluginOwnerLocked(owner))
                return owner;

            if (!IsLoadedPluginOwnerLocked(owner))
            {
                OBELISK_WARN("{} rejected callback because the owner token does not map to a loaded Obelisk plugin.", apiName);
                return nullptr;
            }

            return owner;
        }

        void* ResolveOwnerTokenForUnregister(const char* apiName, uint64_t token)
        {
            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            void* owner = ResolvePluginOwnerTokenLocked(token);
            if (!owner)
            {
                OBELISK_WARN("{} rejected callback unregister because the owner token is invalid.", apiName);
                return nullptr;
            }

            if (owner == g_CurrentPluginOwner ||
                IsInitializingPluginOwnerLocked(owner) ||
                IsLoadedPluginOwnerLocked(owner) ||
                IsUnloadingPluginOwnerLocked(owner))
            {
                return owner;
            }

            OBELISK_WARN("{} rejected callback unregister because the owner token does not map to an Obelisk plugin lifecycle owner.", apiName);
            return nullptr;
        }

        void* ResolveCallbackOwnerForRegistrationLocked(const char* apiName, OnProcessEventCallback callback)
        {
            if (g_CurrentPluginOwner)
            {
                if (IsUnloadingPluginOwnerLocked(g_CurrentPluginOwner))
                {
                    OBELISK_WARN("{} rejected callback because the plugin owner is unloading.", apiName);
                    return nullptr;
                }
                return g_CurrentPluginOwner;
            }

            if (!callback)
                return nullptr;

            Dl_info info{};
            if (dladdr(reinterpret_cast<void*>(callback), &info) == 0)
            {
                OBELISK_WARN("{} rejected callback because its owning shared object could not be resolved.", apiName);
                return nullptr;
            }

            void* owner = info.dli_fbase;
            if (IsUnloadingPluginOwnerLocked(owner))
            {
                OBELISK_WARN("{} rejected callback because the plugin owner is unloading.", apiName);
                return nullptr;
            }

            if (!IsLoadedPluginOwnerLocked(owner))
            {
                OBELISK_WARN("{} rejected callback because its owner is not a loaded Obelisk plugin.", apiName);
                return nullptr;
            }

            return owner;
        }

        template <typename RegisterFn>
        uint64_t RegisterProcessEventCallbackForOwnerToken(const char* apiName, uint64_t ownerToken, RegisterFn registerFn)
        {
            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            void* owner = ResolveOwnerTokenForRegistrationLocked(apiName, ownerToken);
            if (!owner)
                return 0;
            return registerFn(owner);
        }

        template <typename RegisterFn>
        uint64_t RegisterProcessEventCallbackForCallbackOwner(const char* apiName,
                                                              OnProcessEventCallback callback,
                                                              RegisterFn registerFn)
        {
            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            void* owner = ResolveCallbackOwnerForRegistrationLocked(apiName, callback);
            if (!owner)
                return 0;
            return registerFn(owner);
        }

        ShutdownFunc ResolveShutdownFunc(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            std::string error;
            ShutdownFunc shutdownFunc = reinterpret_cast<ShutdownFunc>(loader.Resolve(handle, "ObeliskPlugin_Shutdown", error));
            if (!shutdownFunc)
            {
                OBELISK_INFO("Plugin {} does not export ObeliskPlugin_Shutdown; unload will use callback owner cleanup only.", pluginName);
                return nullptr;
            }

            return shutdownFunc;
        }

        void CallPluginShutdown(const std::string& pluginName, ShutdownFunc shutdownFunc)
        {
            if (!shutdownFunc)
                return;

            try
            {
                shutdownFunc();
                OBELISK_INFO("Plugin {} shutdown completed.", pluginName);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Plugin {} threw during shutdown: {}", pluginName, e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Plugin {} threw an unknown exception during shutdown.", pluginName);
            }
        }

        void SafeCloseLibrary(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            if (!handle)
                return;

            try
            {
                loader.Close(handle);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Plugin {} threw while closing library handle: {}", pluginName, e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Plugin {} threw an unknown exception while closing library handle.", pluginName);
            }
        }

        bool AreGlobalProcessEventCallbacksAllowed()
        {
            const char* env = std::getenv("OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS");
            if (!env || std::string_view(env) != "1")
                return false;

            const char* markerRoot = std::getenv("OBELISK_ROOT");
            const char* instanceId = std::getenv("OBELISK_INSTANCE_ID");
            return Runtime::IsInstanceMarkerEnabled(markerRoot, instanceId, "allow-global-process-event-callbacks");
        }

        bool AreFilteredProcessEventCallbacksAllowed()
        {
            return Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS",
                                                          "allow-filtered-process-event-callbacks");
        }

        bool IsCallProcessEventAllowed()
        {
            return Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ALLOW_CALL_PROCESS_EVENT",
                                                          "allow-call-process-event");
        }

        bool IsProcessEventBlockingAllowed()
        {
            return Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING",
                                                          "allow-process-event-blocking");
        }

        bool AreChatMessageEventsAllowed()
        {
            return Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ENABLE_CHAT_EVENTS",
                                                          "enable-chat-events");
        }

        uint64_t BuildApiCapabilities()
        {
            uint64_t capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS |
                OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS |
                OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS |
                OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS |
                OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;
            if (AreGlobalProcessEventCallbacksAllowed())
                capabilities |= OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS |
                    OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES;
            if (AreFilteredProcessEventCallbacksAllowed())
                capabilities |= OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS |
                    OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES;
            if (IsCallProcessEventAllowed())
                capabilities |= OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT;
            if (IsProcessEventBlockingAllowed())
                capabilities |= OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING;
            if (AreChatMessageEventsAllowed())
                capabilities |= OBELISK_API_CAPABILITY_CHAT_EVENTS;
            return capabilities;
        }

        template <std::size_t N>
        void CopyDescriptorText(char (&destination)[N], std::string_view value)
        {
            static_assert(N > 0);
            const std::size_t count = std::min(N - 1, value.size());
            std::copy_n(value.data(), count, destination);
            destination[count] = '\0';
        }

        bool DescribeResourceKind(uint32_t resourceKind, ObeliskResourceKindDescriptor* out)
        {
            if (!out || out->struct_size < sizeof(ObeliskResourceKindDescriptor))
                return false;

            ObeliskResourceKindDescriptor descriptor{
                .abi_version = OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION,
                .struct_size = sizeof(ObeliskResourceKindDescriptor),
                .resource_kind = resourceKind,
                .reserved0 = 0,
                .flags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
                    OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
                    OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP,
                .supported_gameplay_policy_event_mask = 0,
                .supported_gameplay_policy_field_mask = 0,
                .stable_name = {},
                .display_name = {},
            };

            switch (resourceKind)
            {
                case OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE:
                    descriptor.supported_gameplay_policy_event_mask =
                        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES;
                    descriptor.supported_gameplay_policy_field_mask =
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE;
                    CopyDescriptorText(descriptor.stable_name, "structure");
                    CopyDescriptorText(descriptor.display_name, "Structure");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM:
                    descriptor.supported_gameplay_policy_event_mask =
                        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY;
                    descriptor.supported_gameplay_policy_field_mask =
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
                    CopyDescriptorText(descriptor.stable_name, "inventory_item");
                    CopyDescriptorText(descriptor.display_name, "Inventory Item");
                    *out = descriptor;
                    return true;
                default:
                    return false;
            }
        }

        bool DescribeGameplayPolicyEventKind(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out)
        {
            if (!out || out->struct_size < sizeof(ObeliskGameplayPolicyEventDescriptor))
                return false;

            ObeliskGameplayPolicyEventDescriptor descriptor{
                .abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION,
                .struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor),
                .event_kind = eventKind,
                .resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN,
                .flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD,
                .event_kind_mask = 0,
                .field_mask = 0,
                .stable_name = {},
                .display_name = {},
            };

            switch (eventKind)
            {
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "structure.access_check");
                    CopyDescriptorText(descriptor.display_name, "Structure Access Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "structure.demolish_check");
                    CopyDescriptorText(descriptor.display_name, "Structure Demolish Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET;
                    CopyDescriptorText(descriptor.stable_name, "structure.variant_change");
                    CopyDescriptorText(descriptor.display_name, "Structure Variant Change");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "structure.activation_toggle");
                    CopyDescriptorText(descriptor.display_name, "Structure Activation Toggle");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "structure.pin_code_check");
                    CopyDescriptorText(descriptor.display_name, "Structure Pin Code Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE;
                    CopyDescriptorText(descriptor.stable_name, "structure.seat_check");
                    CopyDescriptorText(descriptor.display_name, "Structure Seat Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;
                    CopyDescriptorText(descriptor.stable_name, "inventory.remote_add_check");
                    CopyDescriptorText(descriptor.display_name, "Inventory Remote Add Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
                    CopyDescriptorText(descriptor.stable_name, "inventory.use_check");
                    CopyDescriptorText(descriptor.display_name, "Inventory Use Check");
                    *out = descriptor;
                    return true;
                default:
                    return false;
            }
        }

        bool IsGlobalProcessEventCallbackCapabilityEnabledForOwnerLocked(void* owner)
        {
            return PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) &&
                AreGlobalProcessEventCallbacksAllowed();
        }

        bool ValidateGlobalProcessEventCallbackCapabilityForOwnerLocked(const char* apiName, void* owner)
        {
            if (IsGlobalProcessEventCallbackCapabilityEnabledForOwnerLocked(owner))
                return true;

            OBELISK_WARN("{} rejected. Use a filtered ProcessEvent callback or enable allow-global-process-event-callbacks for a controlled debug window.", apiName);
            return false;
        }

        bool IsFilteredProcessEventCallbackCapabilityEnabledForOwnerLocked(void* owner)
        {
            return PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) &&
                AreFilteredProcessEventCallbacksAllowed();
        }

        bool ValidateFilteredProcessEventCallbackCapabilityForOwnerLocked(const char* apiName, void* owner)
        {
            if (IsFilteredProcessEventCallbackCapabilityEnabledForOwnerLocked(owner))
                return true;

            OBELISK_WARN("{} rejected. Filtered ProcessEvent callbacks expose raw UE pointers and require allow-filtered-process-event-callbacks for a controlled debug window.", apiName);
            return false;
        }

        bool IsChatMessageEventCapabilityEnabledForOwnerLocked(void* owner)
        {
            return PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_CHAT_EVENTS) &&
                AreChatMessageEventsAllowed();
        }

        bool IsGameplayPolicyEventCapabilityEnabledForOwnerLocked(void* owner)
        {
            return PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS);
        }

        bool ValidateProcessEventCallback(const char* apiName, OnProcessEventCallback callback)
        {
            if (callback)
                return true;

            OBELISK_WARN("{} rejected null callback.", apiName);
            return false;
        }

        bool ValidateFilteredProcessEventCallback(const char* apiName,
                                                  int32_t nameIndex,
                                                  OnProcessEventCallback callback)
        {
            if (!ValidateProcessEventCallback(apiName, callback))
                return false;
            if (nameIndex >= 0)
                return true;

            OBELISK_WARN("{} rejected invalid negative FName index {}.", apiName, nameIndex);
            return false;
        }

        bool ValidateGameplayPolicyEventCallback(const char* apiName,
                                                 ObeliskGameplayPolicyEventCallback callback)
        {
            if (callback)
                return true;

            OBELISK_WARN("{} rejected null callback.", apiName);
            return false;
        }

        bool ValidateChatMessageEventCallback(const char* apiName,
                                              ObeliskChatMessageEventCallback callback)
        {
            if (callback)
                return true;

            OBELISK_WARN("{} rejected null callback.", apiName);
            return false;
        }

        uint32_t ToGameplayPolicyEventKind(StructureEventKind kind)
        {
            switch (kind)
            {
            case StructureEventKind::AllowStructureAccess:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK;
            case StructureEventKind::IsAllowedToDemolish:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK;
            case StructureEventKind::SetVariant:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE;
            case StructureEventKind::AllowToggleActivation:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE;
            case StructureEventKind::VerifyPinCode:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK;
            case StructureEventKind::CanSeat:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK;
            }
            return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN;
        }

        uint32_t ToGameplayPolicyEventKind(InventoryPolicyEventKind kind)
        {
            switch (kind)
            {
            case InventoryPolicyEventKind::AllowRemoteAddToInventory:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK;
            case InventoryPolicyEventKind::CanUse:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK;
            }
            return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN;
        }

        uint64_t ToGameplayPolicyEventMask(uint32_t eventKind)
        {
            switch (eventKind)
            {
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK;
            default:
                return 0;
            }
        }

        void SetGameplayPolicyBoolField(ObeliskGameplayPolicyEvent& publicEvent,
                                        ObeliskGameplayPolicyField field,
                                        bool value)
        {
            const uint64_t bit = 1ull << static_cast<uint32_t>(field);
            publicEvent.field_mask |= bit;
            if (value)
                publicEvent.bool_values |= bit;
            else
                publicEvent.bool_values &= ~bit;
        }

        void SetGameplayPolicyInt32Field(ObeliskGameplayPolicyEvent& publicEvent,
                                         ObeliskGameplayPolicyField field,
                                         int32_t value)
        {
            const uint32_t fieldIndex = static_cast<uint32_t>(field);
            if (fieldIndex >= OBELISK_GAMEPLAY_POLICY_FIELD_COUNT)
                return;
            publicEvent.field_mask |= (1ull << fieldIndex);
            publicEvent.int32_values[fieldIndex] = value;
        }

        void CopyGameplayPolicyScalar(ObeliskGameplayPolicyEvent& publicEvent,
                                      const StructureScalarValue& scalar)
        {
            switch (scalar.Field)
            {
            case StructureScalarField::ReturnValue:
                if (scalar.Type == StructureScalarType::Bool)
                    SetGameplayPolicyBoolField(publicEvent,
                                               OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE,
                                               scalar.BoolValue);
                return;
            case StructureScalarField::VariantIndex:
                if (scalar.Type == StructureScalarType::Int32)
                    SetGameplayPolicyInt32Field(publicEvent,
                                                OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX,
                                                scalar.Int32Value);
                return;
            case StructureScalarField::BForceSet:
                if (scalar.Type == StructureScalarType::Bool)
                    SetGameplayPolicyBoolField(publicEvent,
                                               OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET,
                                               scalar.BoolValue);
                return;
            case StructureScalarField::BForce:
                if (scalar.Type == StructureScalarType::Bool)
                    SetGameplayPolicyBoolField(publicEvent,
                                               OBELISK_GAMEPLAY_POLICY_FIELD_FORCE,
                                               scalar.BoolValue);
                return;
            }
        }

        void CopyGameplayPolicyScalar(ObeliskGameplayPolicyEvent& publicEvent,
                                      const InventoryPolicyScalarValue& scalar)
        {
            switch (scalar.Field)
            {
            case InventoryPolicyScalarField::ReturnValue:
                SetGameplayPolicyBoolField(publicEvent,
                                           OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE,
                                           scalar.BoolValue);
                return;
            case InventoryPolicyScalarField::BRequestedByPlayer:
                SetGameplayPolicyBoolField(publicEvent,
                                           OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER,
                                           scalar.BoolValue);
                return;
            case InventoryPolicyScalarField::BIgnoreCooldown:
                SetGameplayPolicyBoolField(publicEvent,
                                           OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN,
                                           scalar.BoolValue);
                return;
            }
        }

        struct GameplayPolicyEventCallbackState
        {
            uint64_t EventKindMask = 0;
            ObeliskGameplayPolicyEventCallback Callback = nullptr;
            void* UserData = nullptr;
        };

        void DestroyGameplayPolicyEventCallbackState(void* userData)
        {
            delete static_cast<GameplayPolicyEventCallbackState*>(userData);
        }

        void InvokeGameplayPolicyEventCallback(const GameplayPolicyEventCallbackState& state,
                                               const ObeliskGameplayPolicyEvent& event)
        {
            try
            {
                state.Callback(&event, state.UserData);
            }
            catch (const std::exception& e)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Gameplay policy event callback threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Gameplay policy event callback threw an unknown exception.");
            }
        }

        void DispatchGameplayPolicyEventFromStructure(const StructureEventView& event, void* userData)
        {
            auto* state = static_cast<GameplayPolicyEventCallbackState*>(userData);
            if (!state || !state->Callback)
                return;

            const uint32_t eventKind = ToGameplayPolicyEventKind(event.Kind);
            if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN)
                return;
            const uint64_t eventMask = ToGameplayPolicyEventMask(eventKind);
            if (eventMask == 0 || (state->EventKindMask & eventMask) == 0)
                return;

            ObeliskGameplayPolicyEvent publicEvent{
                .abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
                .struct_size = sizeof(ObeliskGameplayPolicyEvent),
                .event_kind = eventKind,
                .resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                .flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                .field_mask = 0,
                .bool_values = 0,
                .int32_values = {},
            };
            for (const StructureScalarValue& scalar : event.Scalars)
                CopyGameplayPolicyScalar(publicEvent, scalar);
            InvokeGameplayPolicyEventCallback(*state, publicEvent);
        }

        void DispatchGameplayPolicyEventFromInventory(const InventoryPolicyEventView& event, void* userData)
        {
            auto* state = static_cast<GameplayPolicyEventCallbackState*>(userData);
            if (!state || !state->Callback)
                return;

            const uint32_t eventKind = ToGameplayPolicyEventKind(event.Kind);
            if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN)
                return;
            const uint64_t eventMask = ToGameplayPolicyEventMask(eventKind);
            if (eventMask == 0 || (state->EventKindMask & eventMask) == 0)
                return;

            ObeliskGameplayPolicyEvent publicEvent{
                .abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
                .struct_size = sizeof(ObeliskGameplayPolicyEvent),
                .event_kind = eventKind,
                .resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                .flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                    OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                .field_mask = 0,
                .bool_values = 0,
                .int32_values = {},
            };
            for (const InventoryPolicyScalarValue& scalar : event.Scalars)
                CopyGameplayPolicyScalar(publicEvent, scalar);
            InvokeGameplayPolicyEventCallback(*state, publicEvent);
        }

        struct ChatMessageEventCallbackState
        {
            ObeliskChatMessageEventCallback Callback = nullptr;
            void* UserData = nullptr;
        };

        void DestroyChatMessageEventCallbackState(void* userData)
        {
            delete static_cast<ChatMessageEventCallbackState*>(userData);
        }

        void InvokeChatMessageEventCallback(const ChatMessageEventCallbackState& state,
                                            const ObeliskChatMessageEvent& event)
        {
            try
            {
                state.Callback(&event, state.UserData);
            }
            catch (const std::exception& e)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message event callback threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message event callback threw an unknown exception.");
            }
        }

        void DispatchPublicChatMessageEvent(const ChatMessageView& message, void* userData)
        {
            auto* state = static_cast<ChatMessageEventCallbackState*>(userData);
            if (!state || !state->Callback)
                return;

            const uint32_t sendMode = static_cast<uint32_t>(message.SendMode);
            if (sendMode > static_cast<uint32_t>(ChatSendMode::Alliance))
                return;

            ObeliskChatMessageEvent publicEvent{
                .abi_version = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION,
                .struct_size = sizeof(ObeliskChatMessageEvent),
                .send_mode = sendMode,
                .reserved0 = 0,
                .flags = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD,
                .sequence = AllocateChatMessageSequence(),
                .message = {
                    .data = message.Message.data(),
                    .size = message.Message.size(),
                },
            };
            InvokeChatMessageEventCallback(*state, publicEvent);
        }

        uint64_t AllocateChatMessageRegistrationIdLocked()
        {
            uint64_t id = 0;
            do
            {
                id = NextChatMessageRegistrationId()++;
                if (NextChatMessageRegistrationId() == 0)
                    NextChatMessageRegistrationId() = 1;
            } while (id == 0 || ChatMessageRegistrations().find(id) != ChatMessageRegistrations().end());
            return id;
        }

        uint64_t RegisterChatMessageEventForOwner(void* owner,
                                                  ObeliskChatMessageEventCallback callback,
                                                  void* userData)
        {
            if (!owner || !callback)
                return 0;
            if (!IsChatMessageEventCapabilityEnabledForOwnerLocked(owner))
                return 0;

            ChatEventDispatcher* dispatcher = PluginOwnerChatDispatcherLocked(owner);
            if (!dispatcher)
                return 0;

            uint64_t publicRegistrationId = 0;
            {
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                publicRegistrationId = AllocateChatMessageRegistrationIdLocked();
            }

            auto state = std::make_unique<ChatMessageEventCallbackState>(
                ChatMessageEventCallbackState{callback, userData});
            const uint64_t internalRegistrationId = dispatcher->Register(
                owner,
                ChatMessageSubscription{
                    DispatchPublicChatMessageEvent,
                    state.get(),
                    DestroyChatMessageEventCallbackState,
                });
            if (internalRegistrationId == 0)
                return 0;
            (void)state.release();

            try
            {
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                ChatMessageRegistrations()[publicRegistrationId] = ChatMessageRegistration{
                    .Owner = owner,
                    .Dispatcher = dispatcher,
                    .InternalRegistrationId = internalRegistrationId,
                };
            }
            catch (...)
            {
                (void)dispatcher->Unregister(internalRegistrationId);
                throw;
            }
            return publicRegistrationId;
        }

        bool UnregisterChatMessageRegistrationForOwner(void* owner, uint64_t registrationId)
        {
            if (!owner || registrationId == 0)
                return false;

            ChatMessageRegistration registration;
            {
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                const auto it = ChatMessageRegistrations().find(registrationId);
                if (it == ChatMessageRegistrations().end() || it->second.Owner != owner)
                    return false;
                registration = it->second;
                ChatMessageRegistrations().erase(it);
            }

            return registration.Dispatcher &&
                registration.Dispatcher->Unregister(registration.InternalRegistrationId);
        }

        size_t UnregisterChatMessageRegistrationsForOwner(void* owner)
        {
            if (!owner)
                return 0;

            std::vector<std::pair<uint64_t, ChatMessageRegistration>> registrations;
            {
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                for (auto it = ChatMessageRegistrations().begin();
                     it != ChatMessageRegistrations().end();)
                {
                    if (it->second.Owner != owner)
                    {
                        ++it;
                        continue;
                    }
                    registrations.push_back(*it);
                    it = ChatMessageRegistrations().erase(it);
                }
            }

            size_t removed = 0;
            for (const auto& item : registrations)
            {
                const ChatMessageRegistration& registration = item.second;
                if (registration.Dispatcher &&
                    registration.Dispatcher->Unregister(registration.InternalRegistrationId))
                {
                    ++removed;
                }
            }
            return removed;
        }

        uint64_t AllocateGameplayPolicyRegistrationIdLocked()
        {
            uint64_t id = 0;
            do
            {
                id = NextGameplayPolicyRegistrationId()++;
                if (NextGameplayPolicyRegistrationId() == 0)
                    NextGameplayPolicyRegistrationId() = 1;
            } while (id == 0 || GameplayPolicyRegistrations().find(id) != GameplayPolicyRegistrations().end());
            return id;
        }

        uint64_t RegisterGameplayPolicyEventForOwner(void* owner,
                                                     uint64_t eventKindMask,
                                                     ObeliskGameplayPolicyEventCallback callback,
                                                     void* userData)
        {
            if (!owner)
                return 0;
            if (!IsGameplayPolicyEventCapabilityEnabledForOwnerLocked(owner))
                return 0;

            uint64_t publicRegistrationId = 0;
            {
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                publicRegistrationId = AllocateGameplayPolicyRegistrationIdLocked();
            }

            GameplayPolicyRegistration registration{
                .Owner = owner,
                .StructureRegistrationId = 0,
                .InventoryRegistrationId = 0,
            };

            if ((eventKindMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES) != 0)
            {
                auto state = std::make_unique<GameplayPolicyEventCallbackState>(
                    GameplayPolicyEventCallbackState{eventKindMask, callback, userData});
                registration.StructureRegistrationId = StructureEventDispatcher::Get().Register(
                    owner,
                    StructureEventSubscription{
                        DispatchGameplayPolicyEventFromStructure,
                        state.get(),
                        DestroyGameplayPolicyEventCallbackState,
                    });
                if (registration.StructureRegistrationId == 0)
                    return 0;
                (void)state.release();
            }

            try
            {
                if ((eventKindMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY) != 0)
                {
                    auto state = std::make_unique<GameplayPolicyEventCallbackState>(
                        GameplayPolicyEventCallbackState{eventKindMask, callback, userData});
                    registration.InventoryRegistrationId = InventoryPolicyEventDispatcher::Get().Register(
                        owner,
                        InventoryPolicyEventSubscription{
                            DispatchGameplayPolicyEventFromInventory,
                            state.get(),
                            DestroyGameplayPolicyEventCallbackState,
                        });
                    if (registration.InventoryRegistrationId == 0)
                    {
                        if (registration.StructureRegistrationId != 0)
                        {
                            (void)StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                                owner,
                                registration.StructureRegistrationId);
                        }
                        return 0;
                    }
                    (void)state.release();
                }
            }
            catch (...)
            {
                if (registration.StructureRegistrationId != 0)
                {
                    (void)StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.StructureRegistrationId);
                }
                throw;
            }

            try
            {
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                GameplayPolicyRegistrations()[publicRegistrationId] = registration;
            }
            catch (...)
            {
                if (registration.StructureRegistrationId != 0)
                {
                    (void)StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.StructureRegistrationId);
                }
                if (registration.InventoryRegistrationId != 0)
                {
                    (void)InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.InventoryRegistrationId);
                }
                throw;
            }
            return publicRegistrationId;
        }

        bool UnregisterGameplayPolicyRegistrationForOwner(void* owner, uint64_t registrationId)
        {
            if (!owner || registrationId == 0)
                return false;

            GameplayPolicyRegistration registration;
            {
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                const auto it = GameplayPolicyRegistrations().find(registrationId);
                if (it == GameplayPolicyRegistrations().end() || it->second.Owner != owner)
                    return false;
                registration = it->second;
                GameplayPolicyRegistrations().erase(it);
            }

            bool removed = false;
            if (registration.StructureRegistrationId != 0)
            {
                removed = StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                    owner,
                    registration.StructureRegistrationId) || removed;
            }
            if (registration.InventoryRegistrationId != 0)
            {
                removed = InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner(
                    owner,
                    registration.InventoryRegistrationId) || removed;
            }
            return removed;
        }

        size_t UnregisterGameplayPolicyRegistrationsForOwner(void* owner)
        {
            if (!owner)
                return 0;

            std::vector<std::pair<uint64_t, GameplayPolicyRegistration>> registrations;
            {
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                for (auto it = GameplayPolicyRegistrations().begin();
                     it != GameplayPolicyRegistrations().end();)
                {
                    if (it->second.Owner != owner)
                    {
                        ++it;
                        continue;
                    }
                    registrations.push_back(*it);
                    it = GameplayPolicyRegistrations().erase(it);
                }
            }

            size_t removed = 0;
            for (const auto& item : registrations)
            {
                const GameplayPolicyRegistration& registration = item.second;
                bool removedAny = false;
                if (registration.StructureRegistrationId != 0)
                {
                    removedAny = StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.StructureRegistrationId) || removedAny;
                }
                if (registration.InventoryRegistrationId != 0)
                {
                    removedAny = InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.InventoryRegistrationId) || removedAny;
                }
                if (removedAny)
                    ++removed;
            }
            return removed;
        }

        template <typename Fn>
        class ScopeExit
        {
        public:
            explicit ScopeExit(Fn fn)
                : m_Fn(fn)
            {
            }

            ~ScopeExit()
            {
                if (m_Active)
                    m_Fn();
            }

            ScopeExit(const ScopeExit&) = delete;
            ScopeExit& operator=(const ScopeExit&) = delete;

            void Dismiss()
            {
                m_Active = false;
            }

        private:
            Fn m_Fn;
            bool m_Active = true;
        };

        template <typename Fn>
        ScopeExit<Fn> MakeScopeExit(Fn fn)
        {
            return ScopeExit<Fn>(fn);
        }
    }

    // C-API Wrappers for Plugins
    extern "C" {
        void PluginLogInfo(const char* message) { OBELISK_INFO("[Plugin] {}", message ? message : ""); }
        void PluginLogWarn(const char* message) { OBELISK_WARN("[Plugin] {}", message ? message : ""); }
        void PluginLogError(const char* message) { OBELISK_ERROR("[Plugin] {}", message ? message : ""); }

        void PluginRegisterPreProcessEvent(OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPreProcessEvent", callback))
                return;
            try
            {
                (void)RegisterProcessEventCallbackForCallbackOwner(
                    "RegisterPreProcessEvent",
                    callback,
                    [callback](void* owner) {
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwnerLocked("RegisterPreProcessEvent", owner))
                            return uint64_t{0};
                        return EventManager::Get().RegisterPreProcessEventOwned(owner, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPreProcessEvent rejected callback after exception: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPreProcessEvent rejected callback after unknown exception.");
            }
        }
        void PluginRegisterPostProcessEvent(OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPostProcessEvent", callback))
                return;
            try
            {
                (void)RegisterProcessEventCallbackForCallbackOwner(
                    "RegisterPostProcessEvent",
                    callback,
                    [callback](void* owner) {
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwnerLocked("RegisterPostProcessEvent", owner))
                            return uint64_t{0};
                        return EventManager::Get().RegisterPostProcessEventOwned(owner, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPostProcessEvent rejected callback after exception: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPostProcessEvent rejected callback after unknown exception.");
            }
        }
        void PluginRegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPreProcessEventForNameIndex", nameIndex, callback))
                return;
            try
            {
                (void)RegisterProcessEventCallbackForCallbackOwner(
                    "RegisterPreProcessEventForNameIndex",
                    callback,
                    [nameIndex, callback](void* owner) {
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPreProcessEventForNameIndex",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventForNameIndexOwned(owner, nameIndex, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPreProcessEventForNameIndex rejected callback after exception: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPreProcessEventForNameIndex rejected callback after unknown exception.");
            }
        }
        void PluginRegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPostProcessEventForNameIndex", nameIndex, callback))
                return;
            try
            {
                (void)RegisterProcessEventCallbackForCallbackOwner(
                    "RegisterPostProcessEventForNameIndex",
                    callback,
                    [nameIndex, callback](void* owner) {
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPostProcessEventForNameIndex",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPostProcessEventForNameIndexOwned(owner, nameIndex, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPostProcessEventForNameIndex rejected callback after exception: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPostProcessEventForNameIndex rejected callback after unknown exception.");
            }
        }
        uint64_t PluginRegisterPreProcessEventWithOwnerTokenHandle(uint64_t ownerToken, OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPreProcessEventWithOwnerToken", callback))
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterPreProcessEventWithOwnerToken",
                    ownerToken,
                    [callback](void* owner) {
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPreProcessEventWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventOwned(owner, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPreProcessEventWithOwnerToken rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPreProcessEventWithOwnerToken rejected callback after unknown exception.");
                return 0;
            }
        }
        uint64_t PluginRegisterPostProcessEventWithOwnerTokenHandle(uint64_t ownerToken, OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPostProcessEventWithOwnerToken", callback))
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterPostProcessEventWithOwnerToken",
                    ownerToken,
                    [callback](void* owner) {
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPostProcessEventWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPostProcessEventOwned(owner, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPostProcessEventWithOwnerToken rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPostProcessEventWithOwnerToken rejected callback after unknown exception.");
                return 0;
            }
        }
        uint64_t PluginRegisterPreProcessEventForNameIndexWithOwnerTokenHandle(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPreProcessEventForNameIndexWithOwnerToken", nameIndex, callback))
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterPreProcessEventForNameIndexWithOwnerToken",
                    ownerToken,
                    [nameIndex, callback](void* owner) {
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPreProcessEventForNameIndexWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventForNameIndexOwned(owner, nameIndex, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPreProcessEventForNameIndexWithOwnerToken rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPreProcessEventForNameIndexWithOwnerToken rejected callback after unknown exception.");
                return 0;
            }
        }
        uint64_t PluginRegisterPostProcessEventForNameIndexWithOwnerTokenHandle(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback) {
            if (!ValidateFilteredProcessEventCallback("RegisterPostProcessEventForNameIndexWithOwnerToken", nameIndex, callback))
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterPostProcessEventForNameIndexWithOwnerToken",
                    ownerToken,
                    [nameIndex, callback](void* owner) {
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwnerLocked(
                                "RegisterPostProcessEventForNameIndexWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPostProcessEventForNameIndexOwned(owner, nameIndex, callback);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterPostProcessEventForNameIndexWithOwnerToken rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterPostProcessEventForNameIndexWithOwnerToken rejected callback after unknown exception.");
                return 0;
            }
        }
        void PluginRegisterPreProcessEventWithOwnerToken(uint64_t ownerToken, OnProcessEventCallback callback) {
            (void)PluginRegisterPreProcessEventWithOwnerTokenHandle(ownerToken, callback);
        }
        void PluginRegisterPostProcessEventWithOwnerToken(uint64_t ownerToken, OnProcessEventCallback callback) {
            (void)PluginRegisterPostProcessEventWithOwnerTokenHandle(ownerToken, callback);
        }
        void PluginRegisterPreProcessEventForNameIndexWithOwnerToken(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback) {
            (void)PluginRegisterPreProcessEventForNameIndexWithOwnerTokenHandle(ownerToken, nameIndex, callback);
        }
        void PluginRegisterPostProcessEventForNameIndexWithOwnerToken(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback) {
            (void)PluginRegisterPostProcessEventForNameIndexWithOwnerTokenHandle(ownerToken, nameIndex, callback);
        }
        bool PluginUnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId) {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterProcessEventCallbackWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                return EventManager::Get().UnregisterCallbackForOwner(owner, registrationId);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("UnregisterProcessEventCallbackWithOwnerToken failed after exception: {}", e.what());
                return false;
            }
            catch (...)
            {
                OBELISK_ERROR("UnregisterProcessEventCallbackWithOwnerToken failed after unknown exception.");
                return false;
            }
        }
        uint64_t PluginRegisterGameplayPolicyEventWithOwnerTokenHandle(
            uint64_t ownerToken,
            uint64_t eventKindMask,
            ObeliskGameplayPolicyEventCallback callback,
            void* userData) {
            if (!ValidateGameplayPolicyEventCallback("RegisterGameplayPolicyEventWithOwnerTokenHandle", callback))
                return 0;
            if ((eventKindMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL) == 0)
            {
                OBELISK_WARN("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected empty gameplay policy event mask.");
                return 0;
            }
            if ((eventKindMask & ~OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL) != 0)
            {
                OBELISK_WARN("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected reserved gameplay policy event mask bits.");
                return 0;
            }

            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterGameplayPolicyEventWithOwnerTokenHandle",
                    ownerToken,
                    [eventKindMask, callback, userData](void* owner) {
                        return RegisterGameplayPolicyEventForOwner(owner, eventKindMask, callback, userData);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected callback after unknown exception.");
                return 0;
            }
        }
        bool PluginUnregisterGameplayPolicyEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId) {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterGameplayPolicyEventWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                return UnregisterGameplayPolicyRegistrationForOwner(owner, registrationId);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("UnregisterGameplayPolicyEventWithOwnerToken failed after exception: {}", e.what());
                return false;
            }
            catch (...)
            {
                OBELISK_ERROR("UnregisterGameplayPolicyEventWithOwnerToken failed after unknown exception.");
                return false;
            }
        }
        uint64_t PluginRegisterChatMessageEventWithOwnerTokenHandle(
            uint64_t ownerToken,
            ObeliskChatMessageEventCallback callback,
            void* userData) {
            if (!ValidateChatMessageEventCallback("RegisterChatMessageEventWithOwnerTokenHandle", callback))
                return 0;

            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterChatMessageEventWithOwnerTokenHandle",
                    ownerToken,
                    [callback, userData](void* owner) {
                        return RegisterChatMessageEventForOwner(owner, callback, userData);
                    });
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("RegisterChatMessageEventWithOwnerTokenHandle rejected callback after exception: {}", e.what());
                return 0;
            }
            catch (...)
            {
                OBELISK_ERROR("RegisterChatMessageEventWithOwnerTokenHandle rejected callback after unknown exception.");
                return 0;
            }
        }
        bool PluginUnregisterChatMessageEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId) {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterChatMessageEventWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                return UnregisterChatMessageRegistrationForOwner(owner, registrationId);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("UnregisterChatMessageEventWithOwnerToken failed after exception: {}", e.what());
                return false;
            }
            catch (...)
            {
                OBELISK_ERROR("UnregisterChatMessageEventWithOwnerToken failed after unknown exception.");
                return false;
            }
        }
        bool PluginDescribeResourceKind(uint32_t resourceKind, ObeliskResourceKindDescriptor* out) {
            return DescribeResourceKind(resourceKind, out);
        }
        bool PluginDescribeGameplayPolicyEventKind(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out) {
            return DescribeGameplayPolicyEventKind(eventKind, out);
        }
        void PluginCallProcessEvent(void* caller, void* function, void* parms) {
            if ((g_ApiCapabilities.load(std::memory_order_acquire) &
                 OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) == 0 ||
                !IsCallProcessEventAllowed())
            {
                OBELISK_WARN("CallProcessEvent rejected. Enable allow-call-process-event only for a controlled debug window.");
                return;
            }
            Hooks::ProcessEventHook::CallOriginalProcessEvent(caller, function, parms);
        }
    }

    PluginManager& PluginManager::Get()
    {
        static PluginManager instance;
        return instance;
    }

    PluginManager::PluginManager()
        : PluginManager(DefaultLoader(), ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader)
        : PluginManager(loader, ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher)
        : m_Loader(&loader)
        , m_ChatDispatcher(&chatDispatcher)
    {
        m_Api.LogInfo = PluginLogInfo;
        m_Api.LogWarn = PluginLogWarn;
        m_Api.LogError = PluginLogError;
        m_Api.RegisterPreProcessEvent = PluginRegisterPreProcessEvent;
        m_Api.RegisterPostProcessEvent = PluginRegisterPostProcessEvent;
        m_Api.RegisterPreProcessEventForNameIndex = PluginRegisterPreProcessEventForNameIndex;
        m_Api.RegisterPostProcessEventForNameIndex = PluginRegisterPostProcessEventForNameIndex;
        m_Api.CallProcessEvent = PluginCallProcessEvent;
        m_Api.abi_version = OBELISK_API_ABI_VERSION;
        m_Api.struct_size = sizeof(ObeliskApi);
        m_Api.capabilities = BuildApiCapabilities();
        m_Api.RegisterPreProcessEventWithOwnerToken = PluginRegisterPreProcessEventWithOwnerToken;
        m_Api.RegisterPostProcessEventWithOwnerToken = PluginRegisterPostProcessEventWithOwnerToken;
        m_Api.RegisterPreProcessEventForNameIndexWithOwnerToken = PluginRegisterPreProcessEventForNameIndexWithOwnerToken;
        m_Api.RegisterPostProcessEventForNameIndexWithOwnerToken = PluginRegisterPostProcessEventForNameIndexWithOwnerToken;
        m_Api.RegisterPreProcessEventWithOwnerTokenHandle = PluginRegisterPreProcessEventWithOwnerTokenHandle;
        m_Api.RegisterPostProcessEventWithOwnerTokenHandle = PluginRegisterPostProcessEventWithOwnerTokenHandle;
        m_Api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle = PluginRegisterPreProcessEventForNameIndexWithOwnerTokenHandle;
        m_Api.RegisterPostProcessEventForNameIndexWithOwnerTokenHandle = PluginRegisterPostProcessEventForNameIndexWithOwnerTokenHandle;
        m_Api.UnregisterProcessEventCallbackWithOwnerToken = PluginUnregisterProcessEventCallbackWithOwnerToken;
        m_Api.RegisterGameplayPolicyEventWithOwnerTokenHandle = PluginRegisterGameplayPolicyEventWithOwnerTokenHandle;
        m_Api.UnregisterGameplayPolicyEventWithOwnerToken = PluginUnregisterGameplayPolicyEventWithOwnerToken;
        m_Api.DescribeResourceKind = PluginDescribeResourceKind;
        m_Api.DescribeGameplayPolicyEventKind = PluginDescribeGameplayPolicyEventKind;
        m_Api.RegisterChatMessageEventWithOwnerTokenHandle = PluginRegisterChatMessageEventWithOwnerTokenHandle;
        m_Api.UnregisterChatMessageEventWithOwnerToken = PluginUnregisterChatMessageEventWithOwnerToken;
        g_ApiCapabilities.store(m_Api.capabilities, std::memory_order_release);
        EventManager::SetProcessEventBlockingCapabilityAdvertised(
            (m_Api.capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING) != 0);
    }

    uint64_t PluginManager::ApiCapabilitiesForTesting() const
    {
        return m_Api.capabilities;
    }

    void PluginManager::SetNextPluginOwnerTokenForTesting(uint64_t nextOwnerToken)
    {
        std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
        NextPluginOwnerToken().store(nextOwnerToken == 0 ? 1 : nextOwnerToken, std::memory_order_relaxed);
    }

    void PluginManager::SetNextChatMessageSequenceForTesting(uint64_t nextSequence)
    {
        NextChatMessageSequence().store(nextSequence == 0 ? 1 : nextSequence, std::memory_order_relaxed);
    }

    PluginManager::~PluginManager()
    {
        UnloadAll();
    }

    void PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason)
    {
        const size_t gameplayPolicyRemoved = UnregisterGameplayPolicyRegistrationsForOwner(owner);
        const size_t eventRemoved = EventManager::Get().UnregisterCallbacksForOwner(owner);
        const size_t publicChatRemoved = UnregisterChatMessageRegistrationsForOwner(owner);
        const size_t chatRemoved = m_ChatDispatcher->UnregisterCallbacksForOwner(owner);
        const size_t structureRemoved = StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner);
        const size_t inventoryRemoved = InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner);

        if (gameplayPolicyRemoved > 0)
            OBELISK_INFO("Removed {} gameplay policy callback(s) registered by plugin {} {}.", gameplayPolicyRemoved, pluginName, reason);
        if (eventRemoved > 0)
            OBELISK_INFO("Removed {} ProcessEvent callback(s) registered by plugin {} {}.", eventRemoved, pluginName, reason);
        if (publicChatRemoved > 0)
            OBELISK_INFO("Removed {} public chat callback(s) registered by plugin {} {}.", publicChatRemoved, pluginName, reason);
        if (chatRemoved > 0)
            OBELISK_INFO("Removed {} chat callback(s) registered by plugin {} {}.", chatRemoved, pluginName, reason);
        if (structureRemoved > 0)
            OBELISK_INFO("Removed {} structure callback(s) registered by plugin {} {}.", structureRemoved, pluginName, reason);
        if (inventoryRemoved > 0)
            OBELISK_INFO("Removed {} inventory policy callback(s) registered by plugin {} {}.", inventoryRemoved, pluginName, reason);
    }

    bool PluginManager::IsPluginIdLoaded(const std::string& pluginId) const
    {
        return std::any_of(m_LoadedPlugins.begin(), m_LoadedPlugins.end(),
            [&pluginId](const PluginInfo& plugin) {
                return plugin.pluginId == pluginId;
            });
    }

    void PluginManager::LoadPlugins(const std::string& directory)
    {
        try
        {
            const char* configRootEnv = std::getenv("OBELISK_CONFIG_DIR");
            if (!configRootEnv || configRootEnv[0] == '\0')
            {
                OBELISK_ERROR("OBELISK_CONFIG_DIR is required for plugin loading. Plugins will not be loaded.");
                return;
            }

            const fs::path configRoot = configRootEnv;
            std::string configRootError;
            if (!ValidatePluginConfigRoot(configRoot, true, configRootError))
            {
                OBELISK_ERROR("Invalid OBELISK_CONFIG_DIR: {}. Plugins will not be loaded.", configRootError);
                return;
            }

            const char* instanceIdEnv = std::getenv("OBELISK_INSTANCE_ID");
            const std::string instanceId = instanceIdEnv ? instanceIdEnv : "";
            if (!IsSafeInstanceId(instanceId))
            {
                OBELISK_ERROR("OBELISK_INSTANCE_ID must be a non-empty safe instance id before plugin loading. Plugins will not be loaded.");
                return;
            }

            if (directory.empty())
            {
                OBELISK_ERROR("OBELISK_PLUGIN_DIR or OBELISK_ROOT is required for plugin loading. Plugins will not be loaded.");
                return;
            }

            const fs::path pluginDirectory = directory;
            if (!pluginDirectory.is_absolute())
            {
                OBELISK_ERROR("Plugin directory {} is not absolute. Plugins will not be loaded.", directory);
                return;
            }

            const fs::file_status pluginDirectoryStatus = fs::symlink_status(pluginDirectory);
            if (!fs::exists(pluginDirectoryStatus))
            {
                OBELISK_WARN("Plugin directory {} does not exist. Plugins will not be loaded.", directory);
                return;
            }
            if (fs::is_symlink(pluginDirectoryStatus))
            {
                OBELISK_ERROR("Plugin directory {} is a symlink. Plugins will not be loaded.", directory);
                return;
            }
            if (!fs::is_directory(pluginDirectoryStatus))
            {
                OBELISK_ERROR("Plugin path {} is not a directory. Plugins will not be loaded.", directory);
                return;
            }

            std::vector<fs::path> plugins;
            for (const auto& entry : fs::directory_iterator(pluginDirectory))
            {
                if (entry.path().extension() != ".so")
                    continue;

                if (entry.is_symlink())
                {
                    OBELISK_WARN("Skipping plugin candidate {} because plugin symlinks are not allowed.", entry.path().filename().string());
                    continue;
                }

                if (entry.is_regular_file())
                    plugins.push_back(entry.path());
            }

            std::sort(plugins.begin(), plugins.end());
            OBELISK_INFO("Scanning for plugins in {}. Found {} candidate(s).", directory, plugins.size());

            std::unordered_set<std::string> pluginIds;
            for (const auto& path : plugins)
            {
                std::string pluginName = path.filename().string();

                OBELISK_INFO("Loading plugin: {}", pluginName);

                std::string loaderError;
                void* handle = m_Loader->Open(path, loaderError);
                if (!handle)
                {
                    OBELISK_ERROR("Failed to load plugin {}: {}", pluginName, loaderError);
                    continue;
                }

                auto handleCleanup = MakeScopeExit([&]() {
                    SafeCloseLibrary(*m_Loader, handle, pluginName);
                });

                std::string symbolError;
                GetInfoFunc getInfoFunc = reinterpret_cast<GetInfoFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_GetInfo", symbolError));
                if (!getInfoFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_GetInfo: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                ObeliskPluginMetadata metadata{};
                bool metadataLoaded = false;
                try
                {
                    metadataLoaded = getInfoFunc(&metadata);
                }
                catch (const std::exception& e)
                {
                    OBELISK_ERROR("Plugin {} threw while reporting metadata: {}", pluginName, e.what());
                }
                catch (...)
                {
                    OBELISK_ERROR("Plugin {} threw an unknown exception while reporting metadata.", pluginName);
                }

                if (!metadataLoaded)
                {
                    OBELISK_ERROR("Plugin {} failed to report metadata. Unloading.", pluginName);
                    continue;
                }

                PreparedPluginConfig preparedConfig;
                std::string configError;
                if (!PreparePluginConfig(metadata, configRoot, instanceId, preparedConfig, configError))
                {
                    OBELISK_ERROR("Plugin {} metadata/config rejected: {}. Unloading.", pluginName, configError);
                    continue;
                }

                if (!pluginIds.insert(metadata.plugin_id).second)
                {
                    OBELISK_ERROR("Plugin {} rejected: duplicate plugin_id '{}'. Unloading.", pluginName, metadata.plugin_id);
                    continue;
                }

                if (IsPluginIdLoaded(metadata.plugin_id))
                {
                    OBELISK_WARN("Plugin {} skipped because plugin_id '{}' is already loaded.", pluginName, metadata.plugin_id);
                    continue;
                }

                if (!preparedConfig.enabled)
                {
                    OBELISK_INFO("Plugin {} skipped because config enabled=false.", pluginName);
                    continue;
                }

                if (!preparedConfig.instance_allowed)
                {
                    OBELISK_INFO("Plugin {} skipped because instance '{}' is not in instance_allowlist.", pluginName, instanceId);
                    continue;
                }

                symbolError.clear();
                InitFunc initFunc = reinterpret_cast<InitFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_Init", symbolError));
                if (!initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                ShutdownFunc shutdownFunc = ResolveShutdownFunc(*m_Loader, handle, pluginName);

                const std::string configDir = preparedConfig.directory.string();
                const std::string configPath = preparedConfig.path.string();
                void* pluginOwner = m_Loader->GetSymbolOwner(handle, reinterpret_cast<void*>(initFunc));
                if (!pluginOwner)
                    pluginOwner = handle;
                const uint64_t pluginOwnerToken = AddPluginOwnerToken(pluginOwner, m_Api.capabilities, m_ChatDispatcher);
                auto ownerTokenCleanup = MakeScopeExit([&]() {
                    RemovePluginOwnerToken(pluginOwnerToken);
                });
                AddInitializingPluginOwner(pluginOwner);
                auto initializingOwnerCleanup = MakeScopeExit([&]() {
                    RemoveInitializingPluginOwner(pluginOwner);
                });
                ObeliskPluginInitContext initContext{
                    OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION,
                    sizeof(ObeliskPluginInitContext),
                    configDir.c_str(),
                    configPath.c_str(),
                    instanceId.c_str(),
                    pluginOwnerToken
                };

                bool initialized = false;
                bool initAttempted = false;
                auto initCleanup = MakeScopeExit([&]() {
                    if (!initAttempted)
                        return;
                    MarkPluginOwnerUnloading(pluginOwner);
                    CallPluginShutdown(pluginName, shutdownFunc);
                    RemoveInitializingPluginOwner(pluginOwner);
                    RemovePluginOwnerToken(pluginOwnerToken);
                    UnregisterPluginCallbacks(pluginName, pluginOwner, "after init failure and before dlclose");
                    ClearPluginOwnerUnloading(pluginOwner);
                });

                void* previousOwner = g_CurrentPluginOwner;
                g_CurrentPluginOwner = pluginOwner;
                auto ownerRestore = MakeScopeExit([&]() {
                    g_CurrentPluginOwner = previousOwner;
                });

                initAttempted = true;
                try
                {
                    ObeliskApi pluginApi = m_Api;
                    initialized = initFunc(&pluginApi, &initContext);
                }
                catch (const std::exception& e)
                {
                    OBELISK_ERROR("Plugin {} threw during initialization: {}", pluginName, e.what());
                }
                catch (...)
                {
                    OBELISK_ERROR("Plugin {} threw an unknown exception during initialization.", pluginName);
                }
                ownerRestore.Dismiss();
                g_CurrentPluginOwner = previousOwner;

                if (initialized)
                {
                    OBELISK_INFO("Plugin {} initialized successfully.", pluginName);
                    AddLoadedPluginOwner(pluginOwner);
                    auto loadedOwnerCleanup = MakeScopeExit([&]() {
                        RemoveLoadedPluginOwner(pluginOwner);
                    });
                    m_LoadedPlugins.push_back({pluginName, metadata.plugin_id, handle, pluginOwner, pluginOwnerToken, shutdownFunc});
                    loadedOwnerCleanup.Dismiss();
                    ownerTokenCleanup.Dismiss();
                    initializingOwnerCleanup.Dismiss();
                    RemoveInitializingPluginOwner(pluginOwner);
                    initCleanup.Dismiss();
                    handleCleanup.Dismiss();
                }
                else
                {
                    OBELISK_ERROR("Plugin {} failed to initialize.", pluginName);
                }
            }
        }
        catch (const std::exception& e)
        {
            OBELISK_ERROR("Failed to load plugins from {}: {}", directory, e.what());
        }
        catch (...)
        {
            OBELISK_ERROR("Failed to load plugins from {}: unknown exception", directory);
        }
    }

    void PluginManager::UnloadAll()
    {
        for (auto it = m_LoadedPlugins.rbegin(); it != m_LoadedPlugins.rend(); ++it)
        {
            auto& plugin = *it;
            OBELISK_INFO("Unloading plugin: {}", plugin.name);
            MarkPluginOwnerUnloading(plugin.owner);
            CallPluginShutdown(plugin.name, plugin.shutdown);
            RemoveLoadedPluginOwner(plugin.owner);
            RemovePluginOwnerToken(plugin.ownerToken);
            UnregisterPluginCallbacks(plugin.name, plugin.owner, "before dlclose");
            ClearPluginOwnerUnloading(plugin.owner);
            SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name);
        }
        m_LoadedPlugins.clear();
    }
}
