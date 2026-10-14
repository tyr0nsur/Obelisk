#include "PlayerLifecycleDispatcher.h"
#include "GameplayCallbackScope.h"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <string>

namespace Obelisk::Core
{
    namespace
    {
        struct CallbackScope
        {
            PlayerLifecycleDispatcher* Dispatcher;
            void* Owner;
            CallbackScope* Previous;
        };

        thread_local CallbackScope* g_CurrentCallback = nullptr;

        bool IsInsideDispatcherCallback(PlayerLifecycleDispatcher* dispatcher)
        {
            for (auto* frame = g_CurrentCallback; frame; frame = frame->Previous)
                if (frame->Dispatcher == dispatcher)
                    return true;
            return false;
        }

        bool IsInsideOwnerCallback(PlayerLifecycleDispatcher* dispatcher, void* owner)
        {
            for (auto* frame = g_CurrentCallback; frame; frame = frame->Previous)
                if (frame->Dispatcher == dispatcher && frame->Owner == owner)
                    return true;
            return false;
        }

        bool ValidUtf8(std::string_view text)
        {
            if (!text.data())
                return false;
            for (size_t i = 0; i < text.size();)
            {
                const auto first = static_cast<unsigned char>(text[i++]);
                if (first == 0)
                    return false;
                if (first < 0x80)
                    continue;
                size_t continuation = 0;
                uint32_t scalar = 0;
                uint32_t minimum = 0;
                if (first >= 0xc2 && first <= 0xdf)
                    continuation = 1, scalar = first & 0x1f, minimum = 0x80;
                else if (first >= 0xe0 && first <= 0xef)
                    continuation = 2, scalar = first & 0x0f, minimum = 0x800;
                else if (first >= 0xf0 && first <= 0xf4)
                    continuation = 3, scalar = first & 0x07, minimum = 0x10000;
                else
                    return false;
                if (text.size() - i < continuation)
                    return false;
                while (continuation--)
                {
                    const auto next = static_cast<unsigned char>(text[i++]);
                    if ((next & 0xc0) != 0x80)
                        return false;
                    scalar = (scalar << 6) | (next & 0x3f);
                }
                if (scalar < minimum || scalar > 0x10ffff || (scalar >= 0xd800 && scalar <= 0xdfff))
                    return false;
            }
            return true;
        }

        bool ValidObservation(const PlayerLifecycleSnapshot& snapshot)
        {
            constexpr uint64_t requiredQuality = OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED |
                OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED |
                OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD;
            if (snapshot.Sequence == 0 || snapshot.ProcessEpoch == 0 ||
                (snapshot.Flags & ~OBELISK_PLAYER_LIFECYCLE_FLAGS_SUPPORTED_MASK) ||
                (snapshot.Flags & requiredQuality) != requiredQuality)
                return false;
            const bool originalCalled = (snapshot.Flags & OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED) != 0;
            if (snapshot.Kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED)
                return originalCalled;
            if (snapshot.Kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED)
                return !originalCalled;
            return false;
        }
    }

    PlayerLifecycleDispatcher& PlayerLifecycleDispatcher::Get()
    {
        static auto* dispatcher = new PlayerLifecycleDispatcher;
        return *dispatcher;
    }

    void PlayerLifecycleDispatcher::SetAvailable(bool available) noexcept
    {
        m_Available.store(available, std::memory_order_release);
    }

    bool PlayerLifecycleDispatcher::IsAvailable() const noexcept
    {
        return m_Available.load(std::memory_order_acquire);
    }

    uint64_t PlayerLifecycleDispatcher::Register(void* owner, ObeliskPlayerLifecycleCallback callback, void* userData)
    {
        if (!IsAvailable() || !owner || !callback)
            return 0;
        auto registration = std::make_shared<Registration>();
        registration->Owner = owner;
        registration->Callback = callback;
        registration->UserData = userData;
        std::lock_guard lock(m_Mutex);
        if (!IsAvailable() || m_NextRegistrationId == std::numeric_limits<uint64_t>::max())
            return 0;
        registration->Id = m_NextRegistrationId++;
        m_Registrations.push_back(registration);
        return registration->Id;
    }

    void PlayerLifecycleDispatcher::PruneInactiveLocked()
    {
        std::erase_if(m_Registrations, [](const auto& registration) {
            return !registration->Active && registration->InFlight == 0;
        });
    }

    bool PlayerLifecycleDispatcher::HasOwnerInvocationsLocked(void* owner) const
    {
        return std::any_of(m_Registrations.begin(), m_Registrations.end(), [owner](const auto& registration) {
            return registration->Owner == owner && registration->InFlight != 0;
        });
    }

