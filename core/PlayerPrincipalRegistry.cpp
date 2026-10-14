#include "PlayerPrincipalRegistry.h"

#include <atomic>
#include <limits>

namespace Obelisk::Core
{
    namespace
    {
        constexpr uint64_t kInitialGeneration = 1;
        constexpr PlayerPrincipalInvalidationFlags kKnownInvalidationReasons =
            PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Logout) |
            PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Reconnect) |
            PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::RuntimeReset) |
            PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Superseded);

        bool HasOnlyKnownInvalidationReasons(PlayerPrincipalInvalidationFlags reasons)
        {
            return reasons != 0 && (reasons & ~kKnownInvalidationReasons) == 0;
        }

        bool CanReactivateAfterInvalidation(PlayerPrincipalInvalidationFlags reasons)
        {
            constexpr PlayerPrincipalInvalidationFlags kReconnectSafeInvalidationReasons =
                PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Logout) |
                PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Reconnect);
            constexpr PlayerPrincipalInvalidationFlags kRequiredReconnectReason =
                PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Reconnect);

            return (reasons & kRequiredReconnectReason) != 0 &&
                (reasons & ~kReconnectSafeInvalidationReasons) == 0;
        }

        bool IsRetiredSequenceOlder(uint64_t candidate, uint64_t currentOldest)
        {
            if (candidate == currentOldest)
                return false;

            // The retained window is bounded far below half the counter range, so
            // modular ordering preserves FIFO pruning across sequence wrap.
            constexpr uint64_t kHalfRetiredSequenceRange = uint64_t{1} << 63;
            return currentOldest - candidate < kHalfRetiredSequenceRange;
        }

        uint64_t AllocateRegistryId()
        {
            static auto* nextRegistryId = new std::atomic<uint64_t>(1);
            uint64_t current = nextRegistryId->load(std::memory_order_relaxed);
            while (current != 0)
            {
                const uint64_t candidate = current;
                const uint64_t next =
                    candidate == std::numeric_limits<uint64_t>::max() ? 0 : candidate + 1;
                if (nextRegistryId->compare_exchange_weak(current,
                                                          next,
                                                          std::memory_order_relaxed,
                                                          std::memory_order_relaxed))
                {
                    return candidate;
                }
            }
            return 0;
        }
    }

    PlayerPrincipalRegistry::PlayerPrincipalRegistry()
        : m_RegistryId(AllocateRegistryId())
    {
    }

    PlayerPrincipalRegistry& PlayerPrincipalRegistry::Get()
    {
        static auto* registry = new PlayerPrincipalRegistry();
        return *registry;
    }

    uint64_t PlayerPrincipalRegistry::AllocateHandleLocked()
    {
        while (m_NextHandle != 0)
        {
            const uint64_t candidate = m_NextHandle;
            if (m_NextHandle == std::numeric_limits<uint64_t>::max())
                m_NextHandle = 0;
            else
                ++m_NextHandle;

            if (candidate != 0 && candidate > m_HighWaterHandle &&
                m_Principals.find(candidate) == m_Principals.end())
            {
                m_HighWaterHandle = candidate;
                return candidate;
            }
        }

        return 0;
    }

    uint64_t PlayerPrincipalRegistry::AllocateRetiredSequenceLocked()
    {
        if (m_NextRetiredSequence == 0)
            m_NextRetiredSequence = 1;

        const uint64_t sequence = m_NextRetiredSequence;
        if (m_NextRetiredSequence == std::numeric_limits<uint64_t>::max())
            m_NextRetiredSequence = 1;
        else
            ++m_NextRetiredSequence;
        return sequence;
    }

    void PlayerPrincipalRegistry::PruneRetainedInvalidatedPrincipalsLocked()
    {
        while (m_RetainedInvalidatedCount > m_MaxRetainedInvalidatedPrincipals)
        {
            auto oldest = m_Principals.end();
            for (auto it = m_Principals.begin(); it != m_Principals.end(); ++it)
            {
                if (it->second.Live)
                    continue;
                if (oldest == m_Principals.end() ||
                    IsRetiredSequenceOlder(it->second.RetiredSequence,
                                           oldest->second.RetiredSequence))
                {
                    oldest = it;
                }
            }

            if (oldest == m_Principals.end())
            {
                m_RetainedInvalidatedCount = 0;
                return;
            }

            m_Principals.erase(oldest);
            --m_RetainedInvalidatedCount;
        }
    }

    PlayerPrincipalToken PlayerPrincipalRegistry::AllocatePrincipal()
    {
        if (m_RegistryId == 0)
            return {};

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t handle = AllocateHandleLocked();
        if (handle == 0)
            return {};

        const auto insertResult =
            m_Principals.emplace(handle,
                                 PrincipalEntry{
                                     .Generation = kInitialGeneration,
                                     .InvalidationReasons = 0,
                                     .Live = true,
                                 });
        if (!insertResult.second)
            return {};
        ++m_LiveCount;
        return {handle, kInitialGeneration, m_RegistryId};
    }

    PlayerPrincipalToken PlayerPrincipalRegistry::ReactivatePrincipal(
        const PlayerPrincipalToken& token)
    {
        if (!token.HasValidShape())
            return {};
        if (token.RegistryId != m_RegistryId || m_RegistryId == 0)
            return {};

        std::lock_guard<std::mutex> lock(m_Mutex);
        auto it = m_Principals.find(token.Handle);
        if (it == m_Principals.end() || it->second.Live ||
            it->second.Generation == 0 ||
            it->second.Generation != token.Generation ||
            it->second.Generation == std::numeric_limits<uint64_t>::max() ||
            m_RetainedInvalidatedCount == 0 ||
            !CanReactivateAfterInvalidation(it->second.InvalidationReasons))
        {
            return {};
        }

        ++it->second.Generation;
        it->second.InvalidationReasons = 0;
        it->second.RetiredSequence = 0;
        it->second.Live = true;
        if (m_RetainedInvalidatedCount > 0)
            --m_RetainedInvalidatedCount;
        ++m_LiveCount;
        return {token.Handle, it->second.Generation, m_RegistryId};
    }

    bool PlayerPrincipalRegistry::InvalidatePrincipal(const PlayerPrincipalToken& token,
                                                      PlayerPrincipalInvalidationFlags reasons)
    {
        if (!token.HasValidShape() || !HasOnlyKnownInvalidationReasons(reasons))
            return false;
        if (token.RegistryId != m_RegistryId)
            return false;

        std::lock_guard<std::mutex> lock(m_Mutex);
        auto it = m_Principals.find(token.Handle);
        if (it == m_Principals.end() || !it->second.Live ||
            it->second.Generation != token.Generation)
            return false;
        if (m_LiveCount == 0 ||
            m_RetainedInvalidatedCount == std::numeric_limits<size_t>::max())
        {
            return false;
        }

        it->second.Live = false;
        it->second.InvalidationReasons = reasons;
        it->second.RetiredSequence = AllocateRetiredSequenceLocked();
        --m_LiveCount;
        ++m_RetainedInvalidatedCount;
        PruneRetainedInvalidatedPrincipalsLocked();
        return true;
    }

    bool PlayerPrincipalRegistry::LogoutPrincipal(const PlayerPrincipalToken& token)
    {
        return InvalidatePrincipal(
            token,
            PlayerPrincipalInvalidationFlag(PlayerPrincipalInvalidationReason::Logout));
    }

    PlayerPrincipalLookup PlayerPrincipalRegistry::Lookup(const PlayerPrincipalToken& token) const
    {
        PlayerPrincipalLookup result;
        result.Handle = token.Handle;
        result.RequestedGeneration = token.Generation;
        result.RequestedRegistryId = token.RegistryId;
        result.CurrentRegistryId = m_RegistryId;

        if (token.Handle == 0)
        {
            result.Status = PlayerPrincipalLookupStatus::ZeroHandle;
            return result;
        }

        if (token.Generation == 0)
        {
            result.Status = PlayerPrincipalLookupStatus::ZeroGeneration;
            return result;
        }

        if (token.RegistryId == 0)
        {
            result.Status = PlayerPrincipalLookupStatus::ZeroRegistryId;
            return result;
        }

        if (token.RegistryId != m_RegistryId)
        {
            result.Status = PlayerPrincipalLookupStatus::RegistryMismatch;
            return result;
        }

        std::lock_guard<std::mutex> lock(m_Mutex);
        const auto it = m_Principals.find(token.Handle);
        if (it == m_Principals.end())
        {
            result.Status = PlayerPrincipalLookupStatus::UnknownHandle;
            return result;
        }

        result.CurrentGeneration = it->second.Generation;
        result.InvalidationReasons = it->second.InvalidationReasons;
        result.Live = it->second.Live;

        if (token.Generation != it->second.Generation)
        {
            result.Status = PlayerPrincipalLookupStatus::StaleGeneration;
            return result;
        }

        result.Status = it->second.Live
            ? PlayerPrincipalLookupStatus::Valid
            : PlayerPrincipalLookupStatus::Invalidated;
        return result;
    }

    bool PlayerPrincipalRegistry::Validate(const PlayerPrincipalToken& token) const
    {
        return Lookup(token).IsValid();
    }

    size_t PlayerPrincipalRegistry::LiveCount() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return m_LiveCount;
    }

    size_t PlayerPrincipalRegistry::RetainedInvalidatedCount() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return m_RetainedInvalidatedCount;
    }

#ifdef OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS
    void PlayerPrincipalRegistry::SetNextHandleForTesting(uint64_t nextHandle)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextHandle = nextHandle;
    }

    void PlayerPrincipalRegistry::SetNextRetiredSequenceForTesting(uint64_t nextSequence)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRetiredSequence = nextSequence == 0 ? 1 : nextSequence;
    }

    void PlayerPrincipalRegistry::SetMaxRetainedInvalidatedPrincipalsForTesting(size_t maxRetained)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_MaxRetainedInvalidatedPrincipals = maxRetained;
        PruneRetainedInvalidatedPrincipalsLocked();
    }

    bool PlayerPrincipalRegistry::SetGenerationForTesting(uint64_t handle, uint64_t generation)
    {
        if (handle == 0 || generation == 0)
            return false;

        std::lock_guard<std::mutex> lock(m_Mutex);
        auto it = m_Principals.find(handle);
        if (it == m_Principals.end())
            return false;

        it->second.Generation = generation;
        return true;
    }
#endif
}
