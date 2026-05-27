#include "api/ObeliskApi.h"
#include <string>
#include <mutex>
#include <set>
#include <fstream>
#include <algorithm>
#include <array>
#include <cctype>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <vector>
#include <filesystem>
#include <fcntl.h>
#include <unistd.h>
#include "extern/nlohmann/json.hpp" // Librería JSON unificada
#include "ue/Reflection.h"

using json = nlohmann::json;
using Obelisk::UE::FName;
using Obelisk::UE::FString;
using Obelisk::UE::UObjectBase;

static bool IsReadable(void* ptr, size_t size) {
    if (!ptr || size == 0) return false;
    static int fd = -1;
    if (fd < 0) fd = open("/dev/null", O_WRONLY);
    if (fd < 0) return false;
    return write(fd, ptr, size) >= 0;
}

static ObeliskApi* g_Api = nullptr;

static std::mutex g_ConfigMutex;
static json g_Config;
static std::string g_ConfigPath = "";

static int32_t g_ServerChatIndex = -1;
static int32_t g_ClientMessageIndex = -1;
static int32_t g_ServerChatMessageOffset = -1;
static int32_t g_ClientMessageTextOffset = 0;
static void* g_ClientMessageFunc = nullptr;
static bool g_DiscoveryEnabled = false;

static std::mutex g_ScanMutex;
static std::set<int32_t> g_ScannedIndexes;
static int g_CandidateLogCount = 0;

static json DefaultConfig() {
    return {
        {"ServerChatIndex", -1},
        {"ClientMessageIndex", -1},
        {"ServerChatMessageOffset", -1},
        {"ClientMessageTextOffset", 0}
    };
}

static void WriteDefaultConfigIfMissing() {
    if (g_ConfigPath.empty() || std::filesystem::exists(g_ConfigPath)) {
        return;
    }

    try {
        std::filesystem::create_directories(std::filesystem::path(g_ConfigPath).parent_path());
        std::ofstream o(g_ConfigPath);
        if (o.is_open()) {
            o << g_Config.dump(4);
            if (g_Api) g_Api->LogInfo("[ChatPlugin] Default config created.");
        }
    } catch (...) {
        if (g_Api) g_Api->LogWarn("[ChatPlugin] Failed to create default config.");
    }
}

void LoadConfig() {
    if (g_ConfigPath.empty()) {
        const char* overridePath = std::getenv("OBELISK_CHAT_CONFIG");
        if (overridePath && overridePath[0] != '\0') {
            g_ConfigPath = overridePath;
        } else {
            const char* configDir = std::getenv("OBELISK_CONFIG_DIR");
            if (configDir && configDir[0] != '\0') {
                std::filesystem::path preferred = std::filesystem::path(configDir) / "plugins" / "chat" / "config.json";
                std::filesystem::path legacy = std::filesystem::path(configDir) / "plugins" / "chat_config.json";
                g_ConfigPath = (std::filesystem::exists(legacy) && !std::filesystem::exists(preferred))
                    ? legacy.string()
                    : preferred.string();
            } else {
                const char* root = std::getenv("OBELISK_ROOT");
                if (root && root[0] != '\0') {
                    std::filesystem::path preferred = std::filesystem::path(root) / "config" / "plugins" / "chat" / "config.json";
                    std::filesystem::path legacy = std::filesystem::path(root) / "config" / "plugins" / "chat_config.json";
                    g_ConfigPath = (std::filesystem::exists(legacy) && !std::filesystem::exists(preferred))
                        ? legacy.string()
                        : preferred.string();
                } else {
                    g_ConfigPath = "ObeliskPlugins/chat_config.json";
                }
            }
        }
    }

    std::lock_guard<std::mutex> lock(g_ConfigMutex);
    std::ifstream f(g_ConfigPath);
    if (f.is_open()) {
        try {
            g_Config = json::parse(f);
            if (!g_Config.is_object()) g_Config = json::object();
        } catch (...) {
            g_Config = json::object();
        }
    } else {
        g_Config = DefaultConfig();
        WriteDefaultConfigIfMissing();
    }

    if (g_Config.contains("ServerChatIndex") && g_Config["ServerChatIndex"].is_number_integer()) {
        g_ServerChatIndex = g_Config["ServerChatIndex"].get<int32_t>();
    }
    if (g_Config.contains("ClientMessageIndex") && g_Config["ClientMessageIndex"].is_number_integer()) {
        g_ClientMessageIndex = g_Config["ClientMessageIndex"].get<int32_t>();
    }
    if (g_Config.contains("ServerChatMessageOffset") && g_Config["ServerChatMessageOffset"].is_number_integer()) {
        g_ServerChatMessageOffset = g_Config["ServerChatMessageOffset"].get<int32_t>();
    }
    if (g_Config.contains("ClientMessageTextOffset") && g_Config["ClientMessageTextOffset"].is_number_integer()) {
        g_ClientMessageTextOffset = g_Config["ClientMessageTextOffset"].get<int32_t>();
    }

    const char* discovery = std::getenv("OBELISK_CHAT_DISCOVERY");
    g_DiscoveryEnabled = discovery && std::strcmp(discovery, "1") == 0;
}

