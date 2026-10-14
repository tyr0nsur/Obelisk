#pragma once

#include "ChatEventDispatcher.h"
#include "CommandDispatcher.h"
#include "PlayerLifecycleDispatcher.h"
#include "api/ObeliskApi.h"
#include <filesystem>
#include <string>
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
        };

        std::vector<PluginInfo> m_LoadedPlugins;
        ObeliskApi m_Api{};
        LibraryLoader* m_Loader;
        ChatEventDispatcher* m_ChatDispatcher;
        CommandDispatcher* m_CommandDispatcher;
        PlayerLifecycleDispatcher* m_PlayerLifecycleDispatcher;

        bool UnregisterPluginCallbacks(const std::string& pluginName, void* owner, const char* reason);
        bool IsPluginIdLoaded(const std::string& pluginId) const;
    };
}
