#if !defined(obelisk_EXPORTS)
#define OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
#endif

#include "PluginManager.h"
#include "EventManager.h"
#include "InventoryPolicyEventDispatcher.h"
#include "ItemReturnEventDispatcher.h"
#include "PlayerPrincipalEventDispatcher.h"
#include "PluginConfig.h"
#include "StructureEventDispatcher.h"
#include "TimerManager.h"
#include "OwnerExecutionGate.h"
#include "GameplayCallbackScope.h"
#include "hooks/ProcessEventHook.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include <dlfcn.h>
#include <link.h>
#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cstddef>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <iterator>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string_view>
#include <system_error>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
#include <unistd.h>

namespace fs = std::filesystem;

namespace Obelisk::Core
{
    namespace
    {
        thread_local void* g_CurrentPluginOwner = nullptr;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
        std::atomic_bool g_ForcePluginCallbackCleanupFailureForTesting{false};
        std::atomic_bool g_ForcePluginTimerCleanupFailureForTesting{false};
        std::atomic_bool g_ForcePluginRetentionFailureForTesting{false};
        std::atomic<int> g_PluginRetentionFailureAfterForTesting{-1};
        std::atomic_bool g_ForcePublicChatMessageTrackingFailureForTesting{false};
        std::atomic_bool g_ForcePublicChatMessageInternalUnregisterFailureForTesting{false};
        std::atomic_bool g_ForcePublicChatMessageRollbackUnregisterFailureForTesting{false};
        std::atomic_bool g_ForcePublicGameplayPolicyTrackingFailureForTesting{false};
        std::atomic_bool g_ForcePublicGameplayPolicyInternalUnregisterFailureForTesting{false};
        std::atomic_bool g_ForcePublicGameplayPolicyInventoryUnregisterFailureForTesting{false};
        std::atomic_bool g_ForcePublicGameplayPolicyRollbackUnregisterFailureForTesting{false};
        std::atomic_bool g_ForcePublicGameplayPolicyItemReturnRegistrationThrowForTesting{false};
        std::atomic_bool g_ForcePluginOwnerApiStateFailureForTesting{false};
#endif

        struct GameplayPolicyRegistration
        {
            void* Owner = nullptr;
            uint64_t StructureRegistrationId = 0;
            uint64_t InventoryRegistrationId = 0;
            uint64_t ItemReturnRegistrationId = 0;
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
            CommandDispatcher* Commands = nullptr;
            PlayerLifecycleDispatcher* PlayerLifecycle = nullptr;
            bool Unloading = false;
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

        bool HasPluginOwnerTokenForOwnerLocked(void* owner)
        {
            if (!owner)
                return false;

            return std::any_of(PluginOwnerTokens().begin(),
                               PluginOwnerTokens().end(),
                               [owner](const auto& item) {
                                   return item.second == owner;
                               });
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

        void SafeLogInfoNoThrow(const char* message, const std::string& detail) noexcept;
        void SafeLogWarnNoThrow(const char* message, const char* detail = nullptr) noexcept;
        void SafeLogErrorNoThrow(const char* message, const char* detail = nullptr) noexcept;

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
                link_map* primary = nullptr;
                if (dlinfo(handle, RTLD_DI_LINKMAP, &primary) == 0 && primary &&
                    dladdr(symbol, &symbolInfo) != 0 && symbolInfo.dli_fbase &&
                    symbolInfo.dli_fbase == reinterpret_cast<void*>(primary->l_addr))
                    return symbolInfo.dli_fbase;
                return nullptr;
            }

            bool Close(void* handle, std::string& error) override
            {
                dlerror();
                if (dlclose(handle) == 0)
                    return true;

                const char* closeError = dlerror();
                error = closeError ? closeError : "unknown dlclose error";
                return false;
            }
        };

        DlopenLibraryLoader& DefaultLoader()
        {
            static auto* loader = new DlopenLibraryLoader();
            return *loader;
        }

        bool ValidateNoPathAliasComponents(const fs::path& path, const char* label, std::string& error)
        {
            for (const auto& component : path)
            {
                if (component == path.root_name() || component == path.root_directory())
                    continue;
                if (component == "." || component == "..")
                {
                    error = std::string(label) + " must not contain path alias components";
                    return false;
                }
            }
            return true;
        }

        bool ValidateExistingPathComponentsNoSymlinks(const fs::path& path, const char* label, std::string& error)
        {
            if (!ValidateNoPathAliasComponents(path, label, error))
                return false;

            fs::path current;
            for (const auto& component : path)
            {
                if (component == path.root_name())
                {
                    current = component;
                    continue;
                }
                if (component == path.root_directory())
                {
                    current = current.empty() ? component : current / component;
                    continue;
                }

                current = current.empty() ? component : current / component;
                std::error_code ec;
                const fs::file_status status = fs::symlink_status(current, ec);
                if (status.type() == fs::file_type::not_found)
                    return true;
                if (ec)
                {
                    error = std::string(label) + " path component is not accessible: " + ec.message();
                    return false;
                }
                if (fs::is_symlink(status))
                {
                    error = std::string(label) + " path component must not be a symlink";
                    return false;
                }
                if (current != path && !fs::is_directory(status))
                {
                    error = std::string(label) + " path component must be a directory";
                    return false;
                }
            }
            return true;
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
            const auto it = PluginOwnerApiStates().find(owner);
            if (it != PluginOwnerApiStates().end())
                it->second.Unloading = true;
        }

        void ClearPluginOwnerUnloading(void* owner)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            const auto it = PluginOwnerApiStates().find(owner);
            if (it != PluginOwnerApiStates().end())
                it->second.Unloading = false;
        }

        bool IsUnloadingPluginOwnerLocked(void* owner)
        {
            if (!owner)
                return false;
            const auto it = PluginOwnerApiStates().find(owner);
            return it != PluginOwnerApiStates().end() && it->second.Unloading;
        }

