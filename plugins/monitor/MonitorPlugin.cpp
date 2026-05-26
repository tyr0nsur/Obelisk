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
#define CPPHTTPLIB_OPENSSL_SUPPORT 0
#include "httplib.h"

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

static std::mutex g_WhitelistMutex;
static std::set<std::string> g_Whitelist;
static bool g_WhitelistEnabled = false;

static int32_t g_PreLoginNameIndex = -1;

void LogReaderThread() {
    std::ifstream file("../../Saved/Logs/ShooterGame.log");
    if (!file.is_open()) {
        if (g_Api) g_Api->LogError("MonitorPlugin: No se pudo abrir ShooterGame.log");
        return;
    }
    
    // Ir al final del archivo
    file.seekg(0, std::ios::end);

    std::string line;
    while (true) {
        if (std::getline(file, line)) {
            std::lock_guard<std::mutex> lock(g_LogMutex);
            g_RecentLogs.push_back(line);
            if (g_RecentLogs.size() > 100) { // Mantener solo las últimas 100 líneas
                g_RecentLogs.erase(g_RecentLogs.begin());
            }
        } else {
            file.clear(); // Limpiar el estado de EOF
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }
}

void StartHttpServer() {
    g_HttpServer.Get("/status", [](const httplib::Request&, httplib::Response& res) {
        res.set_content("{\"status\":\"ok\", \"version\":\"1.0\"}", "application/json");
    });

    g_HttpServer.Get("/logs", [](const httplib::Request&, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(g_LogMutex);
        std::string json = "[";
        for (size_t i = 0; i < g_RecentLogs.size(); ++i) {
            // Un escape muy básico para JSON
            std::string escaped = g_RecentLogs[i];
            size_t pos = 0;
            while ((pos = escaped.find('"', pos)) != std::string::npos) {
                escaped.replace(pos, 1, "\\\"");
                pos += 2;
            }
            json += "\"" + escaped + "\"";
            if (i < g_RecentLogs.size() - 1) json += ",";
        }
        json += "]";
        res.set_content(json, "application/json");
    });

    g_HttpServer.Post("/whitelist/toggle", [](const httplib::Request& req, httplib::Response& res) {
        std::lock_guard<std::mutex> lock(g_WhitelistMutex);
        g_WhitelistEnabled = !g_WhitelistEnabled;
        res.set_content(g_WhitelistEnabled ? "{\"enabled\":true}" : "{\"enabled\":false}", "application/json");
    });

    if (g_Api) g_Api->LogInfo("MonitorPlugin: Servidor HTTP escuchando en el puerto 28000");
    g_HttpServer.listen("0.0.0.0", 28000);
}

bool OnProcessEvent(void* caller, void* function, void* parms) {
    if (!function || !parms) return true;

    UObjectBase* funcObj = (UObjectBase*)function;
    int32_t nameIndex = funcObj->NamePrivate.ComparisonIndex;

    if (g_PreLoginNameIndex != -1 && nameIndex != g_PreLoginNameIndex) return true;
    if (!IsReadable(parms, sizeof(FString))) return true;

    FString* options = (FString*)parms;
    
    if (options->ArrayNum > 10 && options->ArrayNum < 1024 && options->Data != nullptr) {
        std::string optStr = options->ToString();
        
        if (optStr.find("SteamClientAuthToken=") != std::string::npos || optStr.find("?bIsFromInvite=") != std::string::npos) {
            if (g_PreLoginNameIndex == -1) g_PreLoginNameIndex = nameIndex;
            
            std::lock_guard<std::mutex> lock(g_WhitelistMutex);
            if (g_WhitelistEnabled) {
                if (g_Api) g_Api->LogInfo("MonitorPlugin: ¡Conexión bloqueada por Whitelist!");
                return false; 
            } else {
                if (g_Api) g_Api->LogInfo("MonitorPlugin: Conexión permitida (Whitelist desactivada)");
            }
        }
    }
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    g_Api = api;
    api->LogInfo("Monitor Plugin Initialized!");
    
    // Iniciar hilos
    g_LogThread = std::thread(LogReaderThread);
    g_LogThread.detach();
    
    g_HttpThread = std::thread(StartHttpServer);
    g_HttpThread.detach();

    api->RegisterPreProcessEvent(OnProcessEvent);
    return true;
}
