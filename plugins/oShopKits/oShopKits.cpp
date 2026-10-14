#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <array>
#include <charconv>
#include <cstring>
#include <fstream>
#include <limits>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace
{
    struct Entry
    {
        std::string Id, Name, Description;
        int64_t Price = 0, MaxClaims = 0, CooldownSeconds = 0;
    };
    ObeliskApi g_Api{};
    uint64_t g_Owner = 0;
    std::array<uint64_t, 2> g_Handles{};
    std::array<std::vector<Entry>, 2> g_Catalogs;
    constexpr size_t kPageSize = 3;
    constexpr std::string_view kAvailability = "Catalogo informativo. Compras y entregas de kits aun no estan disponibles.";
    constexpr const char* kDefaultConfig = R"({
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "catalog_revision": "initial",
  "shop": [],
  "kits": []
})";

    void Error(const char* text) noexcept { try { if (g_Api.LogError) g_Api.LogError(text); } catch (...) {} }
    bool Text(std::string_view value, size_t maximum)
    {
        if (value.empty() || value.size() > maximum) return false;
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
    bool Id(std::string_view value)
    {
        if (value.empty() || value.size() > 64 || value.front() < 'a' || value.front() > 'z') return false;
        for (const char ch : value)
            if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '-' || ch == '_')) return false;
        return true;
    }
    bool Keys(const nlohmann::json& value, std::initializer_list<std::string_view> allowed)
    {
        if (!value.is_object() || value.size() != allowed.size()) return false;
        for (const auto key : allowed) if (!value.contains(std::string(key))) return false;
        return true;
    }
    bool Integral(const nlohmann::json& value, int64_t& result)
    {
        if (!value.is_number_integer()) return false;
        if (value.is_number_unsigned() && value.get<uint64_t>() > static_cast<uint64_t>(std::numeric_limits<int64_t>::max())) return false;
        result = value.get<int64_t>(); return result >= 0;
    }
    bool Config(const ObeliskPluginInitContext& context, bool& enabled)
    {
        if (!context.config_path || !context.instance_id) return false;
        std::ifstream input(context.config_path, std::ios::binary);
        if (!input) return false;
        std::string bytes(32769, '\0'); input.read(bytes.data(), bytes.size());
        if (input.bad() || input.gcount() > 32768) return false;
        bytes.resize(static_cast<size_t>(input.gcount()));
        // Reject duplicate object keys rather than allowing last-value wins.
        std::vector<std::set<std::string>> keyStack;
        bool duplicate = false;
        const auto callback = [&](int, nlohmann::json::parse_event_t event, nlohmann::json& parsed) {
            if (event == nlohmann::json::parse_event_t::object_start) keyStack.emplace_back();
            else if (event == nlohmann::json::parse_event_t::key)
                if (keyStack.empty() || !keyStack.back().insert(parsed.get<std::string>()).second) duplicate = true;
            if (event == nlohmann::json::parse_event_t::object_end && !keyStack.empty()) keyStack.pop_back();
            return true;
        };
        const auto data = nlohmann::json::parse(bytes, callback, false);
        if (duplicate || !Keys(data, {"enabled", "allow_all_instances", "instance_allowlist", "catalog_revision", "shop", "kits"}) ||
            !data["enabled"].is_boolean() || !data["allow_all_instances"].is_boolean() ||
            !data["instance_allowlist"].is_array() || data["instance_allowlist"].size() > 64 ||
            !data["catalog_revision"].is_string() || !Text(data["catalog_revision"].get<std::string>(), 128)) return false;
        bool allowed = data["allow_all_instances"].get<bool>();
        for (const auto& instance : data["instance_allowlist"])
        {
            if (!instance.is_string() || !Text(instance.get<std::string>(), 64)) return false;
            allowed = allowed || instance.get<std::string>() == context.instance_id;
        }
        enabled = data["enabled"].get<bool>() && allowed;
        for (size_t kind = 0; kind < 2; ++kind)
        {
            const auto& catalog = data[kind ? "kits" : "shop"];
            if (!catalog.is_array() || catalog.size() > 64) return false;
            std::set<std::string> ids;
            for (const auto& item : catalog)
            {
                if (!(kind ? Keys(item, {"id", "name", "description", "max_claims", "cooldown_seconds"})
                           : Keys(item, {"id", "name", "description", "price"})) ||
                    !item["id"].is_string() || !item["name"].is_string() || !item["description"].is_string()) return false;
                Entry entry; entry.Id = item["id"].get<std::string>(); entry.Name = item["name"].get<std::string>();
                entry.Description = item["description"].get<std::string>();
                if (!Id(entry.Id) || !ids.insert(entry.Id).second || !Text(entry.Name, 80) || !Text(entry.Description, 256)) return false;
                if (kind ? !Integral(item["max_claims"], entry.MaxClaims) || !Integral(item["cooldown_seconds"], entry.CooldownSeconds)
                         : !Integral(item["price"], entry.Price)) return false;
                g_Catalogs[kind].push_back(std::move(entry));
            }
        }
        return true;
    }
    std::string Fold(std::string_view text)
    {
        std::string result(text); for (auto& ch : result) if (ch >= 'A' && ch <= 'Z') ch += 'a' - 'A'; return result;
    }
    void Reply(const ObeliskCommandInvocation& invocation, std::string_view text)
    {
        if (text.size() > 1024 || !g_Api.ReplyToCommandWithOwnerToken(g_Owner, invocation.invocation_token, {text.data(), text.size()}))
            Error("[oShopKits] Scoped synchronous reply was rejected.");
    }
    void Handle(const ObeliskCommandInvocation* invocation, void*) noexcept
    {
        try
        {
            if (!invocation || invocation->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
                invocation->struct_size < sizeof(*invocation) || !invocation->invocation_token ||
                !invocation->command_text.data || !invocation->command_text.size || invocation->command_text.size > 4096 ||
                invocation->send_mode > 3) return;
            const std::string_view message(invocation->command_text.data, invocation->command_text.size);
            const auto separator = message.find_first_of(" \t"); const auto verb = Fold(message.substr(0, separator));
            if (verb != "/shop" && verb != "/kits") return;
            std::string_view argument = separator == message.npos ? std::string_view{} : message.substr(separator);
            while (!argument.empty() && (argument.front() == ' ' || argument.front() == '\t')) argument.remove_prefix(1);
            while (!argument.empty() && (argument.back() == ' ' || argument.back() == '\t')) argument.remove_suffix(1);
            const bool kit = verb == "/kits"; const auto& catalog = g_Catalogs[kit ? 1 : 0];
            const std::string command = kit ? "/kits" : "/shop";
            if (catalog.empty()) { Reply(*invocation, "No hay entradas configuradas. " + std::string(kAvailability)); return; }
            size_t page = 1;
            if (!argument.empty())
            {
                const bool number = argument.front() >= '0' && argument.front() <= '9';
                if (number)
                {
                    const auto conversion = std::from_chars(argument.data(), argument.data() + argument.size(), page);
                    if (conversion.ec != std::errc{} || conversion.ptr != argument.data() + argument.size() || !page)
                    { Reply(*invocation, "Uso: " + command + " [pagina|id]. " + std::string(kAvailability)); return; }
                }
                else
                {
                    const auto id = Fold(argument);
                    const auto item = std::find_if(catalog.begin(), catalog.end(), [&](const Entry& entry) { return entry.Id == id; });
                    if (item == catalog.end()) { Reply(*invocation, "Entrada desconocida. Usa " + command + ". " + std::string(kAvailability)); return; }
                    std::string response = item->Id + ": " + item->Name + "\n" + item->Description;
                    if (kit) response += "\nLimite: " + (item->MaxClaims ? std::to_string(item->MaxClaims) : "sin limite") +
                        "; espera: " + std::to_string(item->CooldownSeconds) + " s.";
                    else response += "\nPrecio configurado: " + std::to_string(item->Price) + " puntos.";
                    response += "\n"; response += kAvailability; Reply(*invocation, response); return;
                }
            }
            const size_t pages = (catalog.size() + kPageSize - 1) / kPageSize;
            if (page > pages) { Reply(*invocation, "Pagina fuera de rango (1-" + std::to_string(pages) + "). " + std::string(kAvailability)); return; }
            std::string response = (kit ? "Kits" : "Tienda") + std::string(" ") + std::to_string(page) + "/" + std::to_string(pages) + ":";
            for (size_t i = (page - 1) * kPageSize; i < std::min(catalog.size(), page * kPageSize); ++i)
            {
                const auto& item = catalog[i]; response += "\n" + item.Id + " - " + item.Name;
                if (!kit) response += " (" + std::to_string(item.Price) + " puntos)";
            }
            response += "\nDetalle: " + command + " <id>. "; response += kAvailability; Reply(*invocation, response);
        }
        catch (...) { Error("[oShopKits] Invocation failed inside managed callback."); }
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out) return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(*out), "oShopKits", "ObeliskNative Shop and Kits",
            "0.1.0-prototype", "config.json", kDefaultConfig}; return true;
}
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api || !context || g_Owner || api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION || context->struct_size < sizeof(*context) ||
        !context->plugin_owner_token) return false;
    std::memcpy(&g_Api, api, std::min<size_t>(sizeof(g_Api), api->struct_size)); g_Owner = context->plugin_owner_token;
    try
    {
        bool enabled = false;
        if (!Config(*context, enabled)) { Error("[oShopKits] Invalid scoped catalog configuration."); return false; }
        if (!enabled) return true;
        if (g_Api.struct_size < offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) + sizeof(g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle) ||
            !(g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_REPLIES) || !(g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS) ||
            !g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle || !g_Api.UnregisterCommandWithOwnerToken || !g_Api.ReplyToCommandWithOwnerToken)
        { Error("[oShopKits] Required command backend unavailable."); return false; }
        constexpr std::array<const char*, 2> names{"/shop", "/kits"};
        for (size_t i = 0; i < names.size(); ++i)
        {
            g_Handles[i] = g_Api.RegisterCommandWithOptionsWithOwnerTokenHandle(g_Owner, names[i],
                OBELISK_COMMAND_MATCH_FLAG_VERB | OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE, Handle, nullptr);
            if (!g_Handles[i]) { Error("[oShopKits] Invocation registration conflict."); return false; }
        }
        if (g_Api.LogInfo) g_Api.LogInfo("[oShopKits] Informational /shop and /kits registered; game fulfillment unavailable.");
        return true;
    }
    catch (...) { Error("[oShopKits] Init failed; owner cleanup required."); return false; }
}
extern "C" __attribute__((visibility("default"))) uint32_t ObeliskPlugin_LifecycleCapabilities() { return 1u; }
extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_PrepareUnload() { return true; }
extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    for (auto& handle : g_Handles)
    { if (handle && g_Api.UnregisterCommandWithOwnerToken) g_Api.UnregisterCommandWithOwnerToken(g_Owner, handle); handle = 0; }
    for (auto& catalog : g_Catalogs) catalog.clear(); g_Api = {}; g_Owner = 0;
}
