#include "EventManager.h"
#include "runtime/Logger.h"
#include <exception>

namespace Obelisk::Core
{
    EventManager& EventManager::Get()
    {
        static EventManager instance;
        return instance;
    }

    void EventManager::RegisterPreProcessEvent(OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_PreProcessEventCallbacks.push_back(callback);
    }

    void EventManager::RegisterPostProcessEvent(OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_PostProcessEventCallbacks.push_back(callback);
    }

    void EventManager::RegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_FilteredPreProcessEventCallbacks.push_back({nameIndex, callback});
    }

    void EventManager::RegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_FilteredPostProcessEventCallbacks.push_back({nameIndex, callback});
    }

    bool EventManager::HasPreProcessEventCallbacks()
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return !m_PreProcessEventCallbacks.empty() || !m_FilteredPreProcessEventCallbacks.empty();
    }

    bool EventManager::HasPostProcessEventCallbacks()
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return !m_PostProcessEventCallbacks.empty() || !m_FilteredPostProcessEventCallbacks.empty();
    }

    bool EventManager::TriggerPreProcessEvent(void* caller, void* function, void* parms)
    {
        std::vector<OnProcessEventCallback> callbacks;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            callbacks = m_PreProcessEventCallbacks;
        }

        for (auto callback : callbacks)
        {
            if (!callback)
                continue;

            try
            {
                if (!callback(caller, function, parms))
                    return false;
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("PreProcessEvent callback threw: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("PreProcessEvent callback threw an unknown exception.");
            }
        }
        return true;
    }

    bool EventManager::TriggerPreProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms)
    {
        if (!TriggerPreProcessEvent(caller, function, parms))
            return false;

        std::vector<OnProcessEventCallback> callbacks;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_FilteredPreProcessEventCallbacks)
            {
                if (item.first == nameIndex)
                    callbacks.push_back(item.second);
            }
        }

        for (auto callback : callbacks)
        {
            if (!callback)
                continue;

            try
            {
                if (!callback(caller, function, parms))
                    return false;
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Filtered PreProcessEvent callback threw: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Filtered PreProcessEvent callback threw an unknown exception.");
            }
        }
        return true;
    }

    void EventManager::TriggerPostProcessEvent(void* caller, void* function, void* parms)
    {
        std::vector<OnProcessEventCallback> callbacks;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            callbacks = m_PostProcessEventCallbacks;
        }

        for (auto callback : callbacks)
        {
            if (!callback)
                continue;

            try
            {
                callback(caller, function, parms);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("PostProcessEvent callback threw: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("PostProcessEvent callback threw an unknown exception.");
            }
        }
    }

    void EventManager::TriggerPostProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms)
    {
        TriggerPostProcessEvent(caller, function, parms);

        std::vector<OnProcessEventCallback> callbacks;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_FilteredPostProcessEventCallbacks)
            {
                if (item.first == nameIndex)
                    callbacks.push_back(item.second);
            }
        }

        for (auto callback : callbacks)
        {
            if (!callback)
                continue;

            try
            {
                callback(caller, function, parms);
            }
            catch (const std::exception& e)
            {
                OBELISK_ERROR("Filtered PostProcessEvent callback threw: {}", e.what());
            }
            catch (...)
            {
                OBELISK_ERROR("Filtered PostProcessEvent callback threw an unknown exception.");
            }
        }
    }
}
