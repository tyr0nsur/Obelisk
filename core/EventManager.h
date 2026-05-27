#pragma once

#include "api/ObeliskApi.h"
#include <vector>
#include <mutex>
#include <cstddef>

namespace Obelisk::Core
{
    class EventManager
    {
    public:
        EventManager() = default;
        ~EventManager() = default;

        static EventManager& Get();

        void RegisterPreProcessEvent(OnProcessEventCallback callback);
        void RegisterPostProcessEvent(OnProcessEventCallback callback);
        void RegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback);
        void RegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback);
        void RegisterPreProcessEventOwned(void* owner, OnProcessEventCallback callback);
        void RegisterPostProcessEventOwned(void* owner, OnProcessEventCallback callback);
        void RegisterPreProcessEventForNameIndexOwned(void* owner, int32_t nameIndex, OnProcessEventCallback callback);
        void RegisterPostProcessEventForNameIndexOwned(void* owner, int32_t nameIndex, OnProcessEventCallback callback);
        size_t UnregisterCallbacksForOwner(void* owner);

        bool HasPreProcessEventCallbacks();
        bool HasPostProcessEventCallbacks();

        // Called by hooks
        // Returns false if any plugin blocked the event
        bool TriggerPreProcessEvent(void* caller, void* function, void* parms);
        void TriggerPostProcessEvent(void* caller, void* function, void* parms);
        bool TriggerPreProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms);
        void TriggerPostProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms);

    private:
        struct CallbackRegistration {
            int32_t nameIndex;
            OnProcessEventCallback callback;
            void* owner;
        };

        std::mutex m_Mutex;
        std::mutex m_DispatchMutex;
        std::vector<CallbackRegistration> m_PreProcessEventCallbacks;
        std::vector<CallbackRegistration> m_PostProcessEventCallbacks;
        std::vector<CallbackRegistration> m_FilteredPreProcessEventCallbacks;
        std::vector<CallbackRegistration> m_FilteredPostProcessEventCallbacks;
    };
}