void SaveConfig() {
    std::lock_guard<std::mutex> lock(g_ConfigMutex);
    g_Config["ServerChatIndex"] = g_ServerChatIndex;
    g_Config["ClientMessageIndex"] = g_ClientMessageIndex;
    g_Config["ServerChatMessageOffset"] = g_ServerChatMessageOffset;
    g_Config["ClientMessageTextOffset"] = g_ClientMessageTextOffset;
    try {
        std::filesystem::create_directories(std::filesystem::path(g_ConfigPath).parent_path());
    } catch (...) {
        return;
    }
    std::ofstream o(g_ConfigPath);
    if (!o.is_open()) return;
    o << g_Config.dump(4);
}

struct TempFString {
    std::vector<char32_t> Storage;
    FString Value;

    explicit TempFString(const std::string& str) {
        Storage.reserve(str.size() + 1);
        for (size_t i = 0; i < str.size(); ) {
            unsigned char c = str[i];
            char32_t cp = 0;
            if (c <= 0x7F) { cp = c; i += 1; }
            else if ((c & 0xE0) == 0xC0) {
                if (i + 1 < str.size()) { cp = ((c & 0x1F) << 6) | (str[i+1] & 0x3F); i += 2; } else break;
            }
            else if ((c & 0xF0) == 0xE0) {
                if (i + 2 < str.size()) { cp = ((c & 0x0F) << 12) | ((str[i+1] & 0x3F) << 6) | (str[i+2] & 0x3F); i += 3; } else break;
            }
            else if ((c & 0xF8) == 0xF0) {
                if (i + 3 < str.size()) { cp = ((c & 0x07) << 18) | ((str[i+1] & 0x3F) << 12) | ((str[i+2] & 0x3F) << 6) | (str[i+3] & 0x3F); i += 4; } else break;
            } else {
                cp = '?'; i += 1;
            }
            Storage.push_back(cp);
        }
        Storage.push_back(0);

        Value.Data = Storage.data();
        Value.ArrayNum = static_cast<int32_t>(Storage.size());
        Value.ArrayMax = Value.ArrayNum;
    }
};

struct ClientMessageParams {
    FString Message;
    FName Type;
    float MsgLifeTime;
};

struct FStringHit {
    int32_t Offset;
    FString* Value;
    std::string Text;
};

static bool LooksLikeChatText(const std::string& text) {
    if (text.empty() || text.size() > 512) return false;

    int printable = 0;
    int meaningful = 0;
    int replacement = 0;
    for (unsigned char ch : text) {
        if (std::isprint(ch) || std::isspace(ch)) ++printable;
        if (std::isalnum(ch) || std::isspace(ch) || std::ispunct(ch)) ++meaningful;
        if (ch == '?') ++replacement;
    }

    if (printable < static_cast<int>(text.size() * 8 / 10)) return false;
    if (meaningful < 2) return false;
    if (replacement > static_cast<int>(text.size() * 6 / 10)) return false;
    return true;
}

