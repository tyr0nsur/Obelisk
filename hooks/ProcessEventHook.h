#pragma once

namespace Obelisk::Hooks
{
    class ProcessEventHook
    {
    public:
        static void Install();
        static void CallOriginalProcessEvent(void* object, void* function, void* params);
        static bool IsInstalled();
        static bool Remove();
    };
}
