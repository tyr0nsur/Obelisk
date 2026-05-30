#if !defined(obelisk_EXPORTS)
#define OBELISK_EVENT_MANAGER_ENABLE_TEST_HOOKS
#endif

#include "EventManager.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include <algorithm>
#include <atomic>
#include <exception>
#include <new>

namespace Obelisk::Core
{
    namespace
    {
        std::atomic<bool> g_ProcessEventBlockingCapabilityAdvertised{false};
#ifdef OBELISK_EVENT_MANAGER_ENABLE_TEST_HOOKS
        std::atomic<int> g_ForcedSnapshotFailuresRemaining{0};
#endif

        bool IsProcessEventBlockingAllowed()
        {
            return g_ProcessEventBlockingCapabilityAdvertised.load(std::memory_order_acquire) &&
                Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ALLOW_PROCESS_EVENT_BLOCKING",
                                                       "allow-process-event-blocking");
        }

        void MaybeForceSnapshotFailureForTesting()
        {
#ifdef OBELISK_EVENT_MANAGER_ENABLE_TEST_HOOKS
            int remaining = g_ForcedSnapshotFailuresRemaining.load(std::memory_order_acquire);
            while (remaining > 0)
            {
                if (g_ForcedSnapshotFailuresRemaining.compare_exchange_weak(
                        remaining,
                        remaining - 1,
                        std::memory_order_acq_rel,
                        std::memory_order_acquire))
                    throw std::bad_alloc();
            }
            if (remaining < 0)
                throw std::bad_alloc();
#endif
        }

        void SafeLogWarnNoThrow(const char* message) noexcept
        {
            try
            {
                if (Logger::IsInitialized())
                    Logger::Get()->warn("{}", message ? message : "");
            }
            catch (...)
            {
            }
        }

        void SafeLogErrorNoThrow(const char* message, const char* detail = nullptr) noexcept
        {
            try
            {
                if (!Logger::IsInitialized())
                    return;
                if (detail)
                    Logger::Get()->error("{}: {}", message ? message : "", detail);
                else
                    Logger::Get()->error("{}", message ? message : "");
            }
            catch (...)
            {
            }
        }
    }

    EventManager& EventManager::Get()
    {
        static auto* instance = new EventManager();
        return *instance;
    }

    void EventManager::SetProcessEventBlockingCapabilityAdvertised(bool advertised)
    {
        g_ProcessEventBlockingCapabilityAdvertised.store(advertised, std::memory_order_release);
    }

#ifdef OBELISK_EVENT_MANAGER_ENABLE_TEST_HOOKS
    void EventManager::SetForceSnapshotFailureForTesting(bool enabled)
    {
        g_ForcedSnapshotFailuresRemaining.store(enabled ? -1 : 0, std::memory_order_release);
    }

    void EventManager::SetForcedSnapshotFailuresRemainingForTesting(int failuresRemaining)
    {
        g_ForcedSnapshotFailuresRemaining.store(failuresRemaining < 0 ? -1 : failuresRemaining,
                                                std::memory_order_release);
    }