static bool ReadFStringAt(void* parms, int32_t offset, FStringHit& out) {
    if (offset < 0) return false;

    auto* base = static_cast<unsigned char*>(parms);
    auto* candidate = reinterpret_cast<FString*>(base + offset);
    if (!IsReadable(candidate, sizeof(FString))) return false;
    if (!candidate->IsSane()) return false;

    auto score = [](const std::string& value) {
        int result = 0;
        for (unsigned char ch : value) {
            if (std::isprint(ch) || std::isspace(ch)) ++result;
            else result -= 4;
        }
        return result;
    };

    std::string utf16;
    if (IsReadable(candidate->Data, static_cast<size_t>(candidate->ArrayNum) * sizeof(char16_t))) {
        utf16 = candidate->ToAsciiString<char16_t>();
    }

    std::string utf32;
    if (IsReadable(candidate->Data, static_cast<size_t>(candidate->ArrayNum) * sizeof(char32_t))) {
        utf32 = candidate->ToAsciiString<char32_t>();
    }

    std::string text = score(utf32) > score(utf16) ? utf32 : utf16;
    if (!LooksLikeChatText(text)) return false;

    out = { offset, candidate, text };
    return true;
}

static bool FindFStringInParams(void* parms, FStringHit& out) {
    if (!IsReadable(parms, 0x90)) return false;

    for (int32_t offset = 0; offset <= 0x80; offset += 8) {
        if (ReadFStringAt(parms, offset, out)) return true;
    }
    return false;
}

static bool IsDiscoveryMarker(const std::string& text) {
    return text.find("!discover_chat") != std::string::npos ||
           text.find("!discover_reply") != std::string::npos ||
           text.find("obelisk_probe") != std::string::npos ||
           text.find("/info") != std::string::npos;
}

static void LogCandidate(int32_t nameIndex, const FStringHit& hit) {
    if (!g_Api || g_CandidateLogCount >= 40) return;

    ++g_CandidateLogCount;
    std::string preview = hit.Text.substr(0, 96);
    for (char& ch : preview) {
        if (!std::isprint(static_cast<unsigned char>(ch))) ch = 32;
    }

    char buf[256];
    std::snprintf(buf, sizeof(buf), "[ChatPlugin] Candidate text function index=%d offset=%d text=\"%s\"", nameIndex, hit.Offset, preview.c_str());
    g_Api->LogInfo(buf);
}

static void SendClientMessage(void* caller, const std::string& message) {
    if (!g_Api || !g_ClientMessageFunc || g_ClientMessageIndex == -1) return;

    TempFString response(message);
    ClientMessageParams params{};
    params.Message = response.Value;
    params.Type = {0, 0};
    params.MsgLifeTime = 6.0f;

    if (g_ClientMessageTextOffset <= 0) {
        g_Api->CallProcessEvent(caller, g_ClientMessageFunc, &params);
        return;
    }

    std::array<unsigned char, 160> raw{};
    if (g_ClientMessageTextOffset + static_cast<int32_t>(sizeof(FString)) > static_cast<int32_t>(raw.size())) return;
    std::memcpy(raw.data() + g_ClientMessageTextOffset, &response.Value, sizeof(FString));
    g_Api->CallProcessEvent(caller, g_ClientMessageFunc, raw.data());
}

