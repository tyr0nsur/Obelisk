#pragma once

#include "ChatEventDispatcher.h"
#include "CommandDispatcher.h"
#include "PlayerLifecycleDispatcher.h"
#include "OwnerExecutionGate.h"
#include "api/ObeliskApi.h"
#include "extern/nlohmann/json.hpp"
#include <chrono>
#include <filesystem>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace Obelisk::Core
{
    class PluginManager
    {
    public:
        struct LibraryLoader {
            virtual ~LibraryLoader() = default;
            virtual void* Open(const std::filesystem::path& path, std::string& error) = 0;
            virtual void* Resolve(void* handle, const char* symbolName, std::string& error) = 0;
            // Return the primary mapping base, or null when symbol belongs to
            // another mapping (including a DT_NEEDED dependency).
            virtual void* GetSymbolOwner(void* handle, void* symbol) = 0;
            virtual bool Close(void* handle, std::string& error) = 0;
        };

        static PluginManager& Get();

        PluginManager();
        explicit PluginManager(LibraryLoader& loader);
        PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher);
        PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher, CommandDispatcher& commandDispatcher);
        PluginManager(LibraryLoader& loader, ChatEventDispatcher& chatDispatcher, CommandDispatcher& commandDispatcher,
                      PlayerLifecycleDispatcher& playerLifecycleDispatcher);
        ~PluginManager();

        void LoadPlugins(const std::string& directory);
        void UnloadAll();
        // Private operator control, invoked by the serialized game-thread pump.
        // No operation may wait while running plugin/callback/lifecycle code.
        nlohmann::json ExecuteOperation(std::string_view action, std::string_view pluginId,
                                       std::chrono::steady_clock::time_point deadline);
#ifdef OBELISK_PLUGIN_MANAGER_ENABLE_TEST_HOOKS
        uint64_t ApiCapabilitiesForTesting() const;
        static void SetNextPluginOwnerTokenForTesting(uint64_t nextOwnerToken);
        static void SetNextChatMessageSequenceForTesting(uint64_t nextSequence);
#endif

    private:
        struct PluginInfo {
            std::string name;
            std::string pluginId;
            void* handle;
            void* owner;
            uint64_t ownerToken;
            void (*shutdown)();
            bool shutdownCalled = false;
            std::filesystem::path sourcePath;
            std::filesystem::path generationPath;
            OwnerExecutionGate::Binding execution;
            bool (*prepareUnload)() = nullptr;
            uint32_t lifecycleCapabilities = 0;
            bool initialized = false;
            bool initAttempted = false;
            bool shutdownAttempted = false;
            bool shutdownFailed = false;
            bool prepareUnloadFailed = false;
            std::string lastFailure;
        };

        struct KnownPlugin {
            std::filesystem::path sourcePath;
            bool managedCallbacksOnly = false;
        };

        std::vector<PluginInfo> m_LoadedPlugins;
        std::unordered_map<std::string, KnownPlugin> m_KnownPlugins;
        std::filesystem::path m_PluginDirectory;
        std::timed_mutex m_ControlMutex;
        ObeliskApi m_Api{};
        LibraryLoader* m_Loader;
        ChatEventDispatcher* m_ChatDispatcher;
        CommandDispatcher* m_CommandDispatcher;
        PlayerLifecycleDispatcher* m_PlayerLifecycleDispatcher;

        bool UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason,
                                       std::chrono::steady_clock::time_point deadline);
        bool IsPluginIdLoaded(const std::string& pluginId) const;
        void LoadPluginsImpl(const std::string& directory, const std::filesystem::path& selectedSource = {},
                             std::string_view expectedPluginId = {},
                             std::chrono::steady_clock::time_point deadline = std::chrono::steady_clock::time_point::max());
        bool RetirePlugin(PluginInfo& plugin, std::chrono::steady_clock::time_point deadline,
                          bool requireCooperative, std::string& reason);
    };
}
