#include "EventManager.h"
#include "runtime/Logger.h"
#include <algorithm>
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
        RegisterPreProcessEventOwned(nullptr, callback);
    }

    void EventManager::RegisterPostProcessEvent(OnProcessEventCallback callback)
    {
        RegisterPostProcessEventOwned(nullptr, callback);
    }

    void EventManager::RegisterPreProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback)
    {
        RegisterPreProcessEventForNameIndexOwned(nullptr, nameIndex, callback);
    }

    void EventManager::RegisterPostProcessEventForNameIndex(int32_t nameIndex, OnProcessEventCallback callback)
    {
        RegisterPostProcessEventForNameIndexOwned(nullptr, nameIndex, callback);
    }

    uint64_t EventManager::AllocateRegistrationId()
    {
        uint64_t id = 0;
        do
        {
            id = m_NextRegistrationId++;
            if (m_NextRegistrationId == 0)
                m_NextRegistrationId = 1;
        } while (id == 0 || HasRegistrationId(id));

        return id;
    }

    bool EventManager::HasRegistrationId(uint64_t registrationId) const
    {
        auto containsId = [registrationId](const auto& callbacks) {
            return std::any_of(callbacks.begin(), callbacks.end(), [registrationId](const CallbackRegistration& item) {
                return item.id == registrationId;
            });
        };

        return containsId(m_PreProcessEventCallbacks) ||
               containsId(m_PostProcessEventCallbacks) ||
               containsId(m_FilteredPreProcessEventCallbacks) ||
               containsId(m_FilteredPostProcessEventCallbacks);
    }

    uint64_t EventManager::RegisterPreProcessEventOwned(void* owner, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_PreProcessEventCallbacks.push_back({id, -1, callback, owner});
        return id;
    }

    uint64_t EventManager::RegisterPostProcessEventOwned(void* owner, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_PostProcessEventCallbacks.push_back({id, -1, callback, owner});
        return id;
    }

    uint64_t EventManager::RegisterPreProcessEventForNameIndexOwned(void* owner, int32_t nameIndex, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_FilteredPreProcessEventCallbacks.push_back({id, nameIndex, callback, owner});
        return id;
    }

    uint64_t EventManager::RegisterPostProcessEventForNameIndexOwned(void* owner, int32_t nameIndex, OnProcessEventCallback callback)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_FilteredPostProcessEventCallbacks.push_back({id, nameIndex, callback, owner});
        return id;
    }

    bool EventManager::UnregisterCallback(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::lock_guard<std::mutex> lock(m_Mutex);

        auto removeForId = [registrationId](auto& callbacks) -> bool {
            const auto before = callbacks.size();
            callbacks.erase(
                std::remove_if(callbacks.begin(), callbacks.end(), [registrationId](const CallbackRegistration& item) {
                    return item.id == registrationId;
                }),
                callbacks.end());
            return callbacks.size() != before;
        };

        return removeForId(m_PreProcessEventCallbacks) ||
               removeForId(m_PostProcessEventCallbacks) ||
               removeForId(m_FilteredPreProcessEventCallbacks) ||
               removeForId(m_FilteredPostProcessEventCallbacks);
    }

    bool EventManager::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::lock_guard<std::mutex> lock(m_Mutex);

        auto removeForOwnerAndId = [owner, registrationId](auto& callbacks) -> bool {
            const auto before = callbacks.size();
            callbacks.erase(
                std::remove_if(callbacks.begin(), callbacks.end(), [owner, registrationId](const CallbackRegistration& item) {
                    return item.owner == owner && item.id == registrationId;
                }),
                callbacks.end());
            return callbacks.size() != before;
        };

        return removeForOwnerAndId(m_PreProcessEventCallbacks) ||
               removeForOwnerAndId(m_PostProcessEventCallbacks) ||
               removeForOwnerAndId(m_FilteredPreProcessEventCallbacks) ||
               removeForOwnerAndId(m_FilteredPostProcessEventCallbacks);
    }

    size_t EventManager::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::lock_guard<std::mutex> lock(m_Mutex);

        auto removeForOwner = [owner](auto& callbacks) -> size_t {
            const size_t before = callbacks.size();
            callbacks.erase(
                std::remove_if(callbacks.begin(), callbacks.end(), [owner](const CallbackRegistration& item) {
                    return item.owner == owner;
                }),
                callbacks.end());
            return before - callbacks.size();
        };

        return removeForOwner(m_PreProcessEventCallbacks) +
               removeForOwner(m_PostProcessEventCallbacks) +
               removeForOwner(m_FilteredPreProcessEventCallbacks) +
               removeForOwner(m_FilteredPostProcessEventCallbacks);
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

    void EventManager::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }

    bool EventManager::TriggerPreProcessEvent(void* caller, void* function, void* parms)
    {
        std::vector<OnProcessEventCallback> callbacks;
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_PreProcessEventCallbacks)
                callbacks.push_back(item.callback);
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
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_FilteredPreProcessEventCallbacks)
            {
                if (item.nameIndex == nameIndex)
                    callbacks.push_back(item.callback);
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
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_PostProcessEventCallbacks)
                callbacks.push_back(item.callback);
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
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            for (const auto& item : m_FilteredPostProcessEventCallbacks)
            {
                if (item.nameIndex == nameIndex)
                    callbacks.push_back(item.callback);
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
