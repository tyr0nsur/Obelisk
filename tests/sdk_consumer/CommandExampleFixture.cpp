#include <obelisk/ObeliskApi.h>
#include "core/CommandDispatcher.h"

#include <dlfcn.h>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Obelisk::Core::CommandDispatcher;
namespace {
CommandDispatcher commands;
int owner, firstPlayer, secondPlayer;
bool failRegistration;
size_t unregisters;
std::vector<std::pair<void*, std::string>> replies;
void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
uint64_t exact(uint64_t token, const char* name, ObeliskCommandCallback callback, void* data) {
    return token == 73 ? commands.Register(&owner, name, callback, data) : 0;
}
uint64_t options(uint64_t token, const char* name, uint64_t flags, ObeliskCommandCallback callback, void* data) {
    return token == 73 && !failRegistration ? commands.RegisterWithOptions(&owner, name, flags, callback, data) : 0;
}
bool unregister(uint64_t token, uint64_t handle) { ++unregisters; return token == 73 && commands.Unregister(&owner, handle); }
bool reply(uint64_t token, uint64_t invocation, ObeliskCommandStringView text) {
    return token == 73 && commands.Reply(&owner, invocation, {text.data, text.size});
}
bool deliver(void* player, std::string_view text, void*) noexcept {
    try { replies.emplace_back(player, text); return true; } catch (...) { return false; }
}
ObeliskApi api() {
    ObeliskApi value{};
    value.abi_version = OBELISK_API_ABI_VERSION;
    value.struct_size = sizeof(value);
    value.capabilities = OBELISK_API_CAPABILITY_COMMAND_REPLIES | OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS;
    value.RegisterCommandWithOwnerTokenHandle = exact;
    value.RegisterCommandWithOptionsWithOwnerTokenHandle = options;
    value.UnregisterCommandWithOwnerToken = unregister;
    value.ReplyToCommandWithOwnerToken = reply;
    return value;
}
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) { std::cerr << dlerror() << '\n'; return 1; }
    try {
        auto info = reinterpret_cast<bool (*)(ObeliskPluginMetadata*)>(dlsym(library, "ObeliskPlugin_GetInfo"));
        auto init = reinterpret_cast<bool (*)(ObeliskApi*, const ObeliskPluginInitContext*)>(dlsym(library, "ObeliskPlugin_Init"));
        auto shutdown = reinterpret_cast<void (*)()>(dlsym(library, "ObeliskPlugin_Shutdown"));
        auto lifecycle = reinterpret_cast<uint32_t (*)()>(dlsym(library, "ObeliskPlugin_LifecycleCapabilities"));
        auto prepare = reinterpret_cast<bool (*)()>(dlsym(library, "ObeliskPlugin_PrepareUnload"));
        require(info && init && shutdown && lifecycle && prepare, "missing lifecycle exports");
        require(!info(nullptr), "null metadata must reject");
        ObeliskPluginMetadata metadata{};
        require(info(&metadata) && std::string(metadata.plugin_id) == "obelisk_sdk_command_plugin", "wrong metadata");
        require(std::string(metadata.default_config_json) == "{\"enabled\":false,\"allow_all_instances\":false,\"instance_allowlist\":[]}", "config must default disabled");
        require(lifecycle() == OBELISK_PLUGIN_LIFECYCLE_MANAGED_CALLBACKS_ONLY && prepare(), "cooperative contract missing");
        ObeliskPluginInitContext context{};
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = sizeof(context);
        context.plugin_owner_token = 73;
        auto value = api();
        require(!init(nullptr, &context) && !init(&value, nullptr), "null init must reject");
        for (size_t size : {offsetof(ObeliskApi, capabilities), offsetof(ObeliskApi, RegisterCommandWithOwnerTokenHandle),
             offsetof(ObeliskApi, UnregisterCommandWithOwnerToken), offsetof(ObeliskApi, ReplyToCommandWithOwnerToken),
             offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle)}) {
            value = api(); value.struct_size = size;
            require(!init(&value, &context), "truncated API must reject");
        }
        value = api(); value.abi_version++;
        require(!init(&value, &context), "unknown API ABI must reject");
        value = api(); context.abi_version++;
        require(!init(&value, &context), "unknown context ABI must reject");
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = offsetof(ObeliskPluginInitContext, plugin_owner_token);
        require(!init(&value, &context), "truncated context must reject");
        context.struct_size = sizeof(context); context.plugin_owner_token = 0;
        require(!init(&value, &context), "zero owner must reject");
        context.plugin_owner_token = 73;
        for (auto capability : {OBELISK_API_CAPABILITY_COMMAND_REPLIES, OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS}) {
            value = api(); value.capabilities &= ~capability;
            require(!init(&value, &context), "missing capability must reject");
        }
        for (int slot = 0; slot < 4; ++slot) {
            value = api();
            if (slot == 0) value.RegisterCommandWithOwnerTokenHandle = nullptr;
            if (slot == 1) value.RegisterCommandWithOptionsWithOwnerTokenHandle = nullptr;
            if (slot == 2) value.UnregisterCommandWithOwnerToken = nullptr;
            if (slot == 3) value.ReplyToCommandWithOwnerToken = nullptr;
            require(!init(&value, &context), "missing slot must reject");
        }
        value = api();
        require(!init(&value, &context), "unavailable native backend must reject");
        commands.SetAvailable(true); failRegistration = true;
        require(!init(&value, &context) && commands.SubscriptionCount() == 0 && unregisters == 1, "partial init must roll back");
        shutdown(); shutdown(); failRegistration = false;
        for (int generation = 0; generation < 2; ++generation) {
            value = api();
            require(init(&value, &context) && commands.SubscriptionCount() == 2, "init must register both commands");
            require(!init(&value, &context) && commands.SubscriptionCount() == 2, "duplicate init must preserve state");
            value = {}; // Runtime owns the borrowed table; the plugin must have copied it.
            replies.clear();
            require(commands.Dispatch(&firstPlayer, "/sdkhello args", 0, deliver) == 0, "legacy exact command changed");
            require(commands.Dispatch(&firstPlayer, "/SDKHELLO", 0, deliver) == 0, "legacy exact case changed");
            require(commands.Dispatch(&firstPlayer, "/sdkhello", 0, deliver) == 1, "hello not dispatched");
            require(commands.Dispatch(&secondPlayer, "/SDKECHO\t  Hola, ñandú", 0, deliver) == 1, "UTF-8 verb not dispatched");
            require(replies.size() == 2 && replies[0].first == &firstPlayer && replies[1].first == &secondPlayer &&
                    replies[0].second == "Hello from the installed ObeliskNative SDK!" && replies[1].second == "Hola, ñandú", "wrong directed reply");
            require(commands.Dispatch(&firstPlayer, "/sdkechox text", 0, deliver) == 0, "prefix collision");
            commands.Dispatch(&firstPlayer, "/sdkecho", 0, deliver);
            require(replies.back().second.starts_with("Usage:"), "missing usage");
            commands.Dispatch(&firstPlayer, "/sdkecho " + std::string(1025, 'x'), 0, deliver);
            require(replies.back().second.starts_with("Usage:"), "oversized reply must reject");
            require(prepare(), "unload must be cooperative"); shutdown(); shutdown();
            require(commands.SubscriptionCount() == 0 && commands.Dispatch(&firstPlayer, "/sdkhello", 0, deliver) == 0, "shutdown must remove callbacks");
            if (generation == 0) {
                require(dlclose(library) == 0, "library did not close after cleanup");
                library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
                require(library != nullptr, "library did not reload");
                init = reinterpret_cast<bool (*)(ObeliskApi*, const ObeliskPluginInitContext*)>(dlsym(library, "ObeliskPlugin_Init"));
                shutdown = reinterpret_cast<void (*)()>(dlsym(library, "ObeliskPlugin_Shutdown"));
                prepare = reinterpret_cast<bool (*)()>(dlsym(library, "ObeliskPlugin_PrepareUnload"));
                require(init && shutdown && prepare, "reloaded lifecycle exports missing");
            }
        }
        dlclose(library);
        std::cout << "Installed SDK command example: ABI, rollback, directed UTF-8 replies and lifecycle passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        // Retain the mapping on a failed cleanup assertion.
        return 1;
    }
}
