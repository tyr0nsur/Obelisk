#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstring>
#include <fstream>
#include <string>
#include <string_view>

namespace
{
    ObeliskApi g_Api{};
    uint64_t g_Owner = 0;
    std::array<uint64_t, 4> g_Handles{};
    std::string g_Prefix;
    constexpr std::array<std::string_view, 4> kCommands{"/whereami", "/tribe", "/dino", "/structure"};
    constexpr const char* kConfig = R"({
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "prefix": "ObeliskNative"
})";

    void Error(const char* message) noexcept
    {
        try { if (g_Api.LogError) g_Api.LogError(message); } catch (...) {}
    }

    bool ValidPrefix(std::string_view value)
    {
        if (value.empty() || value.size() > 64) return false;
        for (size_t index = 0; index < value.size();)
        {
            const auto head = static_cast<unsigned char>(value[index++]);
            if (head < 0x20 || head == 0x7f) return false;
            if (head < 0x80) continue;
            size_t tailCount = 0; uint32_t scalar = 0, minimum = 0;
            if (head >= 0xc2 && head <= 0xdf) tailCount = 1, scalar = head & 31, minimum = 0x80;
            else if (head >= 0xe0 && head <= 0xef) tailCount = 2, scalar = head & 15, minimum = 0x800;
            else if (head >= 0xf0 && head <= 0xf4) tailCount = 3, scalar = head & 7, minimum = 0x10000;
            else return false;
            if (index + tailCount > value.size()) return false;
            while (tailCount--)
            {
                const auto tail = static_cast<unsigned char>(value[index++]);
                if ((tail & 0xc0) != 0x80) return false;
                scalar = (scalar << 6) | (tail & 63);
            }
            if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff)) return false;
        }
        return true;
    }

    bool Config(const ObeliskPluginInitContext& context, bool& enabled)
    {
        if (!context.config_path || !context.instance_id) return false;
        std::ifstream stream(context.config_path, std::ios::binary);
        if (!stream) return false;
        std::string text(8193, '\0');
        stream.read(text.data(), static_cast<std::streamsize>(text.size()));
        if (stream.bad() || stream.gcount() > 8192) return false;
        text.resize(static_cast<size_t>(stream.gcount()));
        const auto value = nlohmann::json::parse(text, nullptr, false);
        if (!value.is_object() || value.size() != 4 ||
            !value.contains("enabled") || !value["enabled"].is_boolean() ||
            !value.contains("allow_all_instances") || !value["allow_all_instances"].is_boolean() ||
            !value.contains("instance_allowlist") || !value["instance_allowlist"].is_array() ||
            value["instance_allowlist"].size() > 64 ||
            !value.contains("prefix") || !value["prefix"].is_string()) return false;
        bool allowed = value["allow_all_instances"].get<bool>();
        for (const auto& instance : value["instance_allowlist"])
        {
            if (!instance.is_string()) return false;
            const auto name = instance.get<std::string>();
            if (name.empty() || name.size() > 64 || !std::all_of(name.begin(), name.end(), [](unsigned char ch) {
                    return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                           (ch >= '0' && ch <= '9') || ch == '_' || ch == '-' || ch == '.';
                })) return false;
            allowed = allowed || name == context.instance_id;
        }
        auto prefix = value["prefix"].get<std::string>();
        if (!ValidPrefix(prefix)) return false;
        g_Prefix = std::move(prefix);
        enabled = value["enabled"].get<bool>() && allowed;
        return true;
    }

    void Reply(const ObeliskCommandInvocation& event, std::string_view text)
    {
        const auto response = g_Prefix + ": " + std::string(text);
        if (response.size() > 1024 || !g_Api.ReplyToCommandWithOwnerToken(
                g_Owner, event.invocation_token, {response.data(), response.size()}))
            Error("[oWorldTools] Scoped reply rejected.");
    }

    std::string Coordinate(float value)
    {
        std::array<char, 64> text{};
        const auto result = std::to_chars(text.data(), text.data() + text.size(), value, std::chars_format::fixed, 2);
        if (result.ec != std::errc{}) return {};
        return {text.data(), static_cast<size_t>(result.ptr - text.data())};
    }

    void Handle(const ObeliskCommandInvocation* event, void*) noexcept
    {
        try
        {
            if (!event || event->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
                event->struct_size < sizeof(*event) || !event->invocation_token || !event->command_text.data ||
                !event->command_text.size || event->command_text.size > 4096 || event->send_mode > 3) return;
            const std::string_view message(event->command_text.data, event->command_text.size);
            const auto separator = message.find_first_of(" \t");
            std::string verb(message.substr(0, separator));
            for (auto& ch : verb) if (ch >= 'A' && ch <= 'Z') ch = static_cast<char>(ch + ('a' - 'A'));
            const auto found = std::find(kCommands.begin(), kCommands.end(), verb);
            if (found == kCommands.end()) return;
            if (separator != std::string_view::npos && message.find_first_not_of(" \t", separator) != std::string_view::npos)
            {
                Reply(*event, "Uso: " + verb + " (sin argumentos)."); return;
            }
            ObeliskCommandWorldInfo info{};
            info.abi_version = OBELISK_COMMAND_WORLD_INFO_ABI_VERSION;
            info.struct_size = sizeof(info);
            if (!g_Api.GetCommandWorldInfoWithOwnerToken(g_Owner, event->invocation_token, &info) ||
                info.abi_version != OBELISK_COMMAND_WORLD_INFO_ABI_VERSION || info.struct_size < sizeof(info))
            {
                Reply(*event, "No se puede consultar tu personaje en este momento."); return;
            }
            const auto command = static_cast<size_t>(found - kCommands.begin());
            if (command == 0)
            {
                if (!(info.flags & OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE) ||
                    !std::isfinite(info.x) || !std::isfinite(info.y) || !std::isfinite(info.z))
                { Reply(*event, "Tu posicion no esta disponible."); return; }
                const auto x = Coordinate(info.x), y = Coordinate(info.y), z = Coordinate(info.z);
                if (x.empty() || y.empty() || z.empty()) { Reply(*event, "Tu posicion no esta disponible."); return; }
                Reply(*event, "Posicion X=" + x + " Y=" + y + " Z=" + z + " (unidades del mundo).");
            }
            else if (command == 1)
            {
                if (!(info.flags & OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE))
                { Reply(*event, "Tu tribu no esta disponible."); return; }
                Reply(*event, info.native_tribe_id ? "ID de tu tribu: " + std::to_string(info.native_tribe_id) : "No perteneces a una tribu.");
            }
            else if (command == 2)
            {
                if (!(info.flags & OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE))
                { Reply(*event, "Monta un dino para consultar su ID."); return; }
                Reply(*event, "ID del dino montado: " + std::to_string(info.mounted_dino_id1) + "/" + std::to_string(info.mounted_dino_id2) + ".");
            }
            else
            {
                if (!(info.flags & OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE))
                { Reply(*event, "Apunta a una estructura para consultar su ID."); return; }
                Reply(*event, "ID de la estructura a la que apuntas: " + std::to_string(info.target_structure_id) + ".");
            }
        }
        catch (...) { Error("[oWorldTools] Query failed within its managed callback."); }
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out) return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(*out), "oWorldTools", "ObeliskNative World Tools",
            "0.1.0-prototype", "config.json", kConfig};
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api || !context || g_Owner || api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(*context) || !context->plugin_owner_token) return false;
    g_Api = {};
    std::memcpy(&g_Api, api, std::min<size_t>(sizeof(g_Api), api->struct_size));
    g_Owner = context->plugin_owner_token;
    try
    {
        bool enabled = false;
        if (!Config(*context, enabled)) { Error("[oWorldTools] Invalid instance config or prefix."); return false; }
        if (!enabled) return true;
        constexpr auto required = OBELISK_API_CAPABILITY_COMMAND_REPLIES | OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS |
                                  OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE;
        if (g_Api.struct_size < offsetof(ObeliskApi, GetCommandWorldInfoWithOwnerToken) + sizeof(g_Api.GetCommandWorldInfoWithOwnerToken) ||
            (g_Api.capabilities & required) != required || !g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle ||
            !g_Api.UnregisterCommandWithOwnerToken || !g_Api.ReplyToCommandWithOwnerToken || !g_Api.GetCommandWorldInfoWithOwnerToken)
        { Error("[oWorldTools] Native world query backend unavailable."); return false; }
        for (size_t index = 0; index < kCommands.size(); ++index)
        {
            g_Handles[index] = g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle(g_Owner, kCommands[index].data(),
                OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE, Handle, nullptr);
            if (!g_Handles[index]) { Error("[oWorldTools] Invocation registration rejected."); return false; }
        }
        if (g_Api.LogInfo) g_Api.LogInfo("[oWorldTools] /whereami, /tribe, /dino and /structure registered.");
        return true;
    }
    catch (...) { Error("[oWorldTools] Init failed; managed owner cleanup is required."); return false; }
}

extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities() { return 1u; }
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload() { return true; }
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    for (auto& handle : g_Handles)
    {
        if (handle && g_Api.UnregisterCommandWithOwnerToken) g_Api.UnregisterCommandWithOwnerToken(g_Owner, handle);
        handle = 0;
    }
    g_Prefix.clear(); g_Owner = 0; g_Api = {};
}
