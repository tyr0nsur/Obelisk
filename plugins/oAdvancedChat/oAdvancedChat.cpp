#include <obelisk/ObeliskApi.h>
#include <obelisk/ObeliskChatSessionApi.h>
#include "core/AdvancedChatRouter.h"
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cstring>
#include <fstream>
#include <memory>
#include <limits>
#include <string>
#include <string_view>
#include <vector>
#include <utility>

namespace
{
    using namespace Obelisk::Core;
    ObeliskApi g_Api{};
    uint64_t g_Owner = 0;
    std::array<uint64_t, 4> g_Handles{};
    std::unique_ptr<AdvancedChatRouter> g_Router;
    std::vector<AdvancedChatSession> g_Observed;
    std::vector<std::pair<uint64_t, std::string>> g_Names;
    std::vector<AdvancedChatSession> g_Muted;
    std::string g_GlobalPrefix, g_WhisperPrefix;
    constexpr const char* kConfig = R"({
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "global_prefix": "[Global]",
  "whisper_prefix": "[Privado]",
  "burst_messages": 5,
  "rate_window_ms": 3000,
  "muted_sessions": []
})";

    bool Same(AdvancedChatSession a, AdvancedChatSession b) noexcept
    { return a.Id == b.Id && a.Generation == b.Generation; }
    bool Utf8(std::string_view value, size_t maximum) noexcept
    {
        if (value.empty() || value.size() > maximum) return false;
        for (size_t i = 0; i < value.size();)
        {
            const auto head = static_cast<unsigned char>(value[i++]);
            if (head < 0x20 || head == 0x7f) return false;
            if (head < 0x80) continue;
            uint32_t scalar = 0, minimum = 0; size_t count = 0;
            if (head >= 0xc2 && head <= 0xdf) scalar = head & 31, minimum = 0x80, count = 1;
            else if (head >= 0xe0 && head <= 0xef) scalar = head & 15, minimum = 0x800, count = 2;
            else if (head >= 0xf0 && head <= 0xf4) scalar = head & 7, minimum = 0x10000, count = 3;
            else return false;
            if (count > value.size() - i) return false;
            while (count--)
            {
                const auto tail = static_cast<unsigned char>(value[i++]);
                if ((tail & 0xc0) != 0x80) return false;
                scalar = (scalar << 6) | (tail & 63);
            }
            if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff)) return false;
        }
        return true;
    }
    std::string Fold(std::string_view value)
    {
        std::string result(value);
        for (char& ch : result) if (ch >= 'A' && ch <= 'Z') ch += 'a' - 'A';
        return result;
    }
    std::string_view Trim(std::string_view value) noexcept
    {
        while (!value.empty() && (value.front() == ' ' || value.front() == '\t')) value.remove_prefix(1);
        while (!value.empty() && (value.back() == ' ' || value.back() == '\t')) value.remove_suffix(1);
        return value;
    }
    void Error(const char* value) noexcept { try { if (g_Api.LogError) g_Api.LogError(value); } catch (...) {} }
    void Reply(const ObeliskCommandInvocation& invocation, std::string_view value)
    {
        if (!g_Api.ReplyToCommandWithOwnerToken(g_Owner, invocation.invocation_token, {value.data(), value.size()}))
            Error("[oAdvancedChat] Scoped reply rejected.");
    }
    bool Config(const ObeliskPluginInitContext& context, bool& enabled)
    {
        if (!context.config_path || !context.instance_id) return false;
        std::ifstream input(context.config_path, std::ios::binary); if (!input) return false;
        std::string bytes(16385, '\0'); input.read(bytes.data(), bytes.size());
        if (input.bad() || input.gcount() > 16384) return false; bytes.resize(input.gcount());
        const auto config = nlohmann::json::parse(bytes, nullptr, false);
        if (!config.is_object() || config.size() != 8 || !config.contains("enabled") || !config["enabled"].is_boolean() ||
            !config.contains("allow_all_instances") || !config["allow_all_instances"].is_boolean() ||
            !config.contains("instance_allowlist") || !config["instance_allowlist"].is_array() ||
            !config.contains("global_prefix") || !config["global_prefix"].is_string() ||
            !config.contains("whisper_prefix") || !config["whisper_prefix"].is_string() ||
            !config.contains("burst_messages") || !config["burst_messages"].is_number_unsigned() ||
            !config.contains("rate_window_ms") || !config["rate_window_ms"].is_number_unsigned() ||
            !config.contains("muted_sessions") || !config["muted_sessions"].is_array()) return false;
        bool allowed = config["allow_all_instances"].get<bool>();
        if (config["instance_allowlist"].size() > 64 || config["muted_sessions"].size() > 64) return false;
        for (const auto& instance : config["instance_allowlist"])
        {
            if (!instance.is_string()) return false;
            allowed = allowed || instance.get<std::string>() == context.instance_id;
        }
        g_GlobalPrefix = config["global_prefix"].get<std::string>(); g_WhisperPrefix = config["whisper_prefix"].get<std::string>();
        if (!Utf8(g_GlobalPrefix, 64) || !Utf8(g_WhisperPrefix, 64)) return false;
        const auto burst = config["burst_messages"].get<uint64_t>(), window = config["rate_window_ms"].get<uint64_t>();
        if (!burst || burst > 100 || !window || window > 86400000) return false;
        g_Router = std::make_unique<AdvancedChatRouter>(AdvancedChatRouter::Settings{10000, static_cast<uint32_t>(burst), static_cast<int64_t>(window), 100000});
        g_Muted.clear();
        for (const auto& item : config["muted_sessions"])
        {
            if (!item.is_object() || item.size() != 2 || !item.contains("session_token") || !item["session_token"].is_number_unsigned() ||
                !item.contains("process_epoch") || !item["process_epoch"].is_number_unsigned()) return false;
            const AdvancedChatSession value{item["session_token"].get<uint64_t>(), item["process_epoch"].get<uint64_t>()};
            if (!value.Id || !value.Generation || std::any_of(g_Muted.begin(), g_Muted.end(), [&](auto old) { return Same(value, old); })) return false;
            g_Muted.push_back(value);
        }
        enabled = config["enabled"].get<bool>() && allowed; return true;
    }
    bool Session(const ObeliskChatSession& value) noexcept
    {
        return value.abi_version == OBELISK_CHAT_SESSION_ABI_VERSION && value.struct_size >= sizeof(value) &&
            value.session_token && value.process_epoch && value.player_name_size <= OBELISK_CHAT_SESSION_NAME_MAX_BYTES &&
            !(value.flags & ~OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE) &&
            (value.flags & OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE ? value.player_name_size && value.player_name[value.player_name_size] == 0 : value.player_name_size == 0);
    }
    AdvancedChatSession Handle(const ObeliskChatSession& value) noexcept { return {value.session_token, value.process_epoch}; }
    std::string Name(const ObeliskChatSession& value)
    {
        const std::string_view name(value.player_name, value.player_name_size);
        return (value.flags & OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE) && Utf8(name, 256) ? std::string(name) : "Jugador";
    }
    bool Roster(const ObeliskCommandInvocation& invocation, ObeliskChatSession& current)
    {
        current = {OBELISK_CHAT_SESSION_ABI_VERSION, sizeof(current)};
        if (!g_Api.GetCommandChatSessionWithOwnerToken(g_Owner, invocation.invocation_token, &current) || !Session(current)) return false;
        std::array<ObeliskChatSession, OBELISK_CHAT_SESSION_LIST_MAX> records{};
        for (auto& record : records) record = {OBELISK_CHAT_SESSION_ABI_VERSION, sizeof(record)};
        size_t written = 0, total = 0;
        if (!g_Api.ListChatSessionsWithOwnerToken(g_Owner, invocation.invocation_token, records.data(), records.size(), &written, &total) ||
            written > records.size() || total != written) return false;
        std::vector<AdvancedChatSession> observed;
        bool includesCurrent = false;
        for (size_t i = 0; i < written; ++i)
        {
            if (!Session(records[i]) || records[i].process_epoch != current.process_epoch) return false;
            const auto handle = Handle(records[i]);
            if (std::any_of(observed.begin(), observed.end(), [&](auto previous) { return Same(handle, previous); })) return false;
            observed.push_back(handle); includesCurrent |= Same(handle, Handle(current));
        }
        if (!includesCurrent) return false;
        for (auto previous : g_Observed)
            if (std::none_of(observed.begin(), observed.end(), [&](auto value) { return Same(value, previous); })) g_Router->Disconnect(previous);
        for (size_t i = 0; i < written; ++i)
        {
            const auto handle = Handle(records[i]);
            if (g_Router->Upsert({handle, Name(records[i]), "runtime:" + std::to_string(handle.Generation), {}, {}}) != AdvancedChatStatus::Ok) return false;
            if (std::any_of(g_Muted.begin(), g_Muted.end(), [&](auto value) { return Same(value, handle); }))
                g_Router->Mute(handle, std::numeric_limits<int64_t>::max());
        }
        g_Names.clear();
        for (size_t i = 0; i < written; ++i) g_Names.emplace_back(records[i].session_token, Name(records[i]));
        std::sort(g_Names.begin(), g_Names.end());
        g_Observed = std::move(observed); return true;
    }
    void Invoke(const ObeliskCommandInvocation* invocation, void*) noexcept
    {
        try
        {
            if (!invocation || invocation->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
                invocation->struct_size < sizeof(*invocation) || !invocation->invocation_token ||
                !invocation->command_text.data || !invocation->command_text.size || invocation->command_text.size > 4096) return;
            const std::string_view text(invocation->command_text.data, invocation->command_text.size);
            const auto separator = text.find_first_of(" \t"); const auto verb = Fold(text.substr(0, separator));
            auto arguments = separator == std::string_view::npos ? std::string_view{} : Trim(text.substr(separator));
            ObeliskChatSession current;
            if (!Roster(*invocation, current)) { Reply(*invocation, "No se ha podido obtener la lista completa de sesiones observadas."); return; }
            if (verb == "/chathelp")
            {
                if (!arguments.empty()) { Reply(*invocation, "Uso: /chathelp"); return; }
                Reply(*invocation, "/chatglobal <mensaje>; /tell <sesion> <mensaje>; /chatlist [pagina]. Tu sesion: " + std::to_string(current.session_token) +
                    ". Destinos: sesiones observadas durante esta ejecucion."); return;
            }
            if (verb == "/chatlist")
            {
                uint64_t page = 1;
                if (!arguments.empty())
                {
                    const auto parsed = std::from_chars(arguments.data(), arguments.data() + arguments.size(), page);
                    if (parsed.ec != std::errc{} || parsed.ptr != arguments.data() + arguments.size() || !page)
                    { Reply(*invocation, "Uso: /chatlist [pagina]"); return; }
                }
                const size_t pages = (g_Names.size() + 7) / 8;
                if (page > pages) { Reply(*invocation, "Esa pagina no existe en la lista de sesiones observadas."); return; }
                std::string reply = "Sesiones observadas (" + std::to_string(page) + "/" + std::to_string(pages) + "): ";
                const size_t begin = static_cast<size_t>(page - 1) * 8;
                for (size_t i = begin; i < std::min(begin + 8, g_Names.size()); ++i)
                {
                    auto name = g_Names[i].second;
                    if (name.size() > 64)
                    {
                        size_t bytes = 64;
                        while (bytes && (static_cast<unsigned char>(name[bytes]) & 0xc0) == 0x80) --bytes;
                        name.resize(bytes); name += "...";
                    }
                    if (i != begin) reply += "; ";
                    reply += std::to_string(g_Names[i].first) + " " + name;
                }
                Reply(*invocation, reply); return;
            }
            const bool whisper = verb == "/tell";
            if (!whisper && verb != "/chatglobal") return;
            std::optional<AdvancedChatSession> target;
            if (whisper)
            {
                const auto split = arguments.find_first_of(" \t");
                if (split == std::string_view::npos) { Reply(*invocation, "Uso: /tell <sesion> <mensaje>. Consulta /chathelp."); return; }
                const auto tokenText = arguments.substr(0, split); uint64_t token = 0;
                const auto parsed = std::from_chars(tokenText.data(), tokenText.data() + tokenText.size(), token);
                if (parsed.ec != std::errc{} || parsed.ptr != tokenText.data() + tokenText.size() || !token)
                { Reply(*invocation, "El destino debe ser una sesion valida. Consulta /chathelp."); return; }
                const auto found = std::find_if(g_Observed.begin(), g_Observed.end(), [&](auto value) { return value.Id == token; });
                if (found == g_Observed.end()) { Reply(*invocation, "La sesion de destino ya no esta disponible."); return; }
                target = *found; arguments = Trim(arguments.substr(split));
            }
            if (!Utf8(arguments, 512)) { Reply(*invocation, "Escribe un mensaje UTF-8 de 1 a 512 bytes, sin saltos de linea."); return; }
            const auto now = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
            const auto formatted = (whisper ? g_WhisperPrefix : g_GlobalPrefix) + " " + Name(current) + ": " + std::string(arguments);
            const auto plan = g_Router->Plan(Handle(current), whisper ? AdvancedChatChannel::Whisper : AdvancedChatChannel::Global, formatted, now, target);
            if (plan.Status == AdvancedChatStatus::Muted) { Reply(*invocation, "Esta sesion tiene el chat silenciado."); return; }
            if (plan.Status == AdvancedChatStatus::RateLimited) { Reply(*invocation, "Espera unos segundos antes de enviar otro mensaje."); return; }
            if (plan.Status != AdvancedChatStatus::Ok) { Reply(*invocation, "El mensaje no se pudo preparar para la sesion actual."); return; }
            size_t dispatched = 0;
            for (auto destination : plan.Recipients)
                if (g_Router->IsDeliverable(plan, destination) && g_Api.SendChatToSessionWithOwnerToken(g_Owner, invocation->invocation_token,
                    destination.Id, destination.Generation, {plan.Text.data(), plan.Text.size()})) ++dispatched;
            if (dispatched != plan.Recipients.size())
                Reply(*invocation, "Algunas sesiones dejaron de estar disponibles al enviar el mensaje.");
        }
        catch (...) { Error("[oAdvancedChat] Invocation failed within managed callback."); }
    }
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out) return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(*out), "oAdvancedChat", "ObeliskNative Advanced Chat", "0.1.0-prototype", "config.json", kConfig};
    return true;
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api || !context || g_Owner || api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION || context->struct_size < sizeof(*context) || !context->plugin_owner_token) return false;
    std::memcpy(&g_Api, api, std::min<size_t>(sizeof(g_Api), api->struct_size)); g_Owner = context->plugin_owner_token;
    try
    {
        bool enabled = false; if (!Config(*context, enabled)) { Error("[oAdvancedChat] Invalid instance-scoped configuration."); return false; }
        if (!enabled) return true;
        const auto required = OBELISK_API_CAPABILITY_COMMAND_REPLIES | OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS | OBELISK_API_CAPABILITY_CHAT_SESSIONS;
        if ((g_Api.capabilities & required) != required || g_Api.struct_size < offsetof(ObeliskApi, SendChatToSessionWithOwnerToken) + sizeof(g_Api.SendChatToSessionWithOwnerToken) ||
            !g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle || !g_Api.UnregisterCommandWithOwnerToken || !g_Api.ReplyToCommandWithOwnerToken ||
            !g_Api.GetCommandChatSessionWithOwnerToken || !g_Api.ListChatSessionsWithOwnerToken || !g_Api.SendChatToSessionWithOwnerToken)
        { Error("[oAdvancedChat] Scoped session delivery backend unavailable."); return false; }
        constexpr std::array<const char*, 4> names{"/chathelp", "/chatglobal", "/tell", "/chatlist"};
        for (size_t i = 0; i < names.size(); ++i)
        {
            g_Handles[i] = g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle(g_Owner, names[i],
                OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE, Invoke, nullptr);
            if (!g_Handles[i]) return false;
        }
        if (g_Api.LogInfo) g_Api.LogInfo("[oAdvancedChat] Global formatting and session whispers registered.");
        return true;
    }
    catch (...) { Error("[oAdvancedChat] Init failed; owner cleanup is required."); return false; }
}
extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities() { return 1u; }
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload() { return true; }
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    for (auto& handle : g_Handles)
    { if (handle && g_Api.UnregisterCommandWithOwnerToken) g_Api.UnregisterCommandWithOwnerToken(g_Owner, handle); handle = 0; }
    g_Router.reset(); g_Observed.clear(); g_Names.clear(); g_Muted.clear(); g_GlobalPrefix.clear(); g_WhisperPrefix.clear(); g_Owner = 0; g_Api = {};
}