    bool PlayerLifecycleDispatcher::Unregister(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;
        std::unique_lock lock(m_Mutex);
        const auto found = std::find_if(m_Registrations.begin(), m_Registrations.end(), [&](const auto& registration) {
            return registration->Owner == owner && registration->Id == registrationId;
        });
        if (found == m_Registrations.end() || !(*found)->Active)
            return false;
        auto registration = *found;
        registration->Active = false;
        if (!IsInsideDispatcherCallback(this))
            m_Quiescence.wait(lock, [&] { return registration->InFlight == 0; });
        PruneInactiveLocked();
        return true;
    }

    size_t PlayerLifecycleDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;
        std::unique_lock lock(m_Mutex);
        size_t removed = 0;
        for (const auto& registration : m_Registrations)
        {
            if (registration->Owner == owner && registration->Active)
            {
                registration->Active = false;
                ++removed;
            }
        }
        // Cancellation does not permit dlclose on a plugin frame still active
        // here or below a nested callback. A caller must retain the mapping.
        if (IsInsideOwnerCallback(this, owner))
            throw std::logic_error("player lifecycle owner cleanup requires returning from its callback before unload");
        m_Quiescence.wait(lock, [&] { return !HasOwnerInvocationsLocked(owner); });
        PruneInactiveLocked();
        return removed;
    }

    size_t PlayerLifecycleDispatcher::SubscriptionCount() const
    {
        std::lock_guard lock(m_Mutex);
        return std::count_if(m_Registrations.begin(), m_Registrations.end(), [](const auto& registration) {
            return registration->Active;
        });
    }

    void PlayerLifecycleDispatcher::FinishInvocation(const std::shared_ptr<Registration>& registration) noexcept
    {
        {
            std::lock_guard lock(m_Mutex);
            --registration->InFlight;
            PruneInactiveLocked();
        }
        m_Quiescence.notify_all();
    }

    size_t PlayerLifecycleDispatcher::Dispatch(const PlayerLifecycleSnapshot& snapshot) noexcept
    {
        size_t dispatched = 0;
        try
        {
            if (!IsAvailable() || !ValidObservation(snapshot))
                return 0;
            std::vector<std::shared_ptr<Registration>> callbacks;
            {
                std::lock_guard lock(m_Mutex);
                callbacks = m_Registrations;
            }
            if (callbacks.empty())
                return 0;
            uint64_t flags = snapshot.Flags & ~(OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE |
                                               OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE);
            std::string copiedName;
            std::string copiedId;
            const auto copyField = [&](uint64_t flag, std::string_view input, size_t maximum, std::string& copy) {
                if ((snapshot.Flags & flag) && !input.empty() && input.size() <= maximum && ValidUtf8(input))
                {
                    copy.assign(input);
                    flags |= flag;
                }
            };
            copyField(OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE, snapshot.PlayerName,
                      OBELISK_PLAYER_LIFECYCLE_NAME_MAX_BYTES, copiedName);
            copyField(OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE, snapshot.PlatformId,
                      OBELISK_PLAYER_LIFECYCLE_PLATFORM_ID_MAX_BYTES, copiedId);
            const ObeliskPlayerLifecycleEvent event{
                OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION, sizeof(ObeliskPlayerLifecycleEvent), snapshot.Kind, 0,
                flags, snapshot.Sequence, snapshot.ProcessEpoch,
                {(flags & OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE) ? copiedName.data() : nullptr, copiedName.size()},
                {(flags & OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE) ? copiedId.data() : nullptr, copiedId.size()}};
            for (const auto& registration : callbacks)
            {
                {
                    std::lock_guard lock(m_Mutex);
                    if (!registration->Active || !IsAvailable())
                        continue;
                    ++registration->InFlight;
                }
                CallbackScope invocation{this, registration->Owner, g_CurrentCallback};
                g_CurrentCallback = &invocation;
                try
                {
                    GameplayCallbackScope callbackScope(GameplayCallbackFamily::PlayerLifecycle);
                    registration->Callback(&event, registration->UserData);
                    ++dispatched;
                }
                catch (...)
                {
                    // A plugin failure cannot strand owner cleanup or escape to UE.
                }
                g_CurrentCallback = invocation.Previous;
                FinishInvocation(registration);
            }
        }
        catch (...)
        {
            // Optional observation failure must not change the original game call.
        }
        return dispatched;
    }
}