bool OnProcessEvent(void* caller, void* function, void* parms) {
    if (!function || !parms) return true;

    UObjectBase* funcObj = static_cast<UObjectBase*>(function);
    if (!IsReadable(funcObj, sizeof(UObjectBase))) return true;

    int32_t nameIndex = funcObj->NamePrivate.ComparisonIndex;
    bool knownServerChat = (g_ServerChatIndex != -1 && nameIndex == g_ServerChatIndex);
    bool knownClientMessage = (g_ClientMessageIndex != -1 && nameIndex == g_ClientMessageIndex);
    bool discoveryMode = (g_ServerChatIndex == -1 || g_ClientMessageIndex == -1);
    bool canScanUnknown = discoveryMode && g_DiscoveryEnabled;

    if (!knownServerChat && !knownClientMessage && !canScanUnknown) {
        std::lock_guard<std::mutex> lock(g_ScanMutex);
        if (g_ScannedIndexes.count(nameIndex)) return true;
        g_ScannedIndexes.insert(nameIndex);
        return true;
    }

    FStringHit hit{};
    bool hasText = false;
    if (knownServerChat && g_ServerChatMessageOffset >= 0) {
        hasText = ReadFStringAt(parms, g_ServerChatMessageOffset, hit);
    }
    if (!hasText && knownClientMessage && g_ClientMessageTextOffset >= 0) {
        hasText = ReadFStringAt(parms, g_ClientMessageTextOffset, hit);
    }
    if (!hasText) {
        hasText = FindFStringInParams(parms, hit);
    }
    if (!hasText) return true;

    const std::string& text = hit.Text;
    if (canScanUnknown && !IsDiscoveryMarker(text)) {
        return true;
    }

    if (discoveryMode || knownServerChat || knownClientMessage) {
        LogCandidate(nameIndex, hit);
    }

    if (g_ServerChatIndex == -1 && text.find("!discover_chat") != std::string::npos) {
        g_ServerChatIndex = nameIndex;
        g_ServerChatMessageOffset = hit.Offset;
        SaveConfig();
        if (g_Api) g_Api->LogInfo("[ChatPlugin] ServerChat discovered.");
        return false;
    }

    if (g_ClientMessageIndex == -1 && text.find("!discover_reply") != std::string::npos) {
        g_ClientMessageIndex = nameIndex;
        g_ClientMessageTextOffset = hit.Offset;
        g_ClientMessageFunc = function;
        SaveConfig();
        if (g_Api) g_Api->LogInfo("[ChatPlugin] ClientMessage discovered.");
        return true;
    }

    if (knownClientMessage) {
        if (g_ClientMessageFunc == nullptr) g_ClientMessageFunc = function;
        if (g_ClientMessageTextOffset < 0) {
            g_ClientMessageTextOffset = hit.Offset;
            SaveConfig();
        }
    }

    if (knownServerChat && text.find("/info") != std::string::npos) {
        if (g_Api) g_Api->LogInfo("[ChatPlugin] Command /info detected.");

        if (g_ClientMessageFunc != nullptr && g_ClientMessageIndex != -1) {
            SendClientMessage(caller, "Obelisk VIP: Bienvenido al servidor. Plugins 100% nativos.");
        } else if (g_Api) {
            g_Api->LogInfo("[ChatPlugin] ClientMessage not captured yet. Use !discover_reply first.");
        }
        return false;
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    g_Api = api;
    LoadConfig();
    api->LogInfo(g_DiscoveryEnabled
        ? "[ChatPlugin] Motor heurístico de chat inicializado en modo descubrimiento."
        : "[ChatPlugin] Motor heurístico de chat inicializado.");

    bool registeredFiltered = false;
    if (g_ServerChatIndex != -1 && api->RegisterPreProcessEventForNameIndex) {
        api->RegisterPreProcessEventForNameIndex(g_ServerChatIndex, OnProcessEvent);
        registeredFiltered = true;
    }
    if (g_ClientMessageIndex != -1 && api->RegisterPreProcessEventForNameIndex) {
        api->RegisterPreProcessEventForNameIndex(g_ClientMessageIndex, OnProcessEvent);
        registeredFiltered = true;
    }

    if (!registeredFiltered && g_DiscoveryEnabled) {
        api->RegisterPreProcessEvent(OnProcessEvent);
    } else if (!registeredFiltered) {
        api->LogWarn("[ChatPlugin] No hay índices configurados. Activa OBELISK_CHAT_DISCOVERY=1 sólo para descubrimiento controlado.");
    }

    return true;
}