        uint64_t AddPluginOwnerToken(void* owner, uint64_t capabilities, ChatEventDispatcher* chatDispatcher,
                                    CommandDispatcher* commands, PlayerLifecycleDispatcher* playerLifecycle)
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
            try
            {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePluginOwnerApiStateFailureForTesting.load(std::memory_order_acquire))
                    throw std::runtime_error("injected plugin owner API state failure");
#endif
                PluginOwnerApiStates()[owner] = PluginOwnerApiState{
                    .Capabilities = capabilities,
                    .ChatDispatcher = chatDispatcher,
                    .Commands = commands,
                    .PlayerLifecycle = playerLifecycle,
                    .Unloading = false,
                };
            }
            catch (...)
            {
                PluginOwnerTokens().erase(token);
                throw;
            }
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
                void* owner = it->second;
                PluginOwnerTokens().erase(it);
                if (!HasPluginOwnerTokenForOwnerLocked(owner))
                    PluginOwnerApiStates().erase(owner);
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

        CommandDispatcher* PluginOwnerCommandDispatcherLocked(void* owner)
        {
            const auto it = PluginOwnerApiStates().find(owner);
            if (it == PluginOwnerApiStates().end())
                return nullptr;
            return it->second.Commands;
        }

        PlayerLifecycleDispatcher* PluginOwnerPlayerLifecycleDispatcherLocked(void* owner)
        {
            const auto it = PluginOwnerApiStates().find(owner);
            return it == PluginOwnerApiStates().end() ? nullptr : it->second.PlayerLifecycle;
        }

        bool PluginOwnerHasCapability(void* owner, uint64_t capability)
        {
            std::lock_guard lock(PluginOwnerLifecycleMutex());
            return PluginOwnerHasCapabilityLocked(owner, capability);
        }
        ChatEventDispatcher* PluginOwnerChatDispatcher(void* owner)
        {
            std::lock_guard lock(PluginOwnerLifecycleMutex());
            return PluginOwnerChatDispatcherLocked(owner);
        }
        CommandDispatcher* PluginOwnerCommandDispatcher(void* owner)
        {
            std::lock_guard lock(PluginOwnerLifecycleMutex());
            return PluginOwnerCommandDispatcherLocked(owner);
        }
        PlayerLifecycleDispatcher* PluginOwnerPlayerLifecycleDispatcher(void* owner)
        {
            std::lock_guard lock(PluginOwnerLifecycleMutex());
            return PluginOwnerPlayerLifecycleDispatcherLocked(owner);
        }

        bool CurrentPluginOwnerHasCapability(uint64_t capability)
        {
            if (!g_CurrentPluginOwner)
                return false;

            std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
            return PluginOwnerHasCapabilityLocked(g_CurrentPluginOwner, capability) &&
                   !IsUnloadingPluginOwnerLocked(g_CurrentPluginOwner);
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
                SafeLogWarnNoThrow(apiName, "rejected callback because the owner token is invalid.");
                return nullptr;
            }

            if (IsUnloadingPluginOwnerLocked(owner))
            {
                SafeLogWarnNoThrow(apiName, "rejected callback because the plugin owner is unloading.");
                return nullptr;
            }

            if (owner == g_CurrentPluginOwner || IsInitializingPluginOwnerLocked(owner))
                return owner;

            if (!IsLoadedPluginOwnerLocked(owner))
            {
                SafeLogWarnNoThrow(apiName, "rejected callback because the owner token does not map to a loaded Obelisk plugin.");
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
                SafeLogWarnNoThrow(apiName, "rejected callback unregister because the owner token is invalid.");
                return nullptr;
            }

            if (owner == g_CurrentPluginOwner ||
                IsInitializingPluginOwnerLocked(owner) ||
                IsLoadedPluginOwnerLocked(owner) ||
                IsUnloadingPluginOwnerLocked(owner))
            {
                return owner;
            }

            SafeLogWarnNoThrow(apiName, "rejected callback unregister because the owner token does not map to an Obelisk plugin lifecycle owner.");
            return nullptr;
        }

        void* ResolveCallbackOwnerForRegistrationLocked(const char* apiName, OnProcessEventCallback callback)
        {
            if (g_CurrentPluginOwner)
            {
                if (IsUnloadingPluginOwnerLocked(g_CurrentPluginOwner))
                {
                    SafeLogWarnNoThrow(apiName, "rejected callback because the plugin owner is unloading.");
                    return nullptr;
                }
                return g_CurrentPluginOwner;
            }

            if (!callback)
                return nullptr;

            Dl_info info{};
            if (dladdr(reinterpret_cast<void*>(callback), &info) == 0)
            {
                SafeLogWarnNoThrow(apiName, "rejected callback because its owning shared object could not be resolved.");
                return nullptr;
            }

            void* owner = info.dli_fbase;
            if (IsUnloadingPluginOwnerLocked(owner))
            {
                SafeLogWarnNoThrow(apiName, "rejected callback because the plugin owner is unloading.");
                return nullptr;
            }

            if (!IsLoadedPluginOwnerLocked(owner))
            {
                SafeLogWarnNoThrow(apiName, "rejected callback because its owner is not a loaded Obelisk plugin.");
                return nullptr;
            }

            return owner;
        }

        template <typename RegisterFn>
        uint64_t RegisterProcessEventCallbackForOwnerToken(const char* apiName, uint64_t ownerToken, RegisterFn registerFn)
        {
            void* owner = nullptr;
            OwnerExecutionGate::Binding binding;
            {
                std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
                owner = ResolveOwnerTokenForRegistrationLocked(apiName, ownerToken);
                if (owner) binding = OwnerExecutionGate::Get().Capture(owner);
            }
            // A retirement racing this admission denies the lease. Once admitted,
            // retirement waits for tracking/rollback without holding this mutex.
            // Deleters may re-enter registration during rollback.

            if (!binding)
                return 0;
            auto execution = OwnerExecutionGate::EnterRegistration(binding);
            if (!execution)
                return 0;
            try { return registerFn(owner); }
            catch (const std::exception& e) { SafeLogErrorNoThrow(apiName, e.what()); }
            catch (...) { SafeLogErrorNoThrow(apiName, "registration failed with unknown exception"); }
            return 0;
        }

        template <typename RegisterFn>
        uint64_t RegisterProcessEventCallbackForCallbackOwner(const char* apiName,
                                                              OnProcessEventCallback callback,
                                                              RegisterFn registerFn)
        {
            void* owner = nullptr;
            OwnerExecutionGate::Binding binding;
            {
                std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
                owner = ResolveCallbackOwnerForRegistrationLocked(apiName, callback);
                if (owner) binding = OwnerExecutionGate::Get().Capture(owner);
            }

            if (!binding)
                return 0;
            auto execution = OwnerExecutionGate::EnterRegistration(binding);
            if (!execution)
                return 0;
            try { return registerFn(owner); }
            catch (const std::exception& e) { SafeLogErrorNoThrow(apiName, e.what()); }
            catch (...) { SafeLogErrorNoThrow(apiName, "registration failed with unknown exception"); }
            return 0;
        }

        ShutdownFunc ResolveShutdownFunc(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            std::string error;
            ShutdownFunc shutdownFunc = reinterpret_cast<ShutdownFunc>(loader.Resolve(handle, "ObeliskPlugin_Shutdown", error));
            if (!shutdownFunc)
            {
                SafeLogInfoNoThrow(
                    "Plugin does not export ObeliskPlugin_Shutdown; unload will use callback owner cleanup only: ",
                    pluginName);
                return nullptr;
            }

            return shutdownFunc;
        }

        bool CallPluginShutdown(const std::string& pluginName, ShutdownFunc shutdownFunc)
        {
            if (!shutdownFunc)
                return true;

            try
            {
                shutdownFunc();
                SafeLogInfoNoThrow("Plugin shutdown completed: ", pluginName);
                return true;
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow(("Plugin " + pluginName + " threw during shutdown").c_str(), e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow(("Plugin " + pluginName + " threw an unknown exception during shutdown").c_str());
            }
            return false;
        }

        bool SafeCloseLibrary(PluginManager::LibraryLoader& loader, void* handle, const std::string& pluginName)
        {
            if (!handle)
                return true;

            try
            {
                std::string closeError;
                if (loader.Close(handle, closeError))
                    return true;

                SafeLogErrorNoThrow(
                    ("Plugin " + pluginName + " library close failed").c_str(),
                    closeError.empty() ? "unknown close failure" : closeError.c_str());
                return false;
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow(("Plugin " + pluginName + " threw while closing library handle").c_str(), e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow(("Plugin " + pluginName + " threw an unknown exception while closing library handle").c_str());
                return false;
            }
        }

        // A reload never writes into an inode that may still be mapped. Keep the
        // basename for plugins which use it, but give each mapping a private directory.
        fs::path CopyPluginGeneration(const fs::path& configRoot, const fs::path& source)
        {
            const fs::path generations = configRoot / ".native-lifecycle" / "generations";
            for (const auto& directory : {configRoot / ".native-lifecycle", generations})
            {
                std::error_code ec;
                fs::create_directory(directory, ec);
                if (ec && ec != std::errc::file_exists)
                    throw std::system_error(ec, "create plugin generations directory");
                const auto status = fs::symlink_status(directory);
                if (!fs::is_directory(status) || fs::is_symlink(status))
                    throw std::runtime_error("plugin generations directory is unsafe");
                fs::permissions(directory, fs::perms::owner_all, fs::perm_options::replace);
            }
            std::string pattern = (generations / "generation-XXXXXX").string();
            if (!::mkdtemp(pattern.data()))
                throw std::system_error(errno, std::generic_category(), "create private plugin generation");
            const fs::path destination = fs::path(pattern) / source.filename();
            const fs::path temporary = destination.string() + ".pending";
            try
            {
                fs::copy_file(source, temporary, fs::copy_options::none);
                fs::permissions(temporary, fs::perms::owner_read | fs::perms::owner_write, fs::perm_options::replace);
                fs::rename(temporary, destination);
            }
            catch (...)
            {
                std::error_code ignored;
                fs::remove(temporary, ignored);
                fs::remove(destination, ignored);
                fs::remove(fs::path(pattern), ignored);
                throw;
            }
            return destination;
        }

        void RemoveClosedGeneration(const fs::path& path) noexcept
        {
            try
            {
                if (path.empty() || path.parent_path().parent_path().filename() != "generations" ||
                    path.parent_path().parent_path().parent_path().filename() != ".native-lifecycle" ||
                    !path.parent_path().filename().string().starts_with("generation-"))
                    return;
                std::string error;
                if (!ValidateExistingPathComponentsNoSymlinks(path, "Closed plugin generation", error))
                    return;
                std::error_code ec;
                fs::remove(path, ec);
                if (!ec) fs::remove(path.parent_path(), ec); // Only the empty private generation, never its source.
            }
            catch (...) { SafeLogWarnNoThrow("Closed plugin generation file cleanup failed."); }
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
                OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS |
                OBELISK_API_CAPABILITY_TIMERS;
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
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
                    descriptor.event_kind_mask =
                        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "inventory_item.allow_equip_check");
                    CopyDescriptorText(descriptor.display_name, "Inventory Item Allow Equip Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
                    descriptor.event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "inventory_item.can_repair_check");
                    CopyDescriptorText(descriptor.display_name, "Inventory Item Can Repair Check");
                    *out = descriptor;
                    return true;
                case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK:
                    descriptor.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
                    descriptor.flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
                    descriptor.event_kind_mask =
                        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
                    descriptor.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
                    CopyDescriptorText(descriptor.stable_name, "inventory_item.use_onto_item_check");
                    CopyDescriptorText(descriptor.display_name, "Inventory Item Use Onto Item Check");
                    *out = descriptor;
                    return true;
                default:
                    return false;
            }
        }

        bool IsGlobalProcessEventCallbackCapabilityEnabledForOwner(void* owner)
        {
            return PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) &&
                AreGlobalProcessEventCallbacksAllowed();
        }

        bool ValidateGlobalProcessEventCallbackCapabilityForOwner(const char* apiName, void* owner)
        {
            if (IsGlobalProcessEventCallbackCapabilityEnabledForOwner(owner))
                return true;

            SafeLogWarnNoThrow(
                apiName,
                "rejected. Use a filtered ProcessEvent callback or enable allow-global-process-event-callbacks for a controlled debug window.");
            return false;
        }

        bool IsFilteredProcessEventCallbackCapabilityEnabledForOwner(void* owner)
        {
            return PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) &&
                AreFilteredProcessEventCallbacksAllowed();
        }

        bool ValidateFilteredProcessEventCallbackCapabilityForOwner(const char* apiName, void* owner)
        {
            if (IsFilteredProcessEventCallbackCapabilityEnabledForOwner(owner))
                return true;

            SafeLogWarnNoThrow(
                apiName,
                "rejected. Filtered ProcessEvent callbacks expose raw UE pointers and require allow-filtered-process-event-callbacks for a controlled debug window.");
            return false;
        }

        bool IsChatMessageEventCapabilityEnabledForOwner(void* owner)
        {
            return PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_CHAT_EVENTS) &&
                AreChatMessageEventsAllowed();
        }

        bool IsGameplayPolicyEventCapabilityEnabledForOwner(void* owner)
        {
            return PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS);
        }

        bool ValidateProcessEventCallback(const char* apiName, OnProcessEventCallback callback)
        {
            if (callback)
                return true;

            SafeLogWarnNoThrow(apiName, "rejected null callback.");
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

            SafeLogWarnNoThrow(apiName, "rejected invalid negative FName index.");
            return false;
        }

        bool ValidateGameplayPolicyEventCallback(const char* apiName,
                                                 ObeliskGameplayPolicyEventCallback callback)
        {
            if (callback)
                return true;

            SafeLogWarnNoThrow(apiName, "rejected null callback.");
            return false;
        }

        bool ValidateChatMessageEventCallback(const char* apiName,
                                              ObeliskChatMessageEventCallback callback)
        {
            if (callback)
                return true;

            SafeLogWarnNoThrow(apiName, "rejected null callback.");
            return false;
        }

        bool ValidateTimerCallback(const char* apiName, ObeliskTimerCallback callback)
        {
            if (callback)
                return true;

            SafeLogWarnNoThrow(apiName, "rejected null callback.");
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

        uint32_t ToGameplayPolicyEventKind(ItemReturnEventKind kind)
        {
            switch (kind)
            {
            case ItemReturnEventKind::AllowEquipItem:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK;
            case ItemReturnEventKind::CanRepair:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK;
            case ItemReturnEventKind::UseItemOntoItem:
                return OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
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
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK;
            case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK:
                return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
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

        void CopyGameplayPolicyScalar(ObeliskGameplayPolicyEvent& publicEvent,
                                      const ItemReturnScalarValue& scalar)
        {
            switch (scalar.Field)
            {
            case ItemReturnScalarField::ReturnValue:
                SetGameplayPolicyBoolField(publicEvent,
                                           OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE,
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

        void InertGameplayPolicyEventCallbackState(GameplayPolicyEventCallbackState* state)
        {
            if (!state)
                return;
            state->EventKindMask = 0;
            state->Callback = nullptr;
            state->UserData = nullptr;
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
                SafeLogErrorNoThrow("Gameplay policy event callback threw", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("Gameplay policy event callback threw an unknown exception.");
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

        void DispatchGameplayPolicyEventFromItemReturn(const ItemReturnEventView& event, void* userData)
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
            for (const ItemReturnScalarValue& scalar : event.Scalars)
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

        void InertChatMessageEventCallbackState(ChatMessageEventCallbackState* state)
        {
            if (!state)
                return;
            state->Callback = nullptr;
            state->UserData = nullptr;
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
                SafeLogErrorNoThrow("Chat message event callback threw", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("Chat message event callback threw an unknown exception.");
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
            if (!IsChatMessageEventCapabilityEnabledForOwner(owner))
                return 0;

            ChatEventDispatcher* dispatcher = PluginOwnerChatDispatcher(owner);
            if (!dispatcher)
                return 0;

            uint64_t publicRegistrationId = 0;
            {
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                publicRegistrationId = AllocateChatMessageRegistrationIdLocked();
            }

            auto state = std::make_unique<ChatMessageEventCallbackState>(
                ChatMessageEventCallbackState{callback, userData});
            ChatMessageEventCallbackState* statePtr = state.get();
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
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePublicChatMessageTrackingFailureForTesting.load(std::memory_order_acquire))
                    throw std::runtime_error("injected public chat message tracking failure");
#endif
                std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
                ChatMessageRegistrations()[publicRegistrationId] = ChatMessageRegistration{
                    .Owner = owner,
                    .Dispatcher = dispatcher,
                    .InternalRegistrationId = internalRegistrationId,
                };
            }
            catch (...)
            {
                InertChatMessageEventCallbackState(statePtr);
                bool unregistered = false;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (!g_ForcePublicChatMessageRollbackUnregisterFailureForTesting.load(
                        std::memory_order_acquire))
#endif
                {
                    unregistered = dispatcher->UnregisterCallbackForOwner(owner, internalRegistrationId);
                }
                if (!unregistered)
                {
                    SafeLogErrorNoThrow(
                        "Public chat message registration rollback failed; callback state was made inert",
                        "dispatcher unregister failed");
                }
                throw;
            }
            return publicRegistrationId;
        }

        bool UnregisterChatMessageRegistrationForOwner(void* owner, uint64_t registrationId, bool ownerCleanupRetry = false)
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
            }

#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
            if (g_ForcePublicChatMessageInternalUnregisterFailureForTesting.load(std::memory_order_acquire))
                return false;
#endif

            if (!registration.Dispatcher)
                return false;

            bool unregistered = registration.Dispatcher->UnregisterCallbackForOwner(
                owner,
                registration.InternalRegistrationId);
            if (!unregistered)
            {
                if (!ownerCleanupRetry)
                    return false;

                const size_t fallbackRemoved = registration.Dispatcher->UnregisterCallbacksForOwner(owner);
                if (fallbackRemoved == 0)
                    return false;
            }

            std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
            const auto it = ChatMessageRegistrations().find(registrationId);
            if (it == ChatMessageRegistrations().end())
                return true;
            if (it->second.Owner == owner &&
                it->second.Dispatcher == registration.Dispatcher &&
                it->second.InternalRegistrationId == registration.InternalRegistrationId)
            {
                ChatMessageRegistrations().erase(it);
            }
            return true;
        }

        size_t UnregisterChatMessageRegistrationsForOwner(void* owner)
        {
            // Backing owner cleanup already drained callbacks and deferred userdata.
            // Only core-owned aliases remain; do not run a foreign deleter twice in a pass.
            std::lock_guard lock(ChatMessageRegistrationMutex());
            size_t count = 0;
            for (const auto& item : ChatMessageRegistrations()) if (item.second.Owner == owner) ++count;
            if (!count) return 0;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
            if (g_ForcePublicChatMessageInternalUnregisterFailureForTesting.load(std::memory_order_acquire))
                throw std::runtime_error("injected public chat owner tracking cleanup failure");
#endif
            for (auto it = ChatMessageRegistrations().begin(); it != ChatMessageRegistrations().end();)
                if (it->second.Owner == owner) it = ChatMessageRegistrations().erase(it); else ++it;
            return count;
        }

        void ReconcileChatMessageRegistrationsForOwnerAfterDispatcherCleanup(
            void* owner,
            ChatEventDispatcher* dispatcher)
        {
            if (!owner || !dispatcher)
                return;

            std::lock_guard<std::mutex> lock(ChatMessageRegistrationMutex());
            for (auto it = ChatMessageRegistrations().begin(); it != ChatMessageRegistrations().end();)
            {
                if (it->second.Owner == owner && it->second.Dispatcher == dispatcher)
                    it = ChatMessageRegistrations().erase(it);
                else
                    ++it;
            }
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
            if (!IsGameplayPolicyEventCapabilityEnabledForOwner(owner))
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
                .ItemReturnRegistrationId = 0,
            };
            GameplayPolicyEventCallbackState* structureState = nullptr;
            GameplayPolicyEventCallbackState* inventoryState = nullptr;
            GameplayPolicyEventCallbackState* itemReturnState = nullptr;
            const auto rollbackStructure = [&]() {
                if (registration.StructureRegistrationId == 0)
                    return;
                InertGameplayPolicyEventCallbackState(structureState);
                bool unregistered = false;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (!g_ForcePublicGameplayPolicyRollbackUnregisterFailureForTesting.load(
                        std::memory_order_acquire))
#endif
                {
                    unregistered = StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.StructureRegistrationId);
                }
                if (!unregistered)
                {
                    SafeLogErrorNoThrow(
                        "Public gameplay policy structure registration rollback failed; callback state was made inert",
                        "dispatcher unregister failed");
                }
            };
            const auto rollbackInventory = [&]() {
                if (registration.InventoryRegistrationId == 0)
                    return;
                InertGameplayPolicyEventCallbackState(inventoryState);
                bool unregistered = false;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (!g_ForcePublicGameplayPolicyRollbackUnregisterFailureForTesting.load(
                        std::memory_order_acquire))
#endif
                {
                    unregistered = InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.InventoryRegistrationId);
                }
                if (!unregistered)
                {
                    SafeLogErrorNoThrow(
                        "Public gameplay policy inventory registration rollback failed; callback state was made inert",
                        "dispatcher unregister failed");
                }
            };
            const auto rollbackItemReturn = [&]() {
                if (registration.ItemReturnRegistrationId == 0)
                    return;
                InertGameplayPolicyEventCallbackState(itemReturnState);
                bool unregistered = false;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (!g_ForcePublicGameplayPolicyRollbackUnregisterFailureForTesting.load(
                        std::memory_order_acquire))
#endif
                {
                    unregistered = ItemReturnEventDispatcher::Get().UnregisterCallbackForOwner(
                        owner,
                        registration.ItemReturnRegistrationId);
                }
                if (!unregistered)
                {
                    SafeLogErrorNoThrow(
                        "Public gameplay policy item-return registration rollback failed; callback state was made inert",
                        "dispatcher unregister failed");
                }
            };

            if ((eventKindMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES) != 0)
            {
                auto state = std::make_unique<GameplayPolicyEventCallbackState>(
                    GameplayPolicyEventCallbackState{eventKindMask, callback, userData});
                structureState = state.get();
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
                const uint64_t inventoryPolicyMask =
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK;
                if ((eventKindMask & inventoryPolicyMask) != 0)
                {
                    auto state = std::make_unique<GameplayPolicyEventCallbackState>(
                        GameplayPolicyEventCallbackState{eventKindMask, callback, userData});
                    inventoryState = state.get();
                    registration.InventoryRegistrationId = InventoryPolicyEventDispatcher::Get().Register(
                        owner,
                        InventoryPolicyEventSubscription{
                            DispatchGameplayPolicyEventFromInventory,
                            state.get(),
                            DestroyGameplayPolicyEventCallbackState,
                        });
                    if (registration.InventoryRegistrationId == 0)
                    {
                        rollbackStructure();
                        return 0;
                    }
                    (void)state.release();
                }

                const uint64_t itemReturnMask =
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK |
                    OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
                if ((eventKindMask & itemReturnMask) != 0)
                {
                    auto state = std::make_unique<GameplayPolicyEventCallbackState>(
                        GameplayPolicyEventCallbackState{eventKindMask, callback, userData});
                    itemReturnState = state.get();
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                    if (g_ForcePublicGameplayPolicyItemReturnRegistrationThrowForTesting.load(
                            std::memory_order_acquire))
                    {
                        throw std::runtime_error(
                            "injected public gameplay policy item-return registration failure");
                    }
#endif
                    registration.ItemReturnRegistrationId = ItemReturnEventDispatcher::Get().Register(
                        owner,
                        ItemReturnEventSubscription{
                            DispatchGameplayPolicyEventFromItemReturn,
                            state.get(),
                            DestroyGameplayPolicyEventCallbackState,
                        });
                    if (registration.ItemReturnRegistrationId == 0)
                    {
                        rollbackStructure();
                        rollbackInventory();
                        return 0;
                    }
                    (void)state.release();
                }
            }
            catch (...)
            {
                rollbackStructure();
                rollbackInventory();
                rollbackItemReturn();
                throw;
            }

            try
            {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePublicGameplayPolicyTrackingFailureForTesting.load(std::memory_order_acquire))
                    throw std::runtime_error("injected public gameplay policy tracking failure");
#endif
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                GameplayPolicyRegistrations()[publicRegistrationId] = registration;
            }
            catch (...)
            {
                rollbackStructure();
                rollbackInventory();
                rollbackItemReturn();
                throw;
            }
            return publicRegistrationId;
        }

        bool UnregisterGameplayPolicyRegistrationForOwner(void* owner,
                                                          uint64_t registrationId,
                                                          bool ownerCleanupRetry = true)
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
            }

            bool cleanupSucceeded = true;
            bool structureRemoved = false;
            bool inventoryRemoved = false;
            bool itemReturnRemoved = false;
            bool trackingCleaned = false;
            const auto reconcileRemovedDispatcherTracking = [&]() -> bool {
                std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
                const auto it = GameplayPolicyRegistrations().find(registrationId);
                if (it == GameplayPolicyRegistrations().end())
                    return true;
                if (it->second.Owner != owner)
                    return true;

                if (structureRemoved &&
                    it->second.StructureRegistrationId == registration.StructureRegistrationId)
                {
                    it->second.StructureRegistrationId = 0;
                }
                if (inventoryRemoved &&
                    it->second.InventoryRegistrationId == registration.InventoryRegistrationId)
                {
                    it->second.InventoryRegistrationId = 0;
                }
                if (itemReturnRemoved &&
                    it->second.ItemReturnRegistrationId == registration.ItemReturnRegistrationId)
                {
                    it->second.ItemReturnRegistrationId = 0;
                }

                if (it->second.StructureRegistrationId == 0 &&
                    it->second.InventoryRegistrationId == 0 &&
                    it->second.ItemReturnRegistrationId == 0)
                {
                    GameplayPolicyRegistrations().erase(it);
                    return true;
                }

                return false;
            };
            const auto syncRemovedDispatcherTracking = [&]() -> bool {
                try
                {
                    trackingCleaned = reconcileRemovedDispatcherTracking();
                    return true;
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("Failed to update gameplay policy tracking after backing callback cleanup",
                                        e.what());
                    return false;
                }
                catch (...)
                {
                    SafeLogErrorNoThrow(
                        "Failed to update gameplay policy tracking after backing callback cleanup with unknown exception");
                    return false;
                }
            };
            try
            {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePublicGameplayPolicyInternalUnregisterFailureForTesting.load(std::memory_order_acquire))
                    cleanupSucceeded = false;
