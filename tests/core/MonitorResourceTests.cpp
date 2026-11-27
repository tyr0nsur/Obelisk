#include <obelisk/ObeliskApi.h>
#include "core/PluginConfig.h"
#include <nlohmann/json.hpp>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
using Json = nlohmann::json;
namespace {
ObeliskTimerCallback publish = nullptr;
ObeliskPlayerLifecycleCallback observe = nullptr;
unsigned cancelled = 0;
void Require(bool value, const char* error) { if (!value) throw std::runtime_error(error); }
uint64_t Timer(uint64_t owner, uint64_t delay, uint64_t interval, uint64_t flags, ObeliskTimerCallback fn, void*) {
    Require(owner == 42 && delay == 1000 && interval == 2000 && flags == OBELISK_TIMER_FLAG_REPEATING, "unexpected managed timer contract"); publish = fn; return 1;
}
uint64_t Lifecycle(uint64_t owner, ObeliskPlayerLifecycleCallback fn, void*) { Require(owner == 42, "wrong callback owner"); observe = fn; return 2; }
bool Cancel(uint64_t owner, uint64_t) { Require(owner == 42, "wrong cleanup owner"); ++cancelled; return true; }
Json Read(const std::filesystem::path& p) { std::ifstream file(p); return Json::parse(file); }
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    char pattern[] = "/tmp/obelisk-monitor-resource-XXXXXX"; const char* directory = ::mkdtemp(pattern);
    if (!directory) return 2;
    const std::filesystem::path root(directory);
    std::filesystem::path config, snapshot;
    void* library = nullptr;
    try {
        library = ::dlopen(argv[1], RTLD_NOW | RTLD_LOCAL); Require(library != nullptr, "resource dlopen failed");
        auto init = reinterpret_cast<bool(*)(ObeliskApi*,const ObeliskPluginInitContext*)>(::dlsym(library,"ObeliskPlugin_Init"));
        auto shutdown = reinterpret_cast<void(*)()>(::dlsym(library,"ObeliskPlugin_Shutdown"));
        auto prepare = reinterpret_cast<bool(*)()>(::dlsym(library,"ObeliskPlugin_PrepareUnload"));
        Require(init && shutdown && prepare, "missing cooperative exports");
        auto metadata = reinterpret_cast<bool(*)(ObeliskPluginMetadata*)>(::dlsym(library,"ObeliskPlugin_GetInfo"));
        ObeliskPluginMetadata metadataInfo{}; Require(metadata && metadata(&metadataInfo), "metadata unavailable");
        Obelisk::Core::PreparedPluginConfig prepared; std::string configError;
        Require(Obelisk::Core::PreparePluginConfig(metadataInfo,root,"test-map",prepared,configError), "runtime rejected monitor metadata/config");
        config = prepared.path; snapshot = prepared.directory / "monitor.snapshot.json";
        Require(::chmod(prepared.directory.c_str(),0700) == 0, "cannot secure monitor directory");
        std::ofstream(config) << "{\"enabled\":true,\"allow_all_instances\":false,\"instance_allowlist\":[\"test-map\"]}";

        ObeliskApi api{}; api.abi_version = OBELISK_API_ABI_VERSION; api.struct_size = sizeof(api);
        ObeliskPluginInitContext context{OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION,sizeof(context),prepared.directory.c_str(),config.c_str(),"test-map",42};
        Require(!init(&api,&context), "resource accepted absent timer capability");
        api.capabilities = OBELISK_API_CAPABILITY_TIMERS | OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS;
        api.RegisterTimerWithOwnerTokenHandle = Timer; api.UnregisterTimerWithOwnerToken = Cancel;
        api.RegisterPlayerLifecycleWithOwnerTokenHandle = Lifecycle; api.UnregisterPlayerLifecycleWithOwnerToken = Cancel;
        Require(init(&api,&context) && publish && observe, "managed resource did not start");
        std::string name = "Copied Player", id = "opaque-not-authenticated";
        ObeliskPlayerLifecycleEvent event{}; event.abi_version = OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION; event.struct_size = sizeof(event);
        event.kind = OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED; event.sequence = 1; event.process_epoch = 99;
        event.flags = OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE | OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE;
        event.player_name = {name.data(),name.size()}; event.platform_id = {id.data(),id.size()};
        observe(&event,nullptr); name.assign(name.size(),'X'); id.assign(id.size(),'X');
        publish(1,nullptr); auto data = Read(snapshot);
        Require(data["schema"] == "obelisk.monitor.v1" && data["pid"] == ::getpid(), "snapshot producer identity is incorrect");
        Require(data["process"]["rss_bytes"].get<uint64_t>() > 0 && data["process"]["uptime_seconds"].get<double>() > 0, "native OS metrics unavailable");
        Require(data["player_census"].is_null() && data["game_thread"].is_null(), "resource invented a census or tick measurement");
        Require(data["lifecycle"]["recent_events"][0]["name"] == "Copied Player", "resource retained a borrowed lifecycle pointer");
        Require(data["lifecycle"]["recent_events"][0]["opaque_id"] == "opaque-not-authenticated", "opaque identity changed");
        struct stat info{}; Require(!::stat(snapshot.c_str(),&info) && (info.st_mode & 0777) == 0600, "snapshot permissions are not private");
        for (unsigned i=0;i<80;++i) { event.sequence++; observe(&event,nullptr); }
        publish(1,nullptr); data = Read(snapshot);
        Require(data["sequence"] == 2 && data["lifecycle"]["recent_events"].size() == 32 && data["lifecycle"]["login_observations"] == 81, "event retention is not bounded");
        const auto target = root / "untouched"; std::ofstream(target) << "sentinel";
        std::filesystem::create_symlink(target,prepared.directory / "monitor.tmp"); publish(1,nullptr);
        std::ifstream targetFile(target); std::string sentinel; targetFile >> sentinel; Require(sentinel == "sentinel", "publisher followed a symlink");
        Require(Read(snapshot)["sequence"] == 2, "failed publication replaced the last complete snapshot");
        std::filesystem::remove(prepared.directory / "monitor.tmp");
        Require(prepare(),"prepare unload failed"); shutdown(); Require(cancelled == 2,"managed registrations were not cancelled");
        Require(::dlclose(library) == 0,"resource did not unload"); library = nullptr;
        std::filesystem::remove_all(root); std::cout << "MonitorResourceTests passed\n"; return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; if (library) ::dlclose(library); std::filesystem::remove_all(root); return 1; }
}
