#include "api/ObeliskApi.h"
#include <string>
#include <set>
#include <mutex>
#include <vector>
#include <thread>
#include <fstream>
#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

// Safe memory reader
bool IsReadable(void* ptr, size_t size) {
    if (!ptr || size == 0) return false;
    int fd = open("/dev/random", O_WRONLY);
    if (fd < 0) return false;
    ssize_t ret = write(fd, ptr, size);
    close(fd);
    return ret >= 0;
}

struct FString {
    void* Data;
    int32_t ArrayNum;
    int32_t ArrayMax;

    std::string ToString() const {
        if (!IsReadable(Data, ArrayNum * 2)) return "";
        std::string result;
        char16_t* ptr = (char16_t*)Data;
        for (int32_t i = 0; i < ArrayNum && i < 1024; ++i) {
            if (ptr[i] == 0) break;
            result += (char)(ptr[i] & 0xFF);
        }
        return result;
    }
};

struct FName {
    int32_t ComparisonIndex;
    int32_t Number;
};

struct UObjectBase {
    void** VTable;
    int32_t ObjectFlags;
    int32_t InternalIndex;
    void* ClassPrivate;
    FName NamePrivate;
};

static ObeliskApi* g_Api = nullptr;
static httplib::Server g_HttpServer;
static std::thread g_HttpThread;
static std::thread g_LogThread;

static std::mutex g_LogMutex;
static std::vector<std::string> g_RecentLogs;

static std::mutex g_ConfigMutex;
static json g_Config;
static std::string g_ConfigPath = "ObeliskPlugins/config.json";

static int32_t g_PreLoginNameIndex = -1;
static std::mutex g_ScanMutex;
static std::set<int32_t> g_ScannedIndexes;

void LoadConfig() {
    std::lock_guard<std::mutex> lock(g_ConfigMutex);
    std::ifstream f(g_ConfigPath);
    if (f.is_open()) {
        try {
            g_Config = json::parse(f);
        } catch (...) {
            if (g_Api) g_Api->LogError("Error parsing config.json");
        }
    } else {
        // Default config
        g_Config = {
            {"whitelist_enabled", false},
            {"whitelist", json::array()},
            {"admins", json::array()},
            {"offsets", {
                {"PreLoginNameIndex", -1}
            }}
        };
        std::ofstream o(g_ConfigPath);
        o << g_Config.dump(4);
    }
    
    // Cargar caché de offsets si existe
    if (g_Config.contains("offsets") && g_Config["offsets"].contains("PreLoginNameIndex")) {
        g_PreLoginNameIndex = g_Config["offsets"]["PreLoginNameIndex"].get<int32_t>();
    }
}

void SaveConfig() {
    std::ofstream o(g_ConfigPath);
    o << g_Config.dump(4);
}

bool IsWhitelisted(const std::string& steamId) {
    std::lock_guard<std::mutex> lock(g_ConfigMutex);
    if (!g_Config["whitelist_enabled"].get<bool>()) return true;
    for (auto& id : g_Config["whitelist"]) {
        if (id.get<std::string>() == steamId) return true;
    }
    return false;
}

void LogReaderThread() {
    std::ifstream file("../../Saved/Logs/ShooterGame.log");
    if (!file.is_open()) return;
    file.seekg(0, std::ios::end);

    std::string line;
    while (true) {
        if (std::getline(file, line)) {
            std::lock_guard<std::mutex> lock(g_LogMutex);
            g_RecentLogs.push_back(line);
            if (g_RecentLogs.size() > 100) g_RecentLogs.erase(g_RecentLogs.begin());
        } else {
            file.clear();
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }
}

void StartHttpServer() {
    g_HttpServer.Get("/status", [](const httplib::Request&, httplib::Response& res) {
        res.set_content("{\"status\":\"ok\"}", "application/json");
    });

    g_HttpServer.Get("/logs", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(g_LogMutex);
        json j = g_RecentLogs;
        res.set_content(j.dump(), "application/json");
    });

    g_HttpServer.Get("/config", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(g_ConfigMutex);
        res.set_content(g_Config.dump(), "application/json");
    });

    g_HttpServer.Post("/config", [](const httplib::Request& req, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(g_ConfigMutex);
        try {
            g_Config = json::parse(req.body);
            SaveConfig();
            res.set_content("{\"status\":\"success\"}", "application/json");
        } catch(...) {
            res.set_content("{\"status\":\"error\"}", "application/json");
        }
    });

    g_HttpServer.listen("0.0.0.0", 28000);
}

// Extractor de SteamID buscando el MAGIC "0x01100001"
std::string ExtractSteamID(void* parms) {
    if (!IsReadable(parms, 128)) return "";
    uint64_t* ptr = (uint64_t*)parms;
    for (int i = 0; i < 16; ++i) { // scan first 128 bytes
        uint64_t val = ptr[i];
        if ((val >> 32) == 0x01100001) {
            return std::to_string(val);
        }
    }
    return "";
}

bool OnProcessEvent(void* caller, void* function, void* parms) {
    if (!function || !parms) return true;

    UObjectBase* funcObj = (UObjectBase*)function;
    int32_t nameIndex = funcObj->NamePrivate.ComparisonIndex;

    if (g_PreLoginNameIndex != -1) {
        if (nameIndex != g_PreLoginNameIndex) return true;
    } else {
        // Fast-pathing: si ya hemos escaneado esta función y no es PreLogin, la ignoramos.
        {
            std::lock_guard<std::mutex> lock(g_ScanMutex);
            if (g_ScannedIndexes.count(nameIndex)) return true;
            g_ScannedIndexes.insert(nameIndex);
        }
    }

    if (!IsReadable(parms, sizeof(FString))) return true;

    FString* options = (FString*)parms;
    
    if (options->ArrayNum > 10 && options->ArrayNum < 1024 && options->Data != nullptr) {
        std::string optStr = options->ToString();
        
        if (optStr.find("SteamClientAuthToken=") != std::string::npos || optStr.find("?bIsFromInvite=") != std::string::npos) {
            // ¡Heurística exitosa! Guardar en caché permanente.
            if (g_PreLoginNameIndex == -1) {
                g_PreLoginNameIndex = nameIndex;
                std::lock_guard<std::mutex> lock(g_ConfigMutex);
                g_Config["offsets"]["PreLoginNameIndex"] = nameIndex;
                SaveConfig();
            }
            
            std::string steamId = ExtractSteamID(parms);
            
            char buf[256];
            snprintf(buf, sizeof(buf), "PreLogin: Player connecting. Extracted SteamID: %s", steamId.c_str());
            if (g_Api) g_Api->LogInfo(buf);

            if (!steamId.empty() && !IsWhitelisted(steamId)) {
                if (g_Api) g_Api->LogInfo("Conexión bloqueada por Whitelist.");
                return false; 
            }
        }
    }
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    g_Api = api;
    api->LogInfo("Monitor Plugin Initialized!");
    
    LoadConfig();
    
    g_LogThread = std::thread(LogReaderThread);
    g_LogThread.detach();
    
    g_HttpThread = std::thread(StartHttpServer);
    g_HttpThread.detach();

    api->RegisterPreProcessEvent(OnProcessEvent);
    return true;
}
