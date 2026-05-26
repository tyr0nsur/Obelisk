#include "ProcessEventHook.h"
#include "ue/Memory.h"
#include "runtime/Logger.h"
#include <subhook.h>

namespace Obelisk::Hooks
{
    typedef void (*ProcessEvent_t)(void* object, void* function, void* params);
    static subhook_t s_ProcessEventHook = nullptr;

    void ProcessEvent_Detour(void* object, void* function, void* params)
    {
        // Temporary test logic: Just log the first 5 calls to avoid spam
        static int callCount = 0;
        if (callCount < 5) {
            OBELISK_TRACE("ProcessEvent intercepted! Call #{}", ++callCount);
        }

        // Call original function
        ProcessEvent_t original = (ProcessEvent_t)subhook_get_trampoline(s_ProcessEventHook);
        if (original)
            original(object, function, params);
    }

    void ProcessEventHook::Install()
    {
        // 1. Intento por Pattern Scanning
        // Firma exacta extraída heurísticamente para ShooterGameServer Linux
        std::string pattern = "55 48 89 E5 41 57 41 56 41 55 41 54 53 48 81 EC 88 00 00 00 49 89 FC 4D 85 E4 41 0F 95 C6"; 
        void* processEventAddr = Memory::FindPattern(pattern);

        if (!processEventAddr)
        {
            OBELISK_WARN("Pattern not found. Trying direct offset...");
            uintptr_t baseAddress = Memory::GetMainModuleInfo().start;
            if (baseAddress != 0) {
                // Offset duro extraído como backup (0x1D11CB0)
                processEventAddr = reinterpret_cast<void*>(baseAddress + 0x1D11CB0); 
            }
        }

        if (!processEventAddr)
        {
            OBELISK_ERROR("Failed to find ProcessEvent signature or offset. Hook NOT installed.");
            return;
        }

        OBELISK_INFO("Found ProcessEvent at address: {}", processEventAddr);

        s_ProcessEventHook = subhook_new(processEventAddr, (void*)&ProcessEvent_Detour);
        if (subhook_install(s_ProcessEventHook) == 0)
        {
            OBELISK_INFO("ProcessEvent hook installed successfully.");
        }
        else
        {
            OBELISK_ERROR("Failed to install ProcessEvent hook!");
        }
    }
}