#endif
                if (registration.StructureRegistrationId != 0)
                {
                    if (cleanupSucceeded)
                    {
                        structureRemoved = StructureEventDispatcher::Get().UnregisterCallbackForOwner(
                            owner,
                            registration.StructureRegistrationId);
                        if (!structureRemoved && ownerCleanupRetry)
                        {
                            const size_t fallbackRemoved =
                                StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner);
                            structureRemoved = fallbackRemoved != 0;
                        }
                    }
                    cleanupSucceeded = cleanupSucceeded && structureRemoved;
                    if (structureRemoved && !syncRemovedDispatcherTracking())
                        cleanupSucceeded = false;
                }
                if (registration.InventoryRegistrationId != 0)
                {
                    if (cleanupSucceeded)
                    {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                        if (g_ForcePublicGameplayPolicyInventoryUnregisterFailureForTesting.load(
                                std::memory_order_acquire))
                            throw std::runtime_error("injected public gameplay policy inventory unregister failure");
#endif
                        inventoryRemoved = InventoryPolicyEventDispatcher::Get().UnregisterCallbackForOwner(
                            owner,
                            registration.InventoryRegistrationId);
                        if (!inventoryRemoved && ownerCleanupRetry)
                        {
                            const size_t fallbackRemoved =
                                InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner);
                            inventoryRemoved = fallbackRemoved != 0;
                        }
                    }
                    cleanupSucceeded = cleanupSucceeded && inventoryRemoved;
                    if (inventoryRemoved && !syncRemovedDispatcherTracking())
                        cleanupSucceeded = false;
                }
                if (registration.ItemReturnRegistrationId != 0)
                {
                    if (cleanupSucceeded)
                    {
                        itemReturnRemoved = ItemReturnEventDispatcher::Get().UnregisterCallbackForOwner(
                            owner,
                            registration.ItemReturnRegistrationId);
                        if (!itemReturnRemoved && ownerCleanupRetry)
                        {
                            const size_t fallbackRemoved =
                                ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner);
                            itemReturnRemoved = fallbackRemoved != 0;
                        }
                    }
                    cleanupSucceeded = cleanupSucceeded && itemReturnRemoved;
                    if (itemReturnRemoved && !syncRemovedDispatcherTracking())
                        cleanupSucceeded = false;
                }

                if (!trackingCleaned && !syncRemovedDispatcherTracking())
                    cleanupSucceeded = false;
            }
            catch (...)
            {
                if (structureRemoved || inventoryRemoved || itemReturnRemoved)
                    (void)syncRemovedDispatcherTracking();
                throw;
            }

            return cleanupSucceeded && trackingCleaned;
        }

        size_t UnregisterGameplayPolicyRegistrationsForOwner(void* owner)
        {
            std::lock_guard lock(GameplayPolicyRegistrationMutex());
            size_t count = 0;
            bool inventory = false;
            for (const auto& item : GameplayPolicyRegistrations())
                if (item.second.Owner == owner) { ++count; inventory |= item.second.InventoryRegistrationId != 0; }
            if (!count) return 0;
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
            if (g_ForcePublicGameplayPolicyInternalUnregisterFailureForTesting.load(std::memory_order_acquire) ||
                (inventory && g_ForcePublicGameplayPolicyInventoryUnregisterFailureForTesting.load(std::memory_order_acquire)))
                throw std::runtime_error("injected public gameplay owner tracking cleanup failure");
#endif
            for (auto it = GameplayPolicyRegistrations().begin(); it != GameplayPolicyRegistrations().end();)
                if (it->second.Owner == owner) it = GameplayPolicyRegistrations().erase(it); else ++it;
            return count;
        }

        void ReconcileGameplayPolicyRegistrationsForOwnerAfterDispatcherCleanup(
            void* owner,
            bool structureCleaned,
            bool inventoryCleaned,
            bool itemReturnCleaned)
        {
            if (!owner)
                return;

            std::lock_guard<std::mutex> lock(GameplayPolicyRegistrationMutex());
            for (auto it = GameplayPolicyRegistrations().begin(); it != GameplayPolicyRegistrations().end();)
            {
                if (it->second.Owner != owner)
                {
                    ++it;
                    continue;
                }

                if (structureCleaned)
                    it->second.StructureRegistrationId = 0;
                if (inventoryCleaned)
                    it->second.InventoryRegistrationId = 0;
                if (itemReturnCleaned)
                    it->second.ItemReturnRegistrationId = 0;

                if (it->second.StructureRegistrationId == 0 &&
                    it->second.InventoryRegistrationId == 0 &&
                    it->second.ItemReturnRegistrationId == 0)
                {
                    it = GameplayPolicyRegistrations().erase(it);
                }
                else
                {
                    ++it;
                }
            }
        }

        void SafeLogInfoNoThrow(const char* message, const std::string& detail) noexcept
        {
            try
            {
                if (Logger::IsInitialized())
                    Logger::Get()->info("{}{}", message ? message : "", detail);
            }
            catch (...)
            {
            }
        }

        void SafeLogWarnNoThrow(const char* message, const char* detail) noexcept
        {
            try
            {
                if (!Logger::IsInitialized())
                    return;

                if (detail)
                    Logger::Get()->warn("{}: {}", message ? message : "", detail);
                else
                    Logger::Get()->warn("{}", message ? message : "");
            }
            catch (...)
            {
            }
        }

        void SafeLogErrorNoThrow(const char* message, const char* detail) noexcept
        {
            try
            {
                if (!Logger::IsInitialized())
                    return;

                if (detail)
                    Logger::Get()->error("{}: {}", message ? message : "", detail);
                else
                    Logger::Get()->error("{}", message ? message : "");
            }
            catch (...)
            {
            }
        }

        template <typename Fn>
        class NoThrowScopeExit
        {
        public:
            explicit NoThrowScopeExit(Fn fn)
                : m_Fn(std::move(fn))
            {
            }

            ~NoThrowScopeExit() noexcept
            {
                if (!m_Active)
                    return;

                try
                {
                    m_Fn();
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("Plugin cleanup guard threw during scoped cleanup", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("Plugin cleanup guard threw an unknown exception during scoped cleanup.");
                }
            }

            NoThrowScopeExit(const NoThrowScopeExit&) = delete;
            NoThrowScopeExit& operator=(const NoThrowScopeExit&) = delete;

            void Dismiss()
            {
                m_Active = false;
            }

        private:
            Fn m_Fn;
            bool m_Active = true;
        };

        template <typename Fn>
        NoThrowScopeExit<Fn> MakeScopeExit(Fn fn)
        {
            return NoThrowScopeExit<Fn>(std::move(fn));
        }
    }

    // C-API Wrappers for Plugins
    extern "C" {
        void PluginLogInfo(const char* message) { SafeLogInfoNoThrow("[Plugin] ", message ? message : ""); }
        void PluginLogWarn(const char* message) { SafeLogWarnNoThrow("[Plugin]", message ? message : ""); }
        void PluginLogError(const char* message) { SafeLogErrorNoThrow("[Plugin]", message ? message : ""); }

        void PluginRegisterPreProcessEvent(OnProcessEventCallback callback) {
            if (!ValidateProcessEventCallback("RegisterPreProcessEvent", callback))
                return;
            try
            {
                (void)RegisterProcessEventCallbackForCallbackOwner(
                    "RegisterPreProcessEvent",
                    callback,
                    [callback](void* owner) {
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwner("RegisterPreProcessEvent", owner))
                            return uint64_t{0};
                        return EventManager::Get().RegisterPreProcessEventOwned(
                            owner,
                            callback,
                            PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING));
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEvent rejected callback after exception", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEvent rejected callback after unknown exception.");
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
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwner("RegisterPostProcessEvent", owner))
                            return uint64_t{0};
                        return EventManager::Get().RegisterPostProcessEventOwned(owner, callback);
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterPostProcessEvent rejected callback after exception", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPostProcessEvent rejected callback after unknown exception.");
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
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwner(
                                "RegisterPreProcessEventForNameIndex",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventForNameIndexOwned(
                            owner,
                            nameIndex,
                            callback,
                            PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING));
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEventForNameIndex rejected callback after exception", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEventForNameIndex rejected callback after unknown exception.");
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
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwner(
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
                SafeLogErrorNoThrow("RegisterPostProcessEventForNameIndex rejected callback after exception", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPostProcessEventForNameIndex rejected callback after unknown exception.");
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
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwner(
                                "RegisterPreProcessEventWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventOwned(
                            owner,
                            callback,
                            PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING));
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEventWithOwnerToken rejected callback after exception", e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEventWithOwnerToken rejected callback after unknown exception.");
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
                        if (!ValidateGlobalProcessEventCallbackCapabilityForOwner(
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
                SafeLogErrorNoThrow("RegisterPostProcessEventWithOwnerToken rejected callback after exception", e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPostProcessEventWithOwnerToken rejected callback after unknown exception.");
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
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwner(
                                "RegisterPreProcessEventForNameIndexWithOwnerToken",
                                owner))
                        {
                            return uint64_t{0};
                        }
                        return EventManager::Get().RegisterPreProcessEventForNameIndexOwned(
                            owner,
                            nameIndex,
                            callback,
                            PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING));
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterPreProcessEventForNameIndexWithOwnerToken rejected callback after exception",
                                    e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow(
                    "RegisterPreProcessEventForNameIndexWithOwnerToken rejected callback after unknown exception.");
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
                        if (!ValidateFilteredProcessEventCallbackCapabilityForOwner(
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
                SafeLogErrorNoThrow("RegisterPostProcessEventForNameIndexWithOwnerToken rejected callback after exception",
                                    e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow(
                    "RegisterPostProcessEventForNameIndexWithOwnerToken rejected callback after unknown exception.");
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
                SafeLogErrorNoThrow("UnregisterProcessEventCallbackWithOwnerToken failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterProcessEventCallbackWithOwnerToken failed after unknown exception.");
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
                SafeLogWarnNoThrow("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected empty gameplay policy event mask.");
                return 0;
            }
            if ((eventKindMask & ~OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL) != 0)
            {
                SafeLogWarnNoThrow("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected reserved gameplay policy event mask bits.");
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
                SafeLogErrorNoThrow("RegisterGameplayPolicyEventWithOwnerTokenHandle rejected callback after exception",
                                    e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow(
                    "RegisterGameplayPolicyEventWithOwnerTokenHandle rejected callback after unknown exception.");
                return 0;
            }
        }
        bool PluginUnregisterGameplayPolicyEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId) {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterGameplayPolicyEventWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                return UnregisterGameplayPolicyRegistrationForOwner(owner, registrationId, false);
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("UnregisterGameplayPolicyEventWithOwnerToken failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterGameplayPolicyEventWithOwnerToken failed after unknown exception.");
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
                SafeLogErrorNoThrow("RegisterChatMessageEventWithOwnerTokenHandle rejected callback after exception",
                                    e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow(
                    "RegisterChatMessageEventWithOwnerTokenHandle rejected callback after unknown exception.");
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
                SafeLogErrorNoThrow("UnregisterChatMessageEventWithOwnerToken failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterChatMessageEventWithOwnerToken failed after unknown exception.");
                return false;
            }
        }

        uint64_t PluginRegisterCommandWithOwnerTokenHandle(
            uint64_t ownerToken, const char* commandName, ObeliskCommandCallback callback, void* userData)
        {
            if (!commandName || !callback)
                return 0;
            // Bound the C string scan before copying it into runtime storage.
            const size_t commandSize = strnlen(commandName, 65);
            if (commandSize > 64)
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterCommandWithOwnerTokenHandle", ownerToken, [&](void* owner) -> uint64_t {
                        auto* dispatcher = PluginOwnerCommandDispatcher(owner);
                        if (!dispatcher || !dispatcher->IsAvailable() ||
                            !PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_COMMAND_REPLIES))
                            return 0;
                        Dl_info callbackInfo{};
                        if (!dladdr(reinterpret_cast<void*>(callback), &callbackInfo) || callbackInfo.dli_fbase != owner)
                        {
                            SafeLogWarnNoThrow("RegisterCommandWithOwnerTokenHandle",
                                               "rejected callback outside the owning plugin mapping.");
                            return 0;
                        }
                        return dispatcher->Register(owner, {commandName, commandSize}, callback, userData);
                    });
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterCommandWithOwnerTokenHandle failed after exception.");
                return 0;
            }
        }

        bool PluginUnregisterCommandWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
        {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterCommandWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                CommandDispatcher* dispatcher = nullptr;
                {
                    std::lock_guard lock(PluginOwnerLifecycleMutex());
                    dispatcher = PluginOwnerCommandDispatcherLocked(owner);
                }
                // Never hold the lifecycle lock while waiting for callback quiescence.
                return dispatcher && dispatcher->Unregister(owner, registrationId);
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterCommandWithOwnerToken failed after exception.");
                return false;
            }
        }

        bool PluginReplyToCommandWithOwnerToken(uint64_t ownerToken, uint64_t invocationToken,
                                               ObeliskCommandStringView reply)
        {
            if (!reply.data || reply.size == 0 || reply.size > 1024)
                return false;
            try
            {
                void* owner = nullptr;
                CommandDispatcher* dispatcher = nullptr;
                {
                    std::lock_guard lock(PluginOwnerLifecycleMutex());
                    owner = ResolveOwnerTokenForRegistrationLocked("ReplyToCommandWithOwnerToken", ownerToken);
                    if (!owner || !PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_COMMAND_REPLIES))
                        return false;
                    dispatcher = PluginOwnerCommandDispatcherLocked(owner);
                }
                return dispatcher && dispatcher->Reply(owner, invocationToken, {reply.data, reply.size});
            }
            catch (...)
            {
                return false;
            }
        }

        bool PluginGetCommandPlayerWithOwnerToken(uint64_t ownerToken, uint64_t invocationToken,
                                                  ObeliskCommandPlayer* out)
        {
            if (!out || out->struct_size < sizeof(ObeliskCommandPlayer))
                return false;
            try
            {
                void* owner = nullptr;
                CommandDispatcher* dispatcher = nullptr;
                {
                    std::lock_guard lock(PluginOwnerLifecycleMutex());
                    owner = ResolveOwnerTokenForRegistrationLocked("GetCommandPlayerWithOwnerToken", ownerToken);
                    if (!owner || !PluginOwnerHasCapabilityLocked(owner, OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT))
                        return false;
                    dispatcher = PluginOwnerCommandDispatcherLocked(owner);
                }
                return dispatcher && dispatcher->GetPlayer(owner, invocationToken, out);
            }
            catch (...)
            {
                return false;
            }
        }

        uint64_t PluginRegisterPlayerLifecycleWithOwnerTokenHandle(
            uint64_t ownerToken, ObeliskPlayerLifecycleCallback callback, void* userData)
        {
            if (!callback)
                return 0;
            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterPlayerLifecycleWithOwnerTokenHandle", ownerToken, [&](void* owner) -> uint64_t {
                        auto* dispatcher = PluginOwnerPlayerLifecycleDispatcher(owner);
                        if (!dispatcher || !dispatcher->IsAvailable() ||
                            !PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS))
                            return 0;
                        Dl_info callbackInfo{};
                        if (!dladdr(reinterpret_cast<void*>(callback), &callbackInfo) || callbackInfo.dli_fbase != owner)
                        {
                            SafeLogWarnNoThrow("RegisterPlayerLifecycleWithOwnerTokenHandle",
                                               "rejected callback outside the owning plugin mapping.");
                            return 0;
                        }
                        return dispatcher->Register(owner, callback, userData);
                    });
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterPlayerLifecycleWithOwnerTokenHandle failed after exception.");
                return 0;
            }
        }

        bool PluginUnregisterPlayerLifecycleWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
        {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterPlayerLifecycleWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                PlayerLifecycleDispatcher* dispatcher = nullptr;
                {
                    std::lock_guard lock(PluginOwnerLifecycleMutex());
                    dispatcher = PluginOwnerPlayerLifecycleDispatcherLocked(owner);
                }
                return dispatcher && dispatcher->Unregister(owner, registrationId);
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterPlayerLifecycleWithOwnerToken failed after exception.");
                return false;
            }
        }
        uint64_t PluginRegisterTimerWithOwnerTokenHandle(
            uint64_t ownerToken,
            uint64_t delayMs,
            uint64_t intervalMs,
            uint64_t flags,
            ObeliskTimerCallback callback,
            void* userData) {
            if (!ValidateTimerCallback("RegisterTimerWithOwnerTokenHandle", callback))
                return 0;
            if ((flags & ~OBELISK_TIMER_FLAG_REPEATING) != 0)
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected reserved timer flags.");
                return 0;
            }
            if (delayMs == 0)
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected zero delay.");
                return 0;
            }
            if (!TimerManager::IsSupportedDuration(delayMs))
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected unsupported delay.");
                return 0;
            }
            const bool repeating = (flags & OBELISK_TIMER_FLAG_REPEATING) != 0;
            if (repeating && intervalMs == 0)
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected repeating timer with zero interval.");
                return 0;
            }
            if (repeating && !TimerManager::IsSupportedDuration(intervalMs))
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected unsupported repeating interval.");
                return 0;
            }
            if (!repeating && intervalMs != 0)
            {
                SafeLogWarnNoThrow("RegisterTimerWithOwnerTokenHandle rejected one-shot timer with non-zero interval.");
                return 0;
            }

            try
            {
                return RegisterProcessEventCallbackForOwnerToken(
                    "RegisterTimerWithOwnerTokenHandle",
                    ownerToken,
                    [delayMs, intervalMs, repeating, callback, userData](void* owner) {
                        if (!PluginOwnerHasCapability(owner, OBELISK_API_CAPABILITY_TIMERS))
                            return uint64_t{0};
                        return TimerManager::Get().Register(owner, delayMs, intervalMs, repeating, callback, userData);
                    });
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("RegisterTimerWithOwnerTokenHandle rejected callback after exception", e.what());
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("RegisterTimerWithOwnerTokenHandle rejected callback after unknown exception.");
                return 0;
            }
        }
        bool PluginUnregisterTimerWithOwnerToken(uint64_t ownerToken, uint64_t timerId) {
            try
            {
                void* owner = ResolveOwnerTokenForUnregister("UnregisterTimerWithOwnerToken", ownerToken);
                if (!owner)
                    return false;
                return TimerManager::Get().Unregister(owner, timerId);
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("UnregisterTimerWithOwnerToken failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("UnregisterTimerWithOwnerToken failed after unknown exception.");
                return false;
            }
        }
        bool PluginDescribeResourceKind(uint32_t resourceKind, ObeliskResourceKindDescriptor* out) {
            try
            {
                return DescribeResourceKind(resourceKind, out);
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("DescribeResourceKind failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("DescribeResourceKind failed after unknown exception.");
                return false;
            }
        }
        bool PluginDescribeGameplayPolicyEventKind(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out) {
            try
            {
                return DescribeGameplayPolicyEventKind(eventKind, out);
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("DescribeGameplayPolicyEventKind failed after exception", e.what());
                return false;
            }
            catch (...)
            {
                SafeLogErrorNoThrow("DescribeGameplayPolicyEventKind failed after unknown exception.");
                return false;
            }
        }
        void PluginCallProcessEvent(void* caller, void* function, void* parms) {
            try
            {
                if (!CurrentPluginOwnerHasCapability(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) ||
                    !IsCallProcessEventAllowed())
                {
                    SafeLogWarnNoThrow(
                        "CallProcessEvent rejected. Enable allow-call-process-event only for a controlled plugin init debug window.");
                    return;
                }
                Hooks::ProcessEventHook::CallOriginalProcessEvent(caller, function, parms);
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("CallProcessEvent failed after exception", e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow("CallProcessEvent failed after unknown exception.");
            }
        }
    }

    PluginManager& PluginManager::Get()
    {
        static auto* instance = new PluginManager();
        return *instance;
    }

#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
    void SetPluginCallbackCleanupFailureForTesting(bool enabled)
    {
        g_ForcePluginCallbackCleanupFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPluginTimerCleanupFailureForTesting(bool enabled)
    {
        g_ForcePluginTimerCleanupFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPluginRetentionFailureForTesting(bool enabled)
    {
        g_ForcePluginRetentionFailureForTesting.store(enabled, std::memory_order_release);
        g_PluginRetentionFailureAfterForTesting.store(-1, std::memory_order_release);
    }

    void SetPluginRetentionFailureAfterForTesting(int successfulRetentionsBeforeFailure)
    {
        g_ForcePluginRetentionFailureForTesting.store(false, std::memory_order_release);
        g_PluginRetentionFailureAfterForTesting.store(successfulRetentionsBeforeFailure, std::memory_order_release);
    }

    void SetPublicChatMessageInternalUnregisterFailureForTesting(bool enabled)
    {
        g_ForcePublicChatMessageInternalUnregisterFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicChatMessageRollbackUnregisterFailureForTesting(bool enabled)
    {
        g_ForcePublicChatMessageRollbackUnregisterFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicChatMessageTrackingFailureForTesting(bool enabled)
    {
        g_ForcePublicChatMessageTrackingFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicGameplayPolicyInternalUnregisterFailureForTesting(bool enabled)
    {
        g_ForcePublicGameplayPolicyInternalUnregisterFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicGameplayPolicyInventoryUnregisterFailureForTesting(bool enabled)
    {
        g_ForcePublicGameplayPolicyInventoryUnregisterFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicGameplayPolicyRollbackUnregisterFailureForTesting(bool enabled)
    {
        g_ForcePublicGameplayPolicyRollbackUnregisterFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicGameplayPolicyTrackingFailureForTesting(bool enabled)
    {
        g_ForcePublicGameplayPolicyTrackingFailureForTesting.store(enabled, std::memory_order_release);
    }

    void SetPublicGameplayPolicyItemReturnRegistrationThrowForTesting(bool enabled)
    {
        g_ForcePublicGameplayPolicyItemReturnRegistrationThrowForTesting.store(
            enabled,
            std::memory_order_release);
    }

    void SetPluginOwnerApiStateFailureForTesting(bool enabled)
    {
        g_ForcePluginOwnerApiStateFailureForTesting.store(enabled, std::memory_order_release);
    }

    void ClearPluginOwnerLifecycleForTesting(void* owner, uint64_t token)
    {
        std::lock_guard<std::mutex> lock(PluginOwnerLifecycleMutex());
        LoadedPluginOwners().erase(owner);
        InitializingPluginOwners().erase(owner);
        if (token != 0)
            PluginOwnerTokens().erase(token);
        if (!HasPluginOwnerTokenForOwnerLocked(owner))
            PluginOwnerApiStates().erase(owner);
    }
#endif

    PluginManager::PluginManager()
        : PluginManager(DefaultLoader(), ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader)
        : PluginManager(loader, ChatEventDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher)
        : PluginManager(loader, chatDispatcher, CommandDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher,
                                 CommandDispatcher& commandDispatcher)
        : PluginManager(loader, chatDispatcher, commandDispatcher, PlayerLifecycleDispatcher::Get())
    {
    }

    PluginManager::PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher,
                                 CommandDispatcher& commandDispatcher, PlayerLifecycleDispatcher& playerLifecycleDispatcher)
        : m_Loader(&loader)
        , m_ChatDispatcher(&chatDispatcher)
        , m_CommandDispatcher(&commandDispatcher)
        , m_PlayerLifecycleDispatcher(&playerLifecycleDispatcher)
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
        if (m_CommandDispatcher->IsAvailable())
            m_Api.capabilities |= OBELISK_API_CAPABILITY_COMMAND_REPLIES;
        if (m_CommandDispatcher->IsPlayerSnapshotsAvailable())
            m_Api.capabilities |= OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT;
        if (m_PlayerLifecycleDispatcher->IsAvailable())
            m_Api.capabilities |= OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS;
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
        m_Api.RegisterTimerWithOwnerTokenHandle = PluginRegisterTimerWithOwnerTokenHandle;
        m_Api.UnregisterTimerWithOwnerToken = PluginUnregisterTimerWithOwnerToken;
        m_Api.RegisterCommandWithOwnerTokenHandle = PluginRegisterCommandWithOwnerTokenHandle;
        m_Api.UnregisterCommandWithOwnerToken = PluginUnregisterCommandWithOwnerToken;
        m_Api.ReplyToCommandWithOwnerToken = PluginReplyToCommandWithOwnerToken;
        m_Api.GetCommandPlayerWithOwnerToken = PluginGetCommandPlayerWithOwnerToken;
        m_Api.RegisterPlayerLifecycleWithOwnerTokenHandle = PluginRegisterPlayerLifecycleWithOwnerTokenHandle;
        m_Api.UnregisterPlayerLifecycleWithOwnerToken = PluginUnregisterPlayerLifecycleWithOwnerToken;
        EventManager::SetProcessEventBlockingCapabilityAdvertised(
            (m_Api.capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING) != 0);
    }

#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
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
#endif

    PluginManager::~PluginManager()
    {
        try
        {
            UnloadAll();
        }
        catch (const std::exception& e)
        {
            SafeLogErrorNoThrow("PluginManager destructor suppressed unload exception", e.what());
        }
        catch (...)
        {
            SafeLogErrorNoThrow("PluginManager destructor suppressed unknown unload exception");
        }
    }

    bool PluginManager::UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason,
                                                    std::chrono::steady_clock::time_point deadline)
    {
        bool cleanupSucceeded = true;
        const auto cleanupFamily = [&](const char* label, auto cleanup, bool* familySucceeded = nullptr) -> size_t {
            if (familySucceeded)
                *familySucceeded = true;
            try
            {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePluginCallbackCleanupFailureForTesting.load(std::memory_order_acquire))
                    throw std::runtime_error("injected plugin callback cleanup failure");
#endif
                return cleanup();
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow((std::string("Failed to remove ") + label + " callbacks for plugin " + pluginName).c_str(),
                                    e.what());
                cleanupSucceeded = false;
                if (familySucceeded)
                    *familySucceeded = false;
                return 0;
            }
            catch (...)
            {
                SafeLogErrorNoThrow((std::string("Failed to remove ") + label + " callbacks for plugin " + pluginName +
                                    " with unknown exception").c_str());
                cleanupSucceeded = false;
                if (familySucceeded)
                    *familySucceeded = false;
                return 0;
            }
        };

        bool gameplayPolicyCleanupSucceeded = true, publicChatCleanupSucceeded = true;
        bool chatSucceeded = true, structureSucceeded = true, inventorySucceeded = true, itemReturnSucceeded = true;
        const size_t eventRemoved = cleanupFamily("ProcessEvent", [&]() {
            return EventManager::Get().UnregisterCallbacksForOwner(owner, deadline);
        });
        const size_t timerRemoved = cleanupFamily("timer", [&]() {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
            if (g_ForcePluginTimerCleanupFailureForTesting.load(std::memory_order_acquire))
                throw std::runtime_error("injected plugin timer cleanup failure");
#endif
            return TimerManager::Get().UnregisterCallbacksForOwner(owner, deadline);
        });
        const size_t chatRemoved = cleanupFamily("chat", [&]() {
            return m_ChatDispatcher->UnregisterCallbacksForOwner(owner, deadline);
        }, &chatSucceeded);
        const size_t commandRemoved = cleanupFamily("command", [&]() {
            return m_CommandDispatcher->UnregisterCallbacksForOwner(owner, deadline);
        });
        const size_t playerLifecycleRemoved = cleanupFamily("player lifecycle", [&]() {
            return m_PlayerLifecycleDispatcher->UnregisterCallbacksForOwner(owner, deadline);
        });
        const size_t structureRemoved = cleanupFamily("structure", [&]() {
            return StructureEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline);
        }, &structureSucceeded);
        const size_t inventoryRemoved = cleanupFamily("inventory policy", [&]() {
            return InventoryPolicyEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline);
        }, &inventorySucceeded);
        const size_t itemReturnRemoved = cleanupFamily("item return", [&]() {
            return ItemReturnEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline);
        }, &itemReturnSucceeded);
        const size_t playerPrincipalRemoved = cleanupFamily("player principal", [&]() {
            return PlayerPrincipalEventDispatcher::Get().UnregisterCallbacksForOwner(owner, deadline);
        });
        // Erase wrapper aliases only after their backing owner barriers completed.
        // Native cleanup runs exactly once per family in this pass, with the deadline.
        const size_t publicChatRemoved = cleanupFamily("public chat tracking", [&]() -> size_t {
            if (!chatSucceeded) throw std::runtime_error("chat backing cleanup incomplete");
            return UnregisterChatMessageRegistrationsForOwner(owner);
        }, &publicChatCleanupSucceeded);
        const size_t gameplayPolicyRemoved = cleanupFamily("gameplay policy tracking", [&]() -> size_t {
            if (!structureSucceeded || !inventorySucceeded || !itemReturnSucceeded)
                throw std::runtime_error("gameplay backing cleanup incomplete");
            return UnregisterGameplayPolicyRegistrationsForOwner(owner);
        }, &gameplayPolicyCleanupSucceeded);
        if (!publicChatCleanupSucceeded && chatSucceeded && chatRemoved != 0)
            ReconcileChatMessageRegistrationsForOwnerAfterDispatcherCleanup(owner, m_ChatDispatcher);
        if (!gameplayPolicyCleanupSucceeded)
            ReconcileGameplayPolicyRegistrationsForOwnerAfterDispatcherCleanup(
                owner, structureSucceeded && structureRemoved != 0, inventorySucceeded && inventoryRemoved != 0,
                itemReturnSucceeded && itemReturnRemoved != 0);

        const auto logRemoved = [&](size_t count, const char* label) {
            if (count == 0)
                return;
            SafeLogInfoNoThrow("Removed plugin callback(s): ",
                               std::to_string(count) + " " + label + " " + pluginName + " " + (reason ? reason : ""));
        };

        logRemoved(gameplayPolicyRemoved, "gameplay policy");
        logRemoved(eventRemoved, "ProcessEvent");
        logRemoved(publicChatRemoved, "public chat");
        logRemoved(timerRemoved, "timer");
        logRemoved(chatRemoved, "chat");
        logRemoved(commandRemoved, "command");
        logRemoved(playerLifecycleRemoved, "player lifecycle");
        logRemoved(structureRemoved, "structure");
        logRemoved(inventoryRemoved, "inventory policy");
        logRemoved(itemReturnRemoved, "item return");
        logRemoved(playerPrincipalRemoved, "player principal");

        return cleanupSucceeded;
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
        if (g_CurrentPluginOwner || OwnerExecutionGate::IsInsideExecution() || GameplayCallbackScope::Current())
        {
            SafeLogWarnNoThrow("Plugin loading rejected inside plugin execution.");
            return;
        }
        std::lock_guard<std::timed_mutex> control(m_ControlMutex);
        LoadPluginsImpl(directory);
    }

    void PluginManager::LoadPluginsImpl(const std::string& directory, const fs::path& selectedSource,
                                         std::string_view expectedPluginId, std::chrono::steady_clock::time_point deadline)
    {
        try
        {
            const char* instanceIdEnv = std::getenv("OBELISK_INSTANCE_ID");
            const std::string instanceId = instanceIdEnv ? instanceIdEnv : "";
            if (!IsSafeInstanceId(instanceId))
            {
                OBELISK_ERROR("OBELISK_INSTANCE_ID must be a non-empty safe instance id before plugin loading. Plugins will not be loaded.");
                return;
            }

            const char* configRootEnv = std::getenv("OBELISK_CONFIG_DIR");
            if (!configRootEnv || configRootEnv[0] == '\0')
            {
                OBELISK_ERROR("OBELISK_CONFIG_DIR is required for plugin loading. Plugins will not be loaded.");
                return;
            }

            const fs::path configRoot = configRootEnv;
            std::string configRootComponentError;
            if (!ValidateExistingPathComponentsNoSymlinks(configRoot, "OBELISK_CONFIG_DIR", configRootComponentError))
            {
                OBELISK_ERROR("Invalid OBELISK_CONFIG_DIR: {}. Plugins will not be loaded.",
                              configRootComponentError);
                return;
            }

            std::string configRootError;
            if (!ValidatePluginConfigRoot(configRoot, true, configRootError))
            {
                OBELISK_ERROR("Invalid OBELISK_CONFIG_DIR: {}. Plugins will not be loaded.", configRootError);
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

            std::string pluginDirectoryError;
            if (!ValidateExistingPathComponentsNoSymlinks(pluginDirectory, "Plugin directory", pluginDirectoryError))
            {
                OBELISK_ERROR("Plugin directory {} rejected: {}. Plugins will not be loaded.",
                              directory,
                              pluginDirectoryError);
                return;
            }

            std::error_code pluginDirectoryStatusError;
            const fs::file_status pluginDirectoryStatus =
                fs::symlink_status(pluginDirectory, pluginDirectoryStatusError);
            if (pluginDirectoryStatusError)
            {
                OBELISK_ERROR("Plugin directory {} is not accessible: {}. Plugins will not be loaded.",
                              directory,
                              pluginDirectoryStatusError.message());
                return;
            }
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
            std::error_code directoryIteratorError;
            fs::directory_iterator iterator(pluginDirectory, fs::directory_options::none, directoryIteratorError);
            if (directoryIteratorError)
            {
                OBELISK_ERROR("Plugin directory {} could not be opened: {}. Plugins will not be loaded.",
                              directory,
                              directoryIteratorError.message());
                return;
            }

            for (fs::directory_iterator end; iterator != end; iterator.increment(directoryIteratorError))
            {
                if (directoryIteratorError)
                {
                    OBELISK_ERROR("Plugin directory {} iteration failed: {}. Plugins will not be loaded.",
                                  directory,
                                  directoryIteratorError.message());
                    return;
                }

                const auto& entry = *iterator;
                if (entry.path().extension() != ".so")
                    continue;

                std::error_code entryStatusError;
                const fs::file_status entryStatus = entry.symlink_status(entryStatusError);
                if (entryStatusError)
                {
                    OBELISK_WARN("Skipping plugin candidate {} because its status could not be read: {}.",
                                 entry.path().filename().string(),
                                 entryStatusError.message());
                    continue;
                }

                if (fs::is_symlink(entryStatus))
                {
                    OBELISK_WARN("Skipping plugin candidate {} because plugin symlinks are not allowed.", entry.path().filename().string());
                    continue;
                }

                if (fs::is_regular_file(entryStatus) && (selectedSource.empty() || entry.path() == selectedSource))
                    plugins.push_back(entry.path());
            }
            if (directoryIteratorError)
            {
                OBELISK_ERROR("Plugin directory {} iteration failed: {}. Plugins will not be loaded.",
                              directory,
                              directoryIteratorError.message());
                return;
            }

            std::sort(plugins.begin(), plugins.end());
            OBELISK_INFO("Scanning for plugins in {}. Found {} candidate(s).", directory, plugins.size());

            std::unordered_set<std::string> pluginIds;
            for (const auto& path : plugins)
            {
                std::string pluginName = path.filename().string();

                if (std::any_of(m_LoadedPlugins.begin(), m_LoadedPlugins.end(), [&](const PluginInfo& loaded) {
                        return loaded.sourcePath == path;
                    }))
                    continue; // Do not run constructors/GetInfo while this source is still active or retained.
                OBELISK_INFO("Loading plugin: {}", pluginName);

                std::error_code candidateStatusError;
                const fs::file_status candidateStatus = fs::symlink_status(path, candidateStatusError);
                if (candidateStatusError)
                {
                    OBELISK_WARN("Skipping plugin candidate {} because its status could not be rechecked: {}.",
                                 pluginName,
                                 candidateStatusError.message());
                    continue;
                }
                if (fs::is_symlink(candidateStatus) || !fs::is_regular_file(candidateStatus))
                {
                    OBELISK_WARN("Skipping plugin candidate {} because it is no longer a regular non-symlink file.",
                                 pluginName);
                    continue;
                }
                std::string candidatePathError;
                if (!ValidateExistingPathComponentsNoSymlinks(path, "Plugin candidate", candidatePathError))
                {
                    OBELISK_WARN("Skipping plugin candidate {} because its path is unsafe: {}.",
                                 pluginName,
                                 candidatePathError);
                    continue;
                }

                std::string loaderError;
                std::string generationRootError;
                if (!ValidateExistingPathComponentsNoSymlinks(configRoot, "OBELISK_CONFIG_DIR", generationRootError))
                {
                    OBELISK_ERROR("Plugin {} generation copy rejected: {}", pluginName, generationRootError);
                    continue;
                }
                if (std::chrono::steady_clock::now() >= deadline)
                    return;
                const fs::path generationPath = CopyPluginGeneration(configRoot, path);
                if (std::chrono::steady_clock::now() >= deadline)
                {
                    RemoveClosedGeneration(generationPath);
                    return;
                }
                void* handle = nullptr;
                {
                    auto execution = OwnerExecutionGate::EnterLifecycle({}, OwnerExecutionGate::LifecycleEntry::Cleanup);
                    try { handle = m_Loader->Open(generationPath, loaderError); }
                    catch (const std::exception& e) { loaderError = e.what(); }
                    catch (...) { loaderError = "library open threw"; }
                }
                if (!handle)
                {
                    OBELISK_ERROR("Failed to load plugin {}: {}", pluginName, loaderError);
                    RemoveClosedGeneration(generationPath);
                    continue;
                }

                auto handleCleanup = MakeScopeExit([&]() {
                    auto execution = OwnerExecutionGate::EnterLifecycle({}, OwnerExecutionGate::LifecycleEntry::Cleanup);
                    if (SafeCloseLibrary(*m_Loader, handle, pluginName)) RemoveClosedGeneration(generationPath);
                });

                std::string symbolError;
                GetInfoFunc getInfoFunc = reinterpret_cast<GetInfoFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_GetInfo", symbolError));
                if (!getInfoFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_GetInfo: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                symbolError.clear();
                InitFunc initFunc = reinterpret_cast<InitFunc>(m_Loader->Resolve(handle, "ObeliskPlugin_Init", symbolError));
                void* pluginOwner = m_Loader->GetSymbolOwner(handle, reinterpret_cast<void*>(getInfoFunc));
                if (!pluginOwner || (initFunc && m_Loader->GetSymbolOwner(handle, reinterpret_cast<void*>(initFunc)) != pluginOwner))
                {
                    OBELISK_ERROR("Plugin {} Init/GetInfo must belong to the same mapped library.", pluginName);
                    continue;
                }
                if (OwnerExecutionGate::Get().Capture(pluginOwner))
                {
                    OBELISK_ERROR("Plugin {} owning mapping is already bound; leaving existing generation active.", pluginName);
                    continue;
                }
                if (std::chrono::steady_clock::now() >= deadline)
                    return;
                ObeliskPluginMetadata metadata{};
                bool metadataLoaded = false;
                {
                    auto execution = OwnerExecutionGate::EnterLifecycle({}, OwnerExecutionGate::LifecycleEntry::Cleanup);
                    try { metadataLoaded = getInfoFunc(&metadata); }
                    catch (const std::exception& e) { OBELISK_ERROR("Plugin {} threw while reporting metadata: {}", pluginName, e.what()); }
                    catch (...) { OBELISK_ERROR("Plugin {} threw an unknown exception while reporting metadata.", pluginName); }
                }

                if (!metadataLoaded)
                {
                    OBELISK_ERROR("Plugin {} failed to report metadata. Unloading.", pluginName);
                    continue;
                }

                PreparedPluginConfig preparedConfig;
                std::string configError;
                std::string pluginConfigRootComponentError;
                if (!ValidateExistingPathComponentsNoSymlinks(
                        configRoot,
                        "OBELISK_CONFIG_DIR",
                        pluginConfigRootComponentError))
                {
                    OBELISK_ERROR("Plugin {} metadata/config rejected: OBELISK_CONFIG_DIR became unsafe: {}. Unloading.",
                                  pluginName,
                                  pluginConfigRootComponentError);
                    continue;
                }
                if (!PreparePluginConfig(metadata, configRoot, instanceId, preparedConfig, configError))
                {
                    OBELISK_ERROR("Plugin {} metadata/config rejected: {}. Unloading.", pluginName, configError);
                    continue;
                }

                if (!expectedPluginId.empty() && metadata.plugin_id != expectedPluginId)
                {
                    OBELISK_ERROR("Plugin {} replacement identity differs from the selected plugin.", pluginName);
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

                // Metadata-only disabled plugins still prepare their config. A
                // matching primary-mapping Init is required before activation.
                if (!initFunc)
                {
                    OBELISK_ERROR("Plugin {} is missing ObeliskPlugin_Init: {}. Unloading.", pluginName, symbolError);
                    continue;
                }

                ShutdownFunc shutdownFunc = ResolveShutdownFunc(*m_Loader, handle, pluginName);
                symbolError.clear();
                auto prepareUnload = reinterpret_cast<bool (*)()>(m_Loader->Resolve(handle, "ObeliskPlugin_PrepareUnload", symbolError));
                symbolError.clear();
                auto lifecycleCapabilities = reinterpret_cast<uint32_t (*)()>(m_Loader->Resolve(handle, "ObeliskPlugin_LifecycleCapabilities", symbolError));
                const auto ownSymbol = [&](auto symbol) {
                    return !symbol || m_Loader->GetSymbolOwner(handle, reinterpret_cast<void*>(symbol)) == pluginOwner;
                };
                if (!ownSymbol(shutdownFunc) || !ownSymbol(prepareUnload) || !ownSymbol(lifecycleCapabilities))
                {
                    OBELISK_ERROR("Plugin {} lifecycle exports must belong to its Init mapping.", pluginName);
                    continue;
                }
                if (std::chrono::steady_clock::now() >= deadline)
                    return;
                uint32_t lifecycleFlags = 0;
                if (lifecycleCapabilities)
                {
                    auto execution = OwnerExecutionGate::EnterLifecycle({}, OwnerExecutionGate::LifecycleEntry::Cleanup);
                    try { lifecycleFlags = lifecycleCapabilities(); }
                    catch (...) { OBELISK_ERROR("Plugin {} lifecycle declaration threw.", pluginName); continue; }
                }
                // This is a cooperative declaration, not a proof about arbitrary plugin code.
                if (lifecycleFlags != 0 && lifecycleFlags != 1u)
                {
                    OBELISK_ERROR("Plugin {} declares unsupported lifecycle capability bits.", pluginName);
                    continue;
                }
                if (!expectedPluginId.empty() && (lifecycleFlags != 1u || !prepareUnload))
                {
                    OBELISK_ERROR("Plugin {} replacement does not declare cooperative managed callbacks.", pluginName);
                    continue;
                }
                m_KnownPlugins[metadata.plugin_id] = {path, lifecycleFlags == 1u && prepareUnload};
                m_LoadedPlugins.reserve(m_LoadedPlugins.size() + 1);
                const uint64_t pluginOwnerToken = AddPluginOwnerToken(pluginOwner, m_Api.capabilities, m_ChatDispatcher,
                                                                     m_CommandDispatcher, m_PlayerLifecycleDispatcher);
                auto tokenRollback = MakeScopeExit([&]() { RemovePluginOwnerToken(pluginOwnerToken); });
                auto binding = OwnerExecutionGate::Get().Bind(pluginOwner, pluginOwnerToken);
                if (!binding)
                    throw std::runtime_error("plugin execution binding could not be created");
                auto bindingRollback = MakeScopeExit([&]() {
                    if (OwnerExecutionGate::Get().RetireAndDrain(binding, std::chrono::steady_clock::now()) == OwnerExecutionGate::Result::Ok)
                        OwnerExecutionGate::Get().Forget(binding);
                });
                PluginInfo plugin{pluginName, metadata.plugin_id, handle, pluginOwner, pluginOwnerToken, shutdownFunc};
                plugin.sourcePath = path;
                plugin.generationPath = generationPath;
                plugin.execution = binding;
                plugin.prepareUnload = prepareUnload;
                plugin.lifecycleCapabilities = lifecycleFlags;
                tokenRollback.Dismiss();
                handleCleanup.Dismiss();
                auto initializationRollback = MakeScopeExit([&]() {
                    std::string reason;
                    const auto rollbackDeadline = deadline == std::chrono::steady_clock::time_point::max()
                        ? std::chrono::steady_clock::now() + std::chrono::seconds(30) : deadline;
                    if (!RetirePlugin(plugin, rollbackDeadline, false, reason))
                    {
                        m_LoadedPlugins.push_back(std::move(plugin)); // Storage was reserved before plugin execution.
                        SafeLogErrorNoThrow("Retaining failed plugin generation mapped", reason.c_str());
                    }
                });
                bindingRollback.Dismiss();
                AddInitializingPluginOwner(pluginOwner);
                const std::string configDir = preparedConfig.directory.string();
                const std::string configPath = preparedConfig.path.string();
                ObeliskPluginInitContext initContext{
                    OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION, sizeof(ObeliskPluginInitContext),
                    configDir.c_str(), configPath.c_str(), instanceId.c_str(), pluginOwnerToken
                };
                if (std::chrono::steady_clock::now() >= deadline)
                    return;
                {
                    auto execution = OwnerExecutionGate::EnterLifecycle(binding, OwnerExecutionGate::LifecycleEntry::Init);
                    if (!execution)
                        throw std::runtime_error("plugin initialization execution denied");
                    void* previousOwner = g_CurrentPluginOwner;
                    g_CurrentPluginOwner = pluginOwner;
                    auto ownerRestore = MakeScopeExit([&]() { g_CurrentPluginOwner = previousOwner; });
                    plugin.initAttempted = true;
                    try
                    {
                        ObeliskApi pluginApi = m_Api;
                        plugin.initialized = initFunc(&pluginApi, &initContext);
                    }
                    catch (const std::exception& e) { OBELISK_ERROR("Plugin {} threw during initialization: {}", pluginName, e.what()); }
                    catch (...) { OBELISK_ERROR("Plugin {} threw an unknown exception during initialization.", pluginName); }
                }
                if (!plugin.initialized)
                {
                    OBELISK_ERROR("Plugin {} failed to initialize.", pluginName);
                    continue;
                }
                if (std::chrono::steady_clock::now() >= deadline)
                    return;
                AddLoadedPluginOwner(pluginOwner);
                if (OwnerExecutionGate::Get().Activate(binding) != OwnerExecutionGate::Result::Ok)
                    throw std::runtime_error("plugin activation failed");
                RemoveInitializingPluginOwner(pluginOwner);
                m_LoadedPlugins.push_back(std::move(plugin));
                initializationRollback.Dismiss();
                OBELISK_INFO("Plugin {} initialized successfully.", pluginName);
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

    bool PluginManager::RetirePlugin(PluginInfo& plugin, std::chrono::steady_clock::time_point deadline,
                                     bool requireCooperative, std::string& reason)
    {
        const auto fail = [&](const char* value) { plugin.lastFailure = value; reason = value; return false; };
        if (plugin.shutdownFailed)
            return fail("shutdown_failed_retained_mapping");
        if (plugin.prepareUnloadFailed)
            return fail("prepare_unload_failed_retained_mapping");
        if (requireCooperative && (plugin.lifecycleCapabilities != 1u || !plugin.prepareUnload))
            return fail("cooperative_unload_not_declared");
        auto& gate = OwnerExecutionGate::Get();
        if (gate.RetireAndDrain(plugin.execution, deadline) != OwnerExecutionGate::Result::Ok)
            return fail("execution_drain_incomplete");
        if (std::chrono::steady_clock::now() >= deadline)
            return fail("operation_deadline_expired");
        // Unknown legacy workers cannot be made safe by callback cleanup. Keep
        // their mapping and userdata resident even when the runtime is stopping.
        if (plugin.lifecycleCapabilities != 1u || !plugin.prepareUnload)
            return fail("cooperative_unload_not_declared_retained_mapping");
        // Retirement closes callback and registration admission before token changes.
        try { MarkPluginOwnerUnloading(plugin.owner); }
        catch (...) { return fail("owner_retirement_failed"); }
        {
            auto execution = OwnerExecutionGate::EnterLifecycle(plugin.execution, OwnerExecutionGate::LifecycleEntry::Cleanup);
            if (!execution)
                return fail("cleanup_execution_denied");
            bool cleaned = false;
            try { cleaned = UnregisterPluginCallbacks(plugin.name, plugin.owner, "retired; before Shutdown and dlclose", deadline); }
            catch (...) { cleaned = false; }
            if (!cleaned)
                return fail("registration_cleanup_incomplete");
        }
        if (gate.RetireAndDrain(plugin.execution, deadline) != OwnerExecutionGate::Result::Ok)
            return fail("cleanup_drain_incomplete");
        if (std::chrono::steady_clock::now() >= deadline)
            return fail("operation_deadline_expired");
        if (plugin.initialized && plugin.lifecycleCapabilities == 1u && plugin.prepareUnload && !plugin.shutdownCalled)
        {
            auto execution = OwnerExecutionGate::EnterLifecycle(plugin.execution, OwnerExecutionGate::LifecycleEntry::Cleanup);
            if (!execution)
                return fail("prepare_unload_execution_denied");
            void* previousOwner = g_CurrentPluginOwner;
            g_CurrentPluginOwner = plugin.owner;
            auto restore = MakeScopeExit([&]() { g_CurrentPluginOwner = previousOwner; });
            try
            {
                if (!plugin.prepareUnload())
                    return fail("prepare_unload_refused");
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow("Plugin PrepareUnload threw; retaining mapping", e.what());
                plugin.prepareUnloadFailed = true;
                return fail("prepare_unload_threw");
            }
            catch (...) { plugin.prepareUnloadFailed = true; return fail("prepare_unload_threw"); }
        }
        if (std::chrono::steady_clock::now() >= deadline)
            return fail("operation_deadline_expired");
        if (!plugin.shutdownCalled && plugin.initAttempted)
        {
            auto execution = OwnerExecutionGate::EnterLifecycle(plugin.execution, OwnerExecutionGate::LifecycleEntry::Shutdown);
            if (!execution)
                return fail("shutdown_execution_denied");
            void* previousOwner = g_CurrentPluginOwner;
            g_CurrentPluginOwner = plugin.owner;
            auto restore = MakeScopeExit([&]() { g_CurrentPluginOwner = previousOwner; });
            plugin.shutdownAttempted = true;
            if (!CallPluginShutdown(plugin.name, plugin.shutdown))
            {
                plugin.shutdownFailed = true;
                return fail("shutdown_threw");
            }
            plugin.shutdownCalled = true;
        }
        if (std::chrono::steady_clock::now() >= deadline)
            return fail("operation_deadline_expired");
        {
            auto execution = OwnerExecutionGate::EnterLifecycle(plugin.execution, OwnerExecutionGate::LifecycleEntry::Cleanup);
            if (!execution || !SafeCloseLibrary(*m_Loader, plugin.handle, plugin.name))
                return fail("library_close_failed");
        }
        plugin.handle = nullptr;
        // A successful close makes this generation permanently stale. No address
        // reuse can revive captured subscriptions from its old Binding.
        if (gate.Forget(plugin.execution) != OwnerExecutionGate::Result::Ok)
        {
            reason = "closed_generation_forget_failed";
            SafeLogErrorNoThrow("Closed plugin generation could not be forgotten", plugin.name.c_str());
        }
        RemoveLoadedPluginOwner(plugin.owner);
        RemoveInitializingPluginOwner(plugin.owner);
        RemovePluginOwnerToken(plugin.ownerToken);
        ClearPluginOwnerUnloading(plugin.owner);
        RemoveClosedGeneration(plugin.generationPath);
        return true;
    }

    nlohmann::json PluginManager::ExecuteOperation(std::string_view action, std::string_view pluginId,
                                                   std::chrono::steady_clock::time_point deadline)
    {
        using Gate = OwnerExecutionGate;
        nlohmann::json result{{"ok", false}, {"action", action}, {"plugin_id", pluginId},
                              {"state", "unknown"}, {"reason", ""}};
        // Test before locking: waiting here from an admitted callback can deadlock
        // against the controller that is draining that same callback.
        if (g_CurrentPluginOwner || Gate::IsInsideExecution() || GameplayCallbackScope::Current())
        {
            result["reason"] = "control_inside_plugin_execution";
            return result;
        }
        std::unique_lock<std::timed_mutex> control(m_ControlMutex, std::defer_lock);
        if (!control.try_lock_until(deadline))
        {
            result["reason"] = "control_busy_or_deadline_expired";
            return result;
        }
        if (std::chrono::steady_clock::now() >= deadline)
        {
            result["reason"] = "operation_deadline_expired";
            return result;
        }
        const auto phaseName = [](Gate::Phase phase) {
            switch (phase) {
                case Gate::Phase::Initializing: return "initializing";
                case Gate::Phase::Running: return "running";
                case Gate::Phase::Pausing: return "pausing";
                case Gate::Phase::Paused: return "paused";
                case Gate::Phase::Retiring: return "retiring";
                case Gate::Phase::Retired: return "retired";
                default: return "missing";
            }
        };
        const auto describe = [&](const std::string& id, const KnownPlugin& known) {
            nlohmann::json value{{"plugin_id", id}, {"state", "stopped"}, {"cooperative", known.managedCallbacksOnly}};
            const auto loaded = std::find_if(m_LoadedPlugins.begin(), m_LoadedPlugins.end(), [&](const auto& p) { return p.pluginId == id; });
            if (loaded != m_LoadedPlugins.end()) {
                const auto state = Gate::Get().Inspect(loaded->execution);
                value["state"] = phaseName(state.phase);
                value["in_flight"] = state.inFlight;
                value["generation"] = state.generation;
                value["faulted"] = state.faulted;
                value["retained"] = state.phase == Gate::Phase::Retiring || state.phase == Gate::Phase::Retired;
                value["shutdown_failed"] = loaded->shutdownFailed;
                value["prepare_unload_failed"] = loaded->prepareUnloadFailed;
                value["last_failure"] = loaded->lastFailure;
            }
            return value;
        };
        if (action == "status")
        {
            result["plugins"] = nlohmann::json::array();
            std::vector<std::string> ids;
            for (const auto& item : m_KnownPlugins) ids.push_back(item.first);
            std::sort(ids.begin(), ids.end());
            for (const auto& id : ids)
                if (pluginId.empty() || pluginId == id)
                    result["plugins"].push_back(describe(id, m_KnownPlugins.at(id)));
            result["ok"] = pluginId.empty() || m_KnownPlugins.count(std::string(pluginId));
            result["state"] = "status";
            if (!result["ok"].get<bool>()) result["reason"] = "unknown_plugin";
            return result;
        }
        if (action != "start" && action != "pause" && action != "resume" && action != "stop" && action != "reload")
        {
            result["reason"] = "unknown_action";
            return result;
        }
        const auto known = m_KnownPlugins.find(std::string(pluginId));
        if (known == m_KnownPlugins.end())
        {
            result["reason"] = "unknown_plugin";
            return result;
        }
        auto loaded = std::find_if(m_LoadedPlugins.begin(), m_LoadedPlugins.end(), [&](const auto& p) { return p.pluginId == pluginId; });
        if (action == "pause" || action == "resume")
        {
            if (loaded == m_LoadedPlugins.end()) result["reason"] = "plugin_stopped";
            else if (loaded->lifecycleCapabilities != 1u || !loaded->prepareUnload)
                result["reason"] = "cooperative_lifecycle_not_declared";
            else {
                const auto outcome = action == "pause" ? Gate::Get().Pause(loaded->execution, deadline) : Gate::Get().Resume(loaded->execution);
                result["ok"] = outcome == Gate::Result::Ok;
                if (outcome != Gate::Result::Ok) result["reason"] = "transition_or_drain_incomplete";
                // Timer admission resumes without replacing registrations or deadlines.
                if (outcome == Gate::Result::Ok && action == "resume") TimerManager::Get().NotifyOwnerResumed(loaded->owner);
            }
        }
        else if (action == "stop" || action == "reload")
        {
            if (loaded == m_LoadedPlugins.end()) result["reason"] = "plugin_stopped";
            else {
                std::string reason;
                if (RetirePlugin(*loaded, deadline, true, reason)) {
                    m_LoadedPlugins.erase(loaded);
                    result["ok"] = true;
                } else result["reason"] = reason;
            }
        }
        if (action == "start" || (action == "reload" && result["ok"].get<bool>()))
        {
            result["ok"] = false;
            if (IsPluginIdLoaded(std::string(pluginId))) result["reason"] = "plugin_already_mapped";
            else if (!known->second.managedCallbacksOnly) result["reason"] = "cooperative_unload_not_declared";
            else if (std::chrono::steady_clock::now() >= deadline) result["reason"] = "operation_deadline_expired";
            else {
                const fs::path source = known->second.sourcePath;
                LoadPluginsImpl(source.parent_path().string(), source, pluginId, deadline);
                const auto started = std::find_if(m_LoadedPlugins.begin(), m_LoadedPlugins.end(), [&](const auto& p) {
                    return p.pluginId == pluginId && p.initialized &&
                           Gate::Get().Inspect(p.execution).phase == Gate::Phase::Running;
                });
                result["ok"] = started != m_LoadedPlugins.end();
                if (!result["ok"].get<bool>()) result["reason"] = "plugin_start_failed";
            }
        }
        result["state"] = describe(std::string(pluginId), m_KnownPlugins.at(std::string(pluginId)))["state"];
        return result;
    }

    void PluginManager::UnloadAll()
    {
        if (g_CurrentPluginOwner || OwnerExecutionGate::IsInsideExecution() || GameplayCallbackScope::Current())
        {
            SafeLogWarnNoThrow("Plugin unload rejected inside plugin execution.");
            return;
        }
        std::lock_guard<std::timed_mutex> control(m_ControlMutex);
        std::vector<PluginInfo> retainedPlugins;
        try
        {
            retainedPlugins.reserve(m_LoadedPlugins.size());
        }
        catch (const std::exception& e)
        {
            SafeLogErrorNoThrow("Plugin unload retention reserve failed; aborting unload pass", e.what());
            return;
        }
        catch (...)
        {
            SafeLogErrorNoThrow("Plugin unload retention reserve failed with unknown exception; aborting unload pass");
            return;
        }

        auto retainPluginForUnloadRetry = [&](const PluginInfo& plugin, const char* failureMessage) noexcept -> bool
        {
            try
            {
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
                if (g_ForcePluginRetentionFailureForTesting.load(std::memory_order_acquire))
                    throw std::runtime_error("injected plugin retention failure");
                int expected = g_PluginRetentionFailureAfterForTesting.load(std::memory_order_acquire);
                while (expected >= 0)
                {
                    if (expected == 0)
                        throw std::runtime_error("injected delayed plugin retention failure");
                    if (g_PluginRetentionFailureAfterForTesting.compare_exchange_weak(
                            expected,
                            expected - 1,
                            std::memory_order_acq_rel,
                            std::memory_order_acquire))
                        break;
                }
#endif
                retainedPlugins.push_back(plugin);
                return true;
            }
            catch (const std::exception& e)
            {
                SafeLogErrorNoThrow(failureMessage, e.what());
            }
            catch (...)
            {
                SafeLogErrorNoThrow(failureMessage, "unknown exception");
            }
            return false;
        };

        for (auto it = m_LoadedPlugins.rbegin(); it != m_LoadedPlugins.rend(); ++it)
        {
            auto& plugin = *it;
            const auto publishPartialUnloadStateAndAbort = [&]() noexcept
            {
                try
                {
                    static_assert(std::is_nothrow_move_constructible_v<PluginInfo>,
                                  "partial unload retry publication must preserve mapped plugins without allocation");
                    m_LoadedPlugins.erase(it.base(), m_LoadedPlugins.end());
                    m_LoadedPlugins.insert(
                        m_LoadedPlugins.end(),
                        std::make_move_iterator(retainedPlugins.rbegin()),
                        std::make_move_iterator(retainedPlugins.rend()));
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("Failed to publish partial unload progress after retention failure", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("Failed to publish partial unload progress after retention failure with unknown exception");
                }
            };
            SafeLogInfoNoThrow("Unloading plugin: ", plugin.name);
            std::string reason;
            if (!RetirePlugin(plugin, std::chrono::steady_clock::now() + std::chrono::seconds(30), false, reason))
            {
                SafeLogErrorNoThrow("Plugin unload incomplete; retaining mapping", reason.c_str());
                if (!retainPluginForUnloadRetry(plugin, "Plugin retention tracking failed; aborting unload pass"))
                {
                    publishPartialUnloadStateAndAbort();
                    return;
                }
            }
        }
        std::reverse(retainedPlugins.begin(), retainedPlugins.end());
        m_LoadedPlugins = std::move(retainedPlugins);
    }
}
