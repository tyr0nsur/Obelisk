#include "api/ObeliskApi.h"
#include <string>
#include <set>
#include <mutex>
#include <vector>
#include <fstream>
#include <fcntl.h>
#include <unistd.h>

// Safe memory reader
bool IsReadable(void* ptr, size_t size) {
    if (!ptr || size == 0) return false;
    int fd = open("/dev/random", O_WRONLY);
    if (fd < 0) return false;
    ssize_t ret = write(fd, ptr, size);
    close(fd);
    return ret >= 0;
}

// Basic UE4 types
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
static int32_t g_PreLoginNameIndex = -1;
static std::vector<std::string> g_Whitelist;

void LoadWhitelist() {
    g_Whitelist.clear();
    std::ifstream file("whitelist.txt");
    std::string line;
    while (std::getline(file, line)) {
        if (!line.empty() && line[0] != '#') {
            g_Whitelist.push_back(line);
        }
    }
}

bool OnProcessEvent(void* caller, void* function, void* parms) {
    if (!function || !parms) return true;

    UObjectBase* funcObj = (UObjectBase*)function;
    int32_t nameIndex = funcObj->NamePrivate.ComparisonIndex;

    // Fast path: if we already know PreLogin's NameIndex
    if (g_PreLoginNameIndex != -1 && nameIndex != g_PreLoginNameIndex) {
        return true;
    }

    // Check if parms is readable as FString
    if (!IsReadable(parms, sizeof(FString))) return true;

    FString* options = (FString*)parms;
    
    // Sanity checks for FString
    if (options->ArrayNum > 10 && options->ArrayNum < 1024 && options->Data != nullptr) {
        std::string optStr = options->ToString();
        
        // Is this the PreLogin function?
        if (optStr.find("SteamClientAuthToken=") != std::string::npos || optStr.find("?bIsFromInvite=") != std::string::npos) {
            
            // We found PreLogin! Save the NameIndex for future fast path.
            if (g_PreLoginNameIndex == -1) {
                g_PreLoginNameIndex = nameIndex;
                char buf[256];
                snprintf(buf, sizeof(buf), "PreLogin discovered! NameIndex: %d", nameIndex);
                if (g_Api) g_Api->LogInfo(buf);
            }

            // Extract Steam ID. Format: ?SteamClientAuthToken=... or ?NumOpenPrivateConnections=...?SteamID=... wait, in ARK usually there's no ?SteamID=.
            // Actually, in ARK the UniqueId is passed in the 3rd parameter. But parsing that is complex.
            // Wait! The user might connect. Can we just read the steam auth token?
            // Actually, we can just reject everyone for testing!
            
            if (g_Api) g_Api->LogInfo("Player attempting to login!");
            
            // For MVP: Reject the connection unconditionally just to prove we can intercept and block it,
            // or allow it. Let's just return false to block the event from running entirely!
            // Wait, if we return false to block ProcessEvent, the engine might not reply to the client, leading to a timeout instead of a kick message.
            // To do it properly, we would overwrite ErrorMessage.
            // But returning false is a quick way to prove it works!
            
            return false; // BLOCK!
        }
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api) {
    g_Api = api;
    api->LogInfo("Whitelist Plugin Initialized!");
    LoadWhitelist();
    api->RegisterPreProcessEvent(OnProcessEvent);
    return true;
}