#endif

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

    uint64_t EventManager::AllocateRegistrationGeneration()
    {
        uint64_t generation = m_NextRegistrationGeneration++;
        if (m_NextRegistrationGeneration == 0)
            m_NextRegistrationGeneration = 1;
        return generation == 0 ? 1 : generation;
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

    bool EventManager::IsRegistrationActive(uint64_t registrationId) const
    {
        return registrationId != 0 && HasRegistrationId(registrationId);
    }

    uint64_t EventManager::RegisterPreProcessEventOwned(void* owner,
                                                        OnProcessEventCallback callback,
                                                        bool allowProcessEventBlocking)
    {
        if (!callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_PreProcessEventCallbacks.push_back({
            id,
            AllocateRegistrationGeneration(),
            -1,
            callback,
            owner,
            allowProcessEventBlocking,
        });
        return id;
    }

    uint64_t EventManager::RegisterPostProcessEventOwned(void* owner, OnProcessEventCallback callback)
    {
        if (!callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_PostProcessEventCallbacks.push_back({id, AllocateRegistrationGeneration(), -1, callback, owner, false});
        return id;
    }

    uint64_t EventManager::RegisterPreProcessEventForNameIndexOwned(void* owner,
                                                                    int32_t nameIndex,
                                                                    OnProcessEventCallback callback,
                                                                    bool allowProcessEventBlocking)
    {
        if (!callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_FilteredPreProcessEventCallbacks.push_back({
            id,
            AllocateRegistrationGeneration(),
            nameIndex,
            callback,
            owner,
            allowProcessEventBlocking,
        });
        return id;
    }

    uint64_t EventManager::RegisterPostProcessEventForNameIndexOwned(void* owner, int32_t nameIndex, OnProcessEventCallback callback)
    {
        if (!callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_FilteredPostProcessEventCallbacks.push_back({
            id,
            AllocateRegistrationGeneration(),
            nameIndex,
            callback,
            owner,
            false,
        });
        return id;
    }

    bool EventManager::UnregisterCallback(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

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

#ifdef OBELISK_EVENT_MANAGER_ENABLE_TEST_HOOKS
    void EventManager::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }
#endif

    bool EventManager::TriggerPreProcessEvent(void* caller, void* function, void* parms)
    {
        return TriggerPreProcessEvent(caller, function, parms, nullptr);
    }

    bool EventManager::TriggerPreProcessEvent(void* caller, void* function, void* parms, bool* setupFailed)
    {
        try
        {
            if (setupFailed)
                *setupFailed = false;
            std::vector<CallbackSnapshot> callbacks;
            std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
            const auto isSnapshotActive = [this](const CallbackSnapshot& snapshot) {
                return snapshot.id != 0 &&
                    std::any_of(m_PreProcessEventCallbacks.begin(),
                                m_PreProcessEventCallbacks.end(),
                                [&snapshot](const CallbackRegistration& item) {
                                    return item.id == snapshot.id &&
                                           item.generation == snapshot.generation &&
                                           item.callback == snapshot.callback;
                                });
            };
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                MaybeForceSnapshotFailureForTesting();
                callbacks.reserve(m_PreProcessEventCallbacks.size());
                for (const auto& item : m_PreProcessEventCallbacks)
                    callbacks.push_back({item.id, item.generation, item.callback, item.allowProcessEventBlocking});
            }

            for (const auto& snapshot : callbacks)
            {
                if (!snapshot.callback)
                    continue;
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    if (!isSnapshotActive(snapshot))
                        continue;
                }

                try
                {
                    if (!snapshot.callback(caller, function, parms))
                    {
                        if (snapshot.allowProcessEventBlocking && IsProcessEventBlockingAllowed())
                            return false;
                        SafeLogWarnNoThrow(
                            "PreProcessEvent callback returned false, but ProcessEvent blocking is disabled; continuing original event.");
                    }
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("PreProcessEvent callback threw", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("PreProcessEvent callback threw an unknown exception.");
                }
            }
            return true;
        }
        catch (const std::exception& e)
        {
            if (setupFailed)
                *setupFailed = true;
            SafeLogErrorNoThrow("PreProcessEvent dispatch failed internally; continuing original event", e.what());
            return true;
        }
        catch (...)
        {
            if (setupFailed)
                *setupFailed = true;
            SafeLogErrorNoThrow("PreProcessEvent dispatch failed internally with an unknown exception; continuing original event.");
            return true;
        }
    }

    bool EventManager::TriggerPreProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms)
    {
        bool setupFailed = false;
        if (!TriggerPreProcessEvent(caller, function, parms, &setupFailed))
            return false;
        if (setupFailed)
            return true;

        try
        {
            std::vector<CallbackSnapshot> callbacks;
            std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
            const auto isSnapshotActive = [this](const CallbackSnapshot& snapshot) {
                return snapshot.id != 0 &&
                    std::any_of(m_FilteredPreProcessEventCallbacks.begin(),
                                m_FilteredPreProcessEventCallbacks.end(),
                                [&snapshot](const CallbackRegistration& item) {
                                    return item.id == snapshot.id &&
                                           item.generation == snapshot.generation &&
                                           item.callback == snapshot.callback;
                                });
            };
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                MaybeForceSnapshotFailureForTesting();
                callbacks.reserve(m_FilteredPreProcessEventCallbacks.size());
                for (const auto& item : m_FilteredPreProcessEventCallbacks)
                {
                    if (item.nameIndex == nameIndex)
                        callbacks.push_back({item.id, item.generation, item.callback, item.allowProcessEventBlocking});
                }
            }

            for (const auto& snapshot : callbacks)
            {
                if (!snapshot.callback)
                    continue;
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    if (!isSnapshotActive(snapshot))
                        continue;
                }

                try
                {
                    if (!snapshot.callback(caller, function, parms))
                    {
                        if (snapshot.allowProcessEventBlocking && IsProcessEventBlockingAllowed())
                            return false;
                        SafeLogWarnNoThrow(
                            "Filtered PreProcessEvent callback returned false, but ProcessEvent blocking is disabled; continuing original event.");
                    }
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("Filtered PreProcessEvent callback threw", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("Filtered PreProcessEvent callback threw an unknown exception.");
                }
            }
            return true;
        }
        catch (const std::exception& e)
        {
            SafeLogErrorNoThrow("Filtered PreProcessEvent dispatch failed internally; continuing original event", e.what());
            return true;
        }
        catch (...)
        {
            SafeLogErrorNoThrow(
                "Filtered PreProcessEvent dispatch failed internally with an unknown exception; continuing original event.");
            return true;
        }
    }

    void EventManager::TriggerPostProcessEvent(void* caller, void* function, void* parms)
    {
        TriggerPostProcessEvent(caller, function, parms, nullptr);
    }

    void EventManager::TriggerPostProcessEvent(void* caller, void* function, void* parms, bool* setupFailed)
    {
        try
        {
            if (setupFailed)
                *setupFailed = false;
            std::vector<CallbackSnapshot> callbacks;
            std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
            const auto isSnapshotActive = [this](const CallbackSnapshot& snapshot) {
                return snapshot.id != 0 &&
                    std::any_of(m_PostProcessEventCallbacks.begin(),
                                m_PostProcessEventCallbacks.end(),
                                [&snapshot](const CallbackRegistration& item) {
                                    return item.id == snapshot.id &&
                                           item.generation == snapshot.generation &&
                                           item.callback == snapshot.callback;
                                });
            };
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                MaybeForceSnapshotFailureForTesting();
                callbacks.reserve(m_PostProcessEventCallbacks.size());
                for (const auto& item : m_PostProcessEventCallbacks)
                    callbacks.push_back({item.id, item.generation, item.callback, false});
            }

            for (const auto& snapshot : callbacks)
            {
                if (!snapshot.callback)
                    continue;
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    if (!isSnapshotActive(snapshot))
                        continue;
                }

                try
                {
                    snapshot.callback(caller, function, parms);
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("PostProcessEvent callback threw", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("PostProcessEvent callback threw an unknown exception.");
                }
            }
        }
        catch (const std::exception& e)
        {
            if (setupFailed)
                *setupFailed = true;
            SafeLogErrorNoThrow("PostProcessEvent dispatch failed internally", e.what());
        }
        catch (...)
        {
            if (setupFailed)
                *setupFailed = true;
            SafeLogErrorNoThrow("PostProcessEvent dispatch failed internally with an unknown exception.");
        }
    }

    void EventManager::TriggerPostProcessEvent(int32_t nameIndex, void* caller, void* function, void* parms)
    {
        bool setupFailed = false;
        TriggerPostProcessEvent(caller, function, parms, &setupFailed);
        if (setupFailed)
            return;

        try
        {
            std::vector<CallbackSnapshot> callbacks;
            std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
            const auto isSnapshotActive = [this](const CallbackSnapshot& snapshot) {
                return snapshot.id != 0 &&
                    std::any_of(m_FilteredPostProcessEventCallbacks.begin(),
                                m_FilteredPostProcessEventCallbacks.end(),
                                [&snapshot](const CallbackRegistration& item) {
                                    return item.id == snapshot.id &&
                                           item.generation == snapshot.generation &&
                                           item.callback == snapshot.callback;
                                });
            };
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                MaybeForceSnapshotFailureForTesting();
                callbacks.reserve(m_FilteredPostProcessEventCallbacks.size());
                for (const auto& item : m_FilteredPostProcessEventCallbacks)
                {
                    if (item.nameIndex == nameIndex)
                        callbacks.push_back({item.id, item.generation, item.callback, false});
                }
            }

            for (const auto& snapshot : callbacks)
            {
                if (!snapshot.callback)
                    continue;
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    if (!isSnapshotActive(snapshot))
                        continue;
                }

                try
                {
                    snapshot.callback(caller, function, parms);
                }
                catch (const std::exception& e)
                {
                    SafeLogErrorNoThrow("Filtered PostProcessEvent callback threw", e.what());
                }
                catch (...)
                {
                    SafeLogErrorNoThrow("Filtered PostProcessEvent callback threw an unknown exception.");
                }
            }
        }
        catch (const std::exception& e)
        {
            SafeLogErrorNoThrow("Filtered PostProcessEvent dispatch failed internally", e.what());
        }
        catch (...)
        {
            SafeLogErrorNoThrow(
                "Filtered PostProcessEvent dispatch failed internally with an unknown exception.");
        }
    }
}
