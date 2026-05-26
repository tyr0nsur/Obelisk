#pragma once

#include "api/ObeliskApi.h"
#include <vector>
#include <mutex>

namespace Obelisk::Core
{
    class EventManager
    {
    public:
        static EventManager& Get();

        void RegisterPreProcessEvent(OnProcessEventCallback callback);
        void RegisterPostProcessEvent(OnProcessEventCallback callback);
        void RegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback);
        void RegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback);

        bool HasPreProcessEventCallbacks();
        bool HasPostProcessEventCallbacks();

        // Called by hooks
        // Returns false if any plugin blocked the event
        bool TriggerPreProcessEvent(void* caller, void* function, void* parms);
        void TriggerPostProcessEvent(void* caller, void* function, void* parms);
        bool TriggerPreProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms);
        void TriggerPostProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms);

    private:
        EventManager() = default;
        ~EventManager() = default;

        std::mutex m_Mutex;
        std::vector<OnProcessEventCallback> m_PreProcessEventCallbacks;
        std::vector<OnProcessEventCallback> m_PostProcessEventCallbacks;
        std::vector<std::pair<int32_t, OnProcessEventCallback>> m_FilteredPreProcessEventCallbacks;
        std::vector<std::pair<int32_t, OnProcessEventCallback>> m_FilteredPostProcessEventCallbacks;
    };
}
