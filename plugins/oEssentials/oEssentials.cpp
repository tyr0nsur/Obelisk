#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <string>
#include <string_view>

namespace
{
    ObeliskApi g_Api{};
    uint64_t g_OwnerToken = 0;
    std::array<uint64_t, 4> g_Handles{};
    std::array<std::string, 4> g_Texts;
    constexpr std::array<std::string_view, 4> kNames{"/help", "/rules", "/motd", "/serverinfo"};
    constexpr const char* kDefaultConfig = R"({
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "texts": {
    "help": "ObeliskNative: /rules, /motd, /serverinfo. Ayuda: /help rules, /help motd, /help info.",
    "rules": "Respeta a los jugadores y las normas publicadas por la administracion.",
    "motd": "Bienvenido. Este servidor utiliza ObeliskNative.",
    "serverinfo": "Servidor con ObeliskNative para Linux. Consulta /help."
  }
})";

    void Error(const char* text) noexcept
    {
        try { if (g_Api.LogError) g_Api.LogError(text); } catch (...) {}
    }

    bool ValidText(std::string_view value)
    {
        if (value.empty() || value.size() > 1024) return false;
        for (size_t i = 0; i < value.size();)
        {
            const auto head = static_cast<unsigned char>(value[i++]);
            if (!head) return false;
            if (head < 0x80) continue;
            size_t count = 0; uint32_t scalar = 0, minimum = 0;
            if (head >= 0xc2 && head <= 0xdf) count = 1, scalar = head & 31, minimum = 0x80;
            else if (head >= 0xe0 && head <= 0xef) count = 2, scalar = head & 15, minimum = 0x800;
            else if (head >= 0xf0 && head <= 0xf4) count = 3, scalar = head & 7, minimum = 0x10000;
            else return false;
            if (i + count > value.size()) return false;
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

    bool ReadConfig(const ObeliskPluginInitContext& context, bool& enabled)
    {
        if (!context.config_path || !context.instance_id) return false;
        std::ifstream input(context.config_path, std::ios::binary);
        if (!input) return false;
        std::string bytes(16385, '\0');
        input.read(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        if (input.bad() || input.gcount() > 16384) return false;
        bytes.resize(static_cast<size_t>(input.gcount()));
        const auto data = nlohmann::json::parse(bytes, nullptr, false);
        if (!data.is_object() || !data.contains("enabled") || !data["enabled"].is_boolean() ||
            !data.contains("allow_all_instances") || !data["allow_all_instances"].is_boolean() ||
            !data.contains("instance_allowlist") || !data["instance_allowlist"].is_array() ||
            !data.contains("texts") || !data["texts"].is_object()) return false;
        for (auto it = data.begin(); it != data.end(); ++it)
            if (it.key() != "enabled" && it.key() != "allow_all_instances" &&
                it.key() != "instance_allowlist" && it.key() != "texts") return false;
        bool allowed = data["allow_all_instances"].get<bool>();
        for (const auto& instance : data["instance_allowlist"])
        {
            if (!instance.is_string()) return false;
            allowed = allowed || instance.get<std::string>() == context.instance_id;
        }
        enabled = data["enabled"].get<bool>() && allowed;
        constexpr std::array<const char*, 4> keys{"help", "rules", "motd", "serverinfo"};
        if (data["texts"].size() != keys.size()) return false;
        for (size_t i = 0; i < keys.size(); ++i)
        {
            if (!data["texts"].contains(keys[i]) || !data["texts"][keys[i]].is_string()) return false;
            auto text = data["texts"][keys[i]].get<std::string>();
            if (!ValidText(text)) return false;
            g_Texts[i] = std::move(text);
        }
        return true;
    }

    std::string Fold(std::string_view text)
    {
        std::string result(text);
        for (char& ch : result) if (ch >= 'A' && ch <= 'Z') ch = static_cast<char>(ch + ('a' - 'A'));
        return result;
    }

    void Reply(const ObeliskCommandInvocation& event, std::string_view text)
    {
        if (!g_Api.ReplyToCommandWithOwnerToken(g_OwnerToken, event.invocation_token, {text.data(), text.size()}))
            Error("[oEssentials] Synchronous reply was rejected.");
    }

    void HandleInvocation(const ObeliskCommandInvocation* event, void*) noexcept
    {
        try
        {
            if (!event || event->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
                event->struct_size < sizeof(*event) || !event->invocation_token || !event->command_text.data ||
                !event->command_text.size || event->command_text.size > 4096 || event->send_mode > 3) return;
            const std::string_view message(event->command_text.data, event->command_text.size);
            const auto separator = message.find_first_of(" \t");
            const auto verb = Fold(message.substr(0, separator));
            std::string_view argument = separator == std::string_view::npos ? std::string_view{} : message.substr(separator);
            while (!argument.empty() && (argument.front() == ' ' || argument.front() == '\t')) argument.remove_prefix(1);
            while (!argument.empty() && (argument.back() == ' ' || argument.back() == '\t')) argument.remove_suffix(1);
            const auto found = std::find(kNames.begin(), kNames.end(), verb);
            if (found == kNames.end()) return;
            size_t index = static_cast<size_t>(found - kNames.begin());
            if (index == 0 && !argument.empty())
            {
                const auto topic = Fold(argument);
                if (topic == "rules" || topic == "/rules") index = 1;
                else if (topic == "motd" || topic == "/motd") index = 2;
                else if (topic == "info" || topic == "serverinfo" || topic == "/serverinfo") index = 3;
                else { Reply(*event, "Tema desconocido. Usa /help rules, /help motd o /help info."); return; }
            }
            else if (!argument.empty())
            {
                Reply(*event, "Este comando no admite argumentos. Consulta /help."); return;
            }
            Reply(*event, g_Texts[index]);
        }
        catch (...) { Error("[oEssentials] Invocation failed without escaping its callback."); }
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out) return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(*out), "oEssentials", "ObeliskNative Essentials",
            "0.1.0-prototype", "config.json", kDefaultConfig};
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api || !context || g_OwnerToken || api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(*context) || !context->plugin_owner_token) return false;
    std::memcpy(&g_Api, api, std::min<size_t>(sizeof(g_Api), api->struct_size));
    g_OwnerToken = context->plugin_owner_token;
    try
    {
        bool enabled = false;
        if (!ReadConfig(*context, enabled)) { Error("[oEssentials] Invalid scoped config or UTF-8 text."); return false; }
        if (!enabled) return true;
        if (g_Api.struct_size < offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) +
                                  sizeof(g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle) ||
            !(g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_REPLIES) ||
            !(g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS) ||
            !g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle || !g_Api.UnregisterCommandWithOwnerToken ||
            !g_Api.ReplyToCommandWithOwnerToken) { Error("[oEssentials] Required command backend unavailable."); return false; }
        for (size_t i = 0; i < kNames.size(); ++i)
        {
            g_Handles[i] = g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle(g_OwnerToken, kNames[i].data(),
                OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE, HandleInvocation, nullptr);
            if (!g_Handles[i]) { Error("[oEssentials] Registration failed or command namespace conflicts."); return false; }
        }
        if (g_Api.LogInfo) g_Api.LogInfo("[oEssentials] /help, /rules, /motd and /serverinfo registered.");
        return true;
    }
    catch (...) { Error("[oEssentials] Init failed; managed owner cleanup is required."); return false; }
}

extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities() { return 1u; }
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload() { return true; }
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    for (auto& handle : g_Handles)
    {
        if (handle && g_Api.UnregisterCommandWithOwnerToken) g_Api.UnregisterCommandWithOwnerToken(g_OwnerToken, handle);
        handle = 0;
    }
    for (auto& text : g_Texts) text.clear();
    g_OwnerToken = 0; g_Api = {};
}
