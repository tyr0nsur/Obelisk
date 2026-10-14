#include <obelisk/ObeliskApi.h>
#include <obelisk/ObeliskChatSessionApi.h>
#include <nlohmann/json.hpp>
#include <dlfcn.h>
#include <algorithm>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    namespace fs = std::filesystem;
    void Require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
    struct Registration { uint64_t Handle; std::string Name; ObeliskCommandCallback Callback; void* Data; };
    struct Delivery { uint64_t Token, Epoch; std::string Text; };
    struct Harness
    {
        std::vector<Registration> Registrations;
        std::vector<ObeliskChatSession> Sessions;
        std::vector<Delivery> Delivered;
        std::vector<std::string> Replies;
        uint64_t Current = 11, Owner = 43, ActiveInvocation = 0, NextHandle = 0;
        size_t TotalOverride = 0;
        uint64_t FailDestination = 0;
    };
    Harness* g_Test;
    uint64_t Register(uint64_t owner, const char* name, uint64_t flags, ObeliskCommandCallback callback, void* data)
    {
        if (!g_Test || owner != g_Test->Owner || !callback || !name || flags !=
            (OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE)) return 0;
        const auto handle = ++g_Test->NextHandle; g_Test->Registrations.push_back({handle, name, callback, data}); return handle;
    }
    bool Unregister(uint64_t owner, uint64_t handle)
    {
        if (!g_Test || owner != g_Test->Owner) return false;
        const auto count = g_Test->Registrations.size();
        std::erase_if(g_Test->Registrations, [&](const auto& value) { return value.Handle == handle; });
        return g_Test->Registrations.size() != count;
    }
    bool Scope(uint64_t owner, uint64_t invocation)
    { return g_Test && owner == g_Test->Owner && invocation && invocation == g_Test->ActiveInvocation; }
    bool Reply(uint64_t owner, uint64_t invocation, ObeliskCommandStringView text)
    {
        if (!Scope(owner, invocation) || !text.data) return false;
        g_Test->Replies.emplace_back(text.data, text.size); return true;
    }
    bool Current(uint64_t owner, uint64_t invocation, ObeliskChatSession* out)
    {
        if (!Scope(owner, invocation) || !out) return false;
        const auto found = std::find_if(g_Test->Sessions.begin(), g_Test->Sessions.end(), [](auto value) { return value.session_token == g_Test->Current; });
        if (found == g_Test->Sessions.end()) return false; *out = *found; return true;
    }
    bool List(uint64_t owner, uint64_t invocation, ObeliskChatSession* out, size_t capacity, size_t* written, size_t* total)
    {
        if (!Scope(owner, invocation) || !out || !written || !total || capacity > OBELISK_CHAT_SESSION_LIST_MAX) return false;
        *written = std::min(capacity, g_Test->Sessions.size()); *total = g_Test->TotalOverride ? g_Test->TotalOverride : g_Test->Sessions.size();
        std::copy_n(g_Test->Sessions.begin(), *written, out); return true;
    }
    bool Send(uint64_t owner, uint64_t invocation, uint64_t token, uint64_t epoch, ObeliskCommandStringView text)
    {
        if (!Scope(owner, invocation) || !text.data || token == g_Test->FailDestination ||
            std::none_of(g_Test->Sessions.begin(), g_Test->Sessions.end(), [&](auto value) { return value.session_token == token && value.process_epoch == epoch; })) return false;
        g_Test->Delivered.push_back({token, epoch, std::string(text.data, text.size)}); return true;
    }
    ObeliskChatSession Session(uint64_t token, const char* name)
    {
        ObeliskChatSession value{OBELISK_CHAT_SESSION_ABI_VERSION, sizeof(value), token, 900, OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE};
        value.player_name_size = std::strlen(name); std::memcpy(value.player_name, name, value.player_name_size + 1); return value;
    }
    void Invoke(std::string_view verb, std::string message)
    {
        const auto found = std::find_if(g_Test->Registrations.begin(), g_Test->Registrations.end(), [&](const auto& value) { return value.Name == verb; });
        Require(found != g_Test->Registrations.end(), "missing chat command");
        ObeliskCommandInvocation value{OBELISK_COMMAND_INVOCATION_ABI_VERSION, sizeof(value), 0, 0, 31, {message.data(), message.size()}};
        g_Test->ActiveInvocation = value.invocation_token; found->Callback(&value, found->Data); g_Test->ActiveInvocation = 0;
    }
    nlohmann::json Config(uint64_t burst = 20)
    {
        return {{"enabled", true}, {"allow_all_instances", false}, {"instance_allowlist", {"chat-test"}},
            {"global_prefix", "[Global]"}, {"whisper_prefix", "[Privado]"}, {"burst_messages", burst}, {"rate_window_ms", uint64_t{86400000}},
            {"muted_sessions", nlohmann::json::array()}};
    }
}
void TestNativeAdvancedChatPluginIntegration()
{
    const auto root = fs::temp_directory_path() / ("obelisk-chat-plugin-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(root); const auto path = root / "config.json";
    Harness harness; g_Test = &harness; harness.Sessions = {Session(11, "Jugador 玩家"), Session(22, "Otro")};
    void* handle = dlopen(OBELISK_ADVANCED_CHAT_PLUGIN_PATH, RTLD_NOW | RTLD_LOCAL); Require(handle, "real advanced chat DSO failed to load");
    const auto init = reinterpret_cast<bool(*)(ObeliskApi*, const ObeliskPluginInitContext*)>(dlsym(handle, "ObeliskPlugin_Init"));
    const auto shutdown = reinterpret_cast<void(*)()>(dlsym(handle, "ObeliskPlugin_Shutdown"));
    const auto lifecycle = reinterpret_cast<uint32_t(*)()>(dlsym(handle, "ObeliskPlugin_LifecycleCapabilities"));
    Require(init && shutdown && lifecycle && lifecycle() == 1u, "chat plugin lifecycle exports missing");
    ObeliskApi api{}; api.abi_version = OBELISK_API_ABI_VERSION; api.struct_size = sizeof(api);
    api.capabilities = OBELISK_API_CAPABILITY_COMMAND_REPLIES | OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS | OBELISK_API_CAPABILITY_CHAT_SESSIONS;
    api.RegisterCommandWithOptionsWithOwnerTokenHandle = Register; api.UnregisterCommandWithOwnerToken = Unregister; api.ReplyToCommandWithOwnerToken = Reply;
    api.GetCommandChatSessionWithOwnerToken = Current; api.ListChatSessionsWithOwnerToken = List; api.SendChatToSessionWithOwnerToken = Send;
    const auto configPath = path.string();
    const auto configDirectory = root.string();
    ObeliskPluginInitContext context{OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION, sizeof(context), configDirectory.c_str(), configPath.c_str(), "chat-test", harness.Owner};
    auto start = [&](nlohmann::json config) { std::ofstream(path) << config.dump(); Require(init(&api, &context), "chat plugin init failed"); };
    start(Config());
    Require(harness.Registrations.size() == 4, "chat registrations incomplete");
    Invoke("/chathelp", "/CHATHELP"); Require(harness.Replies.back().find("11") != std::string::npos, "own observed session missing");
    Invoke("/chatlist", "/chatlist"); Require(harness.Replies.back().find("22 Otro") != std::string::npos, "observed roster lookup missing");
    Invoke("/chatglobal", "/CHATGLOBAL Hola 🙂");
    Require(harness.Delivered.size() == 2 && harness.Delivered[0].Token == 11 && harness.Delivered[1].Token == 22 &&
        harness.Delivered[0].Epoch == 900 && harness.Delivered[0].Text == "[Global] Jugador 玩家: Hola 🙂", "global formatting/fanout/epoch copy failed");
    harness.Delivered.clear(); Invoke("/tell", "/tell 22 privado");
    Require(harness.Delivered.size() == 2 && harness.Delivered[0].Token == 11 && harness.Delivered[1].Token == 22 &&
        harness.Delivered[1].Text == "[Privado] Jugador 玩家: privado", "whisper crossed destination or lost echo");
    harness.Delivered.clear(); harness.TotalOverride = 65; Invoke("/chatglobal", "/chatglobal incomplete");
    Require(harness.Delivered.empty() && harness.Replies.back().find("completa") != std::string::npos, "truncated roster silently broadcast");
    harness.TotalOverride = 0; harness.Sessions.pop_back(); Invoke("/tell", "/tell 22 stale");
    Require(harness.Delivered.empty() && harness.Replies.back().find("disponible") != std::string::npos, "stale destination revived");
    harness.Sessions.push_back(Session(23, "Reconnected")); Invoke("/tell", "/tell 23 correcto");
    Require(harness.Delivered.size() == 2 && harness.Delivered.back().Token == 23, "fresh session could not receive");
    harness.Delivered.clear(); harness.FailDestination = 23; Invoke("/chatglobal", "/chatglobal race");
    Require(harness.Delivered.size() == 1 && harness.Replies.back().find("Algunas") != std::string::npos, "partial dispatch advertised success");
    harness.FailDestination = 0; harness.Delivered.clear(); Invoke("/tell", "/tell 23 bad\nmessage");
    Require(harness.Delivered.empty(), "newline injection dispatched");
    shutdown(); Require(harness.Registrations.empty(), "shutdown retained executable callbacks");
    start(Config(1)); Invoke("/chatglobal", "/chatglobal first"); harness.Delivered.clear(); Invoke("/chatglobal", "/chatglobal second");
    Require(harness.Delivered.empty() && harness.Replies.back().find("Espera") != std::string::npos, "rate limit failed"); shutdown();
    auto muted = Config(); muted["muted_sessions"] = {{{"session_token", uint64_t{11}}, {"process_epoch", uint64_t{900}}}};
    start(muted); Invoke("/chatglobal", "/chatglobal muted");
    Require(harness.Delivered.empty() && harness.Replies.back().find("silenciado") != std::string::npos, "scoped mute failed"); shutdown();
    Require(harness.Registrations.empty() && dlclose(handle) == 0, "real chat unload failed"); g_Test = nullptr; fs::remove_all(root);
}
